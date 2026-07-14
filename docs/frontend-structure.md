# 前端页面与组件结构设计

## 1. 技术选型

| 层 | 技术选择 |
|---|----------|
| 框架 | Vue 3 + Composition API + TypeScript |
| 状态管理 | Pinia |
| 路由 | Vue Router v4 |
| UI 库 | Element Plus |
| 请求 | Axios |
| 编辑器 | TipTap (富文本) + CodeMirror (Markdown) |
| 图表 | ECharts |
| 测试 | Vitest + Testing Library |

---

## 2. 页面路由设计

```
/login                              # 登录页
/register                           # 注册页
/forgot-password                    # 忘记密码
/                                   # 首页/Dashboard (重定向到 /dashboard)
/dashboard                          # 工作台

-- 组织管理 --
/organization                       # 组织信息
/organization/departments           # 部门管理
/organization/positions             # 岗位管理 (权限)

-- 人力资源管理 --
/hr/employees                       # 员工列表
/hr/employees/create                # 添加员工
/hr/employees/:empId                # 员工详情
/hr/org-chart                       # 组织架构图

/hr/attendance                      # 考勤管理
/hr/attendance/my                   # 我的考勤

/hr/leave                           # 请假管理
/hr/leave/requests                  # 请假记录
/hr/leave/balances                  # 请假额度

/hr/performance                     # 绩效管理
/hr/performance/goals               # 绩效目标
/hr/performance/reviews             # 绩效考核
/hr/performance/reviews/:reviewId   # 考核详情

/hr/recruitment                     # 招聘管理
/hr/recruitment/positions           # 招聘岗位
/hr/candidates                      # 候选人
/hr/interviews                      # 面试安排

/hr/payroll                         # 薪酬管理
/hr/payroll/records                 # 薪资记录
/hr/payroll/structure               # 薪酬结构

-- 任务管理 --
/tasks                              # 任务列表
/tasks/:taskId                      # 任务详情

-- 知识库 --
/wiki                               # 知识库首页
/wiki/pages/:pageId                 # 页面详情/编辑

-- 报表 --
/reports                            # 报表首页
/reports/hr/headcount               # 人员编制
/reports/hr/attendance               # 考勤统计
/reports/hr/turnover                 # 离职率分析

-- 设置 --
/settings                           # 系统设置
/settings/notification              # 通知偏好
/settings/security                  # 安全设置
```

---

## 3. 布局结构

### 3.1 主布局 (MainLayout)

```
+------------------------------------------------+
|  Navbar: Logo | 搜索 | 通知 | 用户菜单          |
+----------+-------------------------------------+
|  Sidebar  |  Main Content Area                 |
|           |                                    |
|  导航菜单  |  Breadcrumb + PageHeader          |
|  快捷入口  |  <router-view />                  |
+----------+-------------------------------------+
```

### 3.2 侧边栏 (Sidebar)
- 置顶: 全局搜索、新建按钮
- Dashboard / 工作台
- 组织管理: 部门、岗位
- 人力资源: 员工、考勤、请假、绩效、招聘、薪酬
- 任务管理: 任务列表
- 知识库
- 报表中心
- 底部: 设置

### 3.3 导航栏 (Navbar)
- 左侧: Logo + 平台名称
- 中部: 全局搜索 (Cmd+K)
- 右侧: 通知中心 + 用户头像菜单

---

## 4. 组件树 (按模块)

### 4.1 通用基础组件
```
Layout/
  MainLayout.vue
  Sidebar/
    SidebarContainer.vue
    NavMenuItem.vue
  Navbar/
    NavbarContainer.vue
    GlobalSearch.vue
    NotificationBell.vue
    UserDropdown.vue

Common/
  Avatar.vue
  UserPicker.vue
  EmployeePicker.vue
  StatusBadge.vue
  DatePicker.vue
  FileUpload.vue
  FilePreview.vue
  MarkdownEditor.vue
  ConfirmDialog.vue
  EmptyState.vue
  LoadingSkeleton.vue
  DataTable.vue
  SearchInput.vue
  PageHeader.vue
  Breadcrumb.vue
```

### 4.2 认证模块
```
Auth/
  LoginForm.vue
  RegisterForm.vue
  ForgotPasswordForm.vue
  ResetPasswordForm.vue
```

### 4.3 Dashboard 模块
```
Dashboard/
  DashboardPage.vue
  WelcomeCard.vue
  MyTaskOverview.vue
  UpcomingDeadlines.vue
  QuickStats.vue
  PendingApprovals.vue         # 待审批的请假
  UpcomingInterviews.vue       # 近期待面试
  AttendanceToday.vue            # 今日出勤概况
  TeamBirthdays.vue
```

### 4.4 组织与岗位模块
```
Organization/
  OrganizationPage.vue
  DepartmentTree.vue             # 部门树
  DepartmentDetail.vue
  CreateDepartmentModal.vue

  PositionList.vue               # 岗位列表
  PositionTree.vue               # 岗位层级树
  PositionDetail.vue
  CreatePositionModal.vue
  RoleList.vue                   # 角色列表
  RoleDetail.vue                 # 角色详情
  RolePermissionEditor.vue       # 角色权限编辑
  DepartmentMemberRole.vue       # 部门成员角色分配
  PermissionCheckTool.vue        # 权限查询工具

  OrgChart.vue                   # 组织架构图
```

### 4.5 人力资源 - 员工管理
```
HR/
  EmployeeListPage.vue
  EmployeeTable.vue
  EmployeeFilterBar.vue           # 部门/岗位/状态筛选
  CreateEmployeeModal.vue
  EmployeeDetailPage.vue
  EmployeeProfile.vue             # 基本信息
  EmployeeContractSection.vue     # 合同信息
  EmployeeContractForm.vue
  EmployeeStatusBadge.vue
  EmployeeTimeline.vue            # 入职/转岗/离职时间线
  EmployeePositionHistory.vue     # 岗位变更历史
  ReportsToTree.vue               # 汇报关系
```

### 4.6 人力资源 - 考勤
```
HR/Attendance/
  AttendancePage.vue
  AttendanceTable.vue
  AttendanceCalendar.vue          # 日历视图
  CheckInButton.vue               # 打卡按钮
  AttendanceSummary.vue           # 汇总卡片
  AttendanceAnomalyList.vue       # 异常记录
  MyAttendancePage.vue
```

### 4.7 人力资源 - 请假
```
HR/Leave/
  LeaveRequestPage.vue
  LeaveRequestForm.vue
  LeaveRequestTable.vue
  LeaveRequestDetail.vue
  LeaveApprovalAction.vue         # 审批/驳回操作
  LeaveBalanceCard.vue            # 额度卡片
  LeaveTypeManager.vue            # 请假类型管理
  LeaveCalendar.vue               # 请假日历
```

### 4.8 人力资源 - 绩效
```
HR/Performance/
  PerformancePage.vue
  GoalList.vue
  GoalEditor.vue
  GoalProgressBar.vue
  ReviewListPage.vue
  ReviewForm.vue                  # 评估表单
  ReviewDetail.vue
  ReviewRatingScale.vue
  ScoreChart.vue
```

### 4.9 人力资源 - 招聘
```
HR/Recruitment/
  RecruitmentPage.vue
  PositionPostForm.vue            # 发布招聘岗位
  PositionCard.vue
  CandidateTable.vue
  CandidateDetail.vue
  CandidateStatusBadge.vue
  InterviewScheduler.vue          # 面试安排
  InterviewFeedbackForm.vue
  InterviewCalendar.vue
```

### 4.10 人力资源 - 薪酬
```
HR/Payroll/
  PayrollPage.vue
  PayrollRecordTable.vue
  PayrollDetail.vue
  PayrollGenerateForm.vue         # 生成薪资
  SalaryStructureTable.vue
  SalaryStructureForm.vue
  PaySlipView.vue                 # 工资条展示
  PayrollSummaryChart.vue
```

### 4.11 任务管理
```
Task/
  TaskListPage.vue
  TaskTable.vue
  TaskFilterBar.vue
  CreateTaskModal.vue
  TaskDetailModal.vue
  TaskDetailPanel.vue
  TaskDescription.vue
  TaskStatusBadge.vue
  TaskPrioritySelect.vue
  SubtaskList.vue
  SubtaskItem.vue
  TaskCommentSection.vue
  TaskCommentItem.vue
  TaskCommentEditor.vue
  TaskActivityLog.vue
  QuickTaskInput.vue
```

### 4.12 知识库
```
Wiki/
  WikiPage.vue
  WikiSidebar.vue
  FolderTree.vue
  PageList.vue
  WikiEditorPage.vue
  WikiViewerPage.vue
  WikiToc.vue
  WikiVersionHistory.vue
  WikiVersionDiff.vue
  CreateFolderModal.vue
  CreatePageModal.vue
  WikiSearchResult.vue
```

### 4.13 通知模块
```
Notification/
  NotificationCenter.vue
  NotificationList.vue
  NotificationItem.vue
  NotificationPreferences.vue
```

### 4.14 报表模块
```
Report/
  ReportPage.vue
  HeadcountChart.vue
  AttendanceSummaryChart.vue
  LeaveStatsChart.vue
  PayrollSummaryChart.vue
  TurnoverChart.vue
  TaskCompletionChart.vue
  ExportModal.vue
  DateRangeSelector.vue
```

### 4.15 设置模块
```
Settings/
  SettingsPage.vue
  OrganizationSettings.vue
  SecuritySettings.vue
  NotificationSettings.vue
  AppearanceSettings.vue
```

---

## 5. 状态管理 (Store) 设计

### 5.1 全局 Store
```
stores/
  authStore.ts           # 认证状态、当前用户、岗位权限
  appStore.ts            # 全局UI状态 (侧边栏、主题)
  notificationStore.ts   # 通知列表、未读数
```

### 5.2 模块 Store
```
stores/
  organizationStore.ts   # 组织信息、部门树
  roleStore.ts                   # 角色列表、角色权限
  employeeStore.ts       # 员工列表、当前员工
  attendanceStore.ts     # 考勤记录
  leaveStore.ts          # 请假申请、额度
  performanceStore.ts    # 绩效目标、考核
  recruitmentStore.ts    # 招聘岗位、候选人
  payrollStore.ts        # 薪资记录
  taskStore.ts           # 任务列表
  wikiStore.ts           # 文件夹树、当前页面
  reportStore.ts         # 报表数据
```

### 5.3 Store 职责原则
- 每个 Store 只管理一个业务域的数据
- API 请求统一在 Store action 中发起
- 列表数据缓存 5 分钟，可主动刷新
- 表单状态不进入全局 Store，使用组件本地状态
- 权限校验依赖 authStore 中的角色和部门列表
- 每个用户可拥有多个部门角色，权限为所有角色的并集

---

## 6. 关键交互流程

### 6.1 请假审批流
```
员工提交请假 → 状态 pending
                  ↓
        上级收到通知 (WS)
                  ↓
        上级查看详情 → 审批通过/驳回
                  ↓
        员工收到结果通知
                  ↓
        额度更新 (通过时扣减)
```

### 6.2 组织架构图展示
```
加载组织架构数据 → 递归构建树
                  ↓
        按部门分组，每个节点展示
        部门名 + 负责人 + 人数
                  ↓
        展开下级部门
                  ↓
        点击员工 → 跳转员工详情
```

### 6.3 实时通知推送
```
WS 连接 (登录后建立) → 接收 notification.new
                     → Store 追加到列表
                     → NotificationBell 红点更新
                     → Toast 提示 (非聚焦页面不弹)
```

---

## 7. 响应式适配策略

| 断点 | 宽度 | 布局调整 |
|------|------|----------|
| xs | < 640px | 侧边栏抽屉，表格变列表 |
| sm | 640-768px | 侧边栏图标模式 |
| md | 768-1024px | 完整侧边栏 |
| lg | 1024-1280px | 完整布局 + 侧栏 |
| xl | > 1280px | 完整布局 |
