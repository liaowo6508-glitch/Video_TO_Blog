# AI Pipeline Platform

基于 LangGraph 的智能任务编排平台 MVP。当前首版实现聚焦 `video_to_blog`：将 Bilibili 或通用视频链接下载、检测字幕、必要时进行 ASR 转写，并调用 DeepSeek 生成结构化中文博客文章。

## 已实现能力
- LangGraph 状态机编排骨架
- `video_to_blog` 流水线注册机制
- `ingest(metadata) -> subtitle -> asr -> llm -> storage` 节点链路
- 字幕存在时自动跳过 ASR
- 优先下载字幕文本，无字幕时使用本地 Whisper 转写（Groq 为备用）
- FastAPI 接口：创建任务、查看任务、列出流水线
- 任务执行日志：节点阶段、任务状态、失败原因
- `yt-dlp` 下载进度映射到服务终端日志，便于观测音频下载状态
- 本地 JSON 任务存储与 Markdown 结果落盘

## 目录结构
```text
AI_project_talking_about/
├── api/
├── config/
├── engine/
├── models/
├── nodes/
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

本地 Whisper 模型会在首次运行时自动下载。

Ubuntu 示例：

```bash
sudo apt update
sudo apt install -y ffmpeg
```

### 3. 配置环境变量
在项目根目录创建 `.env`：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key
GROQ_API_KEY=optional_groq_api_key_for_backup
BILIBILI_SESSDATA=optional_bilibili_sessdata
BILIBILI_COOKIE_FILE=optional_path_to_cookies_txt
BILIBILI_NO_PROXY=false
APP_HOST=0.0.0.0
APP_PORT=8000
DEEPSEEK_MODEL=deepseek-chat
PROMPT_CONFIG_PATH=optional_path_to_prompts_yaml  # 默认 config/prompts.yaml
ASR_PROVIDER=local_whisper       # 默认：本地 Whisper，不需要外网
LOCAL_WHISPER_MODEL=small        # 可选：tiny/base/small/medium/large-v3
GROQ_MODEL=whisper-large-v3-turbo  # 仅当 ASR_PROVIDER=groq 时生效
FFMPEG_LOCATION=optional_path_to_ffmpeg_bin_dir_or_binary
```

说明：
- `DEEPSEEK_API_KEY`：用于博客内容生成。
- `GROQ_API_KEY`：可选，仅在 `ASR_PROVIDER=groq` 时才需要，用于云端 Whisper ASR（备用方案）。
- `ASR_PROVIDER`：默认为 `local_whisper`（本地转写，不需要外网）。设为 `groq` 可切换为云端方案。
- `LOCAL_WHISPER_MODEL`：本地 Whisper 模型规模，影响精度和速度，`small` 为推荐默认值。
- `BILIBILI_SESSDATA`：部分 B站 视频下载或高质量访问时需要，可选。
- `BILIBILI_COOKIE_FILE`：优先于 `BILIBILI_SESSDATA`，推荐填写浏览器导出的 Netscape `cookies.txt` 文件路径。
- `BILIBILI_NO_PROXY`：设为 `true` 时，`yt-dlp` 将不使用当前 shell 里的代理环境变量，适合排查 B站 `412` 或代理拦截问题。
- `FFMPEG_LOCATION`：可选，指向 `ffmpeg/ffprobe` 所在目录，或可执行文件路径，用于 `yt-dlp` 后处理阶段定位二进制。

## 启动服务
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

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
- 当前执行节点：`ingest` / `subtitle` / `asr` / `llm` / `storage`
- 字幕是否命中、是否跳过 ASR
- `yt-dlp` 音频下载进度：百分比、已下载大小、总大小、速度、ETA

### 典型日志示例
```text
[15:40:12] INFO [6d2f...] 任务已创建 pipeline=video_to_blog
[15:40:12] INFO [6d2f...] 开始执行流水线
[15:40:12] INFO [6d2f...] 进入 ingest：抓取元信息
[15:40:13] INFO [6d2f...] 进入 subtitle：优先尝试字幕
[15:40:14] INFO [6d2f...] 未获取到字幕，转入 ASR
[15:40:14] INFO [6d2f...] 进入 asr：下载音频并转写
[15:40:15] INFO [BV1Y6Ec6zEYY] ⬇ audio   23.4%  3.2MB/13.8MB  @ 1.1MB/s  ETA 9s
[15:40:23] INFO [BV1Y6Ec6zEYY] ✅ audio 下载完成  →  /.../data/video_down/<YYYYMMDD_HHMMSS>_<task_id>/BV1Y6Ec6zEYY.wav  (8.1s)
[15:40:31] INFO [6d2f...] ASR 完成，转写长度=12456
[15:40:37] INFO [6d2f...] 任务成功完成
```

### 建议的观测方式
1. 调用 `POST /tasks` 创建任务。
2. 直接查看运行 `uvicorn` 的终端输出，观察节点切换和下载进度。
3. 同时轮询 `GET /tasks/{task_id}`，确认状态是否从 `pending` → `running` → `succeeded` / `failed`。

## 快速开始（命令行）

只需一条命令传入视频 URL，其余全部自动处理：

```bash
python run.py "https://www.bilibili.com/video/BV1xfczzgEsR"
```

输出示例：

```
任务已创建: task_id=a1b2c3d4-...  status=pending
查询命令: curl http://127.0.0.1:8000/tasks/a1b2c3d4-...
```

## API 示例
### 查看支持的流水线
```bash
curl http://127.0.0.1:8000/pipelines
```

### 创建视频转博客任务（直接传入 URL）

```bash
python run.py "https://www.bilibili.com/video/BV1xfczzgEsR"
```

### 创建视频转博客任务（curl，手动构造 JSON）

如果使用 curl，**JSON 必须写在单行或用单引号包裹**，避免 shell 换行符破坏 JSON 格式：

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"pipeline": "video_to_blog", "input_url": "https://www.bilibili.com/video/BV1xfczzgEsR"}'
```

> **注意**：JSON 中不要有换行或制表符等控制字符，否则返回 422 `JSON decode error: Invalid control character`。建议直接使用上方的 `run.py` 脚本。
```

### 查询任务状态
```bash
curl http://127.0.0.1:8000/tasks/<task_id>
```

## 数据输出
- 任务状态：`data/tasks/<task_id>.json`
- 博客结果：`data/results/<task_id>.md`
- 音视频资源：`data/video_down/<task_dir>/`
  - 字幕文件或音频 wav 均保存在任务专属文件夹下
  - 文件夹命名格式：`<YYYYMMDD_HHMMSS>_<task_id>`
- 视频元信息：保存在任务状态 JSON 中

### 失败任务的中间产物
- 即使任务最终状态为 `failed`，已成功下载的字幕等中间产物仍会保留在 `data/video_down/<task_dir>/` 中。
- `data/tasks/<task_id>.json` 会尽量保留已经完成节点的中间结果，例如 `subtitle_path`、`has_subtitle` 和 `node_results.subtitle`。
- 因此请同时查看任务状态和任务目录，不要仅凭最终 `failed` 判断“没有任何产物”。

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

## 执行逻辑
1. `ingest`：仅抓取视频标题、视频 ID 等元信息，不下载完整视频。
2. `subtitle`：优先下载现有字幕或自动字幕文本。
3. 若有字幕，直接进入 `llm`。
4. 若无字幕，进入 `asr`，仅下载音频并调用本地 Whisper 转写。
5. `llm`：调用 DeepSeek 将文本整理成博客。
6. `storage`：把博客落盘并更新任务状态。

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
