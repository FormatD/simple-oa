# 企业管理平台 (Enterprise Management)

基于 FastAPI + Vue 3 的企业管理平台。

## 技术栈

- **Frontend**: Vue 3 + TypeScript + Element Plus + Pinia
- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
- **Auth**: JWT (Access + Refresh Token rotation), BCrypt, TOTP MFA
- **Infrastructure**: Docker Compose

## 快速开始

### 前置要求
- Docker & Docker Compose
- Python 3.12+ (本地开发)
- Node.js 20+ (本地前端开发)

### 使用 Docker Compose (开发环境)

```bash
cp .env.example .env
docker compose up -d
```

访问 http://localhost:5173

### 本地开发

**后端:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

### 生产部署

```bash
# 准备环境变量
cp .env.example .env
# 编辑 .env 填写生产环境配置（密钥、数据库密码等）

# 使用生产配置启动
docker compose -f docker-compose.prod.yml up -d

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

## 项目结构

```
enterprise-mgmt/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/         # API 路由
│   │   ├── core/           # 核心模块 (安全/RLS/可观测性)
│   │   ├── models/         # SQLAlchemy 模型
│   │   └── schemas/        # Pydantic 模式
│   └── requirements.txt
├── frontend/                # Vue 3 前端
│   └── src/
│       ├── api/            # API 客户端
│       ├── layouts/        # 布局组件（含移动端响应式）
│       ├── router/         # 路由
│       ├── stores/         # Pinia 状态
│       ├── types/          # TypeScript 类型
│       └── views/          # 页面组件
├── scripts/                # 初始化脚本
├── docker-compose.yml      # 开发环境
├── docker-compose.prod.yml # 生产环境
└── .env.example
```

## 功能模块

### Stage 1 — 项目初始化 + 认证 + 组织与权限
- [x] 项目脚手架搭建 (Vue 3 + Element Plus + FastAPI + PostgreSQL + Redis)
- [x] 认证系统: 注册/登录/Token 轮换(R5)/密码策略(R7)
- [x] 组织管理: 组织/部门 CRUD
- [x] 权限系统: 部门+角色模型, 业务角色
- [x] 基础布局框架: Sidebar/Navbar/Dashboard 骨架
- [x] RLS 多租户隔离 (E5)
- [x] TOTP MFA 支持 (R7)
- [x] 账户锁定策略 (R7)
- [x] Token 轮换 (R5)

### Stage 2 — HR 核心
- [x] 员工档案管理（含合同、紧急联系人 AES-GCM 加密(R8)）
- [x] 请假申请与审批流程（通用工作流引擎集成）
- [x] 考勤打卡（移动端 GPS 打卡）
- [x] 考勤统计与假期额度管理
- [x] 字段级加密 (R6)
- [x] 审批链兜底 (E1)
- [x] 打卡约束 (E2)

### Stage 3 — 团队协作 + 通知
- [x] 任务管理（看板/列表视图）
- [x] 文档管理（Wiki 页面）
- [x] 评论与 @ 提及
- [x] 通知系统（WebSocket + 站内通知）
- [x] 操作日志与审计
- [x] 文件附件与预览
- [x] 权限缓存 (P1)

### Stage 4 — 数据导入 + 报表 + 扩展模块
- [x] 数据导入（批量导入员工/组织数据）
- [x] 报表统计（Dashboard 聚合、导出 Excel/PDF）
- [x] 扩展模块：入职/离职流程、培训管理、福利管理
- [x] 灾备/备份策略 (R4)

### Stage 5 — 技术债务修复 + 优化 + 上线
- [x] R2: OpenTelemetry 可观测性（日志/指标/追踪）
- [x] R3: Redis 拆分（缓存 RDB + 队列 AOF）
- [x] P2: Wiki 全文搜索优化（tsvector + GIN 索引）
- [x] P3: 部门树懒加载（按父节点分页 API）
- [x] R8: 紧急联系人 AES-256-GCM 加密
- [x] 前端响应式完善 + 移动端适配
- [x] Docker Compose 生产部署配置

## Redis 拆分说明 (R3)

Redis 已拆分为两个独立实例：

| 实例 | 端口 | 持久化 | 用途 |
|------|------|--------|------|
| redis-cache | 6379 | RDB (快照) | 权限缓存、会话缓存 |
| redis-queue | 6380 | AOF (追加) | 队列、Pub/Sub、通知 |

## OpenTelemetry 可观测性 (R2)

应用集成了 OpenTelemetry 用于链路追踪和监控：

```bash
# 设置 OTLP 导出端点（可选，留空则只收集不上报）
export OTEL_EXPORTER_ENDPOINT=http://your-otel-collector:4318/v1/traces
```

默认不上报数据，仅在本地收集。集成组件：
- FastAPI 请求追踪
- SQLAlchemy 数据库追踪
- Redis 客户端追踪

## API 文档

启动后端后访问: http://localhost:8000/api/v1/docs
