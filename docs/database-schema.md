# 数据库 Schema 设计

## 1. 约定与规范

### 命名规范
- 表名: 复数形式小写 snake_case (如 `tasks`, `employee_contracts`)
- 列名: 小写 snake_case
- 主键: `id` 列, UUID v4
- 外键: `{引用表名}_id`
- 时间戳: `created_at`, `updated_at`, `deleted_at` (软删除)
- 索引: `idx_{表名}_{列名}` (单列), `idx_{表名}_{列1}_{列2}` (复合)

### 通用字段 (所有业务表)
```sql
id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
deleted_at    TIMESTAMPTZ,  -- 软删除

-- 触发 updated_at 自动更新
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 2. 组织与用户模块

### 2.1 organizations (组织/租户)
```sql
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,
    logo_url    TEXT,
    description TEXT,
    owner_id    UUID NOT NULL,
    settings    JSONB DEFAULT '{}',
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);
CREATE INDEX idx_organizations_owner ON organizations(owner_id);
```

### 2.2 departments (部门/团队)
```sql
CREATE TABLE departments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    parent_id       UUID REFERENCES departments(id),
    name            VARCHAR(200) NOT NULL,
    path            LTREE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_departments_org ON departments(organization_id);
CREATE INDEX idx_departments_parent ON departments(parent_id);
```

### 2.3 users (用户)
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(50),
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    avatar_url      TEXT,
    timezone        VARCHAR(50) DEFAULT 'UTC',
    locale          VARCHAR(10) DEFAULT 'zh-CN',
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_users_email ON users(email);
```

### 2.4 organization_members (组织成员)
```sql
CREATE TABLE organization_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE,
    UNIQUE(organization_id, user_id)
);
CREATE INDEX idx_org_members_org ON organization_members(organization_id);
CREATE INDEX idx_org_members_user ON organization_members(user_id);
```

### 2.5 department_members (部门成员)
```sql
CREATE TABLE department_members (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID NOT NULL REFERENCES departments(id),
    user_id       UUID NOT NULL REFERENCES users(id),
    role_id       UUID REFERENCES roles(id),           -- 在部门的角色
    UNIQUE(department_id, user_id)
);
CREATE INDEX idx_dept_members_dept ON department_members(department_id);
CREATE INDEX idx_dept_members_user ON department_members(user_id);
CREATE INDEX idx_dept_members_role ON department_members(role_id);
```

---

## 3. 角色与权限模块

权限通过**角色 (Role) + 部门 (Department)** 组合定义。角色定义权限集合，部门定义作用范围。

### 3.1 roles (角色定义)
```sql
CREATE TABLE roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(100) UNIQUE NOT NULL,       -- admin / dept_manager / member / viewer
    display_name    VARCHAR(100) NOT NULL,
    description     TEXT,
    is_system       BOOLEAN DEFAULT FALSE,              -- 系统预置角色不可删除
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_roles_org ON roles(organization_id);
```

### 3.2 permissions (权限定义)
```sql
CREATE TABLE permissions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code          VARCHAR(100) UNIQUE NOT NULL,  -- employee.read / leave.approve
    name          VARCHAR(200) NOT NULL,
    module        VARCHAR(50) NOT NULL,           -- hr / task / wiki / system / attendance
    description   TEXT
);
```

### 3.3 role_permissions (角色-权限映射)
```sql
CREATE TABLE role_permissions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);
CREATE INDEX idx_role_perms_role ON role_permissions(role_id);
CREATE INDEX idx_role_perms_permission ON role_permissions(permission_id);
```



> **权限判定**: 用户请求某操作时，系统首先查找用户在目标部门中的角色（通过 department_members.role_id），然后检查该角色是否拥有对应权限。用户可同时属于多个部门，在不同部门拥有不同角色。

## 4. 人力资源管理模块

### 4.1 positions (岗位定义 — 仅用于HR职位名称，无权限含义)
```sql
CREATE TABLE positions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(200) NOT NULL,       -- 高级工程师 / 技术经理 / 总监
    description     TEXT,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_positions_org ON positions(organization_id);
```

### 4.2 employees (员工档案)
```sql
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    employee_no     VARCHAR(50) UNIQUE NOT NULL,
    department_id   UUID REFERENCES departments(id),
    position_id     UUID REFERENCES positions(id),
    reports_to      UUID REFERENCES employees(id),     -- 汇报上级
    hire_date       DATE NOT NULL,
    employment_type VARCHAR(50) DEFAULT 'full_time',   -- full_time / part_time / contract / intern
    status          VARCHAR(50) DEFAULT 'active',       -- active / resigned / suspended / probation
    work_location   VARCHAR(200),
    emergency_contact JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_employees_org ON employees(organization_id);
CREATE INDEX idx_employees_dept ON employees(department_id);
CREATE INDEX idx_employees_position ON employees(position_id);
CREATE INDEX idx_employees_reports_to ON employees(reports_to);
CREATE INDEX idx_employees_status ON employees(status);
```

### 4.3 employee_contracts (员工合同)
```sql
CREATE TABLE employee_contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    contract_type   VARCHAR(50) NOT NULL,       -- probation / fixed / permanent / project
    start_date      DATE NOT NULL,
    end_date        DATE,
    probation_months INTEGER DEFAULT 0,
    signing_date    DATE,
    document_url    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_emp_contracts_employee ON employee_contracts(employee_id);
```

### 4.4 attendance_records (考勤记录)
```sql
CREATE TABLE attendance_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    check_in_time   TIMESTAMPTZ,
    check_out_time  TIMESTAMPTZ,
    status          VARCHAR(50) DEFAULT 'present',  -- present / absent / late / early_leave / leave
    overtime_hours  DECIMAL(5,2) DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(employee_id, date)
);
CREATE INDEX idx_attendance_emp ON attendance_records(employee_id);
CREATE INDEX idx_attendance_date ON attendance_records(date);
CREATE INDEX idx_attendance_status ON attendance_records(status);
```

### 4.5 leave_types (请假类型)
```sql
CREATE TABLE leave_types (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id),
    name              VARCHAR(100) NOT NULL,         -- 年假 / 病假 / 事假 / 婚假 / 产假
    paid              BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT TRUE,
    max_days_per_year INTEGER,
    min_notice_hours  INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_leave_types_org ON leave_types(organization_id);
```

### 4.6 leave_balances (请假额度)
```sql
CREATE TABLE leave_balances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type_id   UUID NOT NULL REFERENCES leave_types(id),
    total_days      DECIMAL(6,2) NOT NULL DEFAULT 0,
    used_days       DECIMAL(6,2) NOT NULL DEFAULT 0,
    pending_days    DECIMAL(6,2) NOT NULL DEFAULT 0,
    year            INTEGER NOT NULL,
    UNIQUE(employee_id, leave_type_id, year)
);
CREATE INDEX idx_leave_balances_emp ON leave_balances(employee_id);
```

### 4.7 leave_requests (请假申请)
```sql
CREATE TABLE leave_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type_id   UUID NOT NULL REFERENCES leave_types(id),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    total_days      DECIMAL(6,2) NOT NULL,
    reason          TEXT,
    status          VARCHAR(50) DEFAULT 'pending',   -- pending / approved / rejected / cancelled
    approver_id     UUID REFERENCES employees(id),   -- 自动分配直属上级
    approved_at     TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_leave_requests_emp ON leave_requests(employee_id);
CREATE INDEX idx_leave_requests_status ON leave_requests(status);
CREATE INDEX idx_leave_requests_approver ON leave_requests(approver_id);
```

### 4.8 performance_goals (绩效目标)
```sql
CREATE TABLE performance_goals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    category        VARCHAR(50) DEFAULT 'okr',       -- okr / kpi / task
    period          VARCHAR(50) NOT NULL,             -- 2026-Q1 / 2026-H1 / 2026
    weight          DECIMAL(5,2) DEFAULT 100,        -- 权重占比
    target_value    TEXT,
    actual_value    TEXT,
    progress        INTEGER DEFAULT 0,                -- 0-100
    status          VARCHAR(50) DEFAULT 'draft',      -- draft / in_progress / completed / cancelled
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_perf_goals_emp ON performance_goals(employee_id);
CREATE INDEX idx_perf_goals_period ON performance_goals(period);
```

### 4.9 performance_reviews (绩效考核)
```sql
CREATE TABLE performance_reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    reviewer_id     UUID NOT NULL REFERENCES employees(id),   -- 评估人 (上级)
    period          VARCHAR(50) NOT NULL,
    rating          INTEGER,                        -- 1-5 评分
    overall_score   DECIMAL(5,2),
    strengths       TEXT,
    improvements    TEXT,
    comments        TEXT,
    status          VARCHAR(50) DEFAULT 'draft',    -- draft / submitted / acknowledged / completed
    submitted_at    TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_perf_reviews_emp ON performance_reviews(employee_id);
CREATE INDEX idx_perf_reviews_reviewer ON performance_reviews(reviewer_id);
CREATE INDEX idx_perf_reviews_period ON performance_reviews(period);
```

### 4.10 recruitment_positions (招聘岗位)
```sql
CREATE TABLE recruitment_positions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    department_id   UUID REFERENCES departments(id),
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    requirements    TEXT,
    headcount       INTEGER DEFAULT 1,
    filled_count    INTEGER DEFAULT 0,
    salary_range    JSONB,                          -- { "min": 10000, "max": 20000 }
    status          VARCHAR(50) DEFAULT 'open',     -- open / paused / closed / filled
    published_at    TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_rec_positions_org ON recruitment_positions(organization_id);
CREATE INDEX idx_rec_positions_dept ON recruitment_positions(department_id);
CREATE INDEX idx_rec_positions_status ON recruitment_positions(status);
```

### 4.11 candidates (候选人)
```sql
CREATE TABLE candidates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recruitment_id      UUID NOT NULL REFERENCES recruitment_positions(id) ON DELETE CASCADE,
    name                VARCHAR(200) NOT NULL,
    email               VARCHAR(255),
    phone               VARCHAR(50),
    resume_url          TEXT,
    current_company     VARCHAR(200),
    current_position    VARCHAR(200),
    years_experience    INTEGER,
    education           VARCHAR(100),
    status              VARCHAR(50) DEFAULT 'new',  -- new / screening / interview / offer / hired / rejected
    source              VARCHAR(100),               -- linkedin / 猎头 / 内推 / 官网
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);
CREATE INDEX idx_candidates_recruitment ON candidates(recruitment_id);
CREATE INDEX idx_candidates_status ON candidates(status);
```

### 4.12 interview_records (面试记录)
```sql
CREATE TABLE interview_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    interviewer_id  UUID NOT NULL REFERENCES employees(id),
    round           INTEGER NOT NULL,              -- 第几轮面试
    interview_type  VARCHAR(50) DEFAULT 'onsite',  -- onsite / video / phone
    scheduled_at    TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER,
    rating          INTEGER,                       -- 1-5
    feedback        TEXT,
    result          VARCHAR(50) DEFAULT 'pending', -- pending / pass / fail / hold
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_interviews_candidate ON interview_records(candidate_id);
CREATE INDEX idx_interviews_interviewer ON interview_records(interviewer_id);
```

### 4.13 salary_structures (薪酬结构)
```sql
CREATE TABLE salary_structures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    position_id     UUID REFERENCES positions(id),
    grade           VARCHAR(50) NOT NULL,          -- T1 / T2 / M1 / M2
    base_salary_min DECIMAL(12,2),
    base_salary_max DECIMAL(12,2),
    allowances      JSONB DEFAULT '[]',            -- [{ "name": "餐补", "amount": 500 }]
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_salary_structures_org ON salary_structures(organization_id);
```

### 4.14 payroll_records (薪资记录)
```sql
CREATE TABLE payroll_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    period          VARCHAR(50) NOT NULL,          -- 2026-01 / 2026-02
    base_salary     DECIMAL(12,2) NOT NULL,
    allowances      DECIMAL(12,2) DEFAULT 0,       -- 补贴
    overtime_pay    DECIMAL(12,2) DEFAULT 0,
    deductions      DECIMAL(12,2) DEFAULT 0,       -- 扣款
    social_insurance DECIMAL(12,2) DEFAULT 0,      -- 社保
    tax             DECIMAL(12,2) DEFAULT 0,
    net_pay         DECIMAL(12,2) NOT NULL,         -- 实发
    status          VARCHAR(50) DEFAULT 'draft',    -- draft / confirmed / paid
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_payroll_records_emp ON payroll_records(employee_id);
CREATE INDEX idx_payroll_records_period ON payroll_records(period);
```

---

## 5. 任务管理模块

### 5.1 tasks (任务)
```sql
CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    assigner_id     UUID NOT NULL REFERENCES users(id),
    assignee_id     UUID REFERENCES users(id),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    status          VARCHAR(50) NOT NULL DEFAULT 'todo',  -- todo / in_progress / review / done
    priority        VARCHAR(20) NOT NULL DEFAULT 'medium',
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    tags            TEXT[] DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_tasks_org ON tasks(organization_id);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX idx_tasks_assigner ON tasks(assigner_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_tags ON tasks USING GIN(tags);
```

### 5.2 task_subtasks (子任务)
```sql
CREATE TABLE task_subtasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title       VARCHAR(500) NOT NULL,
    is_done     BOOLEAN DEFAULT FALSE,
    sort_order  INTEGER DEFAULT 0,
    assignee_id UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_task_subtasks_task ON task_subtasks(task_id);
```

### 5.3 task_comments (任务评论)
```sql
CREATE TABLE task_comments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id       UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author_id     UUID NOT NULL REFERENCES users(id),
    parent_id     UUID REFERENCES task_comments(id),
    content       TEXT NOT NULL,
    mentions      UUID[] DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at    TIMESTAMPTZ
);
CREATE INDEX idx_task_comments_task ON task_comments(task_id);
CREATE INDEX idx_task_comments_author ON task_comments(author_id);
```

### 5.4 task_activities (任务操作日志)
```sql
CREATE TABLE task_activities (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    actor_id    UUID NOT NULL REFERENCES users(id),
    action      VARCHAR(100) NOT NULL,
    field       VARCHAR(100),
    old_value   TEXT,
    new_value   TEXT,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_task_activities_task ON task_activities(task_id);
CREATE INDEX idx_task_activities_created ON task_activities(created_at);
```

---

## 6. 文档管理模块

### 6.1 wiki_folders (知识库文件夹)
```sql
CREATE TABLE wiki_folders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    parent_id       UUID REFERENCES wiki_folders(id),
    name            VARCHAR(200) NOT NULL,
    sort_order      INTEGER DEFAULT 0,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_wiki_folders_org ON wiki_folders(organization_id);
CREATE INDEX idx_wiki_folders_parent ON wiki_folders(parent_id);
```

### 6.2 wiki_pages (知识库页面)
```sql
CREATE TABLE wiki_pages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    folder_id       UUID REFERENCES wiki_folders(id),
    title           VARCHAR(500) NOT NULL,
    content         TEXT,
    content_html    TEXT,
    format          VARCHAR(20) DEFAULT 'markdown',
    version         INTEGER NOT NULL DEFAULT 1,
    is_published    BOOLEAN DEFAULT TRUE,
    created_by      UUID NOT NULL REFERENCES users(id),
    last_edited_by  UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_wiki_pages_org ON wiki_pages(organization_id);
CREATE INDEX idx_wiki_pages_folder ON wiki_pages(folder_id);
CREATE INDEX idx_wiki_pages_search ON wiki_pages USING GIN(to_tsvector('simple', title || ' ' || content));
```

### 6.3 wiki_page_versions (页面版本历史)
```sql
CREATE TABLE wiki_page_versions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id     UUID NOT NULL REFERENCES wiki_pages(id) ON DELETE CASCADE,
    version     INTEGER NOT NULL,
    title       VARCHAR(500) NOT NULL,
    content     TEXT,
    content_html TEXT,
    change_note VARCHAR(500),
    edited_by   UUID NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(page_id, version)
);
CREATE INDEX idx_wiki_versions_page ON wiki_page_versions(page_id);
```

---

## 7. 通知模块

### 7.1 notifications (通知)
```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    type            VARCHAR(100) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    content         TEXT,
    sender_id       UUID REFERENCES users(id),
    source_type     VARCHAR(50),            -- task / wiki / leave / attendance
    source_id       UUID,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notifications_org ON notifications(organization_id);
CREATE INDEX idx_notifications_created ON notifications(created_at);
CREATE INDEX idx_notifications_type ON notifications(type);
```

### 7.2 notification_recipients (通知接收)
```sql
CREATE TABLE notification_recipients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id),
    is_read         BOOLEAN DEFAULT FALSE,
    read_at         TIMESTAMPTZ,
    UNIQUE(notification_id, user_id)
);
CREATE INDEX idx_notif_recip_user ON notification_recipients(user_id);
CREATE INDEX idx_notif_recip_unread ON notification_recipients(user_id, is_read)
    WHERE is_read = FALSE;
```

### 7.3 notification_preferences (通知偏好)
```sql
CREATE TABLE notification_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    notification_type VARCHAR(100) NOT NULL,
    channel_in_app  BOOLEAN DEFAULT TRUE,
    channel_email   BOOLEAN DEFAULT FALSE,
    digest          VARCHAR(20) DEFAULT 'instant',
    UNIQUE(user_id, notification_type)
);
CREATE INDEX idx_notif_pref_user ON notification_preferences(user_id);
```

---

## 8. 审计模块

### 8.1 audit_logs (审计日志)
```sql
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    actor_id        UUID NOT NULL REFERENCES users(id),
    action          VARCHAR(200) NOT NULL,
    resource_type   VARCHAR(50) NOT NULL,
    resource_id     UUID,
    resource_name   VARCHAR(500),
    details         JSONB DEFAULT '{}',
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_org ON audit_logs(organization_id);
CREATE INDEX idx_audit_actor ON audit_logs(actor_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
```

---

## 9. 索引与性能优化策略

### 9.1 复合索引建议
```sql
-- 考勤查询 (员工 + 日期范围)
CREATE INDEX idx_attendance_emp_date ON attendance_records(employee_id, date);

-- 请假审批 (审批人 + 状态)
CREATE INDEX idx_leave_requests_approver_status ON leave_requests(approver_id, status);

-- 绩效查询 (员工 + 周期)
CREATE INDEX idx_perf_goals_emp_period ON performance_goals(employee_id, period);

-- 任务列表 (负责人 + 状态)
CREATE INDEX idx_tasks_assignee_status ON tasks(assignee_id, status);
```

### 9.2 分区表策略
当单表数据量超过 5000 万行时考虑分区：
- `audit_logs` 按 `created_at` 月分区
- `attendance_records` 按 `date` 月分区
- `payroll_records` 按 `period` 月分区

### 9.3 扩展模块
```sql
-- 启用全文搜索
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_wiki_pages_title_trgm ON wiki_pages USING GIN(title gin_trgm_ops);

-- 启用物化路径 (部门树)
CREATE EXTENSION IF NOT EXISTS ltree;

-- 启用 hr 相关约束触发器
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

---

## 10. ER 关系总结

```
organizations
  ├── departments (树形, parent_id)
  ├── roles (RBAC角色)
  └── organization_members
        └── users
              └── employees
                    ├── employee_contracts
                    ├── attendance_records
                    ├── leave_balances
                    ├── leave_requests
                    │     └── leave_types
                    ├── performance_goals
                    ├── performance_reviews
                    └── payroll_records

roles
  ├── role_permissions
  └── permissions

positions (HR-only, 无权限含义)
  └── salary_structures

recruitment_positions
  └── candidates
        └── interview_records

tasks
  ├── task_subtasks
  ├── task_comments
  └── task_activities

wiki_folders
  └── wiki_pages
        └── wiki_page_versions

notifications
  └── notification_recipients

audit_logs (独立流水记录)
```
