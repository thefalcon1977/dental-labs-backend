/*
Advance-search (IDs only) - SQL-only implementation notes

- This file defines `camunda_ticket_search_ids(...)` which returns a page of process
  instance IDs (proc_inst_id_) after applying filters + sorting + pagination.

- If `criteria` is provided, it becomes the *primary filter*:
  - nested logical tree: {"operator":"and|or","conditions":[...]} (recursive)
  - leaf: {"field":"...","action":"...","value":...}
  - leaf also supports:
    - variable: {"field":"variable","variable_name":"...","action":"...","value":...}

- Variable criteria uses **history variables** (`act_hi_varinst`) and compares against
  the **latest value** for the given (proc_inst_id_, variable_name) by `create_time_`
  (ties broken by id_).
*/

CREATE OR REPLACE FUNCTION camunda_ticket_search_status(
    state_ text,
    end_time_ timestamptz,
    delete_reason_ text
) RETURNS text
LANGUAGE sql
STABLE
AS $$
    SELECT CASE
        WHEN end_time_ IS NULL AND state_ ILIKE 'suspended' THEN 'SUSPENDED'
        WHEN end_time_ IS NULL THEN 'ACTIVE'
        WHEN end_time_ IS NOT NULL AND delete_reason_ ILIKE '%cancelled%' THEN 'CANCELLED'
        WHEN end_time_ IS NOT NULL AND delete_reason_ ILIKE '%canceled%' THEN 'CANCELLED'
        WHEN end_time_ IS NOT NULL AND (
            delete_reason_ ILIKE '%terminated%'
            OR delete_reason_ ILIKE '%termination%'
        ) THEN 'EXTERNALLY_TERMINATED'
        WHEN end_time_ IS NOT NULL AND (delete_reason_ IS NULL OR delete_reason_ = '')
        THEN 'COMPLETED'
        WHEN end_time_ IS NOT NULL THEN 'EXTERNALLY_TERMINATED'
        ELSE 'COMPLETED'
    END;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_duration_ms(
    start_time_ timestamp,
    end_time_ timestamp,
    duration_ bigint
) RETURNS bigint
LANGUAGE sql
STABLE
AS $$
    SELECT CASE
        WHEN end_time_ IS NULL
        THEN (
            EXTRACT(EPOCH FROM (NOW() - (start_time_ AT TIME ZONE 'Asia/Tehran'))) * 1000
        )::bigint
        ELSE duration_
    END;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_parse_numeric(
    value_json jsonb
) RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    value_text text;
BEGIN
    IF value_json IS NULL THEN
        RETURN NULL;
    END IF;

    value_text := TRIM(BOTH '"' FROM value_json::text);

    IF value_text ~ '^-?[0-9]+(\.[0-9]+)?$' THEN
        RETURN value_text::numeric;
    END IF;

    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_match_text(
    action text,
    field_value text,
    value_json jsonb
) RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    normalized_action text := LOWER(action);
    value_text text;
    values text[];
BEGIN
    IF normalized_action = 'is_empty' THEN
        RETURN field_value IS NULL OR BTRIM(field_value) = '';
    ELSIF normalized_action = 'is_not_empty' THEN
        RETURN field_value IS NOT NULL AND BTRIM(field_value) <> '';
    END IF;

    IF value_json IS NULL THEN
        RETURN FALSE;
    END IF;

    IF normalized_action IN ('in', 'not_in') THEN
        IF jsonb_typeof(value_json) = 'array' THEN
            SELECT ARRAY_AGG(elem) INTO values
            FROM jsonb_array_elements_text(value_json) elem;
        ELSE
            value_text := TRIM(BOTH '"' FROM value_json::text);
            values := ARRAY[value_text];
        END IF;

        IF normalized_action = 'in' THEN
            RETURN field_value = ANY(values);
        END IF;

        RETURN field_value IS NULL OR field_value <> ALL(values);
    END IF;

    value_text := TRIM(BOTH '"' FROM value_json::text);

    CASE normalized_action
        WHEN '==' THEN RETURN field_value = value_text;
        WHEN '!=' THEN RETURN field_value IS DISTINCT FROM value_text;
        WHEN 'like' THEN RETURN field_value LIKE value_text;
        WHEN 'ilike' THEN RETURN field_value ILIKE value_text;
        WHEN 'not_like' THEN RETURN field_value IS NULL OR field_value NOT LIKE value_text;
        WHEN 'not_ilike' THEN RETURN field_value IS NULL OR field_value NOT ILIKE value_text;
        ELSE RETURN FALSE;
    END CASE;
END;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_match_numeric(
    action text,
    field_value numeric,
    value_json jsonb
) RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    normalized_action text := LOWER(action);
    value_num numeric;
    values numeric[];
BEGIN
    IF normalized_action = 'is_empty' THEN
        RETURN field_value IS NULL;
    ELSIF normalized_action = 'is_not_empty' THEN
        RETURN field_value IS NOT NULL;
    END IF;

    IF value_json IS NULL THEN
        RETURN FALSE;
    END IF;

    IF normalized_action IN ('in', 'not_in') THEN
        IF jsonb_typeof(value_json) = 'array' THEN
            SELECT ARRAY_AGG(camunda_ticket_search_parse_numeric(elem)) INTO values
            FROM jsonb_array_elements(value_json) elem;
        ELSE
            values := ARRAY[camunda_ticket_search_parse_numeric(value_json)];
        END IF;

        IF normalized_action = 'in' THEN
            RETURN field_value = ANY(values);
        END IF;

        RETURN field_value IS NULL OR field_value <> ALL(values);
    END IF;

    value_num := camunda_ticket_search_parse_numeric(value_json);

    CASE normalized_action
        WHEN '==' THEN RETURN field_value = value_num;
        WHEN '!=' THEN RETURN field_value IS DISTINCT FROM value_num;
        WHEN '>' THEN RETURN field_value > value_num;
        WHEN '>=' THEN RETURN field_value >= value_num;
        WHEN '<' THEN RETURN field_value < value_num;
        WHEN '<=' THEN RETURN field_value <= value_num;
        ELSE RETURN FALSE;
    END CASE;
END;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_match_time(
    action text,
    field_value timestamptz,
    value_json jsonb
) RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    normalized_action text := LOWER(action);
    value_text text;
    value_time timestamptz;
BEGIN
    IF normalized_action = 'is_empty' THEN
        RETURN field_value IS NULL;
    ELSIF normalized_action = 'is_not_empty' THEN
        RETURN field_value IS NOT NULL;
    END IF;

    IF value_json IS NULL THEN
        RETURN FALSE;
    END IF;

    value_text := TRIM(BOTH '"' FROM value_json::text);
    value_time := value_text::timestamptz;

    CASE normalized_action
        WHEN '==' THEN RETURN field_value = value_time;
        WHEN '!=' THEN RETURN field_value IS DISTINCT FROM value_time;
        WHEN '>' THEN RETURN field_value > value_time;
        WHEN '>=' THEN RETURN field_value >= value_time;
        WHEN '<' THEN RETURN field_value < value_time;
        WHEN '<=' THEN RETURN field_value <= value_time;
        ELSE RETURN FALSE;
    END CASE;
END;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_variable_value(
    proc_inst_id text,
    variable_name text
) RETURNS text
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(v.text_, v.text2_, v.long_::text, v.double_::text)
    FROM act_hi_varinst v
    WHERE v.proc_inst_id_ = proc_inst_id
      AND v.name_ = variable_name
    ORDER BY v.create_time_ DESC NULLS LAST, v.id_ DESC
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_eval_condition(
    condition jsonb,
    proc_inst_id text,
    proc_def_id text,
    business_key text,
    start_user_id text,
    start_time timestamptz,
    end_time timestamptz,
    state text,
    delete_reason text,
    tenant_id text,
    duration_value bigint
) RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    field_name text := LOWER(condition->>'field');
    action text := LOWER(condition->>'action');
    value_json jsonb := condition->'value';
    variable_name text := condition->>'variable_name';
    field_value text;
    field_value_num numeric;
BEGIN
    IF field_name IN ('ticket_number') THEN
        RETURN camunda_ticket_search_match_text(action, business_key, value_json);
    ELSIF field_name IN ('ticket_type') THEN
        SELECT arp.name_ INTO field_value
        FROM act_re_procdef arp
        WHERE arp.id_ = proc_def_id;
        RETURN camunda_ticket_search_match_text(action, field_value, value_json);
    ELSIF field_name IN ('ticket_title') THEN
        SELECT arpt.instance_title_ INTO field_value
        FROM act_ru_execution_titles arpt
        WHERE arpt.execution_id_ = proc_inst_id
        LIMIT 1;
        RETURN camunda_ticket_search_match_text(action, field_value, value_json);
    ELSIF field_name IN ('ticket_status') THEN
        field_value := camunda_ticket_search_status(state, end_time, delete_reason);
        RETURN camunda_ticket_search_match_text(action, field_value, value_json);
    ELSIF field_name IN ('creator') THEN
        RETURN camunda_ticket_search_match_text(action, start_user_id, value_json);
    ELSIF field_name IN ('create_time') THEN
        RETURN camunda_ticket_search_match_time(action, start_time, value_json);
    ELSIF field_name IN ('end_time') THEN
        RETURN camunda_ticket_search_match_time(action, end_time, value_json);
    ELSIF field_name IN ('duration_ms', 'process_duration') THEN
        field_value_num := camunda_ticket_search_duration_ms(
            start_time,
            end_time,
            duration_value
        );
        RETURN camunda_ticket_search_match_numeric(action, field_value_num, value_json);
    ELSIF field_name IN ('tenant_id') THEN
        RETURN camunda_ticket_search_match_text(action, tenant_id, value_json);
    ELSIF field_name IN ('variable') THEN
        field_value := camunda_ticket_search_variable_value(proc_inst_id, variable_name);
        IF action IN ('>', '>=', '<', '<=') THEN
            RETURN camunda_ticket_search_match_numeric(
                action,
                camunda_ticket_search_parse_numeric(to_jsonb(field_value)),
                value_json
            );
        END IF;
        RETURN camunda_ticket_search_match_text(action, field_value, value_json);
    END IF;

    RETURN FALSE;
END;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_eval_criteria(
    criteria jsonb,
    proc_inst_id text,
    proc_def_id text,
    business_key text,
    start_user_id text,
    start_time timestamptz,
    end_time timestamptz,
    state text,
    delete_reason text,
    tenant_id text,
    duration_value bigint
) RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    operator text;
    conditions jsonb;
    condition jsonb;
BEGIN
    IF criteria IS NULL THEN
        RETURN TRUE;
    END IF;

    IF criteria ? 'type' AND criteria->>'type' = 'group' THEN
        operator := COALESCE(criteria->>'operator', 'and');
        conditions := criteria->'children';
    ELSE
        operator := COALESCE(criteria->>'operator', 'and');
        conditions := criteria->'conditions';
    END IF;

    IF conditions IS NULL OR jsonb_typeof(conditions) <> 'array' THEN
        RETURN TRUE;
    END IF;

    IF LOWER(operator) = 'and' THEN
        FOR condition IN SELECT * FROM jsonb_array_elements(conditions)
        LOOP
            IF condition ? 'operator' OR (condition ? 'type' AND condition->>'type' = 'group') THEN
                IF NOT camunda_ticket_search_eval_criteria(
                    condition,
                    proc_inst_id,
                    proc_def_id,
                    business_key,
                    start_user_id,
                    start_time,
                    end_time,
                    state,
                    delete_reason,
                    tenant_id,
                    duration_value
                ) THEN
                    RETURN FALSE;
                END IF;
            ELSIF NOT camunda_ticket_search_eval_condition(
                condition,
                proc_inst_id,
                proc_def_id,
                business_key,
                start_user_id,
                start_time,
                end_time,
                state,
                delete_reason,
                tenant_id,
                duration_value
            ) THEN
                RETURN FALSE;
            END IF;
        END LOOP;
        RETURN TRUE;
    END IF;

    -- OR
    FOR condition IN SELECT * FROM jsonb_array_elements(conditions)
    LOOP
        IF condition ? 'operator' OR (condition ? 'type' AND condition->>'type' = 'group') THEN
            IF camunda_ticket_search_eval_criteria(
                condition,
                proc_inst_id,
                proc_def_id,
                business_key,
                start_user_id,
                start_time,
                end_time,
                state,
                delete_reason,
                tenant_id,
                duration_value
            ) THEN
                RETURN TRUE;
            END IF;
        ELSIF camunda_ticket_search_eval_condition(
            condition,
            proc_inst_id,
            proc_def_id,
            business_key,
            start_user_id,
            start_time,
            end_time,
            state,
            delete_reason,
            tenant_id,
            duration_value
        ) THEN
            RETURN TRUE;
        END IF;
    END LOOP;

    RETURN FALSE;
END;
$$;

CREATE OR REPLACE FUNCTION camunda_ticket_search_ids(
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
    user_basket_ids text[] DEFAULT NULL,
    tenant_id text DEFAULT NULL,
    criteria jsonb DEFAULT NULL,
    sort_by text DEFAULT 'create_time',
    sort_order text DEFAULT 'desc',
    limit_count int DEFAULT 50,
    offset_count int DEFAULT 0
) RETURNS TABLE(proc_inst_id_ text)
LANGUAGE sql
STABLE
AS $$
    WITH processor_agg AS (
        SELECT
            aht.proc_inst_id_,
            MIN(
                NULLIF(
                    COALESCE(aht.assignee_, ahi.user_id_, ahi.group_id_, ''),
                    ''
                )
            ) AS first_processor
        FROM act_hi_taskinst aht
        LEFT JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
        WHERE aht.end_time_ IS NULL
        GROUP BY aht.proc_inst_id_
    ),
    phase_agg AS (
        SELECT
            aai.proc_inst_id_,
            MIN(aai.act_name_) AS first_phase
        FROM act_hi_actinst aai
        WHERE aai.end_time_ IS NULL
        GROUP BY aai.proc_inst_id_
    )
    SELECT ahp.proc_inst_id_
    FROM act_hi_procinst ahp
    LEFT JOIN act_re_procdef arp ON arp.id_ = ahp.proc_def_id_
    LEFT JOIN act_ru_execution_titles arpt ON arpt.execution_id_ = ahp.id_
    LEFT JOIN processor_agg proc ON proc.proc_inst_id_ = ahp.id_
    LEFT JOIN phase_agg pha ON pha.proc_inst_id_ = ahp.id_
    WHERE 1 = 1
      -- Tenant (simple filter only; ignored when criteria is provided)
      AND (
          criteria IS NOT NULL
          OR tenant_id IS NULL
          OR ahp.tenant_id_ = tenant_id
      )

      -- Criteria overrides simple filters (see doc)
      AND (
          criteria IS NULL
          OR camunda_ticket_search_eval_criteria(
              criteria,
              ahp.id_,
              ahp.proc_def_id_,
              ahp.business_key_,
              ahp.start_user_id_,
              ahp.start_time_,
              ahp.end_time_,
              ahp.state_,
              ahp.delete_reason_,
              ahp.tenant_id_,
              ahp.duration_
          )
      )

      -- Simple filters (applied only when criteria is NOT provided)
      AND (
          criteria IS NOT NULL
          OR (
              -- Text filters
              (ticket_type IS NULL OR arp.name_ ILIKE '%' || ticket_type || '%')
              AND (ticket_number IS NULL OR ahp.business_key_ ILIKE '%' || ticket_number || '%')
              AND (ticket_title IS NULL OR arpt.instance_title_ ILIKE '%' || ticket_title || '%')

              -- Creator
              AND (creator_list IS NULL OR ahp.start_user_id_ = ANY(creator_list))

              -- Status (supports comma-separated input)
              AND (
                  ticket_status IS NULL
                  OR camunda_ticket_search_status(
                      ahp.state_,
                      ahp.end_time_,
                      ahp.delete_reason_
                  ) = ANY(regexp_split_to_array(upper(ticket_status), '\s*,\s*'))
              )
          )
      )

      -- Processor filter
      AND (
          criteria IS NOT NULL
          OR
          processor_list IS NULL
          OR EXISTS (
              SELECT 1
              FROM act_hi_taskinst aht
              LEFT JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
              WHERE aht.proc_inst_id_ = ahp.id_
                AND aht.end_time_ IS NULL
                AND (
                    aht.assignee_ = ANY(processor_list)
                    OR (
                        ahi.type_ = 'candidate'
                        AND (
                            ahi.user_id_ = ANY(processor_list)
                            OR ahi.group_id_ = ANY(processor_list)
                        )
                    )
                )
          )
      )

      -- Assignee filter (supports empty string)
      AND (
          criteria IS NOT NULL
          OR
          assignee_list IS NULL
          OR EXISTS (
              SELECT 1
              FROM act_hi_taskinst aht
              LEFT JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
              WHERE aht.proc_inst_id_ = ahp.id_
                AND aht.end_time_ IS NULL
                AND (
                    aht.assignee_ = ANY(assignee_list)
                    OR (
                        ahi.type_ = 'candidate'
                        AND (
                            ahi.user_id_ = ANY(assignee_list)
                            OR ahi.group_id_ = ANY(assignee_list)
                        )
                    )
                    OR (
                        '' = ANY(assignee_list)
                        AND (aht.assignee_ IS NULL OR aht.assignee_ = '')
                    )
                )
          )
      )

      -- Phase filter
      AND (
          criteria IS NOT NULL
          OR
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
      -- Camunda stores timestamps as `timestamp` (no tz). In this deployment they
      -- represent Asia/Tehran wall-time. Interpret them accordingly before comparing
      -- against timestamptz inputs to avoid session-timezone shifts.
      AND (
          criteria IS NOT NULL
          OR start_time_from IS NULL
          OR (ahp.start_time_ AT TIME ZONE 'Asia/Tehran') >= start_time_from
      )
      AND (
          criteria IS NOT NULL
          OR start_time_to IS NULL
          OR (ahp.start_time_ AT TIME ZONE 'Asia/Tehran') <= start_time_to
      )
      AND (
          criteria IS NOT NULL
          OR end_time_from IS NULL
          OR (ahp.end_time_ AT TIME ZONE 'Asia/Tehran') >= end_time_from
      )
      AND (
          criteria IS NOT NULL
          OR end_time_to IS NULL
          OR (ahp.end_time_ AT TIME ZONE 'Asia/Tehran') <= end_time_to
      )

      -- Pending filter (active tasks only)
      AND (
          criteria IS NOT NULL
          OR
          pending_basket_ids IS NULL
          OR EXISTS (
              SELECT 1
              FROM act_hi_taskinst aht
              LEFT JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
              WHERE aht.proc_inst_id_ = ahp.id_
                AND aht.end_time_ IS NULL
                AND (
                    aht.assignee_ = ANY(pending_basket_ids)
                    OR (
                        ahi.type_ = 'candidate'
                        AND (
                            ahi.user_id_ = ANY(pending_basket_ids)
                            OR ahi.group_id_ = ANY(pending_basket_ids)
                        )
                    )
                )
          )
      )

      -- Processed by filter (completed tasks only)
      AND (
          criteria IS NOT NULL
          OR
          processed_by_basket_ids IS NULL
          OR EXISTS (
              SELECT 1
              FROM act_hi_taskinst aht
              LEFT JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
              WHERE aht.proc_inst_id_ = ahp.id_
                AND aht.end_time_ IS NOT NULL
                AND (aht.delete_reason_ IS NULL OR aht.delete_reason_ = 'completed')
                AND (
                    aht.assignee_ = ANY(processed_by_basket_ids)
                    OR (
                        ahi.type_ IN ('candidate', 'assignee')
                        AND (
                            ahi.user_id_ = ANY(processed_by_basket_ids)
                            OR ahi.group_id_ = ANY(processed_by_basket_ids)
                        )
                    )
                )
          )
      )

      -- Permission filters (user basket)
      AND (
          criteria IS NOT NULL
          OR
          user_basket_ids IS NULL
          OR (
              -- Rule 1: creator
              ahp.start_user_id_ = ANY(user_basket_ids)
              OR
              -- Rule 2: current assignee
              EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND aht.assignee_ = ANY(user_basket_ids)
              )
              OR
              -- Rule 3: candidate users
              EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND ahi.type_ = 'candidate'
                    AND ahi.user_id_ = ANY(user_basket_ids)
              )
              OR
              -- Rule 4: candidate groups
              EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  JOIN act_hi_identitylink ahi ON ahi.task_id_ = aht.id_
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NULL
                    AND ahi.type_ = 'candidate'
                    AND ahi.group_id_ = ANY(user_basket_ids)
              )
              OR
              -- Rule 5: historical involvement (completed tasks)
              EXISTS (
                  SELECT 1
                  FROM act_hi_taskinst aht
                  WHERE aht.proc_inst_id_ = ahp.id_
                    AND aht.end_time_ IS NOT NULL
                    AND aht.delete_reason_ IS NULL
                    AND aht.assignee_ = ANY(user_basket_ids)
              )
              OR
              -- Rule 6: group historical involvement
              EXISTS (
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
              OR
              -- Rule 7: same group as creator
              EXISTS (
                  SELECT 1
                  FROM act_id_membership m_user
                  JOIN act_id_membership m_creator
                    ON m_user.group_id_ = m_creator.group_id_
                  WHERE m_user.user_id_ = ANY(user_basket_ids)
                    AND m_creator.user_id_ = ahp.start_user_id_
              )
          )
      )

    ORDER BY
      CASE WHEN sort_by = 'create_time' AND sort_order = 'asc' THEN ahp.start_time_ END ASC,
      CASE WHEN sort_by = 'create_time' AND sort_order = 'desc' THEN ahp.start_time_ END DESC,
      CASE WHEN sort_by = 'end_time' AND sort_order = 'asc' THEN ahp.end_time_ END ASC NULLS LAST,
      CASE WHEN sort_by = 'end_time' AND sort_order = 'desc' THEN ahp.end_time_ END DESC NULLS LAST,
      CASE WHEN sort_by = 'ticket_number' AND sort_order = 'asc' THEN ahp.business_key_ END ASC,
      CASE WHEN sort_by = 'ticket_number' AND sort_order = 'desc' THEN ahp.business_key_ END DESC,
      CASE WHEN sort_by = 'ticket_type' AND sort_order = 'asc' THEN arp.name_ END ASC,
      CASE WHEN sort_by = 'ticket_type' AND sort_order = 'desc' THEN arp.name_ END DESC,
      CASE WHEN sort_by = 'creator' AND sort_order = 'asc' THEN ahp.start_user_id_ END ASC,
      CASE WHEN sort_by = 'creator' AND sort_order = 'desc' THEN ahp.start_user_id_ END DESC,
      CASE WHEN sort_by IN ('ticket_status') AND sort_order = 'asc'
           THEN camunda_ticket_search_status(ahp.state_, ahp.end_time_, ahp.delete_reason_)
      END ASC,
      CASE WHEN sort_by IN ('ticket_status') AND sort_order = 'desc'
           THEN camunda_ticket_search_status(ahp.state_, ahp.end_time_, ahp.delete_reason_)
      END DESC,
      CASE WHEN sort_by IN ('duration', 'duration_ms', 'process_duration')
           AND sort_order = 'asc'
      THEN camunda_ticket_search_duration_ms(ahp.start_time_, ahp.end_time_, ahp.duration_)
      END ASC NULLS LAST,
      CASE WHEN sort_by IN ('duration', 'duration_ms', 'process_duration')
           AND sort_order = 'desc'
      THEN camunda_ticket_search_duration_ms(ahp.start_time_, ahp.end_time_, ahp.duration_)
      END DESC NULLS LAST,
      CASE WHEN sort_by IN ('processor', 'current_processors') AND sort_order = 'asc'
           THEN proc.first_processor
      END ASC NULLS LAST,
      CASE WHEN sort_by IN ('processor', 'current_processors') AND sort_order = 'desc'
           THEN proc.first_processor
      END DESC NULLS LAST,
      CASE WHEN sort_by IN ('ticket_phases') AND sort_order = 'asc'
           THEN pha.first_phase
      END ASC NULLS LAST,
      CASE WHEN sort_by IN ('ticket_phases') AND sort_order = 'desc'
           THEN pha.first_phase
      END DESC NULLS LAST,
      CASE WHEN sort_by = 'ticket_title' AND sort_order = 'asc' THEN arpt.instance_title_ END ASC NULLS LAST,
      CASE WHEN sort_by = 'ticket_title' AND sort_order = 'desc' THEN arpt.instance_title_ END DESC NULLS LAST,
      ahp.id_
    LIMIT limit_count OFFSET offset_count;
$$;
