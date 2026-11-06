create database camunda
    with owner camunda;

create table public.act_ge_property
(
    name_  varchar(64) not null
        primary key,
    value_ varchar(300),
    rev_   integer
);

alter table public.act_ge_property
    owner to camunda;

create table public.act_ge_schema_log
(
    id_        varchar(64) not null
        primary key,
    timestamp_ timestamp,
    version_   varchar(255)
);

alter table public.act_ge_schema_log
    owner to camunda;

create table public.act_re_deployment
(
    id_          varchar(64) not null
        primary key,
    name_        varchar(255),
    deploy_time_ timestamp,
    source_      varchar(255),
    tenant_id_   varchar(64)
);

alter table public.act_re_deployment
    owner to camunda;

create table public.act_ge_bytearray
(
    id_                varchar(64) not null
        primary key,
    rev_               integer,
    name_              varchar(255),
    deployment_id_     varchar(64)
        constraint act_fk_bytearr_depl
            references public.act_re_deployment,
    bytes_             bytea,
    generated_         boolean,
    tenant_id_         varchar(64),
    type_              integer,
    create_time_       timestamp,
    root_proc_inst_id_ varchar(64),
    removal_time_      timestamp
);

alter table public.act_ge_bytearray
    owner to camunda;

create index act_idx_bytear_depl
    on public.act_ge_bytearray (deployment_id_);

create index act_idx_bytearray_root_pi
    on public.act_ge_bytearray (root_proc_inst_id_);

create index act_idx_bytearray_rm_time
    on public.act_ge_bytearray (removal_time_);

create index act_idx_bytearray_name
    on public.act_ge_bytearray (name_);

create index act_idx_deployment_name
    on public.act_re_deployment (name_);

create index act_idx_deployment_tenant_id
    on public.act_re_deployment (tenant_id_);

create table public.act_ru_job
(
    id_                  varchar(64)       not null
        primary key,
    rev_                 integer,
    type_                varchar(255)      not null,
    lock_exp_time_       timestamp,
    lock_owner_          varchar(255),
    exclusive_           boolean,
    execution_id_        varchar(64),
    root_proc_inst_id_   varchar(64),
    process_instance_id_ varchar(64),
    process_def_id_      varchar(64),
    process_def_key_     varchar(255),
    retries_             integer,
    exception_stack_id_  varchar(64)
        constraint act_fk_job_exception
            references public.act_ge_bytearray,
    exception_msg_       varchar(4000),
    failed_act_id_       varchar(255),
    duedate_             timestamp,
    repeat_              varchar(255),
    repeat_offset_       bigint  default 0,
    handler_type_        varchar(255),
    handler_cfg_         varchar(4000),
    deployment_id_       varchar(64),
    suspension_state_    integer default 1 not null,
    job_def_id_          varchar(64),
    priority_            bigint  default 0 not null,
    sequence_counter_    bigint,
    tenant_id_           varchar(64),
    create_time_         timestamp,
    last_failure_log_id_ varchar(64),
    batch_id_            varchar(64)
);

alter table public.act_ru_job
    owner to camunda;

create index act_idx_job_execution_id
    on public.act_ru_job (execution_id_);

create index act_idx_job_handler
    on public.act_ru_job (handler_type_, handler_cfg_);

create index act_idx_job_procinst
    on public.act_ru_job (process_instance_id_);

create index act_idx_job_root_procinst
    on public.act_ru_job (root_proc_inst_id_);

create index act_idx_job_tenant_id
    on public.act_ru_job (tenant_id_);

create index act_idx_job_job_def_id
    on public.act_ru_job (job_def_id_);

create index act_idx_job_exception
    on public.act_ru_job (exception_stack_id_);

create index act_idx_job_handler_type
    on public.act_ru_job (handler_type_);

create table public.act_ru_jobdef
(
    id_                varchar(64)  not null
        primary key,
    rev_               integer,
    proc_def_id_       varchar(64),
    proc_def_key_      varchar(255),
    act_id_            varchar(255),
    job_type_          varchar(255) not null,
    job_configuration_ varchar(255),
    suspension_state_  integer,
    job_priority_      bigint,
    tenant_id_         varchar(64),
    deployment_id_     varchar(64)
);

alter table public.act_ru_jobdef
    owner to camunda;

create index act_idx_jobdef_tenant_id
    on public.act_ru_jobdef (tenant_id_);

create index act_idx_jobdef_proc_def_id
    on public.act_ru_jobdef (proc_def_id_);

create table public.act_re_procdef
(
    id_                 varchar(64)          not null
        primary key,
    rev_                integer,
    category_           varchar(255),
    name_               varchar(255),
    key_                varchar(255)         not null,
    version_            integer              not null,
    deployment_id_      varchar(64),
    resource_name_      varchar(4000),
    dgrm_resource_name_ varchar(4000),
    has_start_form_key_ boolean,
    suspension_state_   integer,
    tenant_id_          varchar(64),
    version_tag_        varchar(64),
    history_ttl_        integer,
    startable_          boolean default true not null
);

alter table public.act_re_procdef
    owner to camunda;

create table public.act_ru_execution
(
    id_                varchar(64) not null
        primary key,
    rev_               integer,
    root_proc_inst_id_ varchar(64),
    proc_inst_id_      varchar(64)
        constraint act_fk_exe_procinst
            references public.act_ru_execution,
    business_key_      varchar(255),
    parent_id_         varchar(64)
        constraint act_fk_exe_parent
            references public.act_ru_execution,
    proc_def_id_       varchar(64)
        constraint act_fk_exe_procdef
            references public.act_re_procdef,
    super_exec_        varchar(64)
        constraint act_fk_exe_super
            references public.act_ru_execution,
    super_case_exec_   varchar(64),
    case_inst_id_      varchar(64),
    act_id_            varchar(255),
    act_inst_id_       varchar(64),
    is_active_         boolean,
    is_concurrent_     boolean,
    is_scope_          boolean,
    is_event_scope_    boolean,
    suspension_state_  integer,
    cached_ent_state_  integer,
    sequence_counter_  bigint,
    tenant_id_         varchar(64),
    proc_def_key_      varchar(255)
);

alter table public.act_ru_execution
    owner to camunda;

create index act_idx_exe_root_pi
    on public.act_ru_execution (root_proc_inst_id_);

create index act_idx_exec_buskey
    on public.act_ru_execution (business_key_);

create index act_idx_exec_tenant_id
    on public.act_ru_execution (tenant_id_);

create index act_idx_exe_procinst
    on public.act_ru_execution (proc_inst_id_);

create index act_idx_exe_parent
    on public.act_ru_execution (parent_id_);

create index act_idx_exe_super
    on public.act_ru_execution (super_exec_);

create index act_idx_exe_procdef
    on public.act_ru_execution (proc_def_id_);

create index act_idx_procdef_deployment_id
    on public.act_re_procdef (deployment_id_);

create index act_idx_procdef_tenant_id
    on public.act_re_procdef (tenant_id_);

create index act_idx_procdef_ver_tag
    on public.act_re_procdef (version_tag_);

create table public.act_re_camformdef
(
    id_            varchar(64)  not null
        primary key,
    rev_           integer,
    key_           varchar(255) not null,
    version_       integer      not null,
    deployment_id_ varchar(64),
    resource_name_ varchar(4000),
    tenant_id_     varchar(64)
);

alter table public.act_re_camformdef
    owner to camunda;

create table public.act_ru_event_subscr
(
    id_            varchar(64)  not null
        primary key,
    rev_           integer,
    event_type_    varchar(255) not null,
    event_name_    varchar(255),
    execution_id_  varchar(64)
        constraint act_fk_event_exec
            references public.act_ru_execution,
    proc_inst_id_  varchar(64),
    activity_id_   varchar(255),
    configuration_ varchar(255),
    created_       timestamp    not null,
    tenant_id_     varchar(64)
);

alter table public.act_ru_event_subscr
    owner to camunda;

create index act_idx_event_subscr_config_
    on public.act_ru_event_subscr (configuration_);

create index act_idx_event_subscr_tenant_id
    on public.act_ru_event_subscr (tenant_id_);

create index act_idx_event_subscr
    on public.act_ru_event_subscr (execution_id_);

create index act_idx_event_subscr_evt_name
    on public.act_ru_event_subscr (event_name_);

create table public.act_ru_incident
(
    id_                     varchar(64)  not null
        primary key,
    rev_                    integer      not null,
    incident_timestamp_     timestamp    not null,
    incident_msg_           varchar(4000),
    incident_type_          varchar(255) not null,
    execution_id_           varchar(64)
        constraint act_fk_inc_exe
            references public.act_ru_execution,
    activity_id_            varchar(255),
    failed_activity_id_     varchar(255),
    proc_inst_id_           varchar(64)
        constraint act_fk_inc_procinst
            references public.act_ru_execution,
    proc_def_id_            varchar(64)
        constraint act_fk_inc_procdef
            references public.act_re_procdef,
    cause_incident_id_      varchar(64)
        constraint act_fk_inc_cause
            references public.act_ru_incident,
    root_cause_incident_id_ varchar(64)
        constraint act_fk_inc_rcause
            references public.act_ru_incident,
    configuration_          varchar(255),
    tenant_id_              varchar(64),
    job_def_id_             varchar(64)
        constraint act_fk_inc_job_def
            references public.act_ru_jobdef,
    annotation_             varchar(4000)
);

alter table public.act_ru_incident
    owner to camunda;

create index act_idx_inc_configuration
    on public.act_ru_incident (configuration_);

create index act_idx_inc_tenant_id
    on public.act_ru_incident (tenant_id_);

create index act_idx_inc_job_def
    on public.act_ru_incident (job_def_id_);

create index act_idx_inc_causeincid
    on public.act_ru_incident (cause_incident_id_);

create index act_idx_inc_exid
    on public.act_ru_incident (execution_id_);

create index act_idx_inc_procdefid
    on public.act_ru_incident (proc_def_id_);

create index act_idx_inc_procinstid
    on public.act_ru_incident (proc_inst_id_);

create index act_idx_inc_rootcauseincid
    on public.act_ru_incident (root_cause_incident_id_);

create table public.act_ru_authorization
(
    id_                varchar(64) not null
        primary key,
    rev_               integer     not null,
    type_              integer     not null,
    group_id_          varchar(255),
    user_id_           varchar(255),
    resource_type_     integer     not null,
    resource_id_       varchar(255),
    perms_             integer,
    removal_time_      timestamp,
    root_proc_inst_id_ varchar(64),
    constraint act_uniq_auth_user
        unique (type_, user_id_, resource_type_, resource_id_),
    constraint act_uniq_auth_group
        unique (type_, group_id_, resource_type_, resource_id_)
);

alter table public.act_ru_authorization
    owner to camunda;

create index act_idx_auth_group_id
    on public.act_ru_authorization (group_id_);

create index act_idx_auth_resource_id
    on public.act_ru_authorization (resource_id_);

create index act_idx_auth_root_pi
    on public.act_ru_authorization (root_proc_inst_id_);

create index act_idx_auth_rm_time
    on public.act_ru_authorization (removal_time_);

create table public.act_ru_filter
(
    id_            varchar(64)  not null
        primary key,
    rev_           integer      not null,
    resource_type_ varchar(255) not null,
    name_          varchar(255) not null,
    owner_         varchar(255),
    query_         text         not null,
    properties_    text
);

alter table public.act_ru_filter
    owner to camunda;

create table public.act_ru_meter_log
(
    id_           varchar(64) not null
        primary key,
    name_         varchar(64) not null,
    reporter_     varchar(255),
    value_        bigint,
    timestamp_    timestamp,
    milliseconds_ bigint default 0
);

alter table public.act_ru_meter_log
    owner to camunda;

create index act_idx_meter_log_ms
    on public.act_ru_meter_log (milliseconds_);

create index act_idx_meter_log_name_ms
    on public.act_ru_meter_log (name_, milliseconds_);

create index act_idx_meter_log_report
    on public.act_ru_meter_log (name_, reporter_, milliseconds_);

create index act_idx_meter_log_time
    on public.act_ru_meter_log (timestamp_);

create index act_idx_meter_log
    on public.act_ru_meter_log (name_, timestamp_);

create table public.act_ru_task_meter_log
(
    id_            varchar(64) not null
        primary key,
    assignee_hash_ bigint,
    timestamp_     timestamp
);

alter table public.act_ru_task_meter_log
    owner to camunda;

create index act_idx_task_meter_log_time
    on public.act_ru_task_meter_log (timestamp_);

create table public.act_ru_ext_task
(
    id_                  varchar(64)      not null
        primary key,
    rev_                 integer          not null,
    worker_id_           varchar(255),
    topic_name_          varchar(255),
    retries_             integer,
    error_msg_           varchar(4000),
    error_details_id_    varchar(64)
        constraint act_fk_ext_task_error_details
            references public.act_ge_bytearray,
    lock_exp_time_       timestamp,
    create_time_         timestamp,
    suspension_state_    integer,
    execution_id_        varchar(64)
        constraint act_fk_ext_task_exe
            references public.act_ru_execution,
    proc_inst_id_        varchar(64),
    proc_def_id_         varchar(64),
    proc_def_key_        varchar(255),
    act_id_              varchar(255),
    act_inst_id_         varchar(64),
    tenant_id_           varchar(64),
    priority_            bigint default 0 not null,
    last_failure_log_id_ varchar(64)
);

alter table public.act_ru_ext_task
    owner to camunda;

create index act_idx_ext_task_topic
    on public.act_ru_ext_task (topic_name_);

create index act_idx_ext_task_tenant_id
    on public.act_ru_ext_task (tenant_id_);

create index act_idx_ext_task_priority
    on public.act_ru_ext_task (priority_);

create index act_idx_ext_task_err_details
    on public.act_ru_ext_task (error_details_id_);

create index act_idx_ext_task_exec
    on public.act_ru_ext_task (execution_id_);

create table public.act_ru_batch
(
    id_                  varchar(64) not null
        primary key,
    rev_                 integer     not null,
    type_                varchar(255),
    total_jobs_          integer,
    jobs_created_        integer,
    jobs_per_seed_       integer,
    invocations_per_job_ integer,
    seed_job_def_id_     varchar(64)
        constraint act_fk_batch_seed_job_def
            references public.act_ru_jobdef,
    batch_job_def_id_    varchar(64)
        constraint act_fk_batch_job_def
            references public.act_ru_jobdef,
    monitor_job_def_id_  varchar(64)
        constraint act_fk_batch_monitor_job_def
            references public.act_ru_jobdef,
    suspension_state_    integer,
    configuration_       varchar(255),
    tenant_id_           varchar(64),
    create_user_id_      varchar(255),
    start_time_          timestamp,
    exec_start_time_     timestamp
);

alter table public.act_ru_batch
    owner to camunda;

create index act_idx_batch_seed_job_def
    on public.act_ru_batch (seed_job_def_id_);

create index act_idx_batch_monitor_job_def
    on public.act_ru_batch (monitor_job_def_id_);

create index act_idx_batch_job_def
    on public.act_ru_batch (batch_job_def_id_);

create table public.act_hi_procinst
(
    id_                        varchar(64) not null
        primary key,
    proc_inst_id_              varchar(64) not null
        unique,
    business_key_              varchar(255),
    proc_def_key_              varchar(255),
    proc_def_id_               varchar(64) not null,
    start_time_                timestamp   not null,
    end_time_                  timestamp,
    removal_time_              timestamp,
    duration_                  bigint,
    start_user_id_             varchar(255),
    start_act_id_              varchar(255),
    end_act_id_                varchar(255),
    super_process_instance_id_ varchar(64),
    root_proc_inst_id_         varchar(64),
    super_case_instance_id_    varchar(64),
    case_inst_id_              varchar(64),
    delete_reason_             varchar(4000),
    tenant_id_                 varchar(64),
    state_                     varchar(255),
    restarted_proc_inst_id_    varchar(64)
);

alter table public.act_hi_procinst
    owner to camunda;

create index act_idx_hi_pro_inst_end
    on public.act_hi_procinst (end_time_);

create index act_idx_hi_pro_i_buskey
    on public.act_hi_procinst (business_key_);

create index act_idx_hi_pro_inst_tenant_id
    on public.act_hi_procinst (tenant_id_);

create index act_idx_hi_pro_inst_proc_def_key
    on public.act_hi_procinst (proc_def_key_);

create index act_idx_hi_pro_inst_proc_time
    on public.act_hi_procinst (start_time_, end_time_);

create index act_idx_hi_pi_pdefid_end_time
    on public.act_hi_procinst (proc_def_id_, end_time_);

create index act_idx_hi_pro_inst_root_pi
    on public.act_hi_procinst (root_proc_inst_id_);

create index act_idx_hi_pro_inst_rm_time
    on public.act_hi_procinst (removal_time_);

create index act_idx_hi_pro_rst_pro_inst_id
    on public.act_hi_procinst (restarted_proc_inst_id_);

create table public.act_hi_actinst
(
    id_                 varchar(64)  not null
        primary key,
    parent_act_inst_id_ varchar(64),
    proc_def_key_       varchar(255),
    proc_def_id_        varchar(64)  not null,
    root_proc_inst_id_  varchar(64),
    proc_inst_id_       varchar(64)  not null,
    execution_id_       varchar(64)  not null,
    act_id_             varchar(255) not null,
    task_id_            varchar(64),
    call_proc_inst_id_  varchar(64),
    call_case_inst_id_  varchar(64),
    act_name_           varchar(255),
    act_type_           varchar(255) not null,
    assignee_           varchar(255),
    start_time_         timestamp    not null,
    end_time_           timestamp,
    duration_           bigint,
    act_inst_state_     integer,
    sequence_counter_   bigint,
    tenant_id_          varchar(64),
    removal_time_       timestamp
);

alter table public.act_hi_actinst
    owner to camunda;

create index act_idx_hi_actinst_root_pi
    on public.act_hi_actinst (root_proc_inst_id_);

create index act_idx_hi_act_inst_start_end
    on public.act_hi_actinst (start_time_, end_time_);

create index act_idx_hi_act_inst_end
    on public.act_hi_actinst (end_time_);

create index act_idx_hi_act_inst_procinst
    on public.act_hi_actinst (proc_inst_id_, act_id_);

create index act_idx_hi_act_inst_comp
    on public.act_hi_actinst (execution_id_, act_id_, end_time_, id_);

create index act_idx_hi_act_inst_stats
    on public.act_hi_actinst (proc_def_id_, proc_inst_id_, act_id_, end_time_, act_inst_state_);

create index act_idx_hi_act_inst_tenant_id
    on public.act_hi_actinst (tenant_id_);

create index act_idx_hi_act_inst_proc_def_key
    on public.act_hi_actinst (proc_def_key_);

create index act_idx_hi_ai_pdefid_end_time
    on public.act_hi_actinst (proc_def_id_, end_time_);

create index act_idx_hi_act_inst_rm_time
    on public.act_hi_actinst (removal_time_);

create table public.act_hi_taskinst
(
    id_                varchar(64) not null
        primary key,
    task_def_key_      varchar(255),
    proc_def_key_      varchar(255),
    proc_def_id_       varchar(64),
    root_proc_inst_id_ varchar(64),
    proc_inst_id_      varchar(64),
    execution_id_      varchar(64),
    case_def_key_      varchar(255),
    case_def_id_       varchar(64),
    case_inst_id_      varchar(64),
    case_execution_id_ varchar(64),
    act_inst_id_       varchar(64),
    name_              varchar(255),
    parent_task_id_    varchar(64),
    description_       varchar(4000),
    owner_             varchar(255),
    assignee_          varchar(255),
    start_time_        timestamp   not null,
    end_time_          timestamp,
    duration_          bigint,
    delete_reason_     varchar(4000),
    priority_          integer,
    due_date_          timestamp,
    follow_up_date_    timestamp,
    tenant_id_         varchar(64),
    removal_time_      timestamp,
    task_state_        varchar(64)
);

alter table public.act_hi_taskinst
    owner to camunda;

create index act_idx_hi_taskinst_root_pi
    on public.act_hi_taskinst (root_proc_inst_id_);

create index act_idx_hi_task_inst_tenant_id
    on public.act_hi_taskinst (tenant_id_);

create index act_idx_hi_task_inst_proc_def_key
    on public.act_hi_taskinst (proc_def_key_);

create index act_idx_hi_taskinst_procinst
    on public.act_hi_taskinst (proc_inst_id_);

create index act_idx_hi_taskinstid_procinst
    on public.act_hi_taskinst (id_, proc_inst_id_);

create index act_idx_hi_task_inst_rm_time
    on public.act_hi_taskinst (removal_time_);

create index act_idx_hi_task_inst_start
    on public.act_hi_taskinst (start_time_);

create index act_idx_hi_task_inst_end
    on public.act_hi_taskinst (end_time_);

create table public.act_hi_varinst
(
    id_                varchar(64)  not null
        primary key,
    proc_def_key_      varchar(255),
    proc_def_id_       varchar(64),
    root_proc_inst_id_ varchar(64),
    proc_inst_id_      varchar(64),
    execution_id_      varchar(64),
    act_inst_id_       varchar(64),
    case_def_key_      varchar(255),
    case_def_id_       varchar(64),
    case_inst_id_      varchar(64),
    case_execution_id_ varchar(64),
    task_id_           varchar(64),
    name_              varchar(255) not null,
    var_type_          varchar(100),
    create_time_       timestamp,
    rev_               integer,
    bytearray_id_      varchar(64),
    double_            double precision,
    long_              bigint,
    text_              varchar(4000),
    text2_             varchar(4000),
    tenant_id_         varchar(64),
    state_             varchar(20),
    removal_time_      timestamp
);

alter table public.act_hi_varinst
    owner to camunda;

create index act_idx_hi_varinst_root_pi
    on public.act_hi_varinst (root_proc_inst_id_);

create index act_idx_hi_procvar_proc_inst
    on public.act_hi_varinst (proc_inst_id_);

create index act_idx_hi_procvar_name_type
    on public.act_hi_varinst (name_, var_type_);

create index act_idx_hi_casevar_case_inst
    on public.act_hi_varinst (case_inst_id_);

create index act_idx_hi_var_inst_tenant_id
    on public.act_hi_varinst (tenant_id_);

create index act_idx_hi_var_inst_proc_def_key
    on public.act_hi_varinst (proc_def_key_);

create index act_idx_hi_varinst_bytear
    on public.act_hi_varinst (bytearray_id_);

create index act_idx_hi_varinst_rm_time
    on public.act_hi_varinst (removal_time_);

create index act_idx_hi_var_pi_name_type
    on public.act_hi_varinst (proc_inst_id_, name_, var_type_);

create index act_idx_hi_varinst_name
    on public.act_hi_varinst (name_);

create index act_idx_hi_varinst_act_inst_id
    on public.act_hi_varinst (act_inst_id_);

create table public.act_hi_detail
(
    id_                varchar(64)  not null
        primary key,
    type_              varchar(255) not null,
    proc_def_key_      varchar(255),
    proc_def_id_       varchar(64),
    root_proc_inst_id_ varchar(64),
    proc_inst_id_      varchar(64),
    execution_id_      varchar(64),
    case_def_key_      varchar(255),
    case_def_id_       varchar(64),
    case_inst_id_      varchar(64),
    case_execution_id_ varchar(64),
    task_id_           varchar(64),
    act_inst_id_       varchar(64),
    var_inst_id_       varchar(64),
    name_              varchar(255) not null,
    var_type_          varchar(64),
    rev_               integer,
    time_              timestamp    not null,
    bytearray_id_      varchar(64),
    double_            double precision,
    long_              bigint,
    text_              varchar(4000),
    text2_             varchar(4000),
    sequence_counter_  bigint,
    tenant_id_         varchar(64),
    operation_id_      varchar(64),
    removal_time_      timestamp,
    initial_           boolean
);

alter table public.act_hi_detail
    owner to camunda;

create index act_idx_hi_detail_root_pi
    on public.act_hi_detail (root_proc_inst_id_);

create index act_idx_hi_detail_proc_inst
    on public.act_hi_detail (proc_inst_id_);

create index act_idx_hi_detail_act_inst
    on public.act_hi_detail (act_inst_id_);

create index act_idx_hi_detail_case_inst
    on public.act_hi_detail (case_inst_id_);

create index act_idx_hi_detail_case_exec
    on public.act_hi_detail (case_execution_id_);

create index act_idx_hi_detail_time
    on public.act_hi_detail (time_);

create index act_idx_hi_detail_name
    on public.act_hi_detail (name_);

create index act_idx_hi_detail_task_id
    on public.act_hi_detail (task_id_);

create index act_idx_hi_detail_tenant_id
    on public.act_hi_detail (tenant_id_);

create index act_idx_hi_detail_proc_def_key
    on public.act_hi_detail (proc_def_key_);

create index act_idx_hi_detail_bytear
    on public.act_hi_detail (bytearray_id_);

create index act_idx_hi_detail_rm_time
    on public.act_hi_detail (removal_time_);

create index act_idx_hi_detail_task_bytear
    on public.act_hi_detail (bytearray_id_, task_id_);

create index act_idx_hi_detail_var_inst_id
    on public.act_hi_detail (var_inst_id_);

create table public.act_hi_identitylink
(
    id_                varchar(64) not null
        primary key,
    timestamp_         timestamp   not null,
    type_              varchar(255),
    user_id_           varchar(255),
    group_id_          varchar(255),
    task_id_           varchar(64),
    root_proc_inst_id_ varchar(64),
    proc_def_id_       varchar(64),
    operation_type_    varchar(64),
    assigner_id_       varchar(64),
    proc_def_key_      varchar(255),
    tenant_id_         varchar(64),
    removal_time_      timestamp
);

alter table public.act_hi_identitylink
    owner to camunda;

create index act_idx_hi_ident_lnk_root_pi
    on public.act_hi_identitylink (root_proc_inst_id_);

create index act_idx_hi_ident_lnk_user
    on public.act_hi_identitylink (user_id_);

create index act_idx_hi_ident_lnk_group
    on public.act_hi_identitylink (group_id_);

create index act_idx_hi_ident_lnk_tenant_id
    on public.act_hi_identitylink (tenant_id_);

create index act_idx_hi_ident_lnk_proc_def_key
    on public.act_hi_identitylink (proc_def_key_);

create index act_idx_hi_ident_link_task
    on public.act_hi_identitylink (task_id_);

create index act_idx_hi_ident_link_rm_time
    on public.act_hi_identitylink (removal_time_);

create index act_idx_hi_ident_lnk_timestamp
    on public.act_hi_identitylink (timestamp_);

create table public.act_hi_comment
(
    id_                varchar(64)       not null
        primary key,
    type_              varchar(255),
    time_              timestamp         not null,
    user_id_           varchar(255),
    task_id_           varchar(64),
    root_proc_inst_id_ varchar(64),
    proc_inst_id_      varchar(64),
    action_            varchar(255),
    message_           varchar(4000),
    full_msg_          bytea,
    tenant_id_         varchar(64),
    removal_time_      timestamp,
    rev_               integer default 1 not null
);

alter table public.act_hi_comment
    owner to camunda;

create index act_idx_hi_comment_task
    on public.act_hi_comment (task_id_);

create index act_idx_hi_comment_root_pi
    on public.act_hi_comment (root_proc_inst_id_);

create index act_idx_hi_comment_procinst
    on public.act_hi_comment (proc_inst_id_);

create index act_idx_hi_comment_rm_time
    on public.act_hi_comment (removal_time_);

create table public.act_hi_attachment
(
    id_                varchar(64) not null
        primary key,
    rev_               integer,
    user_id_           varchar(255),
    name_              varchar(255),
    description_       varchar(4000),
    type_              varchar(255),
    task_id_           varchar(64),
    root_proc_inst_id_ varchar(64),
    proc_inst_id_      varchar(64),
    url_               varchar(4000),
    content_id_        varchar(64),
    tenant_id_         varchar(64),
    create_time_       timestamp,
    removal_time_      timestamp
);

alter table public.act_hi_attachment
    owner to camunda;

create index act_idx_hi_attachment_content
    on public.act_hi_attachment (content_id_);

create index act_idx_hi_attachment_root_pi
    on public.act_hi_attachment (root_proc_inst_id_);

create index act_idx_hi_attachment_procinst
    on public.act_hi_attachment (proc_inst_id_);

create index act_idx_hi_attachment_task
    on public.act_hi_attachment (task_id_);

create index act_idx_hi_attachment_rm_time
    on public.act_hi_attachment (removal_time_);

create table public.act_hi_op_log
(
    id_                varchar(64) not null
        primary key,
    deployment_id_     varchar(64),
    proc_def_id_       varchar(64),
    proc_def_key_      varchar(255),
    root_proc_inst_id_ varchar(64),
    proc_inst_id_      varchar(64),
    execution_id_      varchar(64),
    case_def_id_       varchar(64),
    case_inst_id_      varchar(64),
    case_execution_id_ varchar(64),
    task_id_           varchar(64),
    job_id_            varchar(64),
    job_def_id_        varchar(64),
    batch_id_          varchar(64),
    user_id_           varchar(255),
    timestamp_         timestamp   not null,
    operation_type_    varchar(64),
    operation_id_      varchar(64),
    entity_type_       varchar(30),
    property_          varchar(64),
    org_value_         varchar(4000),
    new_value_         varchar(4000),
    tenant_id_         varchar(64),
    removal_time_      timestamp,
    category_          varchar(64),
    external_task_id_  varchar(64),
    annotation_        varchar(4000)
);

alter table public.act_hi_op_log
    owner to camunda;

create index act_idx_hi_op_log_root_pi
    on public.act_hi_op_log (root_proc_inst_id_);

create index act_idx_hi_op_log_procinst
    on public.act_hi_op_log (proc_inst_id_);

create index act_idx_hi_op_log_procdef
    on public.act_hi_op_log (proc_def_id_);

create index act_idx_hi_op_log_task
    on public.act_hi_op_log (task_id_);

create index act_idx_hi_op_log_rm_time
    on public.act_hi_op_log (removal_time_);

create index act_idx_hi_op_log_timestamp
    on public.act_hi_op_log (timestamp_);

create index act_idx_hi_op_log_user_id
    on public.act_hi_op_log (user_id_);

create index act_idx_hi_op_log_op_type
    on public.act_hi_op_log (operation_type_);

create index act_idx_hi_op_log_entity_type
    on public.act_hi_op_log (entity_type_);

create table public.act_hi_incident
(
    id_                     varchar(64)  not null
        primary key,
    proc_def_key_           varchar(255),
    proc_def_id_            varchar(64),
    root_proc_inst_id_      varchar(64),
    proc_inst_id_           varchar(64),
    execution_id_           varchar(64),
    create_time_            timestamp    not null,
    end_time_               timestamp,
    incident_msg_           varchar(4000),
    incident_type_          varchar(255) not null,
    activity_id_            varchar(255),
    failed_activity_id_     varchar(255),
    cause_incident_id_      varchar(64),
    root_cause_incident_id_ varchar(64),
    configuration_          varchar(255),
    history_configuration_  varchar(255),
    incident_state_         integer,
    tenant_id_              varchar(64),
    job_def_id_             varchar(64),
    annotation_             varchar(4000),
    removal_time_           timestamp
);

alter table public.act_hi_incident
    owner to camunda;

create index act_idx_hi_incident_tenant_id
    on public.act_hi_incident (tenant_id_);

create index act_idx_hi_incident_proc_def_key
    on public.act_hi_incident (proc_def_key_);

create index act_idx_hi_incident_root_pi
    on public.act_hi_incident (root_proc_inst_id_);

create index act_idx_hi_incident_procinst
    on public.act_hi_incident (proc_inst_id_);

create index act_idx_hi_incident_rm_time
    on public.act_hi_incident (removal_time_);

create index act_idx_hi_incident_create_time
    on public.act_hi_incident (create_time_);

create index act_idx_hi_incident_end_time
    on public.act_hi_incident (end_time_);

create table public.act_hi_job_log
(
    id_                     varchar(64)      not null
        primary key,
    timestamp_              timestamp        not null,
    job_id_                 varchar(64)      not null,
    job_duedate_            timestamp,
    job_retries_            integer,
    job_priority_           bigint default 0 not null,
    job_exception_msg_      varchar(4000),
    job_exception_stack_id_ varchar(64),
    job_state_              integer,
    job_def_id_             varchar(64),
    job_def_type_           varchar(255),
    job_def_configuration_  varchar(255),
    act_id_                 varchar(255),
    failed_act_id_          varchar(255),
    execution_id_           varchar(64),
    root_proc_inst_id_      varchar(64),
    process_instance_id_    varchar(64),
    process_def_id_         varchar(64),
    process_def_key_        varchar(255),
    deployment_id_          varchar(64),
    sequence_counter_       bigint,
    tenant_id_              varchar(64),
    hostname_               varchar(255),
    removal_time_           timestamp,
    batch_id_               varchar(64)
);

alter table public.act_hi_job_log
    owner to camunda;

create index act_idx_hi_job_log_root_pi
    on public.act_hi_job_log (root_proc_inst_id_);

create index act_idx_hi_job_log_procinst
    on public.act_hi_job_log (process_instance_id_);

create index act_idx_hi_job_log_procdef
    on public.act_hi_job_log (process_def_id_);

create index act_idx_hi_job_log_tenant_id
    on public.act_hi_job_log (tenant_id_);

create index act_idx_hi_job_log_job_def_id
    on public.act_hi_job_log (job_def_id_);

create index act_idx_hi_job_log_proc_def_key
    on public.act_hi_job_log (process_def_key_);

create index act_idx_hi_job_log_ex_stack
    on public.act_hi_job_log (job_exception_stack_id_);

create index act_idx_hi_job_log_rm_time
    on public.act_hi_job_log (removal_time_);

create index act_idx_hi_job_log_job_conf
    on public.act_hi_job_log (job_def_configuration_);

create table public.act_hi_batch
(
    id_                  varchar(64) not null
        primary key,
    type_                varchar(255),
    total_jobs_          integer,
    jobs_per_seed_       integer,
    invocations_per_job_ integer,
    seed_job_def_id_     varchar(64),
    monitor_job_def_id_  varchar(64),
    batch_job_def_id_    varchar(64),
    tenant_id_           varchar(64),
    create_user_id_      varchar(255),
    start_time_          timestamp   not null,
    end_time_            timestamp,
    removal_time_        timestamp,
    exec_start_time_     timestamp
);

alter table public.act_hi_batch
    owner to camunda;

create index act_hi_bat_rm_time
    on public.act_hi_batch (removal_time_);

create table public.act_hi_ext_task_log
(
    id_                varchar(64)      not null
        primary key,
    timestamp_         timestamp        not null,
    ext_task_id_       varchar(64)      not null,
    retries_           integer,
    topic_name_        varchar(255),
    worker_id_         varchar(255),
    priority_          bigint default 0 not null,
    error_msg_         varchar(4000),
    error_details_id_  varchar(64),
    act_id_            varchar(255),
    act_inst_id_       varchar(64),
    execution_id_      varchar(64),
    proc_inst_id_      varchar(64),
    root_proc_inst_id_ varchar(64),
    proc_def_id_       varchar(64),
    proc_def_key_      varchar(255),
    tenant_id_         varchar(64),
    state_             integer,
    removal_time_      timestamp
);

alter table public.act_hi_ext_task_log
    owner to camunda;

create index act_hi_ext_task_log_root_pi
    on public.act_hi_ext_task_log (root_proc_inst_id_);

create index act_hi_ext_task_log_procinst
    on public.act_hi_ext_task_log (proc_inst_id_);

create index act_hi_ext_task_log_procdef
    on public.act_hi_ext_task_log (proc_def_id_);

create index act_hi_ext_task_log_proc_def_key
    on public.act_hi_ext_task_log (proc_def_key_);

create index act_hi_ext_task_log_tenant_id
    on public.act_hi_ext_task_log (tenant_id_);

create index act_idx_hi_exttasklog_errordet
    on public.act_hi_ext_task_log (error_details_id_);

create index act_hi_ext_task_log_rm_time
    on public.act_hi_ext_task_log (removal_time_);

create table public.act_id_group
(
    id_   varchar(64) not null
        primary key,
    rev_  integer,
    name_ varchar(255),
    type_ varchar(255)
);

alter table public.act_id_group
    owner to camunda;

create table public.act_id_user
(
    id_            varchar(64) not null
        primary key,
    rev_           integer,
    first_         varchar(255),
    last_          varchar(255),
    email_         varchar(255),
    pwd_           varchar(255),
    salt_          varchar(255),
    lock_exp_time_ timestamp,
    attempts_      integer,
    picture_id_    varchar(64)
);

alter table public.act_id_user
    owner to camunda;

create table public.act_id_membership
(
    user_id_  varchar(64) not null
        constraint act_fk_memb_user
            references public.act_id_user,
    group_id_ varchar(64) not null
        constraint act_fk_memb_group
            references public.act_id_group,
    primary key (user_id_, group_id_)
);

alter table public.act_id_membership
    owner to camunda;

create index act_idx_memb_group
    on public.act_id_membership (group_id_);

create index act_idx_memb_user
    on public.act_id_membership (user_id_);

create table public.act_id_info
(
    id_        varchar(64) not null
        primary key,
    rev_       integer,
    user_id_   varchar(64),
    type_      varchar(64),
    key_       varchar(255),
    value_     varchar(255),
    password_  bytea,
    parent_id_ varchar(255)
);

alter table public.act_id_info
    owner to camunda;

create table public.act_id_tenant
(
    id_   varchar(64) not null
        primary key,
    rev_  integer,
    name_ varchar(255)
);

alter table public.act_id_tenant
    owner to camunda;

create table public.act_id_tenant_member
(
    id_        varchar(64) not null
        primary key,
    tenant_id_ varchar(64) not null
        constraint act_fk_tenant_memb
            references public.act_id_tenant,
    user_id_   varchar(64)
        constraint act_fk_tenant_memb_user
            references public.act_id_user,
    group_id_  varchar(64)
        constraint act_fk_tenant_memb_group
            references public.act_id_group,
    constraint act_uniq_tenant_memb_user
        unique (tenant_id_, user_id_),
    constraint act_uniq_tenant_memb_group
        unique (tenant_id_, group_id_)
);

alter table public.act_id_tenant_member
    owner to camunda;

create index act_idx_tenant_memb
    on public.act_id_tenant_member (tenant_id_);

create index act_idx_tenant_memb_user
    on public.act_id_tenant_member (user_id_);

create index act_idx_tenant_memb_group
    on public.act_id_tenant_member (group_id_);

create table public.act_re_case_def
(
    id_                 varchar(64)  not null
        primary key,
    rev_                integer,
    category_           varchar(255),
    name_               varchar(255),
    key_                varchar(255) not null,
    version_            integer      not null,
    deployment_id_      varchar(64),
    resource_name_      varchar(4000),
    dgrm_resource_name_ varchar(4000),
    tenant_id_          varchar(64),
    history_ttl_        integer
);

alter table public.act_re_case_def
    owner to camunda;

create index act_idx_case_def_tenant_id
    on public.act_re_case_def (tenant_id_);

create table public.act_ru_case_execution
(
    id_              varchar(64) not null
        primary key,
    rev_             integer,
    case_inst_id_    varchar(64)
        constraint act_fk_case_exe_case_inst
            references public.act_ru_case_execution,
    super_case_exec_ varchar(64),
    super_exec_      varchar(64),
    business_key_    varchar(255),
    parent_id_       varchar(64)
        constraint act_fk_case_exe_parent
            references public.act_ru_case_execution,
    case_def_id_     varchar(64)
        constraint act_fk_case_exe_case_def
            references public.act_re_case_def,
    act_id_          varchar(255),
    prev_state_      integer,
    current_state_   integer,
    required_        boolean,
    tenant_id_       varchar(64)
);

alter table public.act_ru_case_execution
    owner to camunda;

create table public.act_ru_task
(
    id_                varchar(64) not null
        primary key,
    rev_               integer,
    execution_id_      varchar(64)
        constraint act_fk_task_exe
            references public.act_ru_execution,
    proc_inst_id_      varchar(64)
        constraint act_fk_task_procinst
            references public.act_ru_execution,
    proc_def_id_       varchar(64)
        constraint act_fk_task_procdef
            references public.act_re_procdef,
    case_execution_id_ varchar(64)
        constraint act_fk_task_case_exe
            references public.act_ru_case_execution,
    case_inst_id_      varchar(64),
    case_def_id_       varchar(64)
        constraint act_fk_task_case_def
            references public.act_re_case_def,
    name_              varchar(255),
    parent_task_id_    varchar(64),
    description_       varchar(4000),
    task_def_key_      varchar(255),
    owner_             varchar(255),
    assignee_          varchar(255),
    delegation_        varchar(64),
    priority_          integer,
    create_time_       timestamp,
    last_updated_      timestamp,
    due_date_          timestamp,
    follow_up_date_    timestamp,
    suspension_state_  integer,
    tenant_id_         varchar(64),
    task_state_        varchar(64)
);

alter table public.act_ru_task
    owner to camunda;

create index act_idx_task_create
    on public.act_ru_task (create_time_);

create index act_idx_task_last_updated
    on public.act_ru_task (last_updated_);

create index act_idx_task_assignee
    on public.act_ru_task (assignee_);

create index act_idx_task_owner
    on public.act_ru_task (owner_);

create index act_idx_task_tenant_id
    on public.act_ru_task (tenant_id_);

create index act_idx_task_exec
    on public.act_ru_task (execution_id_);

create index act_idx_task_procinst
    on public.act_ru_task (proc_inst_id_);

create index act_idx_task_procdef
    on public.act_ru_task (proc_def_id_);

create index act_idx_task_case_exec
    on public.act_ru_task (case_execution_id_);

create index act_idx_task_case_def_id
    on public.act_ru_task (case_def_id_);

create table public.act_ru_identitylink
(
    id_          varchar(64) not null
        primary key,
    rev_         integer,
    group_id_    varchar(255),
    type_        varchar(255),
    user_id_     varchar(255),
    task_id_     varchar(64)
        constraint act_fk_tskass_task
            references public.act_ru_task,
    proc_def_id_ varchar(64)
        constraint act_fk_athrz_procedef
            references public.act_re_procdef,
    tenant_id_   varchar(64)
);

alter table public.act_ru_identitylink
    owner to camunda;

create index act_idx_ident_lnk_user
    on public.act_ru_identitylink (user_id_);

create index act_idx_ident_lnk_group
    on public.act_ru_identitylink (group_id_);

create index act_idx_tskass_task
    on public.act_ru_identitylink (task_id_);

create index act_idx_athrz_procedef
    on public.act_ru_identitylink (proc_def_id_);

create table public.act_ru_variable
(
    id_                  varchar(64)  not null
        primary key,
    rev_                 integer,
    type_                varchar(255) not null,
    name_                varchar(255) not null,
    execution_id_        varchar(64)
        constraint act_fk_var_exe
            references public.act_ru_execution,
    proc_inst_id_        varchar(64)
        constraint act_fk_var_procinst
            references public.act_ru_execution,
    proc_def_id_         varchar(64),
    case_execution_id_   varchar(64)
        constraint act_fk_var_case_exe
            references public.act_ru_case_execution,
    case_inst_id_        varchar(64)
        constraint act_fk_var_case_inst
            references public.act_ru_case_execution,
    task_id_             varchar(64),
    batch_id_            varchar(64)
        constraint act_fk_var_batch
            references public.act_ru_batch,
    bytearray_id_        varchar(64)
        constraint act_fk_var_bytearray
            references public.act_ge_bytearray,
    double_              double precision,
    long_                bigint,
    text_                varchar(4000),
    text2_               varchar(4000),
    var_scope_           varchar(64),
    sequence_counter_    bigint,
    is_concurrent_local_ boolean,
    tenant_id_           varchar(64),
    constraint act_uniq_variable
        unique (var_scope_, name_)
);

alter table public.act_ru_variable
    owner to camunda;

create index act_idx_variable_task_id
    on public.act_ru_variable (task_id_);

create index act_idx_variable_tenant_id
    on public.act_ru_variable (tenant_id_);

create index act_idx_variable_task_name_type
    on public.act_ru_variable (task_id_, name_, type_);

create index act_idx_var_exe
    on public.act_ru_variable (execution_id_);

create index act_idx_var_procinst
    on public.act_ru_variable (proc_inst_id_);

create index act_idx_var_bytearray
    on public.act_ru_variable (bytearray_id_);

create index act_idx_batch_id
    on public.act_ru_variable (batch_id_);

create index act_idx_var_case_exe
    on public.act_ru_variable (case_execution_id_);

create index act_idx_var_case_inst_id
    on public.act_ru_variable (case_inst_id_);

create index act_idx_case_exec_buskey
    on public.act_ru_case_execution (business_key_);

create index act_idx_case_exe_case_inst
    on public.act_ru_case_execution (case_inst_id_);

create index act_idx_case_exe_parent
    on public.act_ru_case_execution (parent_id_);

create index act_idx_case_exe_case_def
    on public.act_ru_case_execution (case_def_id_);

create index act_idx_case_exec_tenant_id
    on public.act_ru_case_execution (tenant_id_);

create table public.act_ru_case_sentry_part
(
    id_                  varchar(64) not null
        primary key,
    rev_                 integer,
    case_inst_id_        varchar(64)
        constraint act_fk_case_sentry_case_inst
            references public.act_ru_case_execution,
    case_exec_id_        varchar(64)
        constraint act_fk_case_sentry_case_exec
            references public.act_ru_case_execution,
    sentry_id_           varchar(255),
    type_                varchar(255),
    source_case_exec_id_ varchar(64),
    standard_event_      varchar(255),
    source_              varchar(255),
    variable_event_      varchar(255),
    variable_name_       varchar(255),
    satisfied_           boolean,
    tenant_id_           varchar(64)
);

alter table public.act_ru_case_sentry_part
    owner to camunda;

create index act_idx_case_sentry_case_inst
    on public.act_ru_case_sentry_part (case_inst_id_);

create index act_idx_case_sentry_case_exec
    on public.act_ru_case_sentry_part (case_exec_id_);

create table public.act_hi_caseinst
(
    id_                        varchar(64) not null
        primary key,
    case_inst_id_              varchar(64) not null
        unique,
    business_key_              varchar(255),
    case_def_id_               varchar(64) not null,
    create_time_               timestamp   not null,
    close_time_                timestamp,
    duration_                  bigint,
    state_                     integer,
    create_user_id_            varchar(255),
    super_case_instance_id_    varchar(64),
    super_process_instance_id_ varchar(64),
    tenant_id_                 varchar(64)
);

alter table public.act_hi_caseinst
    owner to camunda;

create index act_idx_hi_cas_i_close
    on public.act_hi_caseinst (close_time_);

create index act_idx_hi_cas_i_buskey
    on public.act_hi_caseinst (business_key_);

create index act_idx_hi_cas_i_tenant_id
    on public.act_hi_caseinst (tenant_id_);

create table public.act_hi_caseactinst
(
    id_                 varchar(64)  not null
        primary key,
    parent_act_inst_id_ varchar(64),
    case_def_id_        varchar(64)  not null,
    case_inst_id_       varchar(64)  not null,
    case_act_id_        varchar(255) not null,
    task_id_            varchar(64),
    call_proc_inst_id_  varchar(64),
    call_case_inst_id_  varchar(64),
    case_act_name_      varchar(255),
    case_act_type_      varchar(255),
    create_time_        timestamp    not null,
    end_time_           timestamp,
    duration_           bigint,
    state_              integer,
    required_           boolean,
    tenant_id_          varchar(64)
);

alter table public.act_hi_caseactinst
    owner to camunda;

create index act_idx_hi_cas_a_i_create
    on public.act_hi_caseactinst (create_time_);

create index act_idx_hi_cas_a_i_end
    on public.act_hi_caseactinst (end_time_);

create index act_idx_hi_cas_a_i_comp
    on public.act_hi_caseactinst (case_act_id_, end_time_, id_);

create index act_idx_hi_cas_a_i_tenant_id
    on public.act_hi_caseactinst (tenant_id_);

create table public.act_re_decision_req_def
(
    id_                 varchar(64)  not null
        primary key,
    rev_                integer,
    category_           varchar(255),
    name_               varchar(255),
    key_                varchar(255) not null,
    version_            integer      not null,
    deployment_id_      varchar(64),
    resource_name_      varchar(4000),
    dgrm_resource_name_ varchar(4000),
    tenant_id_          varchar(64)
);

alter table public.act_re_decision_req_def
    owner to camunda;

create table public.act_re_decision_def
(
    id_                 varchar(64)  not null
        primary key,
    rev_                integer,
    category_           varchar(255),
    name_               varchar(255),
    key_                varchar(255) not null,
    version_            integer      not null,
    deployment_id_      varchar(64),
    resource_name_      varchar(4000),
    dgrm_resource_name_ varchar(4000),
    dec_req_id_         varchar(64)
        constraint act_fk_dec_req
            references public.act_re_decision_req_def,
    dec_req_key_        varchar(255),
    tenant_id_          varchar(64),
    history_ttl_        integer,
    version_tag_        varchar(64)
);

alter table public.act_re_decision_def
    owner to camunda;

create index act_idx_dec_def_tenant_id
    on public.act_re_decision_def (tenant_id_);

create index act_idx_dec_def_req_id
    on public.act_re_decision_def (dec_req_id_);

create index act_idx_dec_req_def_tenant_id
    on public.act_re_decision_req_def (tenant_id_);

create table public.act_hi_decinst
(
    id_                varchar(64)  not null
        primary key,
    dec_def_id_        varchar(64)  not null,
    dec_def_key_       varchar(255) not null,
    dec_def_name_      varchar(255),
    proc_def_key_      varchar(255),
    proc_def_id_       varchar(64),
    proc_inst_id_      varchar(64),
    case_def_key_      varchar(255),
    case_def_id_       varchar(64),
    case_inst_id_      varchar(64),
    act_inst_id_       varchar(64),
    act_id_            varchar(255),
    eval_time_         timestamp    not null,
    removal_time_      timestamp,
    collect_value_     double precision,
    user_id_           varchar(255),
    root_dec_inst_id_  varchar(64),
    root_proc_inst_id_ varchar(64),
    dec_req_id_        varchar(64),
    dec_req_key_       varchar(255),
    tenant_id_         varchar(64)
);

alter table public.act_hi_decinst
    owner to camunda;

create index act_idx_hi_dec_inst_id
    on public.act_hi_decinst (dec_def_id_);

create index act_idx_hi_dec_inst_key
    on public.act_hi_decinst (dec_def_key_);

create index act_idx_hi_dec_inst_pi
    on public.act_hi_decinst (proc_inst_id_);

create index act_idx_hi_dec_inst_ci
    on public.act_hi_decinst (case_inst_id_);

create index act_idx_hi_dec_inst_act
    on public.act_hi_decinst (act_id_);

create index act_idx_hi_dec_inst_act_inst
    on public.act_hi_decinst (act_inst_id_);

create index act_idx_hi_dec_inst_time
    on public.act_hi_decinst (eval_time_);

create index act_idx_hi_dec_inst_tenant_id
    on public.act_hi_decinst (tenant_id_);

create index act_idx_hi_dec_inst_root_id
    on public.act_hi_decinst (root_dec_inst_id_);

create index act_idx_hi_dec_inst_req_id
    on public.act_hi_decinst (dec_req_id_);

create index act_idx_hi_dec_inst_req_key
    on public.act_hi_decinst (dec_req_key_);

create index act_idx_hi_dec_inst_root_pi
    on public.act_hi_decinst (root_proc_inst_id_);

create index act_idx_hi_dec_inst_rm_time
    on public.act_hi_decinst (removal_time_);

create table public.act_hi_dec_in
(
    id_                varchar(64) not null
        primary key,
    dec_inst_id_       varchar(64) not null,
    clause_id_         varchar(64),
    clause_name_       varchar(255),
    var_type_          varchar(100),
    bytearray_id_      varchar(64),
    double_            double precision,
    long_              bigint,
    text_              varchar(4000),
    text2_             varchar(4000),
    tenant_id_         varchar(64),
    create_time_       timestamp,
    root_proc_inst_id_ varchar(64),
    removal_time_      timestamp
);

alter table public.act_hi_dec_in
    owner to camunda;

create index act_idx_hi_dec_in_inst
    on public.act_hi_dec_in (dec_inst_id_);

create index act_idx_hi_dec_in_clause
    on public.act_hi_dec_in (dec_inst_id_, clause_id_);

create index act_idx_hi_dec_in_root_pi
    on public.act_hi_dec_in (root_proc_inst_id_);

create index act_idx_hi_dec_in_rm_time
    on public.act_hi_dec_in (removal_time_);

create table public.act_hi_dec_out
(
    id_                varchar(64) not null
        primary key,
    dec_inst_id_       varchar(64) not null,
    clause_id_         varchar(64),
    clause_name_       varchar(255),
    rule_id_           varchar(64),
    rule_order_        integer,
    var_name_          varchar(255),
    var_type_          varchar(100),
    bytearray_id_      varchar(64),
    double_            double precision,
    long_              bigint,
    text_              varchar(4000),
    text2_             varchar(4000),
    tenant_id_         varchar(64),
    create_time_       timestamp,
    root_proc_inst_id_ varchar(64),
    removal_time_      timestamp
);

alter table public.act_hi_dec_out
    owner to camunda;

create index act_idx_hi_dec_out_inst
    on public.act_hi_dec_out (dec_inst_id_);

create index act_idx_hi_dec_out_rule
    on public.act_hi_dec_out (rule_order_, clause_id_);

create index act_idx_hi_dec_out_root_pi
    on public.act_hi_dec_out (root_proc_inst_id_);

create index act_idx_hi_dec_out_rm_time
    on public.act_hi_dec_out (removal_time_);
