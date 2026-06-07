# AI Pipeline Platform - 智能任务编排平台

> 本文档基于 2026-06-06 讨论，记录平台架构设计与首个流水线实现。
>
> **核心理念**：视频转博客只是第一个场景，底层是一套通用的 LangGraph 任务编排平台，支持未来扩展更多任务流。

---

## 一、目标概述

构建一套基于 LangGraph 的通用 AI 任务编排平台：

- **短期目标**：将 Bilibili 视频自动转化为结构化博客文章
- **长期目标**：平台化，支持多任务流接入、工具可插拔、多 Agent 协作

---

## 二、平台架构

### 2.1 系统分层

```mermaid
flowchart TD
    subgraph 应用层["应用层"]
        A["Web UI<br/>(Streamlit/Gradio)"]
        B["REST API<br/>(FastAPI)"]
        C["CLI 工具"]
    end

    subgraph 调度层["调度层"]
        D["任务调度器<br/>(Celery / Temporal)"]
        E["LangGraph 执行引擎"]
    end

    subgraph 节点层["节点层（可复用）"]
        F["IngestNode<br/>内容摄入"]
        G["SubtitleNode<br/>字幕处理"]
        H["ASRNode<br/>语音转写"]
        I["LLMNode<br/>内容生成"]
        J["StorageNode<br/>存储/索引"]
        S["PublishPrepareNode<br/>发布准备"]
    end

    subgraph 工具层["工具层（可插拔）"]
        K["yt-dlp"]
        L["ffmpeg"]
        M["Local Whisper"]
        N["DeepSeek / Gemini"]
        O["ChromaDB"]
    end

    subgraph 平台适配层["平台适配层（独立组件）"]
        P1["CSDN Formatter<br/>front matter剥离 / 元数据提取"]
        P2["CSDN Publisher<br/>浏览器自动发布"]
    end

    subgraph 存储层["存储层"]
        P["PostgreSQL<br/>(任务状态)"]
        Q["Redis<br/>(消息队列)"]
        R["本地文件系统<br/>(音视频/字幕/博客)"]
    end

    A --> B
    B --> D
    D --> E
    E --> F & G & H & I & J & S
    F --> K
    G --> L
    H --> M
    I --> N
    J --> O
    S --> P1 --> P2
    F & G & H & I & J & S --> P & Q & R

    style 调度层 fill:#e3f2fd,stroke:#1565c0
    style 节点层 fill:#e8f5e9,stroke:#2e7d32
    style 工具层 fill:#fff3e0,stroke:#ef6c00
    style 平台适配层 fill:#f3e5f5,stroke:#7b1fa2
```

### 2.2 核心执行流程

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Scheduler as Celery
    participant Engine as LangGraph Engine
    participant Nodes as Nodes Registry
    participant Adapter as Platform Adapter
    participant Storage as PostgreSQL

    User->>API: POST /tasks {pipeline, input_url}
    API->>Storage: 创建任务记录
    API->>Scheduler: 分发异步任务
    API-->>User: task_id

    Scheduler->>Engine: 执行流水线
    Engine->>Nodes: 依次调用节点
    Engine->>Nodes: ingest → subtitle → asr/llm → storage
    Nodes-->>Engine: 返回 state 更新
    Engine->>Storage: 更新任务状态
    Engine-->>Scheduler: 执行完成

    opt 启用平台发布
        Scheduler->>Adapter: prepare_publish(platform=csdn)
        Adapter->>Adapter: 剥离 front matter / 提取标题摘要标签
        Adapter->>Adapter: 生成平台可直接消费的正文内容
        Adapter-->>Scheduler: publish payload
    end

    User->>API: GET /tasks/{task_id}
    API->>Storage: 查询状态
    Storage-->>API: 任务状态 + 结果
    API-->>User: 博客内容
```

### 2.3 平台适配原则

- **内容生成层保持平台无关**：LLM 继续输出标准 Markdown，不为 CSDN 单独改写提示词。
- **平台差异下沉到适配层**：例如 CSDN 所需的标题、标签、摘要、分类专栏等字段，由独立组件处理。
- **适配器只做发布准备，不反向污染正文**：正文作为通用 Markdown 保留，适配器仅剥离 front matter、提取元数据、必要时裁剪不兼容信息。
- **发布与生成解耦**：即使自动发布失败，`data/blogs/` 中的 Markdown 结果仍然可直接复用。

---

## 三、框架选型

### 3.1 编排框架对比

| 框架 | 定位 | 多任务流 | 推荐度 |
|------|------|----------|--------|
| **LangGraph** | LLM 任务编排 / 状态机 | ⭐⭐⭐⭐ 强 | ✅ 首选 |
| CrewAI | 多 Agent 协作 | ⭐⭐⭐ 一般 | 简单场景 |
| AutoGen | 多 Agent 对话 | ⭐⭐⭐ 一般 | 开发者友好 |
| Dify | 无代码平台 | ⭐⭐⭐ 弱 | 快速验证 |
| FastAPI 自研 | 底层框架 | 完全可控 | 极致定制 |

### 3.2 选择 LangGraph 的理由

```mermaid
flowchart LR
    A["为什么选 LangGraph？"] --> B["状态机模型<br/>节点间数据流转自然"]
    A --> C["条件分支<br/>字幕有/无自动分流"]
    A --> D["可持久化<br/>中断后可恢复"]
    A --> E["生态完整<br/>LangSmith 监控 + Tracing"]
    A --> F["演进平滑<br/>多 Agent / RAG / Tool Calling 叠加"]

    style A fill:#e1f5fe,stroke:#1565c0
    style B fill:#c8e6c9
    style C fill:#c8e6c9
    style D fill:#c8e6c9
    style E fill:#c8e6c9
    style F fill:#c8e6c9
```

---

## 四、核心代码设计

### 4.1 当前状态定义（与实现保持一致）

```python
class PipelineState(TypedDict, total=False):
    task_id: str
    video_url: str
    pipeline_type: str
    created_at: str
    updated_at: str

    video_id: str | None
    task_dir: str | None
    video_title: str
    video_path: str | None
    subtitle_path: str | None
    audio_path: str | None
    transcript: str | None
    source_text: str | None
    blog_content: str | None
    article_title: str | None
    output_path: str | None

    has_subtitle: bool
    status: PipelineStatus
    error: str | None
    node_results: dict[str, Any]
```

### 4.2 当前节点职责（贴近现有实现）

```python
# nodes/ingest.py
# 仅抓取视频元信息，不下载完整视频
# 写入 video_id / video_title / node_results.ingest

# nodes/subtitle.py
# 优先下载现有字幕或自动字幕
# 若成功则写入 subtitle_path、has_subtitle=True
# 并立即持久化任务状态，避免后续失败时丢失中间结果

# nodes/asr.py
# 仅在无字幕时执行
# 使用 yt-dlp 下载 bestaudio，并通过 FFmpegExtractAudio 转成 wav
# 再调用本地 Whisper 转写，写入 audio_path / transcript / source_text

# nodes/llm.py
# 优先使用 transcript；若不存在则读取 subtitle_path 对应文本
# 调用 DeepSeek 生成结构化中文博客，写入 blog_content

# nodes/storage.py
# 将博客 Markdown 落盘到 data/blogs/<YYYY-MM-DD>_<文章标题>.md
# 文件名格式：<日期>_<文章标题>.md，标题从 LLM 生成内容中提取
# 写入 output_path，并标记任务成功

# nodes/publish_prepare.py  # 规划新增
# 不改写 LLM 提示词，不修改原始 Markdown 内容目标
# 负责读取 output_path 对应 markdown，剥离 front matter
# 提取 title / description / tags / categories / image 等发布元数据
# 为下游平台适配器生成 publish payload
```

### 4.3 平台适配组件（规划新增）

```python
# adapters/csdn_formatter.py
# 输入：标准 markdown 文件
# 输出：CSDN 发布所需 payload
# 职责：
#   1. 剥离 YAML front matter
#   2. 提取 title / tags / description / image / categories
#   3. 保留正文 markdown 原样，不为 CSDN 特意改写内容风格
#   4. 输出 body/title/summary/tags 等结构化结果

# adapters/csdn_publisher.py
# 输入：formatter 产出的 publish payload
# 输出：发布结果（如 draft_url / article_url / publish_status）
# 职责：
#   1. 打开已登录的 CSDN 编辑页
#   2. 填充标题、正文、标签、摘要、专栏、可见范围
#   3. 提交发布或保存草稿
#   4. 将结果回写任务状态
```

### 4.4 当前产物落盘约定

- 任务状态：`data/tasks/<task_id>.json`
- 博客结果：`data/blogs/<YYYY-MM-DD>_<文章标题>.md`
- 音频/字幕等中间资源：`data/video_down/<task_dir>/`
- `task_dir` 命名格式：`<YYYYMMDD_HHMMSS>_<task_id>`
- 若字幕节点已成功，相关 `subtitle_path` / `has_subtitle` 会立即持久化，即使后续节点失败也会保留

### 4.5 图构建（条件边实现分支）

```python
from langgraph.graph import StateGraph, END

def should_skip_asr(state: PipelineState) -> str:
    """字幕存在则跳过 ASR，节省 15-20 分钟"""
    return "asr_node" if not state.get("skip_asr") else "llm_node"

def should_publish_platform(state: PipelineState) -> str:
    """启用平台发布时进入发布准备节点，否则直接结束"""
    return "publish_prepare" if state.get("publish_target") == "csdn" else END

def build_video_to_blog_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("subtitle", subtitle_node)
    graph.add_node("asr", asr_node)
    graph.add_node("llm", llm_node)
    graph.add_node("storage", storage_node)
    graph.add_node("publish_prepare", publish_prepare_node)  # 规划新增

    graph.add_edge("ingest", "subtitle")
    graph.add_conditional_edges("subtitle", should_skip_asr)
    graph.add_edge("llm", "storage")
    graph.add_conditional_edges("storage", should_publish_platform)
    graph.add_edge("publish_prepare", END)

    return graph.compile()
```

### 4.6 流水线注册机制（核心扩展点）

```python
# engine/registry.py
class PipelineRegistry:
    _pipelines: dict[str, Any] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(func):
            cls._pipelines[name] = func()
            return func
        return decorator

    @classmethod
    def get(cls, name: str) -> Any:
        return cls._pipelines[name]

# pipelines/video_to_blog.py
@PipelineRegistry.register("video_to_blog")
def video_to_blog_pipeline() -> StateGraph:
    """视频转博客流水线"""
    ...

# pipelines/video_to_summary.py
@PipelineRegistry.register("video_to_summary")
def video_to_summary_pipeline() -> StateGraph:
    """视频转摘要流水线"""
    ...

# pipelines/youtube_to_podcast.py  # 未来
@PipelineRegistry.register("youtube_to_podcast")
def yt_to_podcast_pipeline() -> StateGraph:
    ...
```

### 4.7 服务工厂（工具可替换）

```python
# tools/asr_factory.py
class ASRServiceFactory:
    @staticmethod
    def get(service: str):
        services = {
            "local_whisper": LocalWhisperASR(),  # 默认，选首后不需要外网
        }
        return services[service]

# tools/llm_factory.py
class LLMServiceFactory:
    @staticmethod
    def get(provider: str):
        providers = {
            "deepseek": DeepSeekLLM(),
            "gemini": GeminiLLM(),
            "openai": OpenAILLM(),
        }
        return providers[provider]
```

---

## 五、API 层设计

```python
# api/routes/tasks.py
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="AI Pipeline Platform")

class TaskRequest(BaseModel):
    pipeline: str              # "video_to_blog" | "video_to_summary" | ...
    input_url: str
    publish_target: str | None = None  # 发布目标平台，如 "csdn"；None 则仅生成博客不发布
    config: dict = {}          # 可选参数覆盖

class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: datetime

@app.post("/tasks")
def create_task(req: TaskRequest) -> TaskResponse:
    task_id = schedule_task(req.pipeline, req.input_url, req.config, req.publish_target)
    return TaskResponse(task_id=task_id, status="pending", created_at=datetime.now())

@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    return get_task_status(task_id)

@app.get("/pipelines")
def list_pipelines() -> list[str]:
    return list(PipelineRegistry._pipelines.keys())
```

---

## 六、目录结构

```
AI_project_talking_about/
├── api/                    # FastAPI 网关
│   └── routes/
│       ├── tasks.py        # 任务 CRUD
│       └── webhooks.py     # 回调通知
├── engine/                 # LangGraph 执行引擎
│   ├── graph.py           # 图构建
│   ├── state.py           # 状态定义
│   └── registry.py        # 流水线注册
├── nodes/                  # 节点实现
│   ├── ingest.py          # 内容摄入
│   ├── subtitle.py        # 字幕处理
│   ├── asr.py             # 语音转写
│   ├── llm.py             # 内容生成
│   ├── storage.py         # 存储/索引
│   └── publish_prepare.py # 发布准备（规划新增）
├── adapters/               # 平台适配层（规划新增）
│   ├── csdn_formatter.py  # CSDN front matter 剥离 / 元数据提取
│   └── csdn_publisher.py  # CSDN 浏览器自动发布
├── tools/                  # 底层工具封装（可插拔）
│   ├── yt_dlp_tool.py
│   ├── ffmpeg_tool.py
│   ├── whisper_tool.py
│   ├── deepseek_tool.py
│   └── chromadb_tool.py
├── pipelines/              # 流水线定义
│   ├── video_to_blog.py   # ✅ 首个流水线
│   ├── video_to_summary.py
│   └── __future__/       # 未来流水线占位
├── scheduler/              # 任务调度
│   └── celery_app.py
├── models/                # 数据模型
│   └── schemas.py
└── config/
    └── settings.py         # 服务配置（ASR/LLM 可切换）
```

---

## 七、实施路线

```mermaid
flowchart TD
    P1["Phase 1<br/>框架搭建 ✅"] --> P2["Phase 2<br/>video_to_blog ✅"]
    P2 --> P3["Phase 3<br/>多流水线扩展 🔄"]
    P3 --> P4["Phase 4<br/>调度增强"]
    P4 --> P5["Phase 5<br/>多 Agent"]

    P1 -.- T1["LangGraph 骨架<br/>State/Node 接口规范"]
    P2 -.- T2["完整视频→博客流程<br/>首个可用流水线"]
    P3 -.- T3["summary / tweets / CSDN发布<br/>可扩展性验证"]
    P4 -.- T4["Celery 异步<br/>WebSocket / 重试"]
    P5 -.- T5["多 Agent 协作<br/>工具调用增强"]

    style P1 fill:#c8e6c9,stroke:#2e7d32
    style P2 fill:#c8e6c9,stroke:#2e7d32
    style P3 fill:#fff9c4,stroke:#f9a825
    style P4 fill:#ffccbc
    style P5 fill:#f3e5f5
```

|| 阶段 | 状态 | 内容 | 预计代码量 |
||------|------|------|-----------|
|| Phase 1 | ✅ 完成 | LangGraph + FastAPI 骨架，State / Node 接口规范 | ~300 行 |
|| Phase 2 | ✅ 完成 | 完整 video_to_blog 流水线，通过注册接入 | ~500 行 |
|| Phase 3 | 🔄 进行中 | 注册 2-3 个新流水线（summary / tweets / CSDN发布）| ~200 行 |
|| Phase 4 | 📋 待开始 | Celery 异步、WebSocket 推送、任务重试 | ~400 行 |
|| Phase 5 | 📋 未来 | 多 Agent 协作流水线 | ~300 行 |
|| **合计** | | | **~1700 行** |

---

## 八、工具链详细说明

### 8.1 视频处理

- **yt-dlp**：从 B站下载视频/音频/字幕（注意：它不能替代 ffmpeg）
- **ffmpeg**：音视频格式转换，输出 Whisper 所需的 16kHz 单声道 WAV

### 8.2 ASR 方案对比

| 方案 | 费用 | 速度 | 推荐度 |
|------|------|------|--------|
| **本地 Whisper small（CPU）**| ¥0 | 12-20分钟/30分钟 | ⭐⭐⭐ 首选（已默认启用）|
| SiliconFlow FunAudioLLM | ¥0.1/分钟 | 快 | ⭐ 备用 |


**i5-12500H CPU 转写性能预估：**
- tiny：2-4 分钟（精度差，不推荐）
- base：5-8 分钟（一般）
- **small：12-20 分钟（推荐，精度良好）**
- medium：30-50 分钟（偏慢）
- large-v3：60-100 分钟（CPU太慢，不考虑）

### 8.3 LLM 方案

| 模型 | 价格（/百万 tokens）| 适用场景 |
|------|---------------------|----------|
| **DeepSeek V4-Pro** | ¥0.87 输入 / ¥1.74 输出 | 复杂博客生成 |
| **DeepSeek V4-Flash** | ¥0.14 输入 / ¥0.28 输出 | 日常快速处理 |
| Gemini Flash 2.0 | 免费（有配额）| 备用、多模态扩展 |

> DeepSeek V4 官方定价：https://api-docs.deepseek.com
>
> ⚠️ **DeepSeek V4 是纯文本 LLM，不具备语音转文字（ASR）功能**

---

## 九、注册流水线一览

```mermaid
flowchart TD
    subgraph 已实现["✅ 已实现"]
        V2B["video_to_blog<br/>视频 → 博客"]
    end

    subgraph 规划中["🔄 规划中"]
        V2S["video_to_summary<br/>视频 → 摘要"]
        V2T["video_to_tweets<br/>视频 → 推文"]
        CSDN["csdn_publish<br/>博客 → CSDN发布"]
    end

    subgraph 未来["📋 未来扩展"]
        Y2P["youtube_to_podcast<br/>油管 → 播客"]
        M2B["multi_agent_review<br/>多 Agent 审稿"]
        DOC["doc_to_knowledge<br/>文档 → 知识库"]
    end

    V2B --> CSDN
    V2B & V2S & V2T --> Y2P
    Y2P --> M2B
    M2B --> DOC
```

> **说明**：`csdn_publish` 不是独立流水线，而是 `video_to_blog` 的可选后处理阶段。通过 API 的 `publish_target: "csdn"` 参数触发，自动执行 `publish_prepare` 节点 + CSDN 平台适配器。

---

## 十、成本估算（每月）

假设每天处理 3 个 30 分钟视频：

```mermaid
pie title 月度成本构成（¥3-8/月）
    "DeepSeek V4-Flash（LLM生成）" : 5
    "视频下载 / 音频处理 / ASR / 存储" : 0
```

| 环节 | 方案 | 月成本 |
|------|------|--------|
| 视频下载 | yt-dlp + B站 cookies | ¥0 |
| 音频处理 | ffmpeg | ¥0 |
| 语音转写 | 本地 Whisper | ¥0 |
| LLM 生成 | DeepSeek V4-Flash | ¥3-8 |
| 向量存储 | ChromaDB 本地 | ¥0 |
| 存储 | 本地 SSD | ¥0 |
| **总计** | | **¥3-8/月** |

---

## 十一、环境验证清单

```bash
# 1. 确认 yt-dlp 能解析 B 站视频
yt-dlp --list-subs "https://www.bilibili.com/video/BV1xx411c7mD"

# 2. 确认 Whisper 可用
python -c "import whisper; print('Whisper OK')"

# 3. 确认 ffmpeg / ffprobe 可用
ffmpeg -version
ffprobe -version

# 4. 若未加入 PATH，可在 .env 中配置
# FFMPEG_LOCATION=/path/to/ffmpeg/bin

# 5. 确认 DeepSeek API 可用
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "你好"}]
  }'


# 6. 确认 LangGraph 可用（平台核心依赖）
python -c "from langgraph.graph import StateGraph; print('LangGraph OK')"
```

---

## 十二、技术限制说明

- **DeepSeek V4 无 ASR 能力**：是纯文本 LLM，语音转文字必须依赖独立 ASR 服务（如本地 Whisper）
- **B站字幕获取**：约 20-30% 视频有字幕，知识区成功率更高，建议优先尝试再降级
- **分P视频**：需解析后按集逐一处理
- **B站下载认证**：高画质下载需要 SESSDATA（从手机 App 登录获取）
