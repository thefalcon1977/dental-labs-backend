-- Fix Camunda ticket timestamp timezone interpretation.
--
-- Camunda stores `start_time_` / `end_time_` as `timestamp` (no tz) but the
-- application treats them as UTC wall-time. If Postgres implicitly casts these
-- values to timestamptz using the session timezone, API responses can appear
-- offset by a few hours.
--
-- This migration updates the ticket list SQL functions to explicitly interpret
-- Camunda timestamps as UTC when returning `create_time` / `end_time` and when
-- calculating durations.

CREATE OR REPLACE FUNCTION public.camunda_ticket_details(proc_inst_ids text[])
    RETURNS TABLE(
        ticket_uid text,
        ticket_title text,
        ticket_number text,
        ticket_type text,
        ticket_status text,
        current_phases text,
        current_processors text,
        creator text,
        duration bigint,
        create_time timestamp with time zone,
        end_time timestamp with time zone
    )
    STABLE
    LANGUAGE sql
AS
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
                EPOCH FROM ((NOW() AT TIME ZONE 'UTC') - ahp.start_time_)
            ) * 1000
            ELSE ahp.duration_
        END AS duration,
        (ahp.start_time_ AT TIME ZONE 'UTC') AS create_time,
        (ahp.end_time_ AT TIME ZONE 'UTC') AS end_time
    FROM act_hi_procinst ahp
    LEFT JOIN act_re_procdef arp ON arp.id_ = ahp.proc_def_id_
    LEFT JOIN act_ru_execution_titles arpt ON arpt.execution_id_ = ahp.proc_inst_id_
    LEFT JOIN phase_agg ON phase_agg.proc_inst_id_ = ahp.id_
    LEFT JOIN processor_agg ON processor_agg.proc_inst_id_ = ahp.id_
    WHERE ahp.proc_inst_id_ = ANY(proc_inst_ids)
    ORDER BY array_position(proc_inst_ids, ahp.proc_inst_id_);
$$;

ALTER FUNCTION public.camunda_ticket_details(text[]) OWNER TO camunda;


CREATE OR REPLACE FUNCTION public.camunda_ticket_export_rows(
    ticket_type text DEFAULT NULL::text,
    ticket_number text DEFAULT NULL::text,
    ticket_title text DEFAULT NULL::text,
    ticket_status text DEFAULT NULL::text,
    creator_list text[] DEFAULT NULL::text[],
    processor_list text[] DEFAULT NULL::text[],
    assignee_list text[] DEFAULT NULL::text[],
    phase_list text[] DEFAULT NULL::text[],
    start_time_from timestamp with time zone DEFAULT NULL::timestamp with time zone,
    start_time_to timestamp with time zone DEFAULT NULL::timestamp with time zone,
    end_time_from timestamp with time zone DEFAULT NULL::timestamp with time zone,
    end_time_to timestamp with time zone DEFAULT NULL::timestamp with time zone,
    pending_basket_ids text[] DEFAULT NULL::text[],
    processed_by_basket_ids text[] DEFAULT NULL::text[],
    user_basket_ids text[] DEFAULT NULL::text[],
    limit_count integer DEFAULT 1000,
    last_seen_id text DEFAULT NULL::text
)
    RETURNS TABLE(
        ticket_uid text,
        ticket_title text,
        ticket_number text,
        ticket_type text,
        ticket_status text,
        current_phases text,
        current_processors text,
        creator text,
        duration bigint,
        create_time timestamp with time zone,
        end_time timestamp with time zone
    )
    STABLE
    LANGUAGE sql
AS
$$
    WITH base AS (
        SELECT
            ahp.id_,
            ahp.proc_inst_id_,
            ahp.business_key_,
            ahp.proc_def_id_,
            ahp.state_,
            ahp.start_user_id_,
            ahp.start_time_,
            ahp.end_time_,
            ahp.duration_,
            ahp.delete_reason_
        FROM act_hi_procinst ahp
        WHERE 1 = 1
          -- Text filters
          AND (
              ticket_type IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM act_re_procdef arp
                  WHERE arp.id_ = ahp.proc_def_id_
                    AND arp.name_ ILIKE '%' || ticket_type || '%'
              )
          )
          AND (ticket_number IS NULL OR ahp.business_key_ ILIKE '%' || ticket_number || '%')
          AND (
              ticket_title IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM act_ru_execution_titles arpt
                  WHERE arpt.execution_id_ = ahp.id_
                    AND arpt.instance_title_ ILIKE '%' || ticket_title || '%'
              )
          )

          -- Creator
          AND (creator_list IS NULL OR ahp.start_user_id_ = ANY(creator_list))

          -- Status (comma-separated for multiple)
          AND (
              ticket_status IS NULL
              OR ticket_status = ''
              OR ahp.state_ IN (
                  SELECT trim(s)
                  FROM unnest(string_to_array(ticket_status, ',')) AS s
                  WHERE trim(s) != ''
              )
          )

          -- Processor filter
          AND (
              processor_list IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND aht.assignee_ = ANY(processor_list)
              )
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND ahi.type_ = 'candidate'
                    AND (
                        ahi.user_id_ = ANY(processor_list)
                        OR ahi.group_id_ = ANY(processor_list)
                    )
              )
          )

          -- Assignee filter (supports empty string)
          AND (
              assignee_list IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND (
                        aht.assignee_ = ANY(assignee_list)
                        OR (
                            '' = ANY(assignee_list)
                            AND (aht.assignee_ IS NULL OR aht.assignee_ = '')
                        )
                    )
              )
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND ahi.type_ = 'candidate'
                    AND (
                        ahi.user_id_ = ANY(assignee_list)
                        OR ahi.group_id_ = ANY(assignee_list)
                    )
              )
          )

          -- Phase filter
          AND (
              phase_list IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_actinst aai
                  WHERE aai.proc_inst_id_ = ahp.id_
                    AND aai.end_time_ IS NULL
                    AND aai.act_name_ = ANY(phase_list)
              )
          )

          -- Time range filters
          -- Camunda stores timestamps as `timestamp` (UTC wall-time). Interpret them as UTC
          -- before comparing against timestamptz inputs to avoid session-timezone shifts.
          AND (
              start_time_from IS NULL
              OR (ahp.start_time_ AT TIME ZONE 'UTC') >= start_time_from
          )
          AND (
              start_time_to IS NULL
              OR (ahp.start_time_ AT TIME ZONE 'UTC') <= start_time_to
          )
          AND (
              end_time_from IS NULL
              OR (ahp.end_time_ AT TIME ZONE 'UTC') >= end_time_from
          )
          AND (
              end_time_to IS NULL
              OR (ahp.end_time_ AT TIME ZONE 'UTC') <= end_time_to
          )

          -- Pending filter (active tasks only)
          AND (
              pending_basket_ids IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND aht.assignee_ = ANY(pending_basket_ids)
              )
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND ahi.type_ = 'candidate'
                    AND (
                        ahi.user_id_ = ANY(pending_basket_ids)
                        OR ahi.group_id_ = ANY(pending_basket_ids)
                    )
              )
          )

          -- Processed by filter (completed tasks only)
          AND (
              processed_by_basket_ids IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NOT NULL
                    AND (aht.delete_reason_ IS NULL OR aht.delete_reason_ = 'completed')
                    AND aht.assignee_ = ANY(processed_by_basket_ids)
              )
              OR EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NOT NULL
                    AND (aht.delete_reason_ IS NULL OR aht.delete_reason_ = 'completed')
                    AND ahi.type_ IN ('candidate', 'assignee')
                    AND (
                        ahi.user_id_ = ANY(processed_by_basket_ids)
                        OR ahi.group_id_ = ANY(processed_by_basket_ids)
                    )
              )
          )

          -- Permission filters (user basket)
          AND (
              user_basket_ids IS NULL
              OR (
                  ahp.start_user_id_ = ANY(user_basket_ids)
                  OR EXISTS (
                      SELECT 1
                      FROM act_hi_taskinst aht
                      WHERE aht.proc_inst_id_ = ahp.id_
                        AND aht.end_time_ IS NULL
                        AND aht.assignee_ = ANY(user_basket_ids)
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM act_hi_taskinst aht
                      JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                      WHERE aht.proc_inst_id_ = ahp.id_
                        AND aht.end_time_ IS NULL
                        AND ahi.type_ = 'candidate'
                        AND ahi.user_id_ = ANY(user_basket_ids)
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM act_hi_taskinst aht
                      JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                      WHERE aht.proc_inst_id_ = ahp.id_
                        AND aht.end_time_ IS NULL
                        AND ahi.type_ = 'candidate'
                        AND ahi.group_id_ = ANY(user_basket_ids)
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM act_hi_taskinst aht
                      WHERE aht.proc_inst_id_ = ahp.id_
                        AND aht.end_time_ IS NOT NULL
                        AND aht.delete_reason_ IS NULL
                        AND aht.assignee_ = ANY(user_basket_ids)
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM act_hi_taskinst aht
                      JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                      WHERE aht.proc_inst_id_ = ahp.id_
                        AND aht.end_time_ IS NOT NULL
                        AND (aht.delete_reason_ IS NULL OR aht.delete_reason_ = 'completed')
                        AND (ahi.type_ IN ('candidate', 'assignee'))
                        AND (
                            ahi.user_id_ = ANY(user_basket_ids)
                            OR ahi.group_id_ = ANY(user_basket_ids)
                        )
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM act_id_membership m_user
                      JOIN act_id_membership m_creator
                        ON m_user.group_id_ = m_creator.group_id_
                      WHERE m_user.user_id_ = ANY(user_basket_ids)
                        AND m_creator.user_id_ = ahp.start_user_id_
                  )
              )
          )
          AND (
              last_seen_id IS NULL
              OR ahp.id_ > last_seen_id
          )
        ORDER BY ahp.id_
        LIMIT limit_count
    ),
    phase_agg AS (
        SELECT aht.proc_inst_id_,
               STRING_AGG(DISTINCT aht.name_, ', ') AS current_phases
        FROM act_hi_taskinst aht
        JOIN base ON base.id_ = aht.proc_inst_id_
        WHERE aht.end_time_ IS NULL
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
                JOIN base ON base.id_ = aht.proc_inst_id_
                WHERE aht.end_time_ IS NULL
                UNION ALL
                SELECT
                    aht.proc_inst_id_,
                    NULLIF(BTRIM(ahi.user_id_), '') AS processor
                FROM act_hi_taskinst aht
                JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                JOIN base ON base.id_ = aht.proc_inst_id_
                WHERE aht.end_time_ IS NULL
                  AND ahi.type_ = 'candidate'
                UNION ALL
                SELECT
                    aht.proc_inst_id_,
                    NULLIF(BTRIM(ahi.group_id_), '') AS processor
                FROM act_hi_taskinst aht
                JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                JOIN base ON base.id_ = aht.proc_inst_id_
                WHERE aht.end_time_ IS NULL
                  AND ahi.type_ = 'candidate'
            ) normalized_processors
            WHERE processor IS NOT NULL
        ) processors
        GROUP BY proc_inst_id_
    )
    SELECT
        base.id_ AS ticket_uid,
        arpt.instance_title_ AS ticket_title,
        base.business_key_ AS ticket_number,
        arp.name_ AS ticket_type,
        CASE
            WHEN base.end_time_ IS NULL
                 AND base.state_ = 'suspended'
            THEN 'SUSPENDED'
            WHEN base.end_time_ IS NULL
            THEN 'ACTIVE'
            WHEN base.end_time_ IS NOT NULL AND base.delete_reason_ IS NULL
            THEN 'COMPLETED'
            WHEN base.end_time_ IS NOT NULL
                 AND base.delete_reason_ IS NOT NULL
                 AND base.delete_reason_ NOT ILIKE '%terminated%'
                 AND base.delete_reason_ NOT ILIKE '%termination%'
            THEN 'CANCELLED'
            WHEN base.end_time_ IS NOT NULL
                 AND (
                     base.delete_reason_ ILIKE '%terminated%'
                     OR base.delete_reason_ ILIKE '%termination%'
                 )
            THEN 'EXTERNALLY_TERMINATED'
            ELSE 'COMPLETED'
        END AS ticket_status,
        phase_agg.current_phases,
        processor_agg.current_processors,
        base.start_user_id_ AS creator,
        CASE
            WHEN base.end_time_ IS NULL
            THEN EXTRACT(
                EPOCH FROM ((NOW() AT TIME ZONE 'UTC') - base.start_time_)
            ) * 1000
            ELSE base.duration_
        END AS duration,
        (base.start_time_ AT TIME ZONE 'UTC') AS create_time,
        (base.end_time_ AT TIME ZONE 'UTC') AS end_time
    FROM base
    LEFT JOIN act_re_procdef arp ON arp.id_ = base.proc_def_id_
    LEFT JOIN act_ru_execution_titles arpt ON arpt.execution_id_ = base.id_
    LEFT JOIN phase_agg ON phase_agg.proc_inst_id_ = base.id_
    LEFT JOIN processor_agg ON processor_agg.proc_inst_id_ = base.id_;
$$;

ALTER FUNCTION public.camunda_ticket_export_rows(
    text, text, text, text,
    text[], text[], text[], text[],
    timestamp with time zone, timestamp with time zone,
    timestamp with time zone, timestamp with time zone,
    text[], text[], text[],
    integer, text
) OWNER TO camunda;
