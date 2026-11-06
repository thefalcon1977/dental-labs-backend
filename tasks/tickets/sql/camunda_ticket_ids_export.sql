create function public.camunda_ticket_ids_export(ticket_type text DEFAULT NULL::text, ticket_number text DEFAULT NULL::text, ticket_title text DEFAULT NULL::text, ticket_status text DEFAULT NULL::text, creator_list text[] DEFAULT NULL::text[], processor_list text[] DEFAULT NULL::text[], assignee_list text[] DEFAULT NULL::text[], phase_list text[] DEFAULT NULL::text[], start_time_from timestamp with time zone DEFAULT NULL::timestamp with time zone, start_time_to timestamp with time zone DEFAULT NULL::timestamp with time zone, end_time_from timestamp with time zone DEFAULT NULL::timestamp with time zone, end_time_to timestamp with time zone DEFAULT NULL::timestamp with time zone, pending_basket_ids text[] DEFAULT NULL::text[], processed_by_basket_ids text[] DEFAULT NULL::text[], user_basket_ids text[] DEFAULT NULL::text[], limit_count integer DEFAULT 1000, last_seen_id text DEFAULT NULL::text)
    returns TABLE(proc_inst_id_ text)
    stable
    language sql
as
$$
    SELECT ahp.proc_inst_id_
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
    LIMIT limit_count;
$$;

alter function public.camunda_ticket_ids_export(text, text, text, text, text[], text[], text[], text[], timestamp with time zone, timestamp with time zone, timestamp with time zone, timestamp with time zone, text[], text[], text[], integer, text) owner to camunda;
