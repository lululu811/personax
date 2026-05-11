# Poster Generation 设计文档

> **目标**: 为 Agent Team 分析会话集成多风格海报批量生成功能

**架构**: 新增 `agent_team/poster/` 模块，通过格式化器将 `TeamResult` 转为 baoyu 技能输入格式，并行调用多个 baoyu 技能生成不同风格海报。

**技术栈**: Python, baoyu-infographic, baoyu-image-cards, asyncio

---

## 模块设计

### 文件结构

```
agent_team/poster/
├── __init__.py
├── generator.py      # PosterGenerator — 并行调度 baoyu 技能
├── formatter.py      # 内容格式化器（infographic / image-cards）
└── styles.py         # 风格配置注册表
```

### `styles.py` — 风格配置注册表

预定义 3 种默认海报风格：

| 风格 ID | baoyu 技能 | 参数 | 描述 |
|---------|-----------|------|------|
| `infographic-tech` | `baoyu-infographic` | `--layout dense-modules --style pixel-art` | 像素风高密度信息图 |
| `infographic-pro` | `baoyu-infographic` | `--layout bento-grid --style craft-handmade` | 专业手作风格信息图 |
| `image-cards` | `baoyu-image-cards` | `--preset knowledge-card` | 知识卡片系列（3-5张） |

```python
@dataclass
class PosterStyle:
    style_id: str
    skill_name: str          # e.g., "baoyu-infographic"
    args: list[str]          # CLI args, e.g., ["--layout", "dense-modules", "--style", "pixel-art"]
    output_subdir: str       # e.g., "pixel-tech"
    description: str

DEFAULT_STYLES: list[PosterStyle] = [...]
```

### `formatter.py` — 内容格式化器

**`InfographicFormatter`**:
- 输入: `TeamResult`
- 输出: Markdown 格式的 `structured-content.md`
- 结构: 标题、查询问题、Agent 观点列表（name + content 摘要 + confidence）、主持人共识、建议、用户评分

**`ImageCardsFormatter`**:
- 输入: `TeamResult`
- 输出: 卡片系列大纲（cover + 每 Agent 一张 + summary）
- 每张卡片: 标题 + 要点（3-5 条）+ 表情/图标

### `generator.py` — `PosterGenerator`

```python
class PosterGenerator:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or str(Path.home() / ".personax" / "posters")

    async def generate(
        self,
        team_result: TeamResult,
        styles: list[PosterStyle] = None,
    ) -> PosterOutput:
        """并行生成多种风格海报。"""

    def _check_prerequisites(self) -> list[str]:
        """检查 baoyu 技能是否安装，返回缺失列表。"""

    async def _generate_single(
        self,
        team_result: TeamResult,
        style: PosterStyle,
        session_dir: Path,
    ) -> PosterFile:
        """生成单个风格海报，返回文件路径或错误。"""
```

**`PosterOutput`**:
```python
@dataclass
class PosterOutput:
    session_id: str
    output_dir: Path
    files: list[PosterFile]   # 成功生成的文件
    errors: list[PosterError] # 失败的记录

@dataclass
class PosterFile:
    style_id: str
    path: Path
    description: str

@dataclass
class PosterError:
    style_id: str
    error: str
```

---

## 数据流

```
TeamSession.close(scores)
  → TeamResult (rounds, thoughts, synthesis, scores, session_id)
    → PosterGenerator.generate(team_result, styles=DEFAULT_STYLES)
      → 对每个 style:
        - Formatter 生成结构化内容 → 写入 {session_dir}/{style_id}/source.md
        - 构建 baoyu 技能命令（带 --no-confirm）
        - asyncio.create_task(_run_skill_process(...))
      ← asyncio.gather 收集结果
        → PosterOutput
```

---

## CLI 集成

在 `agent_team/cli.py` 的 `_do_scoring()` 中：

```python
def _do_scoring(session: TeamSession):
    # ... 现有评分逻辑 ...
    
    if scores:
        result = session.close(scores)
        click.echo("\n最终报告:")
        click.echo(result.poster_text)
        
        # 新增: 海报生成询问
        if click.confirm("\n是否生成海报？", default=False):
            asyncio.run(_generate_posters(result))

async def _generate_posters(result: TeamResult):
    from agent_team.poster.generator import PosterGenerator, DEFAULT_STYLES
    
    generator = PosterGenerator()
    click.echo("生成海报中...（3种风格并行）\n")
    
    output = await generator.generate(result, styles=DEFAULT_STYLES)
    
    for f in output.files:
        click.echo(f"  ✓ {f.description}: {f.path}")
    for e in output.errors:
        click.echo(f"  ✗ {e.style_id}: {e.error}")
```

---

## 错误处理

| 场景 | 检测时机 | 处理 |
|------|---------|------|
| baoyu 技能未安装 | 生成前 `_check_prerequisites()` | 跳过图片生成，提示安装命令 |
| 图片后端未配置 | 生成前检查环境变量 | fallback 文本海报 |
| 单个风格超时 | `asyncio.wait_for(timeout=60)` | kill 进程，记录错误，继续其他风格 |
| 磁盘空间不足 | 生成前 `shutil.disk_usage()` | 报错，不启动生成 |
| 内容过短 | 生成前 `len(thoughts) < 2` | 提示"内容不足以生成海报" |
| 全部失败 | 生成后检查 `len(files) == 0` | 保留文本海报输出 |

---

## 输出目录结构

```
~/.personax/posters/
└── {session_id}/
    ├── infographic-tech/
    │   ├── source.md
    │   ├── structured-content.md
    │   ├── prompts/
    │   │   └── infographic.md
    │   └── infographic.png
    ├── infographic-pro/
    │   └── infographic.png
    └── image-cards/
        ├── source.md
        ├── outline.md
        ├── prompts/
        │   ├── 01-cover-xxx.md
        │   └── 02-content-xxx.md
        ├── 01-cover-xxx.png
        └── 02-content-xxx.png
```

---

## 测试策略

| 测试文件 | 覆盖内容 |
|---------|---------|
| `tests/agent_team/poster/test_generator.py` | Mock subprocess 调用，验证并行执行、错误收集、超时处理 |
| `tests/agent_team/poster/test_formatter.py` | 验证 TeamResult → markdown 格式转换正确性 |
| `tests/agent_team/poster/test_styles.py` | 验证风格配置注册表加载 |
| `tests/agent_team/test_cli_poster_flow.py` | Mock `click.confirm` 和 `PosterGenerator`，验证 CLI 流程 |

---

## 依赖

- `baoyu-infographic` skill（已安装）
- `baoyu-image-cards` skill（已安装）
- `baoyu-imagine` skill 或等效图片后端（需配置 API Key）
