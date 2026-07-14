-- RLS setup for tenant isolation (CR E5)

-- Tenant context function
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_tenant', true), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Tables that need org-level isolation
CREATE OR REPLACE FUNCTION setup_tenant_rls_on(table_name TEXT) RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', table_name);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', table_name);
    EXECUTE format(
        'DROP POLICY IF EXISTS tenant_isolation ON %I;',
        table_name
    );
    EXECUTE format(
        'CREATE POLICY tenant_isolation ON %I FOR ALL USING (organization_id = current_tenant_id());',
        table_name
    );
END;
$$ LANGUAGE plpgsql;

-- Apply RLS to all tenant-scoped tables
SELECT setup_tenant_rls_on('departments');
SELECT setup_tenant_rls_on('organization_members');
SELECT setup_tenant_rls_on('roles');
SELECT setup_tenant_rls_on('employees');
SELECT setup_tenant_rls_on('employee_contracts');
SELECT setup_tenant_rls_on('attendance_records');
SELECT setup_tenant_rls_on('leave_types');
SELECT setup_tenant_rls_on('leave_balances');
SELECT setup_tenant_rls_on('leave_requests');
SELECT setup_tenant_rls_on('recruitment_positions');
SELECT setup_tenant_rls_on('salary_structures');
SELECT setup_tenant_rls_on('tasks');
SELECT setup_tenant_rls_on('task_subtasks');
SELECT setup_tenant_rls_on('task_comments');
SELECT setup_tenant_rls_on('task_activities');
SELECT setup_tenant_rls_on('wiki_folders');
SELECT setup_tenant_rls_on('wiki_pages');
SELECT setup_tenant_rls_on('notifications');
SELECT setup_tenant_rls_on('notification_recipients');
SELECT setup_tenant_rls_on('audit_logs');

-- Seed default system permissions
INSERT INTO permissions (id, code, name, module) VALUES
    (gen_random_uuid(), 'system.admin', '系统管理', 'system'),
    (gen_random_uuid(), 'org.manage', '组织管理', 'organization'),
    (gen_random_uuid(), 'org.department.manage', '部门管理', 'organization'),
    (gen_random_uuid(), 'org.member.manage', '成员管理', 'organization'),
    (gen_random_uuid(), 'org.role.manage', '角色管理', 'organization'),
    (gen_random_uuid(), 'employee.read', '查看员工', 'hr'),
    (gen_random_uuid(), 'employee.create', '创建员工', 'hr'),
    (gen_random_uuid(), 'employee.update', '编辑员工', 'hr'),
    (gen_random_uuid(), 'employee.delete', '删除员工', 'hr'),
    (gen_random_uuid(), 'attendance.read', '查看考勤', 'attendance'),
    (gen_random_uuid(), 'attendance.checkin', '打卡', 'attendance'),
    (gen_random_uuid(), 'attendance.manage', '管理考勤', 'attendance'),
    (gen_random_uuid(), 'leave.request', '提交请假', 'leave'),
    (gen_random_uuid(), 'leave.approve', '审批请假', 'leave'),
    (gen_random_uuid(), 'leave.manage', '管理请假类型', 'leave'),
    (gen_random_uuid(), 'task.read', '查看任务', 'task'),
    (gen_random_uuid(), 'task.create', '创建任务', 'task'),
    (gen_random_uuid(), 'task.update', '编辑任务', 'task'),
    (gen_random_uuid(), 'task.delete', '删除任务', 'task'),
    (gen_random_uuid(), 'wiki.read', '查看文档', 'wiki'),
    (gen_random_uuid(), 'wiki.create', '创建文档', 'wiki'),
    (gen_random_uuid(), 'wiki.update', '编辑文档', 'wiki'),
    (gen_random_uuid(), 'wiki.delete', '删除文档', 'wiki'),
    (gen_random_uuid(), 'notification.read', '查看通知', 'notification'),
    (gen_random_uuid(), 'audit.read', '查看审计日志', 'audit')
ON CONFLICT (code) DO NOTHING;

-- Seed default system roles (admin)
INSERT INTO roles (id, organization_id, name, display_name, description, is_system)
SELECT
    gen_random_uuid(), org.id, 'admin', '管理员', '系统管理员，拥有所有权限', true
FROM organizations org
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'admin' AND organization_id = org.id);

-- Seed default system roles (member)
INSERT INTO roles (id, organization_id, name, display_name, description, is_system)
SELECT
    gen_random_uuid(), org.id, 'member', '成员', '普通成员', true
FROM organizations org
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'member' AND organization_id = org.id);
