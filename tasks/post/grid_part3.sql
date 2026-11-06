-- =============================================================================
-- Grid report – PART 3: CSV export (run after grid_part1.sql and grid_part2.sql)
-- =============================================================================
-- Requires: grid_report_base() and grid_report_rows() from part1 and part2.
--
-- HOW TO USE
-- ----------
--
-- 1) Export to a CSV file (recommended – no extra quoting):
--
--    From shell (redirect COPY output to file):
--
--      psql -t -A -c "COPY (SELECT * FROM grid_report_csv_lines(
--        'grid_configuration_management_site',
--        '2026-01-01'::timestamp,
--        '2026-12-31'::timestamp
--      )) TO STDOUT" > report.csv
--
--    Or inside psql (writes on server; needs superuser or pg_write_server_files):
--
--      COPY (SELECT * FROM grid_report_csv_lines(
--        'grid_configuration_management_site',
--        '2026-01-01'::timestamp,
--        '2026-12-31'::timestamp
--      )) TO '/tmp/report.csv';
--
-- 2) Get CSV as one string (e.g. for API or to write in your app):
--
--      SELECT grid_report_csv(
--        'grid_configuration_management_site',
--        '2026-01-01'::timestamp,
--        '2026-12-31'::timestamp
--      );
--
--    In code: fetch the single value and write it to a file as plain text (do not
--    re-export as CSV or the client may wrap it in double quotes).
--
-- 3) DataGrip (or any SQL client) → Excel-friendly CSV:
--
--    Do NOT use grid_report_csv_lines() then Export to CSV: the result is one
--    column per line, so the client wraps each line in quotes and Excel shows
--    one column of long text.
--
--    Instead: run grid_report_rows(), then Export Data → CSV. The result has
--    many columns, so the exported CSV has one column per field and opens
--    correctly in Excel.
--
--      SELECT * FROM grid_report_rows(
--        'grid_configuration_management_site',
--        '2025-01-01'::timestamp,
--        '2026-12-31'::timestamp
--      );
--
--    In DataGrip: Execute → in Results use Export Data → CSV → choose local path.
--
-- 4) Get report as rows (no export; for use in code or reporting):
--
--      SELECT * FROM grid_report_rows(
--        'grid_configuration_management_site',
--        '2025-01-01'::timestamp,
--        '2026-12-31'::timestamp
--      );
--
-- =============================================================================

-- Helper: escape one value for CSV (quote if needed, double internal double-quotes)
CREATE OR REPLACE FUNCTION public.grid_report_csv_escape(val text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE
    WHEN val IS NULL OR val = '' THEN ''
    WHEN val ~ '[",\n\r]' THEN '"' || replace(val, '"', '""') || '"'
    ELSE val
  END;
$$;

-- Main: return full CSV (header + data rows) as single text
CREATE OR REPLACE FUNCTION public.grid_report_csv(
    p_form_key   text,
    p_start_time timestamp,
    p_end_time   timestamp
)
RETURNS text
LANGUAGE sql
STABLE
AS $$
WITH
header AS (
  SELECT 'excel_row_no,ticket_title,ticket_number,ticket_status,ticket_creator,ticket_end_time,ticket_start_time,task_assignee,cm_ready_report_time_start,cm_ready_report_time_end,ola,ticket_ola,cr_no,cr_type,mvo,region,subregion_name,site_id,cell_name,technology,rnc_bsc_site_name,vendor,mo,parameter,current_value,proposed_value,redline,atoll_update_required,implementation_date,oss,band,device_number' AS line
),
rows_ordered AS (
  SELECT *
  FROM public.grid_report_rows(p_form_key, p_start_time, p_end_time)
  ORDER BY ticket_start_time, ticket_number, excel_row_no
),
data_lines AS (
  SELECT
    grid_report_csv_escape(excel_row_no::text) || ',' ||
    grid_report_csv_escape(ticket_title) || ',' ||
    grid_report_csv_escape(ticket_number) || ',' ||
    grid_report_csv_escape(ticket_status) || ',' ||
    grid_report_csv_escape(ticket_creator) || ',' ||
    grid_report_csv_escape(ticket_end_time::text) || ',' ||
    grid_report_csv_escape(ticket_start_time::text) || ',' ||
    grid_report_csv_escape(task_assignee) || ',' ||
    grid_report_csv_escape(cm_ready_report_time_start::text) || ',' ||
    grid_report_csv_escape(cm_ready_report_time_end::text) || ',' ||
    grid_report_csv_escape(ola::text) || ',' ||
    grid_report_csv_escape(ticket_ola::text) || ',' ||
    grid_report_csv_escape(cr_no) || ',' ||
    grid_report_csv_escape(cr_type) || ',' ||
    grid_report_csv_escape(mvo) || ',' ||
    grid_report_csv_escape(region) || ',' ||
    grid_report_csv_escape(subregion_name) || ',' ||
    grid_report_csv_escape(site_id) || ',' ||
    grid_report_csv_escape(cell_name) || ',' ||
    grid_report_csv_escape(technology) || ',' ||
    grid_report_csv_escape(rnc_bsc_site_name) || ',' ||
    grid_report_csv_escape(vendor) || ',' ||
    grid_report_csv_escape(mo) || ',' ||
    grid_report_csv_escape(parameter) || ',' ||
    grid_report_csv_escape(current_value) || ',' ||
    grid_report_csv_escape(proposed_value) || ',' ||
    grid_report_csv_escape(redline) || ',' ||
    grid_report_csv_escape(atoll_update_required) || ',' ||
    grid_report_csv_escape(implementation_date) || ',' ||
    grid_report_csv_escape(oss) || ',' ||
    grid_report_csv_escape(band) || ',' ||
    grid_report_csv_escape(device_number) AS line
  FROM rows_ordered
),
all_lines AS (
  SELECT 0 AS ord, line FROM header
  UNION ALL
  SELECT row_number() OVER ()::bigint, line FROM data_lines
)
SELECT string_agg(line, E'\n' ORDER BY ord)
FROM all_lines;
$$;

-- Return CSV as one line per row (no wrapping quotes when using COPY TO STDOUT)
CREATE OR REPLACE FUNCTION public.grid_report_csv_lines(
    p_form_key   text,
    p_start_time timestamp,
    p_end_time   timestamp
)
RETURNS SETOF text
LANGUAGE sql
STABLE
AS $$
WITH
header AS (
  SELECT 0 AS ord, 'excel_row_no,ticket_title,ticket_number,ticket_status,ticket_creator,ticket_end_time,ticket_start_time,task_assignee,cm_ready_report_time_start,cm_ready_report_time_end,ola,ticket_ola,cr_no,cr_type,mvo,region,subregion_name,site_id,cell_name,technology,rnc_bsc_site_name,vendor,mo,parameter,current_value,proposed_value,redline,atoll_update_required,implementation_date,oss,band,device_number' AS line
),
rows_ordered AS (
  SELECT *
  FROM public.grid_report_rows(p_form_key, p_start_time, p_end_time)
  ORDER BY ticket_start_time, ticket_number, excel_row_no
),
data_lines AS (
  SELECT
    (row_number() OVER ())::bigint AS ord,
    grid_report_csv_escape(excel_row_no::text) || ',' ||
    grid_report_csv_escape(ticket_title) || ',' ||
    grid_report_csv_escape(ticket_number) || ',' ||
    grid_report_csv_escape(ticket_status) || ',' ||
    grid_report_csv_escape(ticket_creator) || ',' ||
    grid_report_csv_escape(ticket_end_time::text) || ',' ||
    grid_report_csv_escape(ticket_start_time::text) || ',' ||
    grid_report_csv_escape(task_assignee) || ',' ||
    grid_report_csv_escape(cm_ready_report_time_start::text) || ',' ||
    grid_report_csv_escape(cm_ready_report_time_end::text) || ',' ||
    grid_report_csv_escape(ola::text) || ',' ||
    grid_report_csv_escape(ticket_ola::text) || ',' ||
    grid_report_csv_escape(cr_no) || ',' ||
    grid_report_csv_escape(cr_type) || ',' ||
    grid_report_csv_escape(mvo) || ',' ||
    grid_report_csv_escape(region) || ',' ||
    grid_report_csv_escape(subregion_name) || ',' ||
    grid_report_csv_escape(site_id) || ',' ||
    grid_report_csv_escape(cell_name) || ',' ||
    grid_report_csv_escape(technology) || ',' ||
    grid_report_csv_escape(rnc_bsc_site_name) || ',' ||
    grid_report_csv_escape(vendor) || ',' ||
    grid_report_csv_escape(mo) || ',' ||
    grid_report_csv_escape(parameter) || ',' ||
    grid_report_csv_escape(current_value) || ',' ||
    grid_report_csv_escape(proposed_value) || ',' ||
    grid_report_csv_escape(redline) || ',' ||
    grid_report_csv_escape(atoll_update_required) || ',' ||
    grid_report_csv_escape(implementation_date) || ',' ||
    grid_report_csv_escape(oss) || ',' ||
    grid_report_csv_escape(band) || ',' ||
    grid_report_csv_escape(device_number) AS line
  FROM rows_ordered
),
all_lines AS (
  SELECT ord, line FROM header
  UNION ALL
  SELECT ord, line FROM data_lines
)
SELECT line
FROM all_lines
ORDER BY ord;
$$;
