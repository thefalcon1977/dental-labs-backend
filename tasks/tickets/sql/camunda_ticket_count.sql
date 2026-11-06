DROP FUNCTION IF EXISTS public.camunda_ticket_count(
    text, text, text, text,
    text[], text[], text[], text[],
    timestamptz, timestamptz, timestamptz, timestamptz,
    text[], text[], text[]
);

CREATE OR REPLACE FUNCTION public.camunda_ticket_count(
    ticket_type text DEFAULT NULL,
    ticket_number text DEFAULT NULL,
    ticket_title text DEFAULT NULL,
    ticket_status text DEFAULT NULL,
    creator_list text[] DEFAULT NULL,
    processor_list text[] DEFAULT NULL,
    assignee_list text[] DEFAULT NULL,
    phase_list text[] DEFAULT NULL,
    start_time_from timestamptz DEFAULT NULL,
    start_time_to timestamptz DEFAULT NULL,
    end_time_from timestamptz DEFAULT NULL,
    end_time_to timestamptz DEFAULT NULL,
    pending_basket_ids text[] DEFAULT NULL,
    processed_by_basket_ids text[] DEFAULT NULL,
    user_basket_ids text[] DEFAULT NULL
)
RETURNS bigint
LANGUAGE plpgsql
STABLE
SET jit = off
AS $$
DECLARE
    v_count bigint;
    v_status_list text[];
BEGIN
    -- Parse status list once per function call
    IF ticket_status IS NULL OR ticket_status = '' THEN
        v_status_list := NULL;
    ELSE
        SELECT array_agg(trim(s))
        INTO v_status_list
        FROM unnest(string_to_array(ticket_status, ',')) AS s
        WHERE trim(s) <> '';
        IF v_status_list IS NULL OR cardinality(v_status_list) = 0 THEN
            v_status_list := NULL;
        END IF;
    END IF;

    -- Fast path: only cheap/base filters
    IF ticket_title IS NULL
       AND processor_list IS NULL
       AND assignee_list IS NULL
       AND phase_list IS NULL
       AND pending_basket_ids IS NULL
       AND processed_by_basket_ids IS NULL
       AND user_basket_ids IS NULL
    THEN
        SELECT COUNT(*)
        INTO v_count
        FROM act_hi_procinst ahp
        JOIN act_re_procdef arp
          ON arp.id_ = ahp.proc_def_id_
        WHERE (v_status_list IS NULL OR ahp.state_ = ANY (v_status_list))
          -- Camunda stores timestamps as `timestamp` (no tz). In this deployment they
          -- represent Asia/Tehran wall-time. Interpret them accordingly before comparing
          -- against timestamptz inputs to avoid session-timezone shifts.
          AND (
              start_time_from IS NULL
              OR (ahp.start_time_ AT TIME ZONE 'Asia/Tehran') >= start_time_from
          )
          AND (
              start_time_to IS NULL
              OR (ahp.start_time_ AT TIME ZONE 'Asia/Tehran') <= start_time_to
          )
          AND (
              end_time_from IS NULL
              OR (ahp.end_time_ AT TIME ZONE 'Asia/Tehran') >= end_time_from
          )
          AND (
              end_time_to IS NULL
              OR (ahp.end_time_ AT TIME ZONE 'Asia/Tehran') <= end_time_to
          )
          AND (creator_list IS NULL OR ahp.start_user_id_ = ANY (creator_list))
          AND (ticket_number IS NULL OR ahp.business_key_ ILIKE '%' || ticket_number || '%')
          AND (ticket_type   IS NULL OR arp.name_       ILIKE '%' || ticket_type   || '%');

        RETURN v_count;
    END IF;

    -- Full path: keep base small, then use targeted EXISTS
    WITH base_procinst AS (
        SELECT
            ahp.id_,
            ahp.proc_inst_id_,
            ahp.start_user_id_
        FROM act_hi_procinst ahp
        JOIN act_re_procdef arp
          ON arp.id_ = ahp.proc_def_id_
        WHERE (v_status_list IS NULL OR ahp.state_ = ANY (v_status_list))
          -- Camunda stores timestamps as `timestamp` (no tz). In this deployment they
          -- represent Asia/Tehran wall-time. Interpret them accordingly before comparing
          -- against timestamptz inputs to avoid session-timezone shifts.
          AND (
              start_time_from IS NULL
              OR (ahp.start_time_ AT TIME ZONE 'Asia/Tehran') >= start_time_from
          )
          AND (
              start_time_to IS NULL
              OR (ahp.start_time_ AT TIME ZONE 'Asia/Tehran') <= start_time_to
          )
          AND (
              end_time_from IS NULL
              OR (ahp.end_time_ AT TIME ZONE 'Asia/Tehran') >= end_time_from
          )
          AND (
              end_time_to IS NULL
              OR (ahp.end_time_ AT TIME ZONE 'Asia/Tehran') <= end_time_to
          )
          AND (creator_list IS NULL OR ahp.start_user_id_ = ANY (creator_list))
          AND (ticket_number IS NULL OR ahp.business_key_ ILIKE '%' || ticket_number || '%')
          AND (ticket_type   IS NULL OR arp.name_       ILIKE '%' || ticket_type   || '%')
    )
    SELECT COUNT(*)
    INTO v_count
    FROM base_procinst b
    WHERE
        -- title
        (
            ticket_title IS NULL
            OR EXISTS (
                SELECT 1
                FROM act_ru_execution_titles t
                WHERE t.execution_id_ = b.proc_inst_id_
                  AND t.instance_title_ ILIKE '%' || ticket_title || '%'
            )
        )
        -- processor (active task role)
        AND (
            processor_list IS NULL
            OR EXISTS (
                SELECT 1
                FROM act_hi_taskinst aht
                WHERE aht.proc_inst_id_ = b.id_
                  AND aht.end_time_ IS NULL
                  AND (
                      aht.assignee_ = ANY(processor_list)
                      OR EXISTS (
                          SELECT 1
                          FROM act_hi_identitylink ahi
                          WHERE ahi.task_id_ = aht.id_
                            AND (
                                ahi.user_id_ = ANY(processor_list)
                                OR ahi.group_id_ = ANY(processor_list)
                            )
                      )
                  )
            )
        )
        -- assignee (active task role)
        AND (
            assignee_list IS NULL
            OR EXISTS (
                SELECT 1
                FROM act_hi_taskinst aht
                WHERE aht.proc_inst_id_ = b.id_
                  AND aht.end_time_ IS NULL
                  AND (
                      aht.assignee_ = ANY(assignee_list)
                      OR EXISTS (
                          SELECT 1
                          FROM act_hi_identitylink ahi
                          WHERE ahi.task_id_ = aht.id_
                            AND (
                                ahi.user_id_ = ANY(assignee_list)
                                OR ahi.group_id_ = ANY(assignee_list)
                            )
                      )
                  )
            )
        )
        -- phase
        AND (
            phase_list IS NULL
            OR EXISTS (
                SELECT 1
                FROM act_hi_actinst p
                WHERE p.proc_inst_id_ = b.id_
                  AND p.end_time_ IS NULL
                  AND p.act_name_ = ANY(phase_list)
            )
        )
        -- pending (active)
        AND (
            pending_basket_ids IS NULL
            OR EXISTS (
                SELECT 1
                FROM act_hi_taskinst aht
                WHERE aht.proc_inst_id_ = b.id_
                  AND aht.end_time_ IS NULL
                  AND (
                      aht.assignee_ = ANY(pending_basket_ids)
                      OR EXISTS (
                          SELECT 1
                          FROM act_hi_identitylink ahi
                          WHERE ahi.task_id_ = aht.id_
                            AND (
                                ahi.user_id_ = ANY(pending_basket_ids)
                                OR ahi.group_id_ = ANY(pending_basket_ids)
                            )
                      )
                  )
            )
        )
        -- processed_by (completed)
        AND (
            processed_by_basket_ids IS NULL
            OR EXISTS (
                SELECT 1
                FROM act_hi_taskinst aht
                WHERE aht.proc_inst_id_ = b.id_
                  AND aht.end_time_ IS NOT NULL
                  AND (aht.delete_reason_ IS NULL OR aht.delete_reason_ = 'completed')
                  AND (
                      aht.assignee_ = ANY(processed_by_basket_ids)
                      OR EXISTS (
                          SELECT 1
                          FROM act_hi_identitylink ahi
                          WHERE ahi.task_id_ = aht.id_
                            AND (
                                ahi.user_id_ = ANY(processed_by_basket_ids)
                                OR ahi.group_id_ = ANY(processed_by_basket_ids)
                            )
                      )
                  )
            )
        )
        -- permissions
        AND (
            user_basket_ids IS NULL
            OR b.start_user_id_ = ANY(user_basket_ids)
            OR EXISTS (
                SELECT 1
                FROM act_hi_taskinst aht
                WHERE aht.proc_inst_id_ = b.id_
                  AND (
                      aht.assignee_ = ANY(user_basket_ids)
                      OR EXISTS (
                          SELECT 1
                          FROM act_hi_identitylink ahi
                          WHERE ahi.task_id_ = aht.id_
                            AND (
                                ahi.user_id_ = ANY(user_basket_ids)
                                OR ahi.group_id_ = ANY(user_basket_ids)
                            )
                      )
                  )
            )
        );

    RETURN v_count;
END;
$$;
