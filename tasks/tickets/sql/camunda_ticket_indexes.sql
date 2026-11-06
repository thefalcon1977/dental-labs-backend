-- Indexes to speed up Camunda ticket list/count queries.
-- Use CONCURRENTLY for production deployments to avoid blocking writes.
-- Note: GIN trigram indexes require the pg_trgm extension.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- act_hi_procinst: filters and joins
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_procinst_start_time
    ON act_hi_procinst (start_time_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_procinst_end_time
    ON act_hi_procinst (end_time_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_procinst_state
    ON act_hi_procinst (state_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_procinst_proc_def
    ON act_hi_procinst (proc_def_id_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_procinst_business_key_trgm
    ON act_hi_procinst USING gin (business_key_ gin_trgm_ops);

-- act_re_procdef: ticket_type filter
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_re_procdef_name_trgm
    ON act_re_procdef USING gin (name_ gin_trgm_ops);

-- act_ru_execution_titles: ticket_title filter
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ru_exec_titles_exec_id
    ON act_ru_execution_titles (execution_id_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ru_exec_titles_title_trgm
    ON act_ru_execution_titles USING gin (instance_title_ gin_trgm_ops);

-- act_hi_taskinst: processor/assignee/pending/processed checks
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_taskinst_proc_end
    ON act_hi_taskinst (proc_inst_id_, end_time_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_taskinst_proc_assignee_active
    ON act_hi_taskinst (proc_inst_id_, assignee_)
    WHERE end_time_ IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_taskinst_proc_assignee_completed
    ON act_hi_taskinst (proc_inst_id_, assignee_)
    WHERE end_time_ IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_taskinst_delete_reason
    ON act_hi_taskinst (delete_reason_);

-- act_hi_identitylink: candidate/assignee identity checks
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_identitylink_task_type
    ON act_hi_identitylink (task_id_, type_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_identitylink_user
    ON act_hi_identitylink (user_id_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_identitylink_group
    ON act_hi_identitylink (group_id_);

-- act_hi_actinst: phase filter
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_actinst_proc_end
    ON act_hi_actinst (proc_inst_id_, end_time_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hi_actinst_act_name
    ON act_hi_actinst (act_name_);

-- act_id_membership: user basket rule (same group as creator)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_id_membership_user
    ON act_id_membership (user_id_);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_id_membership_group
    ON act_id_membership (group_id_);
