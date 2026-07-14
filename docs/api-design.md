# API 接口设计

## 1. 通用规范

### 1.1 基础信息
- Base URL: `/api/v1`
- 协议: HTTPS (生产)
- 数据格式: JSON
- 时间格式: ISO 8601 (UTC)
- 分页格式: `{ "data": [...], "pagination": { "page": 1, "page_size": 20, "total": 100 } }`

### 1.2 认证方式
- Header: `Authorization: Bearer <access_token>`
- Refresh Token: `POST /api/v1/auth/refresh`

### 1.3 通用响应格式
```json
{ "code": 0, "message": "ok", "data": { ... } }
{ "code": 40001, "message": "参数校验失败", "details": {...} }
```

### 1.4 错误码范围
| 范围 | 含义 |
|------|------|
| 0xxxx | 通用错误 |
| 1xxxx | 认证授权 |
| 2xxxx | 用户/组织 |
| 3xxxx | 人力资源 (HR) |
| 4xxxx | 任务 |
| 5xxxx | 文档 |
| 6xxxx | 通知 |

### 1.5 HTTP 状态码
- 200: 成功
- 201: 创建成功
- 400: 请求参数错误
- 401: 未认证
- 403: 无权限 (岗位权限校验)
- 404: 资源不存在
- 409: 资源冲突
- 422: 业务逻辑错误
- 429: 请求过于频繁
- 500: 服务器内部错误

### 1.6 WebSocket 端点
- `wss://host/ws/v1/notifications?token=<jwt>`
- 事件格式: `{ "event": "notification.new", "data": { ... } }`

---

## 2. 认证模块

### POST /api/v1/auth/login
登录
```
Request:  { "email": "user@example.com", "password": "***" }
Response: { "access_token": "...", "refresh_token": "...", "expires_in": 3600 }
```

### POST /api/v1/auth/register
注册
```
Request:  { "email": "...", "password": "...", "display_name": "..." }
Response: { "user": {...}, "access_token": "...", "refresh_token": "..." }
```

### POST /api/v1/auth/refresh
刷新 Token
```
Request:  { "refresh_token": "..." }
Response: { "access_token": "...", "refresh_token": "...", "expires_in": 3600 }
```

### POST /api/v1/auth/logout
登出
```
Request:  { "refresh_token": "..." }
Response: { "message": "ok" }
```

### GET /api/v1/auth/me
获取当前用户信息 (含岗位权限)
```
Response: { "id": "...", "email": "...", "display_name": "...",
            "employee": {"id":"...", "employee_no":"E001", "position": "..."},
            "permissions": ["employee.read", "attendance.approve"],
            "position_level": 3,
            "organization": {...} }
```

### PUT /api/v1/auth/password
修改密码
```
Request:  { "old_password": "...", "new_password": "..." }
Response: { "message": "ok" }
```

### POST /api/v1/auth/forgot-password
忘记密码
```
Request:  { "email": "..." }
Response: { "message": "重置链接已发送到邮箱" }
```

---

## 3. 用户与组织模块

### 3.1 组织管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/organizations | 创建组织 |
| GET | /api/v1/organizations | 用户所在组织列表 |
| GET | /api/v1/organizations/:orgId | 组织详情 |
| PUT | /api/v1/organizations/:orgId | 更新组织 |
| DELETE | /api/v1/organizations/:orgId | 删除组织 |

### 3.2 部门管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/organizations/:orgId/departments | 创建部门 |
| GET | /api/v1/organizations/:orgId/departments | 部门树 |
| GET | /api/v1/organizations/:orgId/departments/:deptId | 部门详情 |
| PUT | /api/v1/organizations/:orgId/departments/:deptId | 更新部门 |
| DELETE | /api/v1/organizations/:orgId/departments/:deptId | 删除部门 |

### 3.3 用户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/users | 用户列表 |
| GET | /api/v1/users/:userId | 用户详情 |
| PUT | /api/v1/users/:userId | 更新用户信息 |
| GET | /api/v1/users/search?q=xxx | 搜索用户 |

### 3.4 组织成员

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/organizations/:orgId/members | 添加成员 |
| DELETE | /api/v1/organizations/:orgId/members/:userId | 移除成员 |
| GET | /api/v1/organizations/:orgId/members | 成员列表 |

### 3.5 角色管理 (Role)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/organizations/:orgId/roles | 创建角色 |
| GET | /api/v1/organizations/:orgId/roles | 角色列表 |
| GET | /api/v1/organizations/:orgId/roles/:roleId | 角色详情 |
| PUT | /api/v1/organizations/:orgId/roles/:roleId | 更新角色 (非系统) |
| DELETE | /api/v1/organizations/:orgId/roles/:roleId | 删除角色 (非系统) |
| PUT | /api/v1/organizations/:orgId/roles/:roleId/permissions | 设置角色权限 |
| GET | /api/v1/organizations/:orgId/roles/:roleId/permissions | 获取角色权限 |

### 3.6 部门成员角色分配

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/organizations/:orgId/departments/:deptId/members | 添加成员并分配角色 |
| DELETE | /api/v1/organizations/:orgId/departments/:deptId/members/:userId | 移除部门成员 |
| PUT | /api/v1/organizations/:orgId/departments/:deptId/members/:userId/role | 变更成员角色 |
| GET | /api/v1/organizations/:orgId/departments/:deptId/members | 部门成员列表 (含角色) |

### 3.7 权限查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/permissions | 所有可分配权限列表 |
| GET | /api/v1/organizations/:orgId/permissions/check | 校验用户是否有指定权限 (含部门范围) |
| GET | /api/v1/organizations/:orgId/users/:userId/permissions | 查看用户的完整权限 (合并所有部门角色) |

---

## 4. 人力资源管理模块 (HR)

### 4.1 员工档案

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/employees | 创建员工档案 |
| GET | /api/v1/hr/employees | 员工列表 (支持筛选) |
| GET | /api/v1/hr/employees/:empId | 员工详情 |
| PUT | /api/v1/hr/employees/:empId | 更新员工信息 |
| DELETE | /api/v1/hr/employees/:empId | 删除员工 |
| PUT | /api/v1/hr/employees/:empId/status | 变更员工状态 |
| GET | /api/v1/hr/organization-chart | 组织架构图 |

**员工列表查询参数:**
```
?page=1&page_size=20
&department_id=uuid
&position_id=uuid
&status=active,resigned
&employment_type=full_time
&search=姓名/工号
```

**创建员工请求:**
```json
{
  "user_id": "uuid",
  "employee_no": "E001",
  "department_id": "uuid",
  "position_id": "uuid",
  "reports_to": "uuid",
  "hire_date": "2026-01-01",
  "employment_type": "full_time",
  "work_location": "北京"
}
```

### 4.2 员工合同

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/employees/:empId/contracts | 添加合同 |
| GET | /api/v1/hr/employees/:empId/contracts | 合同列表 |
| PUT | /api/v1/hr/contracts/:contractId | 更新合同 |
| DELETE | /api/v1/hr/contracts/:contractId | 删除合同 |

### 4.3 考勤管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/attendance | 打卡 (check-in/out) |
| GET | /api/v1/hr/attendance | 考勤记录列表 |
| GET | /api/v1/hr/attendance/summary | 考勤汇总统计 |
| PUT | /api/v1/hr/attendance/:recordId | 修正考勤记录 |
| GET | /api/v1/hr/attendance/my | 我的考勤 |

**考勤查询:**
```
?employee_id=uuid&date_from=2026-01-01&date_to=2026-01-31&status=late,absent
```

**打卡请求:**
```json
{
  "type": "check_in",   // check_in / check_out
  "timestamp": "2026-01-15T09:00:00Z",
  "location": { "lat": 39.9, "lng": 116.4 }
}
```

### 4.4 请假管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/hr/leave-types | 请假类型列表 |
| POST | /api/v1/hr/leave-types | 创建请假类型 (管理员) |
| PUT | /api/v1/hr/leave-types/:typeId | 更新请假类型 |

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/hr/leave-balances | 我的请假额度 |
| GET | /api/v1/hr/leave-balances/:empId | 员工请假额度 (上级) |

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/leave-requests | 提交请假申请 |
| GET | /api/v1/hr/leave-requests | 请假列表 |
| GET | /api/v1/hr/leave-requests/:reqId | 请假详情 |
| PUT | /api/v1/hr/leave-requests/:reqId | 修改申请 (待审批时) |
| DELETE | /api/v1/hr/leave-requests/:reqId | 撤销申请 |
| PUT | /api/v1/hr/leave-requests/:reqId/approve | 审批通过 (上级) |
| PUT | /api/v1/hr/leave-requests/:reqId/reject | 审批驳回 (上级) |

**请假申请请求:**
```json
{
  "leave_type_id": "uuid",
  "start_date": "2026-01-20",
  "end_date": "2026-01-21",
  "reason": "身体不适"
}
```

### 4.5 绩效管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/performance/goals | 创建绩效目标 |
| GET | /api/v1/hr/performance/goals | 目标列表 |
| PUT | /api/v1/hr/performance/goals/:goalId | 更新目标进度 |
| DELETE | /api/v1/hr/performance/goals/:goalId | 删除目标 |

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/performance/reviews | 创建考核 (上级) |
| GET | /api/v1/hr/performance/reviews | 考核列表 |
| GET | /api/v1/hr/performance/reviews/:reviewId | 考核详情 |
| PUT | /api/v1/hr/performance/reviews/:reviewId | 提交/修改考核 |
| PUT | /api/v1/hr/performance/reviews/:reviewId/acknowledge | 员工确认 |

### 4.6 招聘管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/recruitment/positions | 发布招聘岗位 |
| GET | /api/v1/hr/recruitment/positions | 招聘岗位列表 |
| PUT | /api/v1/hr/recruitment/positions/:posId | 更新招聘岗位 |
| PUT | /api/v1/hr/recruitment/positions/:posId/status | 更改岗位状态 |

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/candidates | 添加候选人 |
| GET | /api/v1/hr/candidates | 候选人列表 |
| PUT | /api/v1/hr/candidates/:candId | 更新候选人 |
| PUT | /api/v1/hr/candidates/:candId/status | 更新候选人状态 |

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/interviews | 安排面试 |
| GET | /api/v1/hr/interviews | 面试列表 |
| PUT | /api/v1/hr/interviews/:interviewId | 提交面试反馈 |
| PUT | /api/v1/hr/interviews/:interviewId/result | 更新面试结果 |

### 4.7 薪酬管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/hr/salary-structures | 薪酬结构列表 |
| POST | /api/v1/hr/salary-structures | 创建薪酬结构 |
| PUT | /api/v1/hr/salary-structures/:structId | 更新薪酬结构 |

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/hr/payroll | 生成薪资记录 |
| GET | /api/v1/hr/payroll | 薪资记录列表 |
| GET | /api/v1/hr/payroll/:payrollId | 薪资详情 |
| PUT | /api/v1/hr/payroll/:payrollId/confirm | 确认薪资 |
| PUT | /api/v1/hr/payroll/:payrollId/pay | 标记已发放 |

---

## 5. 任务管理模块

### 5.1 任务 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/tasks | 创建任务 |
| GET | /api/v1/tasks | 任务列表 |
| GET | /api/v1/tasks/:taskId | 任务详情 |
| PUT | /api/v1/tasks/:taskId | 更新任务 |
| DELETE | /api/v1/tasks/:taskId | 删除任务 |
| PUT | /api/v1/tasks/:taskId/status | 更新状态 |

**创建任务:**
```json
{
  "title": "完成HR模块设计",
  "description": "...",
  "assignee_id": "uuid",
  "priority": "high",
  "due_date": "2026-01-20"
}
```

**任务列表:**
```
GET /api/v1/tasks?status=todo,in_progress&assignee_id=uuid&priority=high&search=关键词
GET /api/v1/tasks/my?status=todo,in_progress
```

### 5.2 子任务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/tasks/:taskId/subtasks | 添加子任务 |
| GET | /api/v1/tasks/:taskId/subtasks | 子任务列表 |
| PUT | /api/v1/tasks/:taskId/subtasks/:subId | 更新子任务 |
| DELETE | /api/v1/tasks/:taskId/subtasks/:subId | 删除子任务 |

### 5.3 任务评论

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/tasks/:taskId/comments | 添加评论 |
| GET | /api/v1/tasks/:taskId/comments | 评论列表 |
| PUT | /api/v1/tasks/:taskId/comments/:commentId | 编辑评论 |
| DELETE | /api/v1/tasks/:taskId/comments/:commentId | 删除评论 |

### 5.4 任务活动日志

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/tasks/:taskId/activities | 活动日志 |

---

## 6. 文档管理模块

### 6.1 文件夹

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/wiki/folders | 创建文件夹 |
| GET | /api/v1/wiki/folders | 文件夹树 |
| PUT | /api/v1/wiki/folders/:folderId | 更新文件夹 |
| DELETE | /api/v1/wiki/folders/:folderId | 删除文件夹 |

### 6.2 页面

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/wiki/pages | 创建页面 |
| GET | /api/v1/wiki/pages/:pageId | 页面详情 |
| PUT | /api/v1/wiki/pages/:pageId | 更新页面 |
| DELETE | /api/v1/wiki/pages/:pageId | 删除页面 |
| GET | /api/v1/wiki/search?q=xxx | 全文搜索 |

### 6.3 版本管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/wiki/pages/:pageId/versions | 版本列表 |
| GET | /api/v1/wiki/pages/:pageId/versions/:version | 版本详情 |
| POST | /api/v1/wiki/pages/:pageId/versions/:version/restore | 回滚版本 |

---

## 7. 通知模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/notifications | 我的通知列表 |
| GET | /api/v1/notifications/unread-count | 未读数 |
| PUT | /api/v1/notifications/:notifId/read | 标记已读 |
| PUT | /api/v1/notifications/read-all | 全部标记已读 |
| GET | /api/v1/notifications/preferences | 通知偏好设置 |
| PUT | /api/v1/notifications/preferences | 更新通知偏好 |

**WebSocket 事件:**
| 事件 | 说明 |
|------|------|
| notification.new | 新通知 |
| task.updated | 任务变更 |
| task.commented | 新评论 |
| leave.requested | 请假申请提交 (通知上级) |
| leave.approved | 请假审批通过 |
| leave.rejected | 请假驳回 |
| attendance.anomaly | 考勤异常 |

---

## 8. 报表与统计模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/reports/personal-summary | 个人工作统计 |
| GET | /api/v1/reports/hr/headcount | 人员编制统计 |
| GET | /api/v1/reports/hr/attendance-summary | 考勤汇总 |
| GET | /api/v1/reports/hr/leave-summary | 请假统计 |
| GET | /api/v1/reports/hr/payroll-summary | 薪资汇总 |
| GET | /api/v1/reports/hr/turnover | 离职率统计 |
| POST | /api/v1/reports/export | 导出数据 |

---

## 9. 审计模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/audit-logs | 审计日志列表 |
| GET | /api/v1/audit-logs/:logId | 日志详情 |
| GET | /api/v1/audit-logs/export | 导出审计日志 |

**查询参数:**
```
?page=1&page_size=50
&actor_id=uuid
&action=employee.create,leave.approve
&resource_type=employee
&date_from=2026-01-01T00:00:00Z
&date_to=2026-03-31T23:59:59Z
```

---

## 10. 文件/资源上传

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/uploads | 上传文件 (multipart) |
| GET | /api/v1/uploads/:uploadId | 文件信息 |
| GET | /api/v1/uploads/:uploadId/download | 下载/预览 |
| DELETE | /api/v1/uploads/:uploadId | 删除文件 |

---

## 11. 全局搜索

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/search | 全局搜索 |

**查询参数:**
```
?q=搜索关键词&scope=task,hr,wiki&page=1&page_size=20
```

**响应:**
```json
{
  "results": [
    { "type": "task", "id": "uuid", "title": "...", "match": "..." },
    { "type": "employee", "id": "uuid", "name": "张三", "match": "..." },
    { "type": "wiki", "id": "uuid", "title": "...", "match": "..." }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 5 }
}
```

---

## 12. 接口版本与兼容策略

- 版本通过 URL 路径标识 (`/api/v1/`, `/api/v2/`)
- 新字段直接添加到 JSON 响应，不做 breaking change
- 字段废弃: 标记 deprecated 并存留至少 2 个 minor 版本
- 破坏性变更: 提升版本号
- 所有接口提供 OpenAPI 3.0 文档: `GET /api/v1/openapi.json`
