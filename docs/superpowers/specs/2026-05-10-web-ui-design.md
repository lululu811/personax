# PersonaX Web UI 设计文档

> 版本：v1.0
> 日期：2026-05-10
> 状态：待审阅

---

## 1. 概述

### 1.1 目标

为 PersonaX 构建一套对外产品的 Web UI，将现有的 CLI-only 交互升级为完整的浏览器体验。

### 1.2 目标用户

外部用户（个人投资者、研究团队），需要完整的用户体系、权限控制和美观的 UI。

### 1.3 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 前端 | Nuxt 3 + Vue 3 | 全栈框架，SSR，Python 开发者友好 |
| 后端 | FastAPI | 自动生成 Swagger 文档，WebSocket 原生支持 |
| 数据库 | SQLite (用户) + DuckDB (行情) | 轻量级，自部署友好 |
| 缓存 | Redis | 会话缓存、速率限制 |
| 向量库 | ChromaDB | 复用现有知识层 |
| 图表 | TradingView Lightweight Charts + ECharts | 专业金融图表 |
| CSS | TailwindCSS | 快速开发，一致性好 |
| 部署 | 自部署 | 先本地/自有服务器 |

---

## 2. 页面结构

### 2.1 全局布局

三栏布局，左侧边栏持久存在：

```
┌──────────┬──────────────────────────┬──────────────┐
│          │                          │              │
│  左侧栏   │      中间主区域            │   右侧面板    │
│  200px   │       flex: 1            │    280px     │
│          │                          │              │
│ 导航      │   对话 / 图表 / 财报       │  技术指标     │
│ 人格切换   │      (Tab 切换)           │  策略信号     │
│ 对话历史   │                          │  知识库引用   │
│ 用户信息   │                          │              │
└──────────┴──────────────────────────┴──────────────┘
```

### 2.2 左侧边栏

- **导航**：对话、图表、财报分析、选股筛选
- **人格切换**：Z哥、付鹏、BOSS墨、财务分析师（头像 + 名称）
- **对话历史**：最近的对话列表，点击可恢复
- **用户信息**：头像、用户名、设置入口

### 2.3 核心页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 对话分析 | `/chat` | 默认页，左中右三栏 |
| 图表可视化 | `/chart/:code` | 独立页面，K 线 + 指标 |
| 财报分析 | `/report/:code` | 仪表盘式总览 |
| 用户设置 | `/settings` | 个人设置、API Key 管理 |
| 登录/注册 | `/auth` | 认证页面 |

---

## 3. 对话分析页面

### 3.1 布局

- **中间区域**：对话消息流，支持 Markdown 渲染
- **右侧面板**：实时展示技术指标、策略信号、知识库引用
- **底部输入**：文本输入 + 附件上传（图片/PDF）

### 3.2 对话功能

- **流式输出**：WebSocket 连接，LLM token 逐字输出
- **Markdown 渲染**：支持代码块、表格、列表
- **信号标签**：对话中的信号以彩色标签展示（B1 ✅、J=8.3、KDJ 金叉）
- **多模态**：支持上传图片/PDF 作为附件

### 3.3 诊断工作流

诊断以**侧边面板**形式呈现，不打断对话流：

1. 当用户触发诊断关键词时，右侧弹出诊断面板
2. 面板内展示当前轮次的问题（结构化表单）
3. 支持快捷回复按钮（如 "短线 · 已持有 · 30%"）
4. 进度条显示当前轮次（1/3、2/3、3/3）
5. 诊断结论生成后，面板自动收起，结论以消息形式出现在对话中

### 3.4 右侧面板

实时更新的三个卡片：

- **技术指标卡片**：当前计算的指标值（KDJ、MACD 等）
- **策略信号卡片**：触发的策略信号及置信度
- **知识库引用卡片**：命中的知识片段链接

---

## 4. 图表可视化页面

### 4.1 布局

独立页面，左侧指标选择器 + 右侧图表区域。

### 4.2 功能

- **K 线图**：日/周/月线切换，支持缩放和拖拽
- **技术指标叠加**：KDJ、MACD、RSI、BBI、布林带、量比，通过左侧选择器开关
- **副图指标**：MACD、RSI 等在 K 线图下方的独立区域
- **信号标记**：B1/B2/S1 等信号在 K 线图上以箭头/标签标记
- **时间段选择**：1M、3M、6M、1Y、ALL 快捷按钮

### 4.3 图表库

使用 **TradingView Lightweight Charts** 作为 K 线图核心，**ECharts** 作为辅助图表（指标副图、资金流向等）。

---

## 5. 财报分析页面

### 5.1 布局

仪表盘式总览，一屏看完所有关键信息。

### 5.2 内容模块

- **股票信息栏**：代码、名称、行业、当前价、涨跌幅、综合评级
- **五维排雷评分**：5 个评分卡（收入真实性、利润质量、现金流、资产负债、股东回报），每个带进度条
- **杜邦分析**：ROE 分解（净利率 × 资产周转 × 权益乘数）
- **估值分析**：PE/PB/PS/PEG 及估值判断
- **风险提示**：红色警告卡片，列出风险点
- **历史趋势**：近 5 年关键财务指标的折线图

### 5.3 数据来源

复用现有 `tools/financial_reports/` 工具链，通过 FastAPI 接口调用 `FinancialReportTool.analyze()`。

---

## 6. 用户系统

### 6.1 认证

- **注册**：邮箱 + 密码，邮箱验证
- **登录**：邮箱 + 密码，JWT token
- **OAuth**（可选后续）：微信登录

### 6.2 用户数据

- **对话历史**：持久化到 SQLite，支持搜索和删除
- **收藏分析**：收藏特定的分析结果
- **个人设置**：默认人格、LLM 偏好、通知设置

### 6.3 数据模型

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对话表
CREATE TABLE conversations (
    id VARCHAR(32) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    persona VARCHAR(50),
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 消息表
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id VARCHAR(32) REFERENCES conversations(id),
    role VARCHAR(20),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 收藏表
CREATE TABLE favorites (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    conversation_id VARCHAR(32),
    message_id INTEGER,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. API 设计

### 7.1 REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录，返回 JWT |
| GET | `/api/users/me` | 当前用户信息 |
| GET | `/api/conversations` | 对话列表 |
| POST | `/api/conversations` | 创建对话 |
| GET | `/api/conversations/:id/messages` | 获取消息历史 |
| POST | `/api/chat` | 发送消息（非流式） |
| GET | `/api/chart/:code` | 获取 K 线数据 |
| GET | `/api/chart/:code/indicators` | 获取指标数据 |
| POST | `/api/report/:code` | 触发财报分析 |
| GET | `/api/personas` | 获取可用人格列表 |
| GET | `/api/tools` | 获取可用工具/指标列表 |

### 7.2 WebSocket API

| 路径 | 说明 |
|------|------|
| `ws://host/ws/chat` | 流式对话，发送 query，逐 token 接收响应 |

消息格式：

```json
// 客户端发送
{
  "type": "message",
  "query": "帮我看看茅台的B1信号",
  "conversation_id": "abc123",
  "persona": "zettaranc",
  "stock_code": "600519"
}

// 服务端流式返回
{"type": "token", "content": "茅台"}
{"type": "token", "content": "现在"}
{"type": "token", "content": "J值"}
...
{"type": "done", "tool_results": {...}, "strategy_results": {...}}
{"type": "diagnosis", "round": 1, "questions": [...]}
```

---

## 8. 项目结构

```
personax/
├── web/                              # Web UI 前端
│   ├── nuxt.config.ts
│   ├── package.json
│   ├── pages/
│   │   ├── index.vue                 # 重定向到 /chat
│   │   ├── chat.vue                  # 对话分析页
│   │   ├── chart/[code].vue          # 图表可视化页
│   │   ├── report/[code].vue         # 财报分析页
│   │   ├── auth/
│   │   │   ├── login.vue
│   │   │   └── register.vue
│   │   └── settings.vue              # 用户设置
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.vue           # 左侧边栏
│   │   │   └── RightPanel.vue        # 右侧技术面板
│   │   ├── chat/
│   │   │   ├── MessageList.vue       # 消息列表
│   │   │   ├── MessageBubble.vue     # 单条消息
│   │   │   ├── ChatInput.vue         # 输入框 + 附件
│   │   │   ├── SignalTag.vue         # 信号标签
│   │   │   └── DiagnosisPanel.vue    # 诊断侧边面板
│   │   ├── chart/
│   │   │   ├── KLineChart.vue        # K 线图
│   │   │   ├── IndicatorSelector.vue # 指标选择器
│   │   │   └── SignalMarker.vue      # 信号标记
│   │   ├── report/
│   │   │   ├── FiveDimensionCard.vue # 五维评分卡
│   │   │   ├── DuPontCard.vue        # 杜邦分析
│   │   │   └── ValuationCard.vue     # 估值分析
│   │   └── common/
│   │       ├── PersonaAvatar.vue     # 人格头像
│   │       └── LoadingSpinner.vue
│   ├── composables/
│   │   ├── useChat.ts                # 对话状态管理
│   │   ├── useWebSocket.ts           # WebSocket 连接
│   │   └── useAuth.ts                # 认证状态
│   ├── stores/
│   │   ├── chat.ts                   # Pinia 对话 store
│   │   └── auth.ts                   # Pinia 认证 store
│   └── styles/
│       └── tailwind.config.ts
│
├── api/                              # FastAPI 后端
│   ├── main.py                       # FastAPI app 入口
│   ├── config.py                     # 配置管理
│   ├── auth/
│   │   ├── router.py                 # 认证路由
│   │   ├── models.py                 # 用户模型
│   │   ├── schemas.py                # Pydantic schemas
│   │   └── dependencies.py           # JWT 依赖注入
│   ├── chat/
│   │   ├── router.py                 # 对话路由
│   │   └── websocket.py              # WebSocket 处理
│   ├── chart/
│   │   └── router.py                 # 图表数据路由
│   ├── report/
│   │   └── router.py                 # 财报分析路由
│   ├── db/
│   │   ├── database.py               # SQLite 连接
│   │   └── migrations/               # 数据库迁移
│   └── middleware/
│       ├── cors.py                   # CORS 配置
│       └── rate_limit.py             # 速率限制
│
├── orchestration/                    # 现有编排层（复用）
├── tools/                            # 现有工具层（复用）
├── personas/                         # 现有人格层（复用）
├── knowledge/                        # 现有知识层（复用）
├── data/                             # 现有数据层（复用）
└── ...
```

---

## 9. 实施计划

### Phase 1：基础框架（1-2 周）

- [ ] 初始化 Nuxt 3 项目 + TailwindCSS
- [ ] 初始化 FastAPI 项目 + SQLite
- [ ] 实现全局三栏布局（左侧栏 + 主区域 + 右侧面板）
- [ ] 实现基础认证（注册/登录/JWT）
- [ ] 对接 OrchestrationEngine 的 REST API

### Phase 2：对话核心（1-2 周）

- [ ] 对话消息列表 + Markdown 渲染
- [ ] WebSocket 流式输出
- [ ] 右侧技术面板实时更新
- [ ] 诊断侧边面板
- [ ] 对话历史持久化

### Phase 3：图表与财报（1-2 周）

- [ ] K 线图页面（TradingView Lightweight Charts）
- [ ] 技术指标叠加 + 信号标记
- [ ] 财报分析仪表盘
- [ ] 五维评分 + 杜邦分析 + 估值

### Phase 4：打磨（1 周）

- [ ] 响应式适配
- [ ] 错误处理 + Loading 状态
- [ ] 性能优化（缓存、懒加载）
- [ ] 部署脚本（Docker Compose）

---

## 10. 依赖清单

### 前端

```json
{
  "nuxt": "^3.x",
  "vue": "^3.x",
  "@pinia/nuxt": "^0.5",
  "@nuxtjs/tailwindcss": "^6.x",
  "lightweight-charts": "^4.x",
  "echarts": "^5.x",
  "markdown-it": "^14.x",
  "@vueuse/core": "^10.x"
}
```

### 后端

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
aiosqlite>=0.19.0
redis>=5.0.0
websockets>=12.0
```

---

## 11. 扩展性设计

### 11.1 已具备的扩展能力

| 扩展场景 | 操作 | 前端改动 | 后端改动 |
|---------|------|---------|---------|
| 新增 persona | `personas/` 目录 + `personas.yaml` | 0（自动发现） | 0（自动注册） |
| 新增技术指标 | `@register_tool` 装饰器 | 0（`/api/tools` 拉取） | 0（自动注册） |
| 新增页面 | Nuxt 文件路由 | 加 `.vue` 文件 | 加 `router.py` |
| 新增后端接口 | FastAPI router 模块化 | 调用新接口 | 加 `api/xxx/router.py` |
| 新增数据源 | `data_sources.yaml` + `DataSource` 子类 | 0 | 0 |

### 11.2 数据库迁移路径

当前使用 SQLite 存储用户数据，单机部署足够。为支持未来扩展：

- **ORM 抽象**：`api/db/database.py` 使用 SQLAlchemy Core（非 ORM），后续从 SQLite 迁移到 PostgreSQL 只需改连接字符串
- **迁移工具**：使用 Alembic 管理 schema 迁移，确保版本化
- **触发条件**：并发写入 >100/s 或需要多实例部署时，迁移到 PostgreSQL

```python
# api/db/database.py — 可切换的数据库后端
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

# 当前：SQLite
DATABASE_URL = "sqlite+aiosqlite:///./data/personax.db"

# 未来迁移到 PostgreSQL：
# DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/personax"
```

### 11.3 API 版本化

所有 API 路径使用版本前缀，避免后续 breaking change：

```
/api/v1/chat          # 当前版本
/api/v2/chat          # 未来版本（如需要）
```

FastAPI router 组织方式：

```python
# api/main.py
from api.v1 import router as v1_router
app.include_router(v1_router, prefix="/api/v1")
```

### 11.4 人格动态化（后续扩展）

当前人格为静态配置文件。如需支持"用户自定义人格"：

- **前端**：增加人格编辑器页面（`/personas/create`），表单化 personality.md 的各字段
- **后端**：增加 `/api/v1/personas` CRUD 接口，支持用户创建/编辑/删除自定义人格
- **存储**：自定义人格存入 SQLite `custom_personas` 表，启动时与静态人格合并
- **优先级**：用户自定义 > 静态配置

```sql
CREATE TABLE custom_personas (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    personality_md TEXT,
    overrides_yaml TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 11.5 插件系统（远期）

如需支持第三方扩展 UI 组件：

- Nuxt 3 支持模块系统（`nuxt-modules`），可作为插件载体
- 后端可通过 FastAPI 的 `APIRouter` 动态挂载
- 前端可通过 Vue 的 `defineAsyncComponent` 懒加载插件组件

---

## 附录：Mockup 截图

设计过程中的视觉 mockup 保存在 `.superpowers/brainstorm/` 目录中。

---

*文档结束*
