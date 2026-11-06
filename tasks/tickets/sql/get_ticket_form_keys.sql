create or replace function public.get_ticket_form_keys(p_deployment_id text)
    returns TABLE(
        resource_name text,
        deployment_id_ text,
        create_time timestamp with time zone,
        activity_type text,
        activity_id text,
        activity_name text,
        form_key text
    )
    stable
    language sql
as
$$
WITH src AS (
    SELECT
        id_ AS resource_id,
        name_ AS resource_name,
        deployment_id_,
        create_time_,
        convert_from(bytes_, 'UTF8') AS xml
    FROM act_ge_bytearray
    WHERE deployment_id_ = p_deployment_id
      AND name_ LIKE '%.bpmn'
),
activities_raw AS (
    SELECT
        resource_id,
        'startEvent' AS activity_type,
        unnest(
            regexp_matches(
                xml,
                '<bpmn:startEvent[^>]*>',
                'g'
            )
        ) AS tag
    FROM src

    UNION ALL

    SELECT
        resource_id,
        'userTask' AS activity_type,
        unnest(
            regexp_matches(
                xml,
                '<bpmn:userTask[^>]*>',
                'g'
            )
        ) AS tag
    FROM src
),
activities AS (
    SELECT
        resource_id,
        activity_type,
        (regexp_match(tag, 'id="([^"]+)"'))[1] AS activity_id,
        (regexp_match(tag, 'name="([^"]+)"'))[1] AS activity_name,
        (regexp_match(tag, 'camunda:formRef="([^"]+)"'))[1] AS form_key
    FROM activities_raw
)
SELECT
    s.resource_name,
    s.deployment_id_,
    s.create_time_,
    a.activity_type,
    a.activity_id,
    a.activity_name,
    a.form_key
FROM src s
LEFT JOIN activities a ON a.resource_id = s.resource_id;
$$;

alter function public.get_ticket_form_keys(text) owner to camunda;
