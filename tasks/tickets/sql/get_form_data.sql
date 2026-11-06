create or replace function public.get_form_data(p_form_keys text[])
    returns TABLE(form_name text, form_key text, form_version integer, form_deployment_id text, form_content bytea, create_time timestamp with time zone)
    stable
    language sql
as
$$
    SELECT DISTINCT ON (arc.key_)
        arc.resource_name_ AS form_name,
        arc.key_ AS form_key,
        arc.version_ AS form_version,
        arc.deployment_id_ AS form_deployment_id,
        agb.bytes_ AS form_content,
        agb.create_time_ AS create_time
    FROM act_re_camformdef arc
    LEFT JOIN act_ge_bytearray agb
        ON arc.deployment_id_ = agb.deployment_id_
    WHERE arc.key_ = ANY(p_form_keys)
    ORDER BY
        arc.key_,
        arc.version_ DESC;
$$;

alter function public.get_form_data(text[]) owner to camunda;
