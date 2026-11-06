-- Migration: Add composite indexes for act_hi_detail form_field equality lookups
--
-- Purpose: Optimize advance-search form_field "==" criteria (e.g. title == 'Test 1').
-- Without these indexes, correlated subqueries on 1.5M+ rows can take 2+ minutes
-- and hit statement timeout.
--
-- Run this after applying the pre-filter optimization (advance_search.py).
-- The pre-filter flips the join order, but these indexes help when the planner
-- scans act_hi_detail by name_ and value first.
--
-- Existing indexes (from user):
--   idx_act_hi_detail_proc_name_time (proc_inst_id_, name_, time_)
--   idx_act_hi_detail_proc_name_text (proc_inst_id_, name_, text_) WHERE text_ IS NOT NULL
--   idx_act_hi_detail_proc_name_long (proc_inst_id_, name_, long_) WHERE long_ IS NOT NULL

-- Index for equality lookups when filtering by name_ and text_ first
-- Helps: SELECT proc_inst_id_ FROM act_hi_detail WHERE name_ = ? AND text_ = ?
CREATE INDEX IF NOT EXISTS idx_act_hi_detail_name_text_proc
ON public.act_hi_detail (name_, text_, proc_inst_id_)
WHERE text_ IS NOT NULL AND text_ <> '';

-- Index for equality lookups when filtering by name_ and text2_ first
CREATE INDEX IF NOT EXISTS idx_act_hi_detail_name_text2_proc
ON public.act_hi_detail (name_, text2_, proc_inst_id_)
WHERE text2_ IS NOT NULL AND text2_ <> '';

-- Index for DISTINCT ON (proc_inst_id_) ORDER BY proc_inst_id_, time_ DESC
-- Used by pre-filter to get latest value per proc_inst_id for a given name_/type_
CREATE INDEX IF NOT EXISTS idx_act_hi_detail_name_type_proc_time
ON public.act_hi_detail (name_, type_, proc_inst_id_, time_ DESC);
