-- =====================================================
-- Create Form Templates Table (PostgreSQL)
-- =====================================================
-- This table stores saved form field templates for Camunda forms
-- Users can save form field values and reuse them later
-- Multiple templates per form per user are supported
-- =====================================================

-- Drop table if exists (use with caution in production)
-- DROP TABLE IF EXISTS act_re_form_template;

-- Create act_re_form_template table
CREATE TABLE IF NOT EXISTS act_re_form_template (
    -- Primary Key
    id_ VARCHAR(64) NOT NULL PRIMARY KEY,

    -- Revision for optimistic locking (Camunda convention)
    rev_ INTEGER NOT NULL DEFAULT 1,

    -- Template Identification
    name_ VARCHAR(255) NOT NULL,
    description_ TEXT,

    -- Form Reference (references Camunda form definition)
    form_key_ VARCHAR(255) NOT NULL,
    form_id_ VARCHAR(64),
    form_version_ INTEGER,

    -- Owner/Creator
    created_by_ VARCHAR(100) NOT NULL,
    modified_by_ VARCHAR(100),

    -- Form Field Data (JSONB)
    form_data_ JSONB NOT NULL,

    -- Sharing Settings
    is_public_ BOOLEAN NOT NULL DEFAULT FALSE,

    -- Categorization
    category_ VARCHAR(100),
    tags_ JSONB,

    -- Usage Tracking
    usage_count_ INTEGER NOT NULL DEFAULT 0,
    last_used_at_ TIMESTAMP,

    -- Timestamps
    created_at_ TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_ TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at_ TIMESTAMP,

    -- Soft Delete
    is_deleted_ BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at_ TIMESTAMP,

    -- Multi-tenancy Support
    tenant_id_ VARCHAR(64)
);

-- =====================================================
-- Create Indexes for Better Performance
-- =====================================================

-- Index on form_key for filtering by form
CREATE INDEX IF NOT EXISTS idx_form_template_form_key ON act_re_form_template(form_key_);

-- Index on form_id for filtering by form ID
CREATE INDEX IF NOT EXISTS idx_form_template_form_id ON act_re_form_template(form_id_);

-- Index on creator for user-specific queries
CREATE INDEX IF NOT EXISTS idx_form_template_created_by ON act_re_form_template(created_by_);

-- Index on is_public for filtering public templates
CREATE INDEX IF NOT EXISTS idx_form_template_is_public ON act_re_form_template(is_public_);

-- Index on category for filtering by category
CREATE INDEX IF NOT EXISTS idx_form_template_category ON act_re_form_template(category_);

-- Index on is_deleted for excluding soft-deleted records
CREATE INDEX IF NOT EXISTS idx_form_template_is_deleted ON act_re_form_template(is_deleted_);

-- Index on tenant_id for multi-tenancy support
CREATE INDEX IF NOT EXISTS idx_form_template_tenant_id ON act_re_form_template(tenant_id_);

-- Index on created_at for sorting by creation date
CREATE INDEX IF NOT EXISTS idx_form_template_created_at ON act_re_form_template(created_at_);

-- Index on usage_count for sorting by popularity
CREATE INDEX IF NOT EXISTS idx_form_template_usage_count ON act_re_form_template(usage_count_);

-- Composite index for common query patterns (user's non-deleted templates)
CREATE INDEX IF NOT EXISTS idx_form_template_user_deleted ON act_re_form_template(created_by_, is_deleted_);

-- Composite index for duplicate name checks (name, created_by, form_key, tenant_id)
-- This index is partial (only for non-deleted templates) for better performance
CREATE INDEX IF NOT EXISTS idx_form_template_name_user_form_tenant
ON act_re_form_template(name_, created_by_, form_key_, tenant_id_)
WHERE is_deleted_ = FALSE;

-- Composite index for form and user queries
CREATE INDEX IF NOT EXISTS idx_form_template_form_user ON act_re_form_template(form_key_, created_by_, is_deleted_);

-- =====================================================
-- Create Trigger for Updated At
-- =====================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_form_template_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at_ = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_act_re_form_template_updated_at ON act_re_form_template;
CREATE TRIGGER update_act_re_form_template_updated_at
    BEFORE UPDATE ON act_re_form_template
    FOR EACH ROW
    EXECUTE FUNCTION update_form_template_updated_at();

-- =====================================================
-- Sample Data (Optional)
-- =====================================================
-- Uncomment to insert sample templates

/*
-- Sample Template 1: Leave Request Form - Standard
INSERT INTO act_re_form_template
(id_, rev_, name_, description_, form_key_, created_by_, form_data_, is_public_, category_, tags_, usage_count_)
VALUES (
    'form-template-001',
    1,
    'Standard Leave Request',
    'Standard leave request with 5 days duration',
    'leave-request-form',
    'john.doe',
    '{"leaveType": "annual", "startDate": "2025-01-15", "endDate": "2025-01-19", "duration": 5, "reason": "Personal vacation"}',
    TRUE,
    'Leave Management',
    '["leave", "standard", "annual"]',
    0
);

-- Sample Template 2: Leave Request Form - Emergency
INSERT INTO act_re_form_template
(id_, rev_, name_, description_, form_key_, created_by_, form_data_, is_public_, category_, tags_, usage_count_)
VALUES (
    'form-template-002',
    1,
    'Emergency Leave Request',
    'Emergency leave request template',
    'leave-request-form',
    'john.doe',
    '{"leaveType": "emergency", "startDate": "", "endDate": "", "duration": 1, "reason": "Emergency"}',
    FALSE,
    'Leave Management',
    '["leave", "emergency"]',
    0
);

-- Sample Template 3: Onboarding Form - New Employee
INSERT INTO act_re_form_template
(id_, rev_, name_, description_, form_key_, created_by_, form_data_, is_public_, category_, tags_, usage_count_)
VALUES (
    'form-template-003',
    1,
    'New Employee Onboarding',
    'Standard onboarding form for new employees',
    'onboarding-form',
    'hr.manager',
    '{"employeeType": "full-time", "department": "Engineering", "startDate": "", "equipment": ["laptop", "monitor"], "accessLevel": "standard"}',
    TRUE,
    'HR',
    '["onboarding", "new-employee", "hr"]',
    0
);
*/

-- =====================================================
-- Verify Table Creation
-- =====================================================

-- Show table structure
-- \d act_re_form_template;

-- Show table indexes
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'act_re_form_template';

-- =====================================================
-- Success Message
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '📝 FORM TEMPLATES SYSTEM INSTALLED SUCCESSFULLY! 📝';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '📋 Table: act_re_form_template';
    RAISE NOTICE '⚙️  Trigger: update_act_re_form_template_updated_at';
    RAISE NOTICE '📊 Indexes: Optimized for performance';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '🎯 Features:';
    RAISE NOTICE '   • Save and reuse form field values';
    RAISE NOTICE '   • Multiple templates per form per user';
    RAISE NOTICE '   • Public/private template sharing';
    RAISE NOTICE '   • Usage tracking and popularity metrics';
    RAISE NOTICE '   • Categorization and tagging system';
    RAISE NOTICE '   • Soft delete functionality';
    RAISE NOTICE '   • Multi-tenancy support';
    RAISE NOTICE '   • JSONB form data storage';
    RAISE NOTICE '   • Camunda naming conventions';
    RAISE NOTICE '';
    RAISE NOTICE '✅ System Status: READY FOR PRODUCTION!';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '🎉 Users can now save and share form templates!';
    RAISE NOTICE '=====================================================';
END $$;

-- =====================================================
-- Notes
-- =====================================================
-- 1. This table should be created in the Camunda database
-- 2. Uses JSONB for better performance with JSON operations
-- 3. Follows Camunda naming conventions (act_re_ prefix, _ suffix)
-- 4. All indexes are optimized for common query patterns
-- 5. Soft delete is used (is_deleted_ flag) instead of hard deletes
-- 6. Usage tracking helps identify popular templates
-- 7. Multi-tenancy support via tenant_id_ column
-- 8. Automatic updated_at_ trigger for timestamp management
-- 9. Supports multiple templates per form per user
-- 10. References Camunda form definitions via form_key_
-- =====================================================
