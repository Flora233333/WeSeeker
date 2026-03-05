# WeSeeker 唯寻

运行在 Windows PC 上的智能文件管家 Agent。用户通过自然语言描述文件需求，系统基于 LLM + Everything 在本地搜索文件、预览文本内容，并在确认后执行发送（当前为 Mock 发送）。

## 当前状态（2026-03）

项目处于可用 MVP 阶段，核心链路已可跑通：

- CLI 对话入口可用（支持 `--debug`）
- Agent 支持工具调用与最多 5 轮连续推理
- 已实现重复查询拦截、低增益早停与澄清追问
- 文件搜索基于 Everything HTTP API（含系统垃圾文件过滤）
- 文本预览支持 25+ 类型与多编码
- 文件发送为 Mock（仅日志输出，不实际发送）

## 核心能力

- 自然语言文件检索（关键词 + 路径提示）
- 路径别名识别（桌面/下载/文档）
- `file_index` 机制减少 LLM 路径幻觉
- 文本类文件内容读取与二次摘要
- 连续工具推理中的停止条件与澄清机制

## 项目结构

```text
WeSeeker/
├── config/
│   ├── settings.yaml
│   └── prompts/
│       ├── system_prompt.md
│       ├── system_prompt_2.md
│       ├── chat.md
│       └── tool_prompts/
├── core/
│   ├── agent.py
│   └── llm_router.py
├── tools/
│   ├── everything_search.py
│   ├── file_summarizer.py
│   └── file_sender.py
├── main.py
├── test_iterative_tool_loop.py
└── task_background.md
```

> 完整设计与阶段性状态请参考：`task_background.md`、`WeSeeker-唯寻_技术大纲.md`

## 环境要求

- 操作系统：Windows（推荐）
- Python：3.8+
- 依赖安装：`pip install -r requirements.txt`
- Everything：需开启 HTTP 服务（默认 `127.0.0.1:8080`）
- 测试执行环境：`conda base`（项目依赖已在 base 环境验证）

## 快速开始

### 1) 安装依赖

```bash
pip install -r requirements.txt
```

### 2) 配置 LLM 与路径

编辑 `config/settings.yaml`：

```yaml
llm:
  provider: "lmstudio"      # lmstudio / ollama / cloud
  api_base: "http://127.0.0.1:1234"
  api_key: ""               # 本地模型可留空
  model: ""

everything:
  host: "127.0.0.1"
  port: 8080

paths:
  desktop: "C:\\Users\\{username}\\Desktop"
  downloads: "C:\\Users\\{username}\\Downloads"
  documents: "C:\\Users\\{username}\\Documents"
```

### 3) 启动 Everything HTTP 服务

在 Everything 中启用：`工具 -> 选项 -> HTTP 服务器 -> 启用`。

### 4) 运行

```bash
python main.py
```

调试模式：

```bash
python main.py --debug
```

## 测试

> 按项目约定，测试请在 `conda base` 环境执行。

连续工具推理测试：

```bash
conda run --no-capture-output -n base python test_iterative_tool_loop.py
```

## 已实现 / 未实现

### 已实现

- CLI 入口与对话历史管理（基础）
- LLM Router（lmstudio / ollama / cloud）
- Everything 文件搜索工具
- 文本内容读取工具（L1/L2/L3）
- 连续工具推理（最多 5 轮）

### 部分实现 / 待完善

- `send_file` 目前为 Mock
- `conversation.py` / `security_gate.py` / `sensitive_sanitizer.py` 仍待落地
- 多格式预览（docx/xlsx/pptx/pdf）待实现

## 注意事项

- 请勿将真实 API Key 提交到仓库
- 当前为只读文件操作设计，不执行删除/修改/移动
- 仓库中部分旧测试文件已失效，详见 `task_background.md`

## License

MIT
