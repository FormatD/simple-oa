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

### 使用 Docker Compose (推荐)

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

## 项目结构

```
enterprise-mgmt/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/         # API 路由
│   │   ├── core/           # 核心模块 (安全/RLS)
│   │   ├── models/         # SQLAlchemy 模型
│   │   └── schemas/        # Pydantic 模式
│   └── requirements.txt
├── frontend/                # Vue 3 前端
│   └── src/
│       ├── api/            # API 客户端
│       ├── layouts/        # 布局组件
│       ├── router/         # 路由
│       ├── stores/         # Pinia 状态
│       ├── types/          # TypeScript 类型
│       └── views/          # 页面组件
├── scripts/                # 初始化脚本
├── docker-compose.yml
└── .env.example
```

## Stage 1 实现的功能

- [x] 项目脚手架搭建 (Vue 3 + Element Plus + FastAPI + PostgreSQL + Redis)
- [x] 认证系统: 注册/登录/Token 轮换(R5)/密码策略(R7)
- [x] 组织管理: 组织/部门 CRUD
- [x] 权限系统: 部门+角色模型, 业务角色
- [x] 基础布局框架: Sidebar/Navbar/Dashboard 骨架
- [x] RLS 多租户隔离 (E5)
- [x] TOTP MFA 支持 (R7)
- [x] 账户锁定策略 (R7)
- [x] Token 轮换 (R5)

## API 文档

启动后端后访问: http://localhost:8000/api/v1/docs
