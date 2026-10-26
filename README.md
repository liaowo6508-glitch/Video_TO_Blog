# B站字幕与博客生成

输入 B 站（或 yt-dlp 支持的）视频链接，下载字幕并清洗为纯文本；也可以继续调用 DeepSeek，把字幕整理成结构化中文博客。

保留两条流水线：

- `subtitle_only`：只输出清洗后的字幕
- `video_to_blog`：输出清洗后的字幕 + DeepSeek 生成的博客

## 环境要求

- Python 3.12（Windows 已验证）
- B站登录态：配置 `sessdata` 或 `cookie_file`，否则通常拿不到字幕
- DeepSeek API Key：仅 `video_to_blog` 需要

## 快速开始（Windows）

```bat
cd /d D:\视频转blog\Video_TO_Blog
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

首次运行会自动从 `config.example.ini` 生成 **`config.ini`**。用记事本打开 `config.ini`，填写：

```ini
[bilibili]
sessdata = 你的SESSDATA

[deepseek]
api_key = 你的DeepSeek Key
model = deepseek-chat
```

保存后直接运行，无需启动任何后端服务：

```bat
venv\Scripts\python.exe main.py https://www.bilibili.com/video/BV1xfczzgEsR
```

也可以双击 `start.bat`（等价于运行 `main.py`，已设置好 UTF-8 编码）。

程序会阻塞执行，完成后打印输出文件路径并退出。不传 URL 则进入交互模式：

```bat
venv\Scripts\python.exe main.py
```

只输出字幕：

```bat
venv\Scripts\python.exe main.py <URL> --pipeline subtitle_only
```

一次处理多个 URL：

```bat
venv\Scripts\python.exe main.py <URL1> <URL2> --pipeline subtitle_only
```

## 配置 `config.ini`

用记事本直接编辑，保存为 UTF-8 即可（兼容 BOM）。所有配置项：

```ini
[bilibili]
# B站登录 cookie，字幕接口需要登录态
sessdata =

# 可选，Netscape 格式 cookies.txt，优先级高于 sessdata
cookie_file =

# B站 412 时可改为 true
no_proxy = false

[deepseek]
# DeepSeek API Key，仅 video_to_blog 需要
api_key =
model = deepseek-chat
base_url = https://api.deepseek.com

[run]
# 默认流水线：video_to_blog / subtitle_only
pipeline = video_to_blog
prompt_config = prompts.yaml
```

> 注释请单独成行；`#` 不要写在值的同一行。

`config.ini` 含密钥，已被 `.gitignore` 忽略；`config.example.ini` 是模板，会随源码提供。

### 获取 SESSDATA

1. Chrome 登录 `bilibili.com`
2. `F12` → **Application / 应用** → **Cookies** → `https://www.bilibili.com`
3. 复制 `SESSDATA` 的值，填入 `config.ini`

`cookie_file` 优先于 `sessdata`，可指向浏览器导出的 Netscape 格式 `cookies.txt`。

## 输出

只保留两类结果，均位于 `data/`：

- **博客**：`data/blogs/<YYYY-MM-DD>_<文章标题>.md`
  - 标题取 LLM 输出正文第一个 `# ` 一级标题
  - 标题非法字符会自动清理；提取失败时降级为 `<日期>_<task_id>.md`
- **清洗后字幕**：`data/subtitles/<视频标题>_<task_id>.txt`
  - 一段一行、无时间戳的纯文本
  - 无字幕时写入标题、URL 和“无可用字幕”

原始 `.srt/.vtt` 字幕只下载到系统临时目录，清洗完成后立即删除，不会留在项目里。也不再生成任务 JSON 等中间文件。

## 隐私与版本控制

- `config.ini` 含 B站 cookie 和 DeepSeek Key，已被 `.gitignore` 忽略，不会提交。
- `data/` 下的博客和字幕是运行产物，同样不会提交。
- 仓库只保留 `config.example.ini` 模板；换机器后首次运行会自动生成新的 `config.ini`，重新填写即可。

## 提示词配置

提示词在根目录 [prompts.yaml](prompts.yaml)，由 [videoblog/config/prompts.py](videoblog/config/prompts.py) 加载。修改后下次任务执行时自动生效。

| 字段 | 说明 |
|------|------|
| `system_prompt` | 定义 LLM 的角色与写作要求 |
| `user_template` | 用户提示词模板，支持 `{video_title}`、`{video_url}`、`{source_text}` |
| `output_format.type` | `markdown` 或 `json` |
| `output_format.json_schema` | `type=json` 时的结构描述 |
| `temperature` | 生成温度 |
| `max_tokens` | 最大生成长度，`null` 表示不限制 |

## 目录结构

```text
Video_TO_Blog/
├── config.example.ini  # 配置模板（随源码提供）
├── config.ini          # 实际配置（首次运行自动生成，已忽略）
├── main.py             # 直接运行入口
├── start.bat           # 双击直接运行
├── prompts.yaml        # 提示词
├── requirements.txt
├── videoblog/          # 核心包
│   ├── config/         # config.ini 读取、提示词加载
│   ├── engine/         # LangGraph 运行器与流水线注册
│   ├── nodes/          # ingest / subtitle / subtitle_store / llm / storage
│   ├── pipelines/      # subtitle_only、video_to_blog
│   ├── storage/        # 博客与字幕落盘
│   ├── tools/          # yt-dlp 封装、字幕解析、DeepSeek 调用
│   └── monitor.py
└── data/
    ├── blogs/          # 博客 Markdown
    └── subtitles/      # 清洗后的字幕文本
```

## 当前限制

- B站字幕需要登录态，匿名请求通常只能拿到“无可用字幕”
- 无字幕时不做音频转写（ASR 模块已移除），`video_to_blog` 会直接失败并给出提示
- `main.py` 为同步执行，一个视频处理完才处理下一个
- B站自动字幕语言为 `ai-zh`；人工字幕优先级更高
