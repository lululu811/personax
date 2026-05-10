# PersonaX Web UI — Phase 1: 基础框架实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 Nuxt 3 + FastAPI 基础框架，实现三栏布局、用户认证、以及与 OrchestrationEngine 的 API 对接。

**Architecture:** Nuxt 3 前端通过 REST API 和 WebSocket 与 FastAPI 后端通信。FastAPI 后端直接调用现有的 OrchestrationEngine，复用全部编排层、工具层、人格层和知识层。用户数据存 SQLite，通过 JWT 认证。

**Tech Stack:** Nuxt 3, Vue 3, TailwindCSS, Pinia, FastAPI, SQLAlchemy, SQLite, python-jose (JWT), passlib (bcrypt)

---

## 文件结构总览

### 新建文件

```
web/                                    # Nuxt 3 前端
├── nuxt.config.ts
├── package.json
├── tailwind.config.ts
├── tsconfig.json
├── app.vue
├── pages/
│   ├── index.vue                       # 重定向到 /chat
│   ├── chat.vue                        # 对话分析页
│   └── auth/
│       ├── login.vue
│       └── register.vue
├── components/
│   ├── layout/
│   │   ├── AppSidebar.vue              # 左侧边栏
│   │   └── AppRightPanel.vue           # 右侧技术面板
│   ├── chat/
│   │   ├── MessageList.vue             # 消息列表
│   │   ├── MessageBubble.vue           # 单条消息
│   │   └── ChatInput.vue              # 输入框
│   └── common/
│       └── PersonaAvatar.vue           # 人格头像
├── composables/
│   ├── useAuth.ts                      # 认证状态
│   └── useChat.ts                      # 对话状态
├── stores/
│   ├── auth.ts                         # Pinia 认证 store
│   └── chat.ts                         # Pinia 对话 store
├── layouts/
│   └── default.vue                     # 默认布局（三栏）
└── middleware/
    └── auth.ts                         # 认证中间件

api/                                    # FastAPI 后端
├── main.py                             # FastAPI app 入口
├── config.py                           # 配置管理
├── auth/
│   ├── __init__.py
│   ├── router.py                       # 认证路由
│   ├── models.py                       # SQLAlchemy 用户模型
│   ├── schemas.py                      # Pydantic schemas
│   ├── dependencies.py                 # JWT 依赖注入
│   └── utils.py                        # 密码哈希、JWT 工具
├── v1/
│   ├── __init__.py
│   ├── router.py                       # v1 路由汇总
│   ├── chat.py                         # 对话 API
│   ├── personas.py                     # 人格列表 API
│   └── tools.py                        # 工具列表 API
├── db/
│   ├── __init__.py
│   └── database.py                     # SQLite 连接
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    └── test_chat.py
```

---

## Task 1: 初始化 Nuxt 3 项目

**Files:**
- Create: `web/package.json`
- Create: `web/nuxt.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/app.vue`

- [ ] **Step 1: 创建 Nuxt 3 项目**

```bash
cd /home/chenlei/001_AI/personax
npx nuxi@latest init web --no-install --git-init false
```

- [ ] **Step 2: 安装依赖**

```bash
cd web
npm install
npm install -D @nuxtjs/tailwindcss @pinia/nuxt
npm install pinia markdown-it @vueuse/core
```

- [ ] **Step 3: 配置 nuxt.config.ts**

```typescript
// web/nuxt.config.ts
export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
    },
  },
  app: {
    head: {
      title: 'PersonaX',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
    },
  },
})
```

- [ ] **Step 4: 配置 TailwindCSS**

```typescript
// web/tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  content: [
    './components/**/*.{vue,js,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './app.vue',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
```

- [ ] **Step 5: 验证项目启动**

```bash
cd web && npm run dev -- --port 3000
```

Expected: Nuxt dev server starts on http://localhost:3000

- [ ] **Step 6: Commit**

```bash
git add web/
git commit -m "feat(web): initialize Nuxt 3 project with TailwindCSS and Pinia"
```

---

## Task 2: 初始化 FastAPI 后端

**Files:**
- Create: `api/__init__.py`
- Create: `api/main.py`
- Create: `api/config.py`
- Create: `api/db/__init__.py`
- Create: `api/db/database.py`
- Create: `api/tests/__init__.py`
- Create: `api/tests/conftest.py`

- [ ] **Step 1: 创建项目结构**

```bash
cd /home/chenlei/001_AI/personax
mkdir -p api/auth api/v1 api/db api/tests
touch api/__init__.py api/auth/__init__.py api/v1/__init__.py api/db/__init__.py api/tests/__init__.py
```

- [ ] **Step 2: 安装 Python 依赖**

```bash
pip install fastapi uvicorn[standard] python-jose[cryptography] passlib[bcrypt] python-multipart aiosqlite sqlalchemy[asyncio] httpx pytest pytest-asyncio
```

- [ ] **Step 3: 创建配置模块**

```python
# api/config.py
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PersonaX API"
    database_url: str = "sqlite+aiosqlite:///./data/personax_web.db"
    secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 创建数据库连接**

```python
# api/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from api.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 5: 创建 FastAPI 入口**

```python
# api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import get_settings
from api.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: 创建测试配置**

```python
# api/tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.db.database import init_db, engine, Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 7: 验证后端启动**

```bash
cd /home/chenlei/001_AI/personax
uvicorn api.main:app --reload --port 8000
```

Expected: FastAPI starts on http://localhost:8000, Swagger at /docs

- [ ] **Step 8: Commit**

```bash
git add api/ requirements.txt
git commit -m "feat(api): initialize FastAPI backend with SQLite and health endpoint"
```

---

## Task 3: 用户认证 — 数据模型

**Files:**
- Create: `api/auth/models.py`
- Create: `api/auth/schemas.py`
- Create: `api/auth/utils.py`
- Test: `api/tests/test_auth.py`

- [ ] **Step 1: 写用户模型测试**

```python
# api/tests/test_auth.py
import pytest
from api.auth.models import User


def test_user_model():
    """User model has required fields."""
    user = User(email="test@example.com", hashed_hash="xxx", display_name="Test")
    assert user.email == "test@example.com"
    assert user.display_name == "Test"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/chenlei/001_AI/personax
python -m pytest api/tests/test_auth.py::test_user_model -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'api.auth.models'`

- [ ] **Step 3: 创建用户模型**

```python
# api/auth/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from api.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: 创建 Pydantic schemas**

```python
# api/auth/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

- [ ] **Step 5: 创建密码和 JWT 工具**

```python
# api/auth/utils.py
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from api.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
```

- [ ] **Step 6: 运行测试确认通过**

```bash
python -m pytest api/tests/test_auth.py::test_user_model -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add api/auth/ api/tests/test_auth.py
git commit -m "feat(api): add user model, schemas, and auth utilities"
```

---

## Task 4: 用户认证 — 注册和登录 API

**Files:**
- Create: `api/auth/router.py`
- Create: `api/auth/dependencies.py`
- Modify: `api/main.py`
- Modify: `api/tests/test_auth.py`

- [ ] **Step 1: 写注册和登录测试**

```python
# api/tests/test_auth.py — 追加
import pytest


@pytest.mark.asyncio
async def test_register(client):
    """POST /api/v1/auth/register creates user and returns token."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "securepass123",
        "display_name": "New User",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate(client):
    """POST /api/v1/auth/register rejects duplicate email."""
    await client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "pass123",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "pass456",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    """POST /api/v1/auth/login returns token for valid credentials."""
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """POST /api/v1/auth/login rejects wrong password."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com",
        "password": "correct",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "incorrect",
    })
    assert resp.status_code == 401
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest api/tests/test_auth.py -v -k "register or login"
```

Expected: FAIL — 404 (路由不存在)

- [ ] **Step 3: 创建认证依赖注入**

```python
# api/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.db.database import get_db
from api.auth.models import User
from api.auth.utils import decode_access_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
```

- [ ] **Step 4: 创建认证路由**

```python
# api/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.db.database import get_db
from api.auth.models import User
from api.auth.schemas import UserCreate, UserResponse, Token, LoginRequest
from api.auth.utils import hash_password, verify_password, create_access_token
from api.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        display_name=data.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user
```

- [ ] **Step 5: 注册路由到 main.py**

```python
# api/main.py — 在 app 创建后添加
from api.auth.router import router as auth_router
app.include_router(auth_router, prefix="/api/v1")
```

- [ ] **Step 6: 运行测试确认通过**

```bash
python -m pytest api/tests/test_auth.py -v
```

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add api/auth/ api/main.py api/tests/test_auth.py
git commit -m "feat(api): add register, login, and /me endpoints with JWT auth"
```

---

## Task 5: 人格和工具列表 API

**Files:**
- Create: `api/v1/personas.py`
- Create: `api/v1/tools.py`
- Create: `api/v1/router.py`
- Modify: `api/main.py`
- Create: `api/tests/test_personas.py`

- [ ] **Step 1: 写人格列表测试**

```python
# api/tests/test_personas.py
import pytest


@pytest.mark.asyncio
async def test_list_personas(client):
    """GET /api/v1/personas returns available personas."""
    resp = await client.get("/api/v1/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "name" in data[0]
    assert "display_name" in data[0]


@pytest.mark.asyncio
async def test_list_tools(client):
    """GET /api/v1/tools returns available technical tools."""
    resp = await client.get("/api/v1/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest api/tests/test_personas.py -v
```

Expected: FAIL — 404

- [ ] **Step 3: 创建人格列表 API**

```python
# api/v1/personas.py
from fastapi import APIRouter
import yaml
from pathlib import Path

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("")
async def list_personas():
    config_path = Path(__file__).parent.parent.parent / "registry" / "personas.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    personas = []
    for name, cfg in config.get("personas", {}).items():
        personas.append({
            "name": name,
            "display_name": cfg.get("display_name", cfg.get("name", name)),
            "description": cfg.get("description", ""),
            "features": cfg.get("features", {}),
        })
    return personas
```

- [ ] **Step 4: 创建工具列表 API**

```python
# api/v1/tools.py
from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def list_tools():
    from tools.quant.technical.interface import list_tools as _list_tools
    tools = _list_tools()
    return [
        {"name": t.name, "description": t.description}
        for t in tools
    ]
```

- [ ] **Step 5: 创建 v1 路由汇总**

```python
# api/v1/router.py
from fastapi import APIRouter
from api.v1.personas import router as personas_router
from api.v1.tools import router as tools_router

router = APIRouter(prefix="/v1")
router.include_router(personas_router)
router.include_router(tools_router)
```

- [ ] **Step 6: 注册到 main.py**

```python
# api/main.py — 替换单独的 auth_router 注册
from api.v1.router import router as v1_router
from api.auth.router import router as auth_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(v1_router, prefix="/api")
```

- [ ] **Step 7: 运行测试确认通过**

```bash
python -m pytest api/tests/test_personas.py -v
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add api/v1/ api/main.py api/tests/test_personas.py
git commit -m "feat(api): add personas and tools list endpoints"
```

---

## Task 6: 对话 API — 非流式

**Files:**
- Create: `api/v1/chat.py`
- Modify: `api/v1/router.py`
- Create: `api/tests/test_chat.py`

- [ ] **Step 1: 写对话测试**

```python
# api/tests/test_chat.py
import pytest


@pytest.mark.asyncio
async def test_chat_requires_auth(client):
    """POST /api/v1/chat requires authentication."""
    resp = await client.post("/api/v1/chat", json={
        "query": "帮我看看茅台",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_chat_with_auth(client):
    """POST /api/v1/chat returns analysis for authenticated user."""
    # Register
    reg = await client.post("/api/v1/auth/register", json={
        "email": "chat@example.com",
        "password": "pass123",
    })
    token = reg.json()["access_token"]

    # Chat
    resp = await client.post("/api/v1/chat", json={
        "query": "帮我看看KDJ指标",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "persona_analysis" in data
    assert "route" in data
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest api/tests/test_chat.py -v
```

Expected: FAIL — 404

- [ ] **Step 3: 创建对话 API**

```python
# api/v1/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.auth.dependencies import get_current_user
from api.auth.models import User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    stock_code: str | None = None
    persona: str = "zettaranc"
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    persona_analysis: str
    route: dict
    tool_results: dict = {}
    strategy_results: dict = {}
    aggregated_signal: dict = {}
    conversation_id: str | None = None


# Lazy-loaded engine singleton
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        from orchestration.engine import OrchestrationEngine
        _engine = OrchestrationEngine()
    return _engine


@router.post("", response_model=ChatResponse)
async def chat(data: ChatRequest, user: User = Depends(get_current_user)):
    from orchestration.engine import OrchestrationRequest
    import pandas as pd

    engine = get_engine()

    df = None
    if data.stock_code:
        try:
            from data.db import Database
            db = Database()
            df = db.get_daily(data.stock_code)
        except Exception:
            pass

    request = OrchestrationRequest(
        query=data.query,
        df=df,
        stock_code=data.stock_code,
        persona_priority=[data.persona],
        conversation_id=data.conversation_id,
    )

    response = engine.execute(request)

    return ChatResponse(
        persona_analysis=response.persona_analysis,
        route={
            "primary": response.route.primary,
            "intent": response.route.intent,
            "confidence": response.route.confidence,
        },
        tool_results={k: str(v) for k, v in response.tool_results.items()},
        strategy_results={k: {
            "action": v.action,
            "confidence": v.confidence,
            "reason": v.reason,
        } for k, v in response.strategy_results.items()},
        aggregated_signal={
            "action": response.aggregated_signal.action,
            "confidence": response.aggregated_signal.confidence,
        },
        conversation_id=response.conversation_id,
    )
```

- [ ] **Step 4: 注册路由**

```python
# api/v1/router.py — 添加
from api.v1.chat import router as chat_router
router.include_router(chat_router)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest api/tests/test_chat.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add api/v1/chat.py api/v1/router.py api/tests/test_chat.py
git commit -m "feat(api): add chat endpoint integrating OrchestrationEngine"
```

---

## Task 7: Nuxt 三栏布局

**Files:**
- Create: `web/layouts/default.vue`
- Create: `web/components/layout/AppSidebar.vue`
- Create: `web/components/layout/AppRightPanel.vue`
- Create: `web/components/common/PersonaAvatar.vue`

- [ ] **Step 1: 创建默认布局**

```vue
<!-- web/layouts/default.vue -->
<template>
  <div class="flex h-screen bg-gray-50">
    <LayoutAppSidebar />
    <main class="flex-1 flex flex-col overflow-hidden">
      <slot />
    </main>
    <LayoutAppRightPanel />
  </div>
</template>
```

- [ ] **Step 2: 创建左侧边栏**

```vue
<!-- web/components/layout/AppSidebar.vue -->
<template>
  <aside class="w-[200px] bg-slate-800 text-slate-300 flex flex-col h-full">
    <!-- Logo -->
    <div class="p-4 font-bold text-white text-lg">PersonaX</div>

    <!-- Navigation -->
    <nav class="px-3 mb-4">
      <NuxtLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-2 px-3 py-2 rounded-md text-sm mb-1"
        :class="$route.path === item.path ? 'bg-slate-700 text-white' : 'hover:bg-slate-700/50'"
      >
        <span>{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <!-- Persona selector -->
    <div class="px-3 mb-4">
      <div class="text-xs uppercase text-slate-500 mb-2 px-3">当前人格</div>
      <button
        v-for="p in personas"
        :key="p.name"
        class="flex items-center gap-2 px-3 py-2 rounded-md text-sm w-full mb-1"
        :class="p.name === activePersona ? 'bg-primary-600 text-white' : 'hover:bg-slate-700/50'"
        @click="$emit('persona-change', p.name)"
      >
        <CommonPersonaAvatar :name="p.name" :size="20" />
        <span>{{ p.display_name }}</span>
      </button>
    </div>

    <!-- Spacer -->
    <div class="flex-1" />

    <!-- User -->
    <div class="p-3 border-t border-slate-700">
      <div class="flex items-center gap-2 text-sm">
        <div class="w-6 h-6 bg-slate-600 rounded-full" />
        <span>{{ user?.display_name || user?.email || '未登录' }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
defineEmits<{
  'persona-change': [name: string]
}>()

const navItems = [
  { path: '/chat', icon: '💬', label: '对话' },
  { path: '/chart/600519', icon: '📈', label: '图表' },
  { path: '/report/600519', icon: '📊', label: '财报分析' },
]

const activePersona = useState('activePersona', () => 'zettaranc')

const { data: personas } = await useFetch('/api/v1/personas', {
  baseURL: useRuntimeConfig().public.apiBase,
  default: () => [],
})

const user = useState('user')
</script>
```

- [ ] **Step 3: 创建右侧面板**

```vue
<!-- web/components/layout/AppRightPanel.vue -->
<template>
  <aside class="w-[280px] bg-white border-l border-gray-200 p-4 overflow-y-auto">
    <h3 class="font-semibold mb-3 text-sm">📈 技术面板</h3>

    <div v-if="toolResults && Object.keys(toolResults).length > 0">
      <div
        v-for="(result, name) in toolResults"
        :key="name"
        class="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-2"
      >
        <div class="font-medium text-sm mb-2">{{ name }}</div>
        <div v-if="result.signals" class="text-xs space-y-1">
          <div
            v-for="(value, signal) in result.signals"
            :key="signal"
            class="flex justify-between"
          >
            <span class="text-gray-500">{{ signal }}</span>
            <span :class="value ? 'text-green-600' : 'text-gray-400'">
              {{ value ? '✅' : '—' }}
            </span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="text-sm text-gray-400 text-center py-8">
      发送消息后查看技术指标
    </div>
  </aside>
</template>

<script setup lang="ts">
const toolResults = useState('toolResults', () => ({}))
</script>
```

- [ ] **Step 4: 创建人格头像组件**

```vue
<!-- web/components/common/PersonaAvatar.vue -->
<template>
  <div
    class="rounded-full flex items-center justify-center text-white font-bold"
    :style="{ width: `${size}px`, height: `${size}px`, background: color, fontSize: `${size * 0.45}px` }"
  >
    {{ initial }}
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  name: string
  size?: number
}>()

const personaColors: Record<string, string> = {
  zettaranc: '#3b82f6',
  fupeng: '#10b981',
  boss_mo: '#f59e0b',
  financial_analyst: '#8b5cf6',
}

const personaInitials: Record<string, string> = {
  zettaranc: 'Z',
  fupeng: '付',
  boss_mo: 'B',
  financial_analyst: '财',
}

const color = computed(() => personaColors[props.name] || '#6b7280')
const initial = computed(() => personaInitials[props.name] || props.name[0])
const size = computed(() => props.size || 28)
</script>
```

- [ ] **Step 5: 验证布局**

```bash
cd web && npm run dev -- --port 3000
```

Expected: 浏览器打开 http://localhost:3000 看到三栏布局

- [ ] **Step 6: Commit**

```bash
git add web/layouts/ web/components/
git commit -m "feat(web): add three-column layout with sidebar and right panel"
```

---

## Task 8: 认证页面（注册/登录）

**Files:**
- Create: `web/pages/auth/login.vue`
- Create: `web/pages/auth/register.vue`
- Create: `web/composables/useAuth.ts`
- Create: `web/stores/auth.ts`
- Create: `web/middleware/auth.ts`
- Modify: `web/pages/index.vue`

- [ ] **Step 1: 创建认证 composable**

```typescript
// web/composables/useAuth.ts
export function useAuth() {
  const config = useRuntimeConfig()
  const token = useCookie('auth_token')
  const user = useState<any>('user', () => null)

  async function login(email: string, password: string) {
    const res = await $fetch<{ access_token: string }>(`${config.public.apiBase}/api/v1/auth/login`, {
      method: 'POST',
      body: { email, password },
    })
    token.value = res.access_token
    await fetchUser()
  }

  async function register(email: string, password: string, displayName?: string) {
    const res = await $fetch<{ access_token: string }>(`${config.public.apiBase}/api/v1/auth/register`, {
      method: 'POST',
      body: { email, password, display_name: displayName },
    })
    token.value = res.access_token
    await fetchUser()
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await $fetch(`${config.public.apiBase}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token.value}` },
      })
    } catch {
      token.value = null
      user.value = null
    }
  }

  function logout() {
    token.value = null
    user.value = null
    navigateTo('/auth/login')
  }

  return { user, token, login, register, fetchUser, logout, isLoggedIn: computed(() => !!token.value) }
}
```

- [ ] **Step 2: 创建认证中间件**

```typescript
// web/middleware/auth.ts
export default defineNuxtRouteMiddleware((to) => {
  const token = useCookie('auth_token')
  if (!token.value && to.path !== '/auth/login' && to.path !== '/auth/register') {
    return navigateTo('/auth/login')
  }
})
```

- [ ] **Step 3: 创建登录页面**

```vue
<!-- web/pages/auth/login.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="w-full max-w-sm">
      <h1 class="text-2xl font-bold text-center mb-8">PersonaX</h1>
      <form @submit.prevent="handleLogin" class="bg-white p-6 rounded-lg shadow">
        <h2 class="text-lg font-semibold mb-4">登录</h2>
        <div v-if="error" class="text-red-500 text-sm mb-3">{{ error }}</div>
        <input
          v-model="email"
          type="email"
          placeholder="邮箱"
          class="w-full px-3 py-2 border rounded-md mb-3 text-sm"
          required
        />
        <input
          v-model="password"
          type="password"
          placeholder="密码"
          class="w-full px-3 py-2 border rounded-md mb-4 text-sm"
          required
        />
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-primary-600 text-white py-2 rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>
        <p class="text-center text-sm text-gray-500 mt-4">
          没有账号？<NuxtLink to="/auth/register" class="text-primary-600">注册</NuxtLink>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })

const { login } = useAuth()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    navigateTo('/chat')
  } catch (e: any) {
    error.value = e?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 4: 创建注册页面**

```vue
<!-- web/pages/auth/register.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="w-full max-w-sm">
      <h1 class="text-2xl font-bold text-center mb-8">PersonaX</h1>
      <form @submit.prevent="handleRegister" class="bg-white p-6 rounded-lg shadow">
        <h2 class="text-lg font-semibold mb-4">注册</h2>
        <div v-if="error" class="text-red-500 text-sm mb-3">{{ error }}</div>
        <input
          v-model="displayName"
          type="text"
          placeholder="昵称（可选）"
          class="w-full px-3 py-2 border rounded-md mb-3 text-sm"
        />
        <input
          v-model="email"
          type="email"
          placeholder="邮箱"
          class="w-full px-3 py-2 border rounded-md mb-3 text-sm"
          required
        />
        <input
          v-model="password"
          type="password"
          placeholder="密码（至少 6 位）"
          class="w-full px-3 py-2 border rounded-md mb-4 text-sm"
          minlength="6"
          required
        />
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-primary-600 text-white py-2 rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>
        <p class="text-center text-sm text-gray-500 mt-4">
          已有账号？<NuxtLink to="/auth/login" class="text-primary-600">登录</NuxtLink>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })

const { register } = useAuth()
const email = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await register(email.value, password.value, displayName.value || undefined)
    navigateTo('/chat')
  } catch (e: any) {
    error.value = e?.data?.detail || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 5: 创建首页重定向**

```vue
<!-- web/pages/index.vue -->
<template>
  <div />
</template>

<script setup lang="ts">
navigateTo('/chat')
</script>
```

- [ ] **Step 6: 验证认证流程**

```bash
cd web && npm run dev -- --port 3000
# 同时运行后端
cd /home/chenlei/001_AI/personax && uvicorn api.main:app --reload --port 8000
```

Expected: 访问 http://localhost:3000 → 跳转到登录页 → 注册 → 登录 → 进入 /chat

- [ ] **Step 7: Commit**

```bash
git add web/pages/ web/composables/ web/stores/ web/middleware/
git commit -m "feat(web): add auth pages, composables, and middleware"
```

---

## Task 9: 对话页面

**Files:**
- Create: `web/pages/chat.vue`
- Create: `web/components/chat/MessageList.vue`
- Create: `web/components/chat/MessageBubble.vue`
- Create: `web/components/chat/ChatInput.vue`
- Modify: `web/layouts/default.vue`

- [ ] **Step 1: 创建消息气泡组件**

```vue
<!-- web/components/chat/MessageBubble.vue -->
<template>
  <div class="flex gap-2" :class="message.role === 'user' ? 'flex-row-reverse' : ''">
    <div
      class="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-white text-xs"
      :class="message.role === 'user' ? 'bg-gray-300' : 'bg-primary-500'"
    >
      {{ message.role === 'user' ? '' : personaInitial }}
    </div>
    <div
      class="px-3 py-2 rounded-xl text-sm max-w-[70%]"
      :class="message.role === 'user'
        ? 'bg-gray-100'
        : 'bg-blue-50 border border-blue-200'"
      v-html="renderedContent"
    />
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt()

const props = defineProps<{
  message: { role: string; content: string }
  persona?: string
}>()

const personaInitials: Record<string, string> = {
  zettaranc: 'Z',
  fupeng: '付',
  boss_mo: 'B',
  financial_analyst: '财',
}

const personaInitial = computed(() => personaInitials[props.persona || 'zettaranc'] || 'Z')
const renderedContent = computed(() => md.render(props.message.content))
</script>
```

- [ ] **Step 2: 创建消息列表组件**

```vue
<!-- web/components/chat/MessageList.vue -->
<template>
  <div ref="listEl" class="flex-1 overflow-y-auto p-4 space-y-3">
    <ChatMessageBubble
      v-for="(msg, i) in messages"
      :key="i"
      :message="msg"
      :persona="persona"
    />
    <div v-if="loading" class="flex gap-2">
      <div class="w-6 h-6 bg-primary-500 rounded-full flex items-center justify-center text-white text-xs">
        {{ personaInitial }}
      </div>
      <div class="bg-blue-50 border border-blue-200 px-3 py-2 rounded-xl text-sm">
        <span class="animate-pulse">思考中...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  messages: Array<{ role: string; content: string }>
  persona?: string
  loading?: boolean
}>()

const listEl = ref<HTMLElement>()

const personaInitials: Record<string, string> = {
  zettaranc: 'Z', fupeng: '付', boss_mo: 'B', financial_analyst: '财',
}
const personaInitial = computed(() => personaInitials[props.persona || 'zettaranc'] || 'Z')

watch(() => props.messages.length, () => {
  nextTick(() => {
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  })
})
</script>
```

- [ ] **Step 3: 创建输入框组件**

```vue
<!-- web/components/chat/ChatInput.vue -->
<template>
  <div class="p-4 bg-white border-t border-gray-200">
    <form @submit.prevent="send" class="flex gap-2 items-center">
      <input
        v-model="text"
        type="text"
        placeholder="输入你的问题..."
        class="flex-1 px-4 py-2 bg-gray-50 border border-gray-200 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        :disabled="loading"
      />
      <button
        type="submit"
        :disabled="!text.trim() || loading"
        class="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center text-white disabled:opacity-50 hover:bg-primary-600"
      >
        ↑
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
defineProps<{ loading?: boolean }>()
const emit = defineEmits<{ send: [text: string] }>()
const text = ref('')

function send() {
  if (text.value.trim()) {
    emit('send', text.value.trim())
    text.value = ''
  }
}
</script>
```

- [ ] **Step 4: 创建对话页面**

```vue
<!-- web/pages/chat.vue -->
<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="px-4 py-3 bg-white border-b border-gray-200 flex items-center gap-2">
      <CommonPersonaAvatar :name="activePersona" :size="28" />
      <div>
        <div class="font-semibold text-sm">{{ personaDisplay }}</div>
        <div class="text-xs text-gray-500">{{ personaDesc }}</div>
      </div>
    </div>

    <!-- Messages -->
    <ChatMessageList :messages="messages" :persona="activePersona" :loading="sending" />

    <!-- Input -->
    <ChatInput :loading="sending" @send="handleSend" />
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const { token } = useAuth()
const config = useRuntimeConfig()
const activePersona = useState('activePersona', () => 'zettaranc')

const messages = useState<Array<{ role: string; content: string }>>('chatMessages', () => [])
const sending = ref(false)

const { data: personas } = await useFetch<any[]>(`${config.public.apiBase}/api/v1/personas`, {
  headers: { Authorization: `Bearer ${token.value}` },
  default: () => [],
})

const personaDisplay = computed(() => {
  const p = personas.value?.find((x: any) => x.name === activePersona.value)
  return p?.display_name || activePersona.value
})
const personaDesc = computed(() => {
  const p = personas.value?.find((x: any) => x.name === activePersona.value)
  return p?.description || ''
})

async function handleSend(text: string) {
  messages.value.push({ role: 'user', content: text })
  sending.value = true

  try {
    const res = await $fetch<any>(`${config.public.apiBase}/api/v1/chat`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token.value}` },
      body: {
        query: text,
        persona: activePersona.value,
      },
    })

    messages.value.push({ role: 'assistant', content: res.persona_analysis })
    useState('toolResults').value = res.tool_results || {}
  } catch (e: any) {
    messages.value.push({ role: 'assistant', content: '抱歉，分析出错了。请稍后重试。' })
  } finally {
    sending.value = false
  }
}
</script>
```

- [ ] **Step 5: 验证完整对话流程**

```bash
# 终端 1: 后端
cd /home/chenlei/001_AI/personax && uvicorn api.main:app --reload --port 8000

# 终端 2: 前端
cd web && npm run dev -- --port 3000
```

Expected: 登录后进入对话页 → 输入问题 → 看到 persona 回复

- [ ] **Step 6: Commit**

```bash
git add web/pages/chat.vue web/components/chat/
git commit -m "feat(web): add chat page with message list, bubble, and input"
```

---

## Task 10: 端到端验证

- [ ] **Step 1: 启动后端并运行全部测试**

```bash
cd /home/chenlei/001_AI/personax
python -m pytest api/tests/ -v --tb=short
```

Expected: 全部 PASS

- [ ] **Step 2: 启动前端并手动验证**

```bash
cd web && npm run dev -- --port 3000
```

验证清单：
- [ ] 访问 http://localhost:3000 → 跳转到登录页
- [ ] 注册新用户 → 自动登录
- [ ] 三栏布局正常显示
- [ ] 左侧栏显示人格列表
- [ ] 输入问题 → 收到 persona 回复
- [ ] 右侧面板显示技术指标

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "feat: Phase 1 complete — Nuxt 3 + FastAPI base framework with auth and chat"
```
