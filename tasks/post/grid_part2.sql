CREATE OR REPLACE FUNCTION public.grid_report_rows(
    p_form_key   text,
    p_start_time timestamp,
    p_end_time   timestamp
)
RETURNS TABLE (
    excel_row_no               integer,
    ticket_title               text,
    ticket_number              text,
    ticket_status              text,
    ticket_creator             text,
    ticket_end_time            timestamp,
    ticket_start_time          timestamp,
    task_assignee              text,
    cm_ready_report_time_start timestamp,
    cm_ready_report_time_end   timestamp,
    ola                        double precision,
    ticket_ola                  double precision,
    cr_no                      text,
    cr_type                    text,
    mvo                        text,
    region                     text,
    subregion_name             text,
    site_id                    text,
    cell_name                  text,
    technology                 text,
    rnc_bsc_site_name          text,
    vendor                     text,
    mo                         text,
    parameter                  text,
    current_value              text,
    proposed_value             text,
    redline                    text,
    atoll_update_required      text,
    implementation_date        text,
    oss                        text,
    band                       text,
    device_number              text
)
LANGUAGE sql
STABLE
AS $$
SELECT
    s.row_no + 1      AS excel_row_no,
    COALESCE(b.ticket_title, '')   AS ticket_title,
    COALESCE(b.ticket_number, '')  AS ticket_number,
    COALESCE(b.ticket_status, 'ACTIVE') AS ticket_status,
    COALESCE(b.ticket_creator, '') AS ticket_creator,
    b.ticket_end_time,
    b.ticket_start_time,
    COALESCE(b.task_assignee, '') AS task_assignee,
    b.cm_ready_report_time_start,
    b.cm_ready_report_time_end,
    b.ola,
    b.ticket_ola,
    jsonb_array_element_text(b.payload->'CR No', s.row_no) AS cr_no,
    jsonb_array_element_text(b.payload->'CR Type (LSA/NSA/HSA)', s.row_no) AS cr_type,
    jsonb_array_element_text(b.payload->'MVO', s.row_no) AS mvo,
    jsonb_array_element_text(b.payload->'Region', s.row_no) AS region,
    jsonb_array_element_text(b.payload->'Subregion Name', s.row_no) AS subregion_name,
    jsonb_array_element_text(b.payload->'Site ID', s.row_no) AS site_id,
    jsonb_array_element_text(b.payload->'Cell Name', s.row_no) AS cell_name,
    jsonb_array_element_text(b.payload->'Technology', s.row_no) AS technology,
    jsonb_array_element_text(b.payload->'RNC/BSC/Site Name', s.row_no) AS rnc_bsc_site_name,
    jsonb_array_element_text(b.payload->'Vendor (H/E/N/Z)', s.row_no) AS vendor,
    jsonb_array_element_text(b.payload->'MO', s.row_no) AS mo,
    jsonb_array_element_text(b.payload->'Parameter', s.row_no) AS parameter,
    jsonb_array_element_text(b.payload->'Current Value', s.row_no) AS current_value,
    jsonb_array_element_text(b.payload->'Proposed Value', s.row_no) AS proposed_value,
    jsonb_array_element_text(b.payload->'Redline (Y/N)', s.row_no) AS redline,
    jsonb_array_element_text(b.payload->'Atoll update Required (Y/N)', s.row_no) AS atoll_update_required,
    jsonb_array_element_text(b.payload->'implementation date', s.row_no) AS implementation_date,
    jsonb_array_element_text(b.payload->'OSS', s.row_no) AS oss,
    jsonb_array_element_text(b.payload->'Band', s.row_no) AS band,
    jsonb_array_element_text(b.payload->'Device Number', s.row_no) AS device_number
FROM public.grid_report_base(p_form_key, p_start_time, p_end_time) b
CROSS JOIN LATERAL generate_series(0, b.payload_row_count - 1) AS s(row_no)
WHERE b.payload_row_count > 0
ORDER BY b.create_time, b.proc_inst_id, s.row_no;
$$;
