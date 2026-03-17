# WeSeeker 唯寻

运行在 Windows PC 上的智能文件管家 Agent。用户通过自然语言描述文件需求，系统基于 LLM + Everything 在本地搜索文件、预览文本内容，并在确认后执行发送（当前为 Mock 发送）。

## 当前状态（2026-03）

项目处于可用 MVP 阶段，核心链路已可跑通：

- CLI 对话入口可用（支持 `--debug`）
- Agent 支持工具调用与最多 5 轮连续推理
- 已实现重复查询拦截、低增益早停与澄清追问
- 文件搜索基于 Everything HTTP API（含系统垃圾文件过滤）
- 文本预览支持 25+ 类型与多编码，`.docx` 支持正文纯文字预览，`.xlsx` 支持首个非空工作表前若干非空行预览，`.pptx` 支持前几页截图预览（缺少 pywin32 时退回文字提取）
- 文件发送为 Mock（仅日志输出，不实际发送）
- 已新增独立 `RAG` 测试链路（`main_rag.py`，当前未接入主 Agent）

## 核心能力

- 自然语言文件检索（关键词 + 路径提示）
- 路径别名识别（桌面/下载/文档）
- `file_index` 机制减少 LLM 路径幻觉
- 文本类文件内容读取与二次摘要
- 连续工具推理中的停止条件与澄清机制

## 项目结构

```text
WeSeeker/
├── config/                              # 配置与 Prompt 目录
│   ├── settings.yaml                    # 全局配置（LLM / Everything / 路径 / 发送目标）
│   └── prompts/                         # 系统 Prompt、闲聊 Prompt、工具 Prompt
│       ├── system_prompt.md             # 旧版系统提示词（保留参考）
│       ├── system_prompt_2.md           # 当前主用系统提示词
│       ├── chat.md                      # 闲聊模式 Prompt
│       └── tool_prompts/                # 各工具的补充提示词
│           ├── file_search.md           # 搜索工具 Prompt
│           ├── file_peek.md             # 预览工具 Prompt
│           └── file_send.md             # 发送工具 Prompt
├── core/                                # Agent 核心编排层
│   ├── agent.py                         # 主循环、消息编排、工具调度入口
│   ├── config_loader.py                 # 配置加载统一入口
│   ├── conversation.py                  # 对话上下文管理（当前为空壳）
│   ├── entities.py                      # ToolSpec / ErrorEvent / PauseEvent 等轻量实体
│   ├── llm_router.py                    # LLM 客户端封装
│   ├── reasoning_state.py               # 推理状态对象
│   ├── security_gate.py                 # 安全校验入口（当前为空壳）
│   ├── sensitive_sanitizer.py           # 敏感信息脱敏入口（当前为空壳）
│   └── tool_executor.py                 # 工具执行循环与去重逻辑
├── tools/                               # 具体工具实现
│   ├── everything_search.py             # Everything HTTP API 搜索
│   ├── file_inspector.py                # 文件元信息读取（当前为空壳）
│   ├── file_sender.py                   # 文件发送（当前为 Mock）
│   ├── file_summarizer.py               # 文件内容提取与摘要辅助
│   ├── folder_lister.py                 # 文件夹直属内容列举
│   ├── search_knowledge.py              # 知识库检索工具接口（预留）
│   └── path_resolver.py                 # 路径智能解析（当前为空壳）
├── rag/                                 # 独立 RAG 检索链路
│   ├── knowledge_base_registry.py       # 知识库注册与别名解析
│   ├── manifest_store.py                # 增量索引清单
│   ├── extractors.py                    # 文件原文抽取
│   ├── chunker.py                       # 文本切块与证据摘要
│   ├── embeddings.py                    # embedding provider 封装（LM Studio / local_hash）
│   ├── vector_store.py                  # ChromaDB 封装
│   ├── retriever.py                     # chunk 召回
│   ├── reranker.py                      # chunk rerank
│   ├── aggregator.py                    # chunk -> file 聚合
│   ├── indexer.py                       # 建库与增量更新
│   └── service.py                       # 检索编排
├── listeners/                           # 消息监听预留层（当前为空壳）
│   ├── wechat_listener.py               # 微信监听入口
│   └── message_parser.py                # 消息预处理
├── storage/                             # 持久化预留层（当前为空壳）
│   ├── db.py                            # SQLite 接口预留
│   └── models.py                        # 数据模型预留
├── doc/                                 # 补充设计与专项说明文档
│   ├── terminal_trace_design.md         # 终端追踪初版设计
│   ├── terminal_trace_design_v2.md      # 终端追踪分阶段实施版
│   ├── tool_class_refactor.md           # Tool 类重构说明（英文）
│   ├── tool_class_refactor_plan_zh.md   # Tool 类重构计划（中文）
│   └── 候选列表序号歧义问题说明.md      # 候选列表序号作用域问题说明
├── test/                                # 测试与调试脚本
│   ├── test_iterative_tool_loop.py      # 连续工具推理测试
│   ├── test_real_fallback_e2e.py        # 真实 API 兜底链路测试
│   ├── test_list_folder_contents.py     # 文件夹展开测试
│   ├── test_empty_response_event.py     # 空响应事件测试
│   └── debug_llm_messages.py            # LLM 消息链调试脚本
├── main.py                              # CLI 入口
├── main_rag.py                          # 独立 RAG 测试入口
├── README.md                            # 项目快速说明
├── AGENTS.md                            # 开发代理工作指南
├── task_background.md                   # 项目背景、进度与日志
└── WeSeeker-唯寻_技术大纲.md            # 完整技术设计蓝图
```

> 完整设计与阶段性状态请参考：`task_background.md`、`WeSeeker-唯寻_技术大纲.md`

## 环境要求

- 操作系统：Windows（推荐）
- Python：3.8+
- 依赖安装：`pip install -r requirements.txt`
- Everything：需开启 HTTP 服务（默认 `127.0.0.1:8080`）
- 测试执行环境：`conda weseeker`（项目依赖与 RAG 链路已在该环境验证）

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

rag:
  enabled: true
  chroma:
    persist_directory: "storage/chroma"
  manifest:
    directory: "storage/rag_manifests"
  embedding:
    provider: "lmstudio"
    api_base: "http://100.69.36.118:1234"
    model: "text-embedding-qwen3-embedding-0.6b"
  knowledge_bases:
    study:
      root_path: "C:\\Users\\Flora\\Desktop\\LM Study"
```

### 3) 启动 Everything HTTP 服务

在 Everything 中启用：`工具 -> 选项 -> HTTP 服务器 -> 启用`。

建议先进入测试环境：

```bash
conda activate weseeker
```

### 4) 运行

```bash
python main.py
```

调试模式：

```bash
python main.py --debug
```

独立 RAG 测试：

```bash
python main_rag.py list-kb
python main_rag.py index --kb study
python main_rag.py search --kb study --query "RAG 的检索增强是什么"
python main_rag.py repl --kb study
```

常见用法说明：

- `python main_rag.py list-kb`
  - 列出当前已注册知识库，例如 `study -> C:\Users\Flora\Desktop\LM Study`
- `python main_rag.py index --kb study`
  - 对指定知识库做增量索引；只重建新增、修改或删除过的文件
- `python main_rag.py index --kb study --force`
  - 强制全量重建该知识库索引；适合切换 embedding 模型、修改切块策略后使用
- `python main_rag.py search --kb study --query "RAG hybrid search rerank"`
  - 在指定知识库中检索内容，返回文件级结果和证据 chunk 摘要
- `python main_rag.py search --kb study --query "RLHF PPO DPO" --max-results 3`
  - 限制返回文件数量，便于快速观察 top 结果
- `python main_rag.py repl --kb study`
  - 进入交互式查询模式，连续测试多个 query；输入 `exit` 或 `quit` 退出

参数说明：

- `--kb`
  - 知识库别名，当前默认使用 `study`
- `--query`
  - 检索主题、问题或关键词
- `--max-results`
  - 最多返回几个文件结果，默认 `5`
- `--force`
  - 强制全量重建索引，仅用于 `index`

当前默认知识库配置：

```yaml
rag:
  knowledge_bases:
    study:
      display_name: "LM Study"
      root_path: "C:\\Users\\Flora\\Desktop\\LM Study"
      aliases:
        - "study"
        - "lm study"
        - "学习资料"
        - "知识库"
```

说明：

- `study` 是知识库的 `kb_id`，也是最推荐传给 `--kb` 或后续 `search_knowledge()` 的值
- `display_name` 主要用于结果展示
- `aliases` 用于后续 LLM 或自然语言别名映射，不影响底层存储命名

## 测试

> 按项目约定，测试请在 `conda weseeker` 环境执行。

连续工具推理测试：

```bash
conda run --no-capture-output -n weseeker python -m test.test_iterative_tool_loop
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
- 多格式预览仍待完善（当前已支持 docx 正文纯文字预览、xlsx 首个非空工作表文本预览、pptx 前几页轻量预览与 PDF 转图预览）

## 注意事项

- 请勿将真实 API Key 提交到仓库
- 当前为只读文件操作设计，不执行删除/修改/移动
- 仓库中部分旧测试文件已失效，详见 `task_background.md`

## License

MIT
