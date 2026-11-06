-- =====================================================
-- Create Search Templates Table (PostgreSQL)
-- =====================================================
-- This table stores saved search query templates for advance-query
-- Users can save complex search criteria and reuse them later
-- =====================================================

-- Drop table if exists (use with caution in production)
-- DROP TABLE IF EXISTS search_templates;

-- Create search_templates table
CREATE TABLE IF NOT EXISTS search_templates (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Template Identification
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Owner/Creator
    created_by VARCHAR(100) NOT NULL,

    -- Template Content (JSON)
    template_payload JSONB NOT NULL,

    -- Sharing Settings
    is_public BOOLEAN NOT NULL DEFAULT FALSE,

    -- Categorization
    category VARCHAR(100),
    tags JSONB,

    -- Usage Tracking
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Soft Delete
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP,

    -- Multi-tenancy Support
    tenant_id VARCHAR(64)
);

-- =====================================================
-- Create Indexes for Better Performance
-- =====================================================

-- Index on creator for user-specific queries
CREATE INDEX idx_search_templates_created_by ON search_templates(created_by);

-- Index on is_public for filtering public templates
CREATE INDEX idx_search_templates_is_public ON search_templates(is_public);

-- Index on category for filtering by category
CREATE INDEX idx_search_templates_category ON search_templates(category);

-- Index on is_deleted for excluding soft-deleted records
CREATE INDEX idx_search_templates_is_deleted ON search_templates(is_deleted);

-- Index on tenant_id for multi-tenancy support
CREATE INDEX idx_search_templates_tenant_id ON search_templates(tenant_id);

-- Index on created_at for sorting by creation date
CREATE INDEX idx_search_templates_created_at ON search_templates(created_at);

-- Index on usage_count for sorting by popularity
CREATE INDEX idx_search_templates_usage_count ON search_templates(usage_count);

-- Composite index for common query patterns (user's non-deleted templates)
CREATE INDEX idx_search_templates_user_deleted ON search_templates(created_by, is_deleted);

-- Composite index for duplicate name checks (name, created_by, tenant_id)
-- This index is partial (only for non-deleted templates) for better performance
CREATE INDEX idx_search_templates_name_user_tenant
ON search_templates(name, created_by, tenant_id)
WHERE is_deleted = FALSE;

-- =====================================================
-- Create Trigger for Updated At
-- =====================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_search_templates_updated_at
    BEFORE UPDATE ON search_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Sample Data (Optional)
-- =====================================================
-- Uncomment to insert sample templates

/*
-- Sample Template 1: Active Tickets
INSERT INTO search_templates
(name, description, created_by, template_payload, is_public, category, tags, usage_count)
VALUES (
    'Active Tickets',
    'Search for all active tickets in the system',
    'admin',
    '{"criteria": {"operator": "and", "conditions": [{"field": "ticket_status", "action": "==", "value": "ACTIVE"}]}, "sort_by": "create_time", "sort_order": "desc", "limit": 50}',
    TRUE,
    'General',
    '["active", "all"]',
    0
);

-- Sample Template 2: High Priority Leave Requests
INSERT INTO search_templates
(name, description, created_by, template_payload, is_public, category, tags, usage_count)
VALUES (
    'High Priority Leave Requests',
    'Active leave requests with high priority',
    'admin',
    '{"criteria": {"operator": "and", "conditions": [{"field": "ticket_type", "action": "==", "value": "Leave Request Process"}, {"field": "ticket_status", "action": "==", "value": "ACTIVE"}, {"field": "variable", "variable_name": "priority", "action": "==", "value": "HIGH"}]}, "selected_columns": ["ticket_number", "creator", "current_phases", "processor", "variables"], "sort_by": "create_time", "sort_order": "desc", "limit": 50}',
    TRUE,
    'Leave Management',
    '["leave", "priority", "high", "active"]',
    0
);

-- Sample Template 3: My Active Tasks
INSERT INTO search_templates
(name, description, created_by, template_payload, is_public, category, tags, usage_count)
VALUES (
    'My Active Tasks',
    'Tasks currently assigned to me',
    'john.doe',
    '{"criteria": {"operator": "and", "conditions": [{"field": "ticket_status", "action": "==", "value": "ACTIVE"}, {"field": "processor", "action": "==", "value": "john.doe"}]}, "selected_columns": ["ticket_number", "ticket_type", "create_time", "current_phases"], "sort_by": "create_time", "sort_order": "desc", "limit": 20}',
    FALSE,
    'Dashboard',
    '["personal", "active", "dashboard"]',
    0
);
*/

-- =====================================================
-- Verify Table Creation
-- =====================================================

-- Show table structure
-- \d search_templates;

-- Show table indexes
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'search_templates';

-- =====================================================
-- Success Message
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '🔍 SEARCH TEMPLATES SYSTEM INSTALLED SUCCESSFULLY! 🔍';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '📋 Table: search_templates';
    RAISE NOTICE '⚙️  Trigger: update_search_templates_updated_at';
    RAISE NOTICE '📊 Indexes: Optimized for performance';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '🎯 Features:';
    RAISE NOTICE '   • Save and reuse complex search queries';
    RAISE NOTICE '   • Public/private template sharing';
    RAISE NOTICE '   • Usage tracking and popularity metrics';
    RAISE NOTICE '   • Categorization and tagging system';
    RAISE NOTICE '   • Soft delete functionality';
    RAISE NOTICE '   • Multi-tenancy support';
    RAISE NOTICE '   • JSONB template storage';
    RAISE NOTICE '';
    RAISE NOTICE '✅ System Status: READY FOR PRODUCTION!';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '🎉 Users can now save and share search templates!';
    RAISE NOTICE '=====================================================';
END $$;

-- =====================================================
-- Notes
-- =====================================================
-- 1. This table should be created in the Camunda database
-- 2. Uses JSONB for better performance with JSON operations
-- 3. SERIAL for auto-incrementing primary key
-- 4. All indexes are optimized for common query patterns
-- 5. Soft delete is used (is_deleted flag) instead of hard deletes
-- 6. Usage tracking helps identify popular templates
-- 7. Multi-tenancy support via tenant_id column
-- 8. Automatic updated_at trigger for timestamp management
-- =====================================================
