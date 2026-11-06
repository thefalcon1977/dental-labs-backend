create function public.camunda_ticket_details(proc_inst_ids text[])
    returns TABLE(ticket_uid text, ticket_title text, ticket_number text, ticket_type text, ticket_status text, current_phases text, current_processors text, creator text, duration bigint, create_time timestamp with time zone, end_time timestamp with time zone)
    stable
    language sql
as
$$
    WITH phase_agg AS (
        SELECT aht.proc_inst_id_,
               STRING_AGG(DISTINCT aht.name_, ', ') AS current_phases
        FROM act_hi_taskinst aht
        WHERE aht.proc_inst_id_ = ANY(proc_inst_ids)
          AND aht.end_time_ IS NULL
        GROUP BY aht.proc_inst_id_
    ),
    processor_agg AS (
        SELECT
            proc_inst_id_,
            STRING_AGG(processor, ', ' ORDER BY processor) AS current_processors
        FROM (
            SELECT DISTINCT
                proc_inst_id_,
                processor
            FROM (
                SELECT
                    aht.proc_inst_id_,
                    NULLIF(BTRIM(aht.assignee_), '') AS processor
                FROM act_hi_taskinst aht
                WHERE aht.proc_inst_id_ = ANY(proc_inst_ids)
                  AND aht.end_time_ IS NULL
                UNION ALL
                SELECT
                    aht.proc_inst_id_,
                    NULLIF(BTRIM(ahi.user_id_), '') AS processor
                FROM act_hi_taskinst aht
                JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                WHERE aht.proc_inst_id_ = ANY(proc_inst_ids)
                  AND aht.end_time_ IS NULL
                  AND ahi.type_ = 'candidate'
                UNION ALL
                SELECT
                    aht.proc_inst_id_,
                    NULLIF(BTRIM(ahi.group_id_), '') AS processor
                FROM act_hi_taskinst aht
                JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                WHERE aht.proc_inst_id_ = ANY(proc_inst_ids)
                  AND aht.end_time_ IS NULL
                  AND ahi.type_ = 'candidate'
            ) normalized_processors
            WHERE processor IS NOT NULL
        ) processors
        GROUP BY proc_inst_id_
    )
    SELECT
        ahp.id_ AS ticket_uid,
        arpt.instance_title_ AS ticket_title,
        ahp.business_key_ AS ticket_number,
        arp.name_ AS ticket_type,
        CASE
            WHEN ahp.end_time_ IS NULL
                 AND ahp.state_ = 'suspended'
            THEN 'SUSPENDED'
            WHEN ahp.end_time_ IS NULL
            THEN 'ACTIVE'
            WHEN ahp.end_time_ IS NOT NULL AND ahp.delete_reason_ IS NULL
            THEN 'COMPLETED'
            WHEN ahp.end_time_ IS NOT NULL
                 AND ahp.delete_reason_ IS NOT NULL
                 AND ahp.delete_reason_ NOT ILIKE '%terminated%'
                 AND ahp.delete_reason_ NOT ILIKE '%termination%'
            THEN 'CANCELLED'
            WHEN ahp.end_time_ IS NOT NULL
                 AND (
                     ahp.delete_reason_ ILIKE '%terminated%'
                     OR ahp.delete_reason_ ILIKE '%termination%'
                 )
            THEN 'EXTERNALLY_TERMINATED'
            ELSE 'COMPLETED'
        END AS ticket_status,
        phase_agg.current_phases,
        processor_agg.current_processors,
        ahp.start_user_id_ AS creator,
        CASE
            WHEN ahp.end_time_ IS NULL
            THEN EXTRACT(
                EPOCH FROM (NOW() - (ahp.start_time_ AT TIME ZONE 'Asia/Tehran'))
            ) * 1000
            ELSE ahp.duration_
        END AS duration,
        (ahp.start_time_ AT TIME ZONE 'Asia/Tehran') AS create_time,
        (ahp.end_time_ AT TIME ZONE 'Asia/Tehran') AS end_time
    FROM act_hi_procinst ahp
    LEFT JOIN act_re_procdef arp ON arp.id_ = ahp.proc_def_id_
    LEFT JOIN act_ru_execution_titles arpt ON arpt.execution_id_ = ahp.proc_inst_id_
    LEFT JOIN phase_agg ON phase_agg.proc_inst_id_ = ahp.id_
    LEFT JOIN processor_agg ON processor_agg.proc_inst_id_ = ahp.id_
    WHERE ahp.proc_inst_id_ = ANY(proc_inst_ids)
    ORDER BY array_position(proc_inst_ids, ahp.proc_inst_id_);
$$;

alter function public.camunda_ticket_details(text[]) owner to camunda;
