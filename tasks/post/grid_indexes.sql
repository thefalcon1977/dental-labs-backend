-- =============================================================================
-- Recommended indexes for grid.sql (Camunda schema)
-- =============================================================================
-- Run against the same schema as grid.sql. Idempotent (IF NOT EXISTS).
-- For production, consider creating with CREATE INDEX CONCURRENTLY to avoid
-- locking; CONCURRENTLY cannot run inside a transaction with other statements.
-- =============================================================================

-- act_hi_varinst: main filter (form key + time range) and cm_ready / cm_ready_times
CREATE INDEX IF NOT EXISTS idx_act_hi_varinst_name_createtime
    ON act_hi_varinst (name_, create_time_);

CREATE INDEX IF NOT EXISTS idx_act_hi_varinst_procid_name
    ON act_hi_varinst (proc_inst_id_, name_);

-- Optional: cover cm_ready lookup (name_ + text_) and bytearray join
CREATE INDEX IF NOT EXISTS idx_act_hi_varinst_name_text
    ON act_hi_varinst (name_, text_) WHERE text_ IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_act_hi_varinst_bytearray_id
    ON act_hi_varinst (bytearray_id_) WHERE bytearray_id_ IS NOT NULL;


-- act_ge_bytearray: join on id_ (skip if id_ is already PK)
-- CREATE INDEX IF NOT EXISTS idx_act_ge_bytearray_id ON act_ge_bytearray (id_);


-- act_hi_procinst: join on proc_inst_id_ (skip if PK)
-- CREATE INDEX IF NOT EXISTS idx_act_hi_procinst_procid ON act_hi_procinst (proc_inst_id_);


-- act_hi_procinst_titles: join on proc_inst_id_
CREATE INDEX IF NOT EXISTS idx_act_hi_procinst_titles_procid
    ON act_hi_procinst_titles (proc_inst_id_);


-- act_ru_execution_titles: join on execution_id_
CREATE INDEX IF NOT EXISTS idx_act_ru_execution_titles_execid
    ON act_ru_execution_titles (execution_id_);


-- act_ru_task: processor lookup (assignee_ + suspension_state_) and proc_inst_id_ for grouping
CREATE INDEX IF NOT EXISTS idx_act_ru_task_assignee_suspension
    ON act_ru_task (assignee_, suspension_state_) WHERE assignee_ IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_act_ru_task_procid
    ON act_ru_task (proc_inst_id_);


-- act_hi_taskinst: processor lookup (assignee_ + end_time_) and proc_inst_id_ for grouping
CREATE INDEX IF NOT EXISTS idx_act_hi_taskinst_assignee_endtime
    ON act_hi_taskinst (assignee_, end_time_) WHERE assignee_ IS NOT NULL AND end_time_ IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_act_hi_taskinst_procid
    ON act_hi_taskinst (proc_inst_id_);
