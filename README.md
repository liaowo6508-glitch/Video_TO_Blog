# AI Pipeline Platform

基于 LangGraph 的智能任务编排平台 MVP。当前首版实现聚焦 `video_to_blog`：将 Bilibili 或通用视频链接下载、检测字幕，并调用 DeepSeek 生成结构化中文博客文章。

## 已实现能力
- LangGraph 状态机编排骨架
- `video_to_blog` 流水线注册机制
- `ingest(metadata) -> subtitle -> subtitle_clean -> llm -> storage` 节点链路
- 字幕不存在时直接报错（B站大部分视频至少有AI字幕）
- 优先下载字幕文本
- 统一字幕解析：使用 `subtitle_parser.py` 解析 SRT/VTT，生成不含时间戳的纯文本供 LLM 使用
- FastAPI 接口：创建任务、查看任务、列出流水线
- 任务执行日志：节点阶段、任务状态、失败原因
- `yt-dlp` 下载进度映射到服务终端日志，便于观测音频下载状态
- 本地 JSON 任务存储与 Markdown 结果落盘
- B站 URL 412 自动裁剪重试，无需人工处理追踪参数
- `video_down` 目录自动保留策略，仅保留最近 N 个任务目录
- `subtitle_only` 流水线：仅下载并清洗字幕，返回文档地址（默认流水线）

## 平台发布（技术储备）

CSDN 发布能力已作为技术储备实现，代码位于：

- `adapters/csdn_formatter.py`：从 Markdown 提取 title / tags / summary，生成 CSDN payload
- `adapters/csdn_publisher.py`：生成发布 instructions 及可选的 automation_spec
- `nodes/publish_prepare.py`：LangGraph 发布准备节点
- `adapters/csdn_publisher.py` 中的 `_build_browser_automation_spec` 包含完整的浏览器自动化操作规范

以上文件均已注释保留，启用路线图见各文件顶部注释。

**核心设计原则**：
- 保持 LLM 输出为平台无关的标准 Markdown
- 在 Markdown 落盘后引入独立的平台适配组件
- `csdn_publisher` 负责浏览器自动化发布，不反向影响内容生成提示词

## 目录结构
```text
AI_project_talking_about/
├── api/
├── config/
├── engine/
├── models/
├── nodes/
├── adapters/        # 平台适配层（技术储备：CSDN 发布）
├── pipelines/
├── storage/
├── tools/
├── data/
├── requirements.txt
└── README.md
```

## 环境准备
### 1. 安装 Python 依赖
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 安装系统依赖
确保本机可直接执行：

```bash
ffmpeg -version
yt-dlp --version
```

Ubuntu 示例：

```bash
sudo apt update
sudo apt install -y ffmpeg
```

### 3. 配置环境变量
在项目根目录创建 `.env`：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key
BILIBILI_SESSDATA=optional_bilibili_sessdata
# BILIBILI_COOKIE_FILE=  # 推荐填写浏览器导出的 Netscape cookies.txt 路径
BILIBILI_NO_PROXY=false
APP_HOST=0.0.0.0
APP_PORT=8000
DEEPSEEK_MODEL=deepseek-v4-pro   # 可选: deepseek-v4-pro / deepseek-v4-flash
# PROMPT_CONFIG_PATH=            # 自定义提示词路径，留空走 config/prompts.yaml
VIDEO_DOWN_MAX_KEEP=5
```

说明：
- `DEEPSEEK_API_KEY`：用于博客内容生成。
- `BILIBILI_SESSDATA`：部分 B站 视频下载或高质量访问时需要，可选。
- `BILIBILI_COOKIE_FILE`：优先于 `BILIBILI_SESSDATA`，推荐填写浏览器导出的 Netscape `cookies.txt` 文件路径。
- `BILIBILI_NO_PROXY`：设为 `true` 时，`yt-dlp` 将不使用当前 shell 里的代理环境变量，适合排查 B站 `412` 或代理拦截问题。
- `FFMPEG_LOCATION`：可选，指向 `ffmpeg/ffprobe` 所在目录，或可执行文件路径，用于 `yt-dlp` 后处理阶段定位二进制。
- `VIDEO_DOWN_MAX_KEEP`：可选，控制 `data/video_down/` 最多保留多少个最近任务目录，默认 `5`。每次创建新任务前会自动清理更早的目录。
- `CSDN_EDITOR_URL` / `CSDN_AUTO_PUBLISH`：**技术储备**，已注释在 `config/settings.py` 中，启用时取消注释即可。

### B站 412 自动重试机制
B站视频 URL 中常携带来源追踪参数（`?spm_id_from=...&vd_source=...`），可能触发 HTTP 412 拦截。
系统会在 `extract_info` 阶段自动拦截该错误，并将 URL 裁剪为纯净格式（`https://www.bilibili.com/video/BV...`）后重试一次，全程无需人工干预。
若仍失败，则按正常流程抛出错误，可检查 cookies 配置或稍后再试。

> **实现细节**：异常匹配同时兼容 `Bilibili`（无括号）和 `[BiliBili]`（有括号）两种格式，确保不同版本 yt-dlp 输出的错误消息均能被正确拦截。

## 启动服务
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

> **提示**：服务端口默认 `8000`，可替换为其他端口。`run.py` 可通过 `--port` 参数匹配对应端口。

启动后可访问：
- `GET /healthz`
- `GET /pipelines`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `GET /tasks`

## 任务监控与日志观测
服务终端现在会输出任务执行日志，便于直接观察后台任务进度。

### 日志覆盖范围
- 任务创建、开始执行、成功完成、失败退出
- 当前执行节点：`ingest` / `subtitle` / `subtitle_clean` / `llm` / `storage`
- 字幕下载进度：百分比、已下载大小、总大小、速度、ETA

### 典型日志示例
```text
[15:40:12] INFO [6d2f...] 任务已创建 pipeline=video_to_blog
[15:40:12] INFO [6d2f...] 开始执行流水线
[15:40:12] INFO [6d2f...] 进入 ingest：抓取元信息
[15:40:13] INFO [6d2f...] 进入 subtitle：尝试下载字幕
[15:40:14] INFO [6d2f...] 字幕获取成功
[15:40:14] INFO [6d2f...] 进入 subtitle_clean：清洗字幕时间戳
[15:40:15] INFO [6d2f...] 字幕清洗完成，文本长度=12456
[15:40:16] INFO [6d2f...] 进入 llm：生成博客
[15:40:23] INFO [6d2f...] LLM 完成，内容长度=4096
[15:40:24] INFO [6d2f...] 进入 storage：存储博客
[15:40:25] INFO [6d2f...] 任务成功完成
```

### 建议的观测方式
1. 调用 `POST /tasks` 创建任务。
2. 直接查看运行 `uvicorn` 的终端输出，观察节点切换和下载进度。
3. 同时轮询 `GET /tasks/{task_id}`，确认状态是否从 `pending` → `running` → `succeeded` / `failed`。

## 快速开始（命令行）

启动后进入持续等待输入模式，直接输入视频 URL 即可：

```bash
python run.py
# 或指定端口和地址
python run.py --port 9000
python run.py -p 9000 -H 192.168.1.100
```

> `run.py` 支持以下参数：
> - `-p, --port PORT` 服务器端口号 (默认: 8000)
> - `-H, --host HOST` 服务器地址 (默认: 127.0.0.1)
> - `--pipeline PIPELINE` 流水线名称 (默认: video_to_blog)
>   - `subtitle_only`: 仅下载并清洗字幕，返回文档地址
>   - `video_to_blog`: 完整视频转博客流程
> - `--poll` 提交后自动轮询直到任务完成，并输出文档地址
> - `-h, --help` 显示帮助信息

### subtitle_only 流水线

```bash
python run.py --pipeline subtitle_only
```

- 仅下载字幕资源并清洗（抹除多余的视频时间信息，默认不保留时间戳）
- 返回字幕文档地址：`data/subtitles/<视频标题>_<task_id>.txt`
- 文件创建时间由文件系统自带属性记录，文件名不重复包含时间戳，避免冗余
- 支持 `--poll` 自动轮询直到完成

### video_to_blog 流水线（默认）

```bash
python run.py --pipeline video_to_blog
```

- 完整视频转博客流程（下载字幕 → 清洗字幕 → LLM 总结 → 存储博客）
- 字幕不可用时任务直接失败（B站大部分视频至少包含 AI 字幕）
- 返回博客文档地址：`data/blogs/<date>_<title>.md`
- 支持 `--poll` 自动轮询直到完成

输入示例：

```
请输入视频 URL，提交后会继续等待下一条输入。
输入 exit、quit、按 Ctrl+D，或按 Ctrl+C 可退出。
当前连接: http://127.0.0.1:8000
URL > https://www.bilibili.com/video/BV1xfczzgEsR
任务已创建: task_id=a1b2c3d4-...  status=pending
查询命令: curl http://127.0.0.1:8000/tasks/a1b2c3d4-...
URL >
```

退出方式：`exit` / `quit` / `Ctrl+D` / `Ctrl+C`

## API 示例
### 查看支持的流水线
```bash
curl http://127.0.0.1:8000/pipelines
```

### 创建视频转博客任务（命令行交互）

```bash
python run.py
# 启动后输入视频 URL 并回车，支持连续提交多个
```

### 创建字幕下载任务（curl，手动构造 JSON）

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"pipeline": "subtitle_only", "input_url": "https://www.bilibili.com/video/BV1xfczzgEsR"}'
```

返回的 `task_id` 可通过 `GET /tasks/<task_id>` 查询；成功后 `subtitle_document_path` 字段即为清洗后的字幕文档地址。

### 创建视频转博客任务（curl，手动构造 JSON）

如果使用 curl，**JSON 必须写在单行或用单引号包裹**，避免 shell 换行符破坏 JSON 格式：

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"pipeline": "video_to_blog", "input_url": "https://www.bilibili.com/video/BV1xfczzgEsR"}'
```

> **注意**：JSON 中不要有换行或制表符等控制字符，否则返回 422 `JSON decode error: Invalid control character`。建议直接使用上方的 `run.py` 脚本。

### 查询任务状态
```bash
curl http://127.0.0.1:8000/tasks/<task_id>
```

## 数据输出
- 任务状态：`data/tasks/<task_id>.json`
- 博客文章：`data/blogs/<YYYY-MM-DD>_<文章标题>.md`
  - 文件命名格式：`<日期>_<文章标题>.md`，例如 `2026-06-07_深入理解LangGraph状态机.md`
  - 标题从 LLM 生成的内容中自动提取（取 Markdown 正文第一个 `# ` 一级标题）
  - 标题中非法字符（`\/:*?"<>|`）会自动去除
  - 若提取失败，文件名格式降级为 `<YYYY-MM-DD>_<task_id>.md`
- 字幕/音频资源：`data/video_down/<task_dir>/`
  - 字幕文件或音频 wav 均保存在任务专属文件夹下
  - 文件夹命名格式：`<YYYYMMDD_HHMMSS>_<task_id>`
  - 系统默认仅保留最近 `5` 个任务目录；每次创建新任务前会自动清理更早目录，可通过 `VIDEO_DOWN_MAX_KEEP` 调整
- 字幕文档（`subtitle_only` 流水线）：`data/subtitles/<视频标题>_<task_id>.txt`
  - 清洗后的字幕纯文本，抹除了多余的视频时间信息（默认不保留时间戳）
  - 每行一段字幕文本，无序号的纯文本格式
  - 文件名不含时间戳：创建时间由文件系统属性记录，task_id 放在标题之后，保证全局唯一
  - 方便后续 LLM 处理或人工查阅
- 视频元信息：保存在任务状态 JSON 中

### 失败任务的中间产物
- 即使任务最终状态为 `failed`，已成功下载的字幕等中间产物仍会先保留在 `data/video_down/<task_dir>/` 中。
- `data/tasks/<task_id>.json` 会尽量保留已经完成节点的中间结果，例如 `subtitle_path`、`has_subtitle` 和 `node_results.subtitle`。
- 但 `data/video_down/` 会在后续新任务创建时按保留策略自动清理旧目录，因此历史任务如需长期留存，请及时转移对应资源文件。

## 提示词配置

LLM 节点的 system prompt、user prompt 模板和输出格式均可通过 YAML 配置文件热调整，无需修改代码。

### 配置文件位置

默认：`config/prompts.yaml`

可通过以下方式指定自定义路径（优先级从高到低）：

1. `PROMPT_CONFIG_PATH` 环境变量
2. `settings.prompt_config_path`（`.env` 中配置）
3. 默认 `config/prompts.yaml`

### 配置项说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `system_prompt` | string | System prompt，定义 LLM 角色与核心要求 |
| `user_template` | string | User prompt 模板，支持 `{video_title}`、`{video_url}`、`{source_text}` 占位符 |
| `output_format.type` | `markdown` \| `json` | LLM 输出格式 |
| `output_format.schema` | string \| null | JSON Schema 描述（仅 `type=json` 时生效） |
| `temperature` | float | 生成温度，0.0-2.0 |
| `max_tokens` | int \| null | 最大生成长度，null 表示不限制 |

### 示例：切换为 JSON 输出

编辑 `config/prompts.yaml`：

```yaml
output_format:
  type: json
  schema: |
    {
      "title": "string",
      "summary": "string",
      "sections": [{"heading": "string", "content": "string"}],
      "tags": ["string"]
    }
```

### 示例：调整 System Prompt

```yaml
system_prompt: |
  你是一名科技博主。请用轻松幽默的语言将视频内容改写成一篇通俗易懂的技术博客。
  要求：
  1. 标题有吸引力，能引发好奇心。
  2. 内容深入浅出，避免过于专业的术语。
  3. 使用 Markdown 格式。
  4. 结尾附加"延伸阅读"小节。
```

配置修改后，下次任务执行时自动生效，无需重启服务。

## DeepSeek 模型

平台默认使用 DeepSeek V4 Preview 系列。模型名、上下文与价格（截至 2026-06）：

| 模型 | 上下文 | 特点 | 适用场景 |
|------|--------|------|----------|
| `deepseek-v4-pro` | 1M tokens | 1.6T 参数 (49B active) MoE，前沿推理 | 长上下文、复杂编码、多步规划 |
| `deepseek-v4-flash` | 1M tokens | 284B 参数 (13B active) MoE，高性价比 | 大批量、低延迟日常任务 |

**Thinking Mode**：V4 系列原生支持 thinking 模式（默认开启），可通过 `extra_body` 控制：
- `extra_body={"thinking": {"type": "disabled"}}` 关闭 thinking
- `extra_body={"reasoning_effort": "high" / "max"}` 控制推理强度

本平台默认走 V4 模型自带的 thinking 行为。如需在节点代码中显式控制，参考 `tools/llm_tool.py:DeepSeekLLMService.generate` 的 `thinking_enabled` / `reasoning_effort` 参数（仅对 V4 模型生效）。

**旧别名**：DeepSeek 在 2026-04-24 上线 V4 系列；旧别名 `deepseek-chat` / `deepseek-reasoner` 当前仍可用作兼容垫片，但将于 **2026-07-24 15:59 UTC** 弃用，届时将路由失败。建议尽早迁移到 V4 模型名。

## 执行逻辑
1. `ingest`：仅抓取视频标题、视频 ID 等元信息，不下载完整视频。
2. `subtitle`：下载视频字幕或自动字幕文本；无字幕则任务失败。
3. `subtitle_clean`：清洗字幕（解析 SRT/VTT 格式，移除时间戳，生成纯文本）。
4. `llm`：调用 DeepSeek 将清洗后的文本整理成博客。
5. `storage`：把博客落盘并更新任务状态。

> **字幕处理**：所有流水线统一使用 `subtitle_parser.py` 解析字幕，优先生成不含时间戳的纯文本，提升 LLM 阅读体验。可通过 `include_subtitle_time` 参数保留时间戳。

## 验证建议
```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/pipelines
```

再用一个公开视频链接发起任务，轮询 `/tasks/{task_id}` 观察状态是否从 `pending` -> `running` -> `succeeded` 或 `failed`。

## 当前限制
- 任务执行使用 FastAPI 后台任务，尚未接入 Celery/Redis。
- 当前终端日志可观测任务进度，但还没有 WebSocket/SSE 实时推送到前端。
- 首版使用本地文件存储，尚未接入 PostgreSQL / ChromaDB。
