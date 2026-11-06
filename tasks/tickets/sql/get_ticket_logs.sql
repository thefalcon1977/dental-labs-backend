create or replace function public.get_ticket_logs(p_proc_inst_id text, p_has_end_time boolean DEFAULT NULL::boolean, p_user_id text DEFAULT NULL::text, p_group_ids text[] DEFAULT NULL::text[])
    returns TABLE(id_ text, task_id text, ticket_id text, process_def_deployment_id text, phase_name text, operator text, operation_mode text, current_processors text[], create_time timestamp with time zone, operation_time timestamp with time zone, task_duration bigint, sequence_counter bigint)
    stable
    language sql
as
$$
    WITH current_proc AS (
        SELECT
            aht.proc_inst_id_,
            array_agg(
                DISTINCT NULLIF(COALESCE(aht.assignee_, ahi.user_id_, ahi.group_id_, ''), '')
                ORDER BY NULLIF(COALESCE(aht.assignee_, ahi.user_id_, ahi.group_id_, ''), '')
            ) AS current_processors
        FROM act_hi_taskinst aht
        LEFT JOIN act_hi_identitylink ahi
            ON ahi.task_id_ = aht.id_
        WHERE aht.proc_inst_id_ = p_proc_inst_id
          AND aht.end_time_ IS NULL
          AND (
                aht.assignee_ IS NOT NULL
                OR (ahi.type_ = 'candidate' AND (ahi.user_id_ IS NOT NULL OR ahi.group_id_ IS NOT NULL))
              )
        GROUP BY aht.proc_inst_id_
    )
    SELECT
        aha.id_ AS id_,
        aha.task_id_ AS task_id,
        aha.proc_inst_id_ AS ticket_id,
        arp.deployment_id_ AS process_def_deployment_id,
        aha.act_name_ AS phase_name,
        CASE
            WHEN aha.act_type_ = 'startEvent' THEN ahp.start_user_id_
            ELSE aha.assignee_
        END AS operator,
        om.operation_mode AS operation_mode,
        COALESCE(cp.current_processors, ARRAY[]::text[]) AS current_processors,
        aha.start_time_ AS create_time,
        aha.end_time_ AS operation_time,
        aha.duration_ AS task_duration,
        aha.sequence_counter_ AS sequence_counter
    FROM act_hi_actinst aha
    LEFT JOIN act_hi_procinst ahp
        ON ahp.proc_inst_id_ = aha.proc_inst_id_
    LEFT JOIN act_re_procdef arp
        ON arp.id_ = aha.proc_def_id_
    LEFT JOIN LATERAL (
        SELECT
            COALESCE(ahd.text_, ahd.text2_) AS operation_mode
        FROM act_hi_detail ahd
        WHERE ahd.proc_inst_id_ = aha.proc_inst_id_
          AND ahd.act_inst_id_ = aha.id_
          AND ahd.name_ = 'operation_mode'
        ORDER BY ahd.time_ DESC NULLS LAST, ahd.sequence_counter_ DESC NULLS LAST
        LIMIT 1
    ) om
        ON TRUE
    LEFT JOIN current_proc cp
        ON cp.proc_inst_id_ = aha.proc_inst_id_
    WHERE aha.proc_inst_id_ = p_proc_inst_id
      AND aha.act_type_ IN ('startEvent', 'userTask')
      AND (
            -- If no filter requested, include:
            -- - all completed rows
            -- - active rows ONLY if caller is allowed (assignee/candidate user/group)
            (
                p_has_end_time IS NULL
                AND (
                    aha.end_time_ IS NOT NULL
                    OR (
                        aha.end_time_ IS NULL
                        AND (p_user_id IS NOT NULL OR p_group_ids IS NOT NULL)
                        AND EXISTS (
                            SELECT 1
                            FROM act_hi_taskinst aht
                            LEFT JOIN act_hi_identitylink ahi
                                ON ahi.task_id_ = aht.id_
                            WHERE aht.proc_inst_id_ = p_proc_inst_id
                              AND aht.end_time_ IS NULL
                              AND (
                                    (p_user_id IS NOT NULL AND aht.assignee_ = p_user_id)
                                    OR (
                                        ahi.type_ = 'candidate'
                                        AND (
                                            (p_user_id IS NOT NULL AND ahi.user_id_ = p_user_id)
                                            OR (p_group_ids IS NOT NULL AND ahi.group_id_ = ANY(p_group_ids))
                                        )
                                    )
                                  )
                        )
                    )
                )
            )
            OR (p_has_end_time = TRUE  AND aha.end_time_ IS NOT NULL)
            OR (
                p_has_end_time = FALSE
                AND aha.end_time_ IS NULL
                AND (p_user_id IS NOT NULL OR p_group_ids IS NOT NULL)
                AND EXISTS (
                    SELECT 1
                    FROM act_hi_taskinst aht
                    LEFT JOIN act_hi_identitylink ahi
                        ON ahi.task_id_ = aht.id_
                    WHERE aht.proc_inst_id_ = p_proc_inst_id
                      AND aht.end_time_ IS NULL
                      AND (
                            (p_user_id IS NOT NULL AND aht.assignee_ = p_user_id)
                            OR (
                                ahi.type_ = 'candidate'
                                AND (
                                    (p_user_id IS NOT NULL AND ahi.user_id_ = p_user_id)
                                    OR (p_group_ids IS NOT NULL AND ahi.group_id_ = ANY(p_group_ids))
                                )
                            )
                          )
                )
            )
          )
    ORDER BY aha.sequence_counter_;
$$;

alter function public.get_ticket_logs(text, boolean, text, text[]) owner to camunda;
