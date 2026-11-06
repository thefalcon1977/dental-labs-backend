CREATE OR REPLACE FUNCTION public.grid_report_base(
    p_form_key   text,
    p_start_time timestamp,
    p_end_time   timestamp
)
RETURNS TABLE (
    proc_inst_id                text,
    create_time                 timestamp,
    payload                     jsonb,
    ticket_number               text,
    ticket_title                text,
    ticket_status               text,
    ticket_creator              text,
    ticket_start_time           timestamp,
    ticket_end_time             timestamp,
    task_assignee               text,
    cm_ready_report_time_start  timestamp,
    cm_ready_report_time_end    timestamp,
    ola                         double precision,
    ticket_ola                  double precision,
    payload_row_count           integer
)
LANGUAGE sql
STABLE
AS $$
WITH
cm_ready AS (
    SELECT DISTINCT proc_inst_id_
    FROM act_hi_varinst
    WHERE name_ = 'cm_ready_report'
      AND text_ = 'yes'
),
cm_ready_times AS (
    SELECT
        proc_inst_id_,
        MAX(CASE WHEN name_ = 'cm_ready_report_time_start' THEN long_ END) AS time_start_long,
        MAX(CASE WHEN name_ = 'cm_ready_report_time_end'   THEN long_ END) AS time_end_long
    FROM act_hi_varinst
    WHERE name_ IN ('cm_ready_report_time_start', 'cm_ready_report_time_end')
      AND long_ IS NOT NULL
    GROUP BY proc_inst_id_
),
processor_combined AS (
    SELECT proc_inst_id_, assignee_ AS processor
    FROM act_ru_task
    WHERE assignee_ IS NOT NULL
      AND (suspension_state_ = 1 OR suspension_state_ IS NULL)
    UNION ALL
    SELECT proc_inst_id_, assignee_ AS processor
    FROM act_hi_taskinst
    WHERE assignee_ IS NOT NULL
      AND end_time_ IS NOT NULL
),
processor_agg AS (
    SELECT proc_inst_id_, string_agg(DISTINCT processor, ', ') AS processor
    FROM processor_combined
    GROUP BY proc_inst_id_
),
base AS (
    SELECT
        v.proc_inst_id_ AS proc_inst_id,
        v.create_time_  AS create_time,
        (convert_from(b.bytes_, 'UTF8')::jsonb) AS payload,
        COALESCE(p.business_key_, '') AS ticket_number,
        COALESCE(pt.instance_title_, et.instance_title_, '') AS ticket_title,
        p.start_user_id_ AS ticket_creator,
        p.start_time_   AS ticket_start_time,
        p.end_time_    AS ticket_end_time,
        pa.processor   AS task_assignee,
        to_timestamp(cm.time_start_long / 1000.0) AS cm_ready_report_time_start,
        to_timestamp(cm.time_end_long / 1000.0)   AS cm_ready_report_time_end,
        CASE
            WHEN cm.time_start_long IS NOT NULL AND cm.time_end_long IS NOT NULL
            THEN (cm.time_end_long - cm.time_start_long) / 1000.0
            ELSE NULL
        END AS ola,
        LOWER(COALESCE(p.delete_reason_, '')) AS _dr,
        p.end_time_ AS _end_time
    FROM act_hi_varinst v
    INNER JOIN cm_ready cr ON v.proc_inst_id_ = cr.proc_inst_id_
    JOIN act_ge_bytearray b ON v.bytearray_id_ = b.id_
    LEFT JOIN act_hi_procinst p ON v.proc_inst_id_ = p.proc_inst_id_
    LEFT JOIN act_hi_procinst_titles pt ON v.proc_inst_id_ = pt.proc_inst_id_
    LEFT JOIN act_ru_execution_titles et ON v.proc_inst_id_ = et.execution_id_
    LEFT JOIN processor_agg pa ON v.proc_inst_id_ = pa.proc_inst_id_
    LEFT JOIN cm_ready_times cm ON v.proc_inst_id_ = cm.proc_inst_id_
    WHERE v.name_ = p_form_key
      AND v.create_time_ BETWEEN p_start_time AND p_end_time
),
base_with_count AS (
    SELECT
        proc_inst_id,
        create_time,
        payload,
        ticket_number,
        ticket_title,
        ticket_creator,
        ticket_start_time,
        ticket_end_time,
        task_assignee,
        cm_ready_report_time_start,
        cm_ready_report_time_end,
        ola,
        CASE
            WHEN cm_ready_report_time_start IS NOT NULL AND cm_ready_report_time_end IS NOT NULL
            THEN EXTRACT(EPOCH FROM (cm_ready_report_time_end - cm_ready_report_time_start))
            ELSE NULL
        END AS ticket_ola,
        CASE
            WHEN _end_time IS NOT NULL AND _dr LIKE '%cancelled%' THEN 'CANCELLED'
            WHEN _end_time IS NOT NULL AND _dr LIKE '%canceled%'  THEN 'CANCELLED'
            WHEN _end_time IS NOT NULL AND (_dr LIKE '%terminated%' OR _dr LIKE '%termination%') THEN 'EXTERNALLY_TERMINATED'
            WHEN _end_time IS NOT NULL AND _dr = '' THEN 'COMPLETED'
            WHEN _end_time IS NOT NULL THEN 'EXTERNALLY_TERMINATED'
            ELSE 'ACTIVE'
        END AS ticket_status,
        GREATEST(
            COALESCE(jsonb_array_length(payload->'CR No'), 0),
            COALESCE(jsonb_array_length(payload->'CR Type (LSA/NSA/HSA)'), 0),
            COALESCE(jsonb_array_length(payload->'MVO'), 0),
            COALESCE(jsonb_array_length(payload->'Region'), 0),
            COALESCE(jsonb_array_length(payload->'Subregion Name'), 0),
            COALESCE(jsonb_array_length(payload->'Site ID'), 0),
            COALESCE(jsonb_array_length(payload->'Cell Name'), 0),
            COALESCE(jsonb_array_length(payload->'Technology'), 0),
            COALESCE(jsonb_array_length(payload->'RNC/BSC/Site Name'), 0),
            COALESCE(jsonb_array_length(payload->'Vendor (H/E/N/Z)'), 0),
            COALESCE(jsonb_array_length(payload->'MO'), 0),
            COALESCE(jsonb_array_length(payload->'Parameter'), 0),
            COALESCE(jsonb_array_length(payload->'Current Value'), 0),
            COALESCE(jsonb_array_length(payload->'Proposed Value'), 0),
            COALESCE(jsonb_array_length(payload->'Redline (Y/N)'), 0),
            COALESCE(jsonb_array_length(payload->'Atoll update Required (Y/N)'), 0),
            COALESCE(jsonb_array_length(payload->'implementation date'), 0),
            COALESCE(jsonb_array_length(payload->'OSS'), 0),
            COALESCE(jsonb_array_length(payload->'Band'), 0),
            COALESCE(jsonb_array_length(payload->'Device Number'), 0)
        ) AS payload_row_count
    FROM base
)
SELECT
    proc_inst_id,
    create_time,
    payload,
    ticket_number,
    ticket_title,
    ticket_status,
    ticket_creator,
    ticket_start_time,
    ticket_end_time,
    task_assignee,
    cm_ready_report_time_start,
    cm_ready_report_time_end,
    ola,
    ticket_ola,
    payload_row_count
FROM base_with_count;
$$;
