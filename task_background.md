# WeSeeker 唯寻 — 项目任务背景

> 本文件是新会话的上下文载入口，用于快速了解项目现状。请持续维护。
> 最后更新：2026-03-18

---

## 〇、本文件维护规范（面向 AI 模型）

本文件 `task_background.md` 是项目开发的连续性保障。每个新会话的 AI 助手在开始工作前应先阅读本文件，在完成工作后应更新本文件。请严格遵循以下规范：

### 何时读取

- **每次新会话开始时**，必须先完整阅读本文件，理解项目现状后再开始工作
- 如果用户的任务涉及修改代码结构、新增/删除模块、修复 bug、调整架构，完成后必须回来更新本文件

### 何时更新

以下情况**必须**更新本文件：

1. **新增或删除了文件/模块** → 更新「三、目录结构」
2. **实现了待实现功能** → 更新「四、当前已实现的功能」，同时从「六、待实现功能」中移除或调整优先级
3. **发现了新 bug 或解决了已知问题** → 更新「五、已知问题与待修复项」
4. **引入了新的依赖/技术栈** → 更新「二、技术栈」
5. **修改了配置结构** → 更新「八、配置说明」
6. **修改了架构流程** → 更新「七、架构设计要点」
7. **产生了 git commit** → 在「九、更新日志」追加一行记录
8. **做了代码变更但未提交** → 在「九、更新日志」末尾以"未提交"标记记录
9. **test/* 和 doc/* 这两个文件夹内的所有文件都不要进行git追踪**

### 如何更新

- **更新日志**（第九节）：每次变更追加一行，格式为 `| 日期 | Commit | 类型 | 内容 |`，类型包括：初始化、功能、Bug 修复、重构、Prompt 重写、文档、配置。未提交时 Commit 列填"未提交"
- **最后更新日期**：修改文件顶部的日期
- **保持简洁**：每个条目用一两句话概括，不写长篇大论。详细的技术方案去看代码和技术大纲
- **保持准确**：只写已确认的事实。不确定的内容用"待确认"标注。不要把计划写成已完成
- **状态标记**统一使用：✅ 已实现、⚠️ 部分实现/Mock、❌ 空壳/未实现

### 不应做的事

- 不要删除历史更新日志记录（只追加，不修改历史）
- 不要在本文件中写详细的技术方案或代码片段（那是技术大纲和代码注释的职责）
- 不要把临时的调试信息写入本文件
- 不要修改已完成的 commit 记录的描述

### 十一、会话协作约定（新增）

- 对于**小范围源文件修改**（如改一两处逻辑、删一小段判断、改命名、调一小段结构），AI 助手应先向用户展示拟修改的代码示例或补丁思路，待用户明确同意后再实际修改源文件。
- 对于**明确同意的编写型任务/较大实现任务**，用户在任务开头已同意后，AI 助手可直接实施，无需在每个小改动前重复确认。
- 本约定仅影响“是否先展示修改示例再落盘”的协作方式，不改变 `task_background.md` 的更新要求。

---

## 一、项目简介

WeSeeker 唯寻是一个运行在 Windows PC 上的**智能文件管家 Agent**。用户通过聊天界面（当前为 CLI，后续对接微信/飞书等）用自然语言描述文件需求，Agent 借助 LLM + Everything SDK 在本地搜索、预览、发送文件。

**核心理念**：Prompt-Centric 架构（System Prompt + Function Calling），LLM 自主决策调用工具，对文件系统仅有只读权限。

**项目仓库位置**：`c:\Users\Flora\Desktop\WeSeeker唯寻\WeSeeker\`

---

## 二、技术栈

| 组件 | 方案 | 状态 |
|------|------|------|
| 语言 | Python 3.8+ | 使用中 |
| LLM 调用 | OpenAI SDK（兼容 LM Studio / Ollama / 云端 API） | 使用中 |
| 文件搜索 | Everything HTTP API（localhost:8080） | 使用中 |
| 向量检索 | ChromaDB（目录级知识库） | ✅ 已在 `weseeker` 环境验证 |
| Embedding | LM Studio Embeddings API（Qwen3-Embedding-0.6B-GGUF） | ✅ 已接入并验证 |
| 配置管理 | PyYAML（config/settings.yaml） | 使用中 |
| 文件预览 | python-pptx / python-docx / PyMuPDF / openpyxl / Pillow / pywin32 | `python-docx` / `openpyxl` / `python-pptx` / Pillow / PyMuPDF / `pywin32` 已使用 |
| 日志 | loguru | 未引入 |
| 数据持久化 | SQLite | 未引入 |
| 消息监听 | 微信/飞书接口 | 未引入 |

当前 requirements.txt 有 10 个依赖：`openai`, `requests`, `pyyaml`, `Pillow`, `PyMuPDF`, `python-docx`, `openpyxl`, `pywin32`, `python-pptx`, `chromadb`

---

## 三、目录结构

```
WeSeeker/
├── config/
│   ├── settings.yaml                  # 全局配置（LLM/Everything/路径/发送目标）
│   └── prompts/
│       ├── system_prompt.md           # 系统提示词 v1（旧版，有多处与实际不符）
│       ├── system_prompt_2.md         # 系统提示词 v2（2026-03-04 重写，与实际对齐）
│       ├── chat.md                    # 闲聊模式 prompt
│       └── tool_prompts/
│           ├── file_search.md         # 搜索工具 prompt（完整）
│           ├── file_peek.md           # 预览工具 prompt（完整）
│           └── file_send.md           # 发送工具 prompt（完整）
├── core/
│   ├── agent.py                       # Agent 主循环（~462行）         ✅ 已实现（支持最多5轮自动工具推理、早停与可维护性重构）
│   ├── llm_router.py                  # LLM 客户端封装（~175行）       ✅ 已实现
│   ├── config_loader.py               # 配置加载统一入口               ✅ 已实现（新增）
│   ├── entities.py                    # 轻量实体定义（ToolSpec/ErrorEvent） ✅ 已实现（新增）
│   ├── reasoning_state.py             # 推理状态对象（dataclass）      ✅ 已实现（新增）
│   ├── tool_executor.py               # 工具执行器（信号推断/去重）    ✅ 已实现（新增）
│   ├── conversation.py                # 上下文管理器                   ❌ 空壳
│   ├── security_gate.py               # 安全指令过滤器                 ❌ 空壳
│   └── sensitive_sanitizer.py         # 敏感信息脱敏器                 ❌ 空壳
├── tools/
│   ├── everything_search.py           # Everything 搜索（~263行）      ✅ 已实现
│   ├── file_sender.py                 # 文件发送（~95行）              ⚠️ Mock 实现
│   ├── file_summarizer.py             # 文件预览（~369行）             ⚠️ 文本/图片/PDF/Docx/Xlsx/Ppt轻量预览
│   ├── folder_lister.py               # 文件夹直属内容列举              ✅ 已实现（新增）
│   ├── search_knowledge.py            # 目录级知识库检索工具接口         ✅ 已实现（新增，未接入主 Agent）
│   ├── file_inspector.py              # 文件元信息                      ❌ 空壳
│   └── path_resolver.py               # 路径智能解析                    ❌ 空壳
├── rag/
│   ├── knowledge_base_registry.py     # 知识库注册与别名解析            ✅ 已实现（新增）
│   ├── manifest_store.py              # 索引增量清单                    ✅ 已实现（新增）
│   ├── extractors.py                  # 文档原文提取                    ✅ 已实现（新增）
│   ├── chunker.py                     # 文本切块与证据摘要              ✅ 已实现（新增）
│   ├── embeddings.py                  # embedding 提供商封装（local_hash / LM Studio） ✅ 已实现（新增）
│   ├── vector_store.py                # ChromaDB 封装                   ✅ 已实现（新增）
│   ├── retriever.py                   # chunk 召回                      ✅ 已实现（新增）
│   ├── reranker.py                    # chunk 重排                      ✅ 已实现（新增）
│   ├── aggregator.py                  # chunk→file 聚合                 ✅ 已实现（新增）
│   ├── indexer.py                     # 全量/增量建库                   ✅ 已实现（新增）
│   └── service.py                     # RAG 检索编排                    ✅ 已实现（新增）
├── doc/
│   ├── terminal_trace_design.md       # 终端追踪初版设计（基于动态加载前提）
│   ├── terminal_trace_design_v2.md    # 终端追踪分阶段实施版（V1/V2）
│   ├── tool_class_refactor.md         # Tool 类重构说明（英文）
│   ├── tool_class_refactor_plan_zh.md # Tool 类重构阶段计划（中文）
│   ├── 候选列表序号歧义问题说明.md    # 候选列表序号作用域问题说明
│   └── test.md                        # 文档草稿/临时记录
├── listeners/
│   ├── wechat_listener.py             # 微信监听                        ❌ 空壳
│   └── message_parser.py              # 消息解析                        ❌ 空壳
├── storage/
│   ├── db.py                          # SQLite 持久化                   ❌ 空壳
│   └── models.py                      # 数据模型                        ❌ 空壳
├── main.py                            # CLI 入口                        ✅ 已实现
├── main_rag.py                        # 独立 RAG 测试入口               ✅ 已实现（新增）
├── test/
│   ├── test_iterative_tool_loop.py    # 连续工具推理与默认兜底文案测试（FakeLLM）
│   ├── test_real_fallback_e2e.py      # 真实 LLM API 澄清/兜底 E2E（可注入澄清失败）
│   ├── test_list_folder_contents.py   # 文件夹展开与目录候选复用测试
│   ├── test_empty_response_event.py   # 空响应事件一次性注入测试
│   ├── test_everything_timestamp.py   # FILETIME 时间戳转换测试
│   ├── test_search_combinations.py    # Everything 组合关键词搜索观察脚本
│   ├── test_filter.py                 # 文件过滤规则测试
│   ├── test_preview.py                # 文本预览基础测试脚本
│   ├── test_image_preview_multimodal.py # 图片预览与多模态摘要测试
│   ├── test_pdf_preview_multimodal.py # PDF 转图预览与多模态摘要测试
│   ├── test_pdf_render_scale.py       # PDF 渲染倍率观察脚本
│   ├── test_preview_full.py           # 预览全流程测试脚本
│   ├── test_full_workflow.py          # 端到端主流程测试脚本
│   ├── test_agent.py                  # Agent 行为测试脚本
│   ├── test_local_llm.py              # 本地 LLM 联调脚本
│   ├── test_search.py                 # Everything 搜索脚本测试
│   ├── debug_llm_messages.py          # 调试脚本（追踪 LLM 消息链）
│   └── test_*.py                      # 其他集成/手工测试脚本
├── requirements.txt
├── README.md
├── AGENTS.md                          # 代码代理开发指南（已按当前实现更新）
├── WeSeeker-唯寻_技术大纲.md          # 技术设计文档（789行，完整蓝图）
└── task_background.md                 # 项目任务背景（新会话载入口）← 本文件
```

---

## 四、当前已实现的功能

### 核心链路（可工作）

1. **CLI 交互** — main.py 提供命令行入口，支持 `--debug` 调试模式、退出/清空命令
2. **Agent 调度** — 用户输入 → LLM 意图识别 → 工具调用 → 结果回传 → 自然语言回复（支持最多 5 轮自动工具推理与早停追问）
3. **LLM 多提供商** — 支持 lmstudio / ollama / cloud 三种模式，通过 settings.yaml 中 `provider` 字段切换
4. **文件搜索** — 通过 Everything HTTP API 进行关键词+路径搜索，自动过滤系统垃圾文件（.lnk/.tmp/desktop.ini 等）
5. **文本文件预览** — 支持 .txt/.md/.py/.json/.csv/.log/.yaml 等 25+ 种文本格式，多编码兼容（UTF-8/GBK/GB2312/UTF-16），三级深度 L1/L2/L3
6. **file_index 防幻觉** — 搜索结果缓存在 Agent.candidate_files，LLM 用序号引用文件而非编造路径
7. **LLM 二次摘要** — 文件内容提取后，额外调一次 LLM 生成口语化总结
8. **自动工具推理与早停** — Agent 支持最多 5 轮自动工具推理，具备重复搜索拦截、低增益早停与最小澄清追问
9. **Agent 内部重构** — Agent 内部已拆分为 `ReasoningState`、`ToolExecutor` 与预览响应渲染小函数；`llm_router.py` 与 `everything_search.py` 统一复用 `config_loader.py`，降低嵌套与重复代码。
10. **健壮性增强** — `Agent.process_message` 支持失败回滚，避免 LLM/工具链路异常污染 `conversation_history` 与 `candidate_files`；工具参数 JSON 非法时返回显式 `invalid_tool_arguments` 信号；Markdown 清理改为保守模式，避免破坏文件名与代码片段。
11. **真实 E2E 兜底验证脚本** — 新增 `test_real_fallback_e2e.py`，复用 `Agent.process_message` + 真实 API；覆盖“正常澄清”与“澄清调用失败后返回默认兜底文案”两条路径，含临时文件自动清理。
12. **测试目录整理** — 所有 `test_*.py` 已收拢到 `test/` 目录，旧测试导入路径与旧接口调用已修复，可用 `python -m test.<module>` 方式执行。
13. **工具注册统一入口（阶段一）** — `Agent.__init__` 新增 `tool_specs` 单一注册源，通过 `entities.py` 中的 `ToolSpec(name, schema, handler)` 派生 `self.tools` 与 `self.tool_functions`，为后续 Tool 类重构做准备，当前行为不变。
14. **一次性错误事件注入** — `Agent` 新增 `pending_error_event`；当 LLM 出现空响应时，不污染 `conversation_history`，而是通过 `entities.py` 中的 `ERROR_EVENTS` 事件映射按类型取预定义 `ErrorEvent`，在下一轮 `_build_messages()` 中临时注入一次后清空，消息顺序为 system prompt → 历史 → 错误注入 → 当前用户输入。
15. **空响应链路测试** — 新增 `test/test_empty_response_event.py`，覆盖“当前轮空响应触发兜底文案、错误事件不写入历史、下一轮仅注入一次 system 提示、注入后自动清空”这一链路。
16. **暂停事件配置收口** — `PauseEvent` 新增 `default_fallback_msg`；澄清失败/空响应时的兜底文案不再由 `agent.py` 分支维护，而是直接读取 `core/entities.py` 中的 pause 配置并返回给用户，`_build_warning_fallback()` 已删除。
17. **文件夹直属内容列举** — 新增 `list_folder_contents` 工具，基于 Everything 的 `parent:"绝对路径"` 查询列出文件夹直属子项；必须先通过 `search_files` 获取文件夹候选，再用 `folder_index` 展开，展开后结果复用 `candidate_files`，后续可继续按序号预览文件或递归展开子文件夹。
18. **文件夹连续推进 Prompt 指引** — 在 `system_prompt_2.md` 的迭代推理规则中补充“围绕同一目标逐层展开文件夹”的保守示例，明确要求先搜索文件夹，再基于 `folder_index` 连续调用 `list_folder_contents`；同时收紧条件，只有在搜索结果对目标文件夹是唯一且高置信度命中时才允许继续向下展开，避免模型对近似命中的文件夹过早钻取。
19. **组合搜索观察脚本** — 新增 `test/test_search_combinations.py`，方便人工尝试 Everything 对多词组合（如“项目 PPT”“过年 文档”）在不同路径约束下的返回结果。
20. **序号作用域提示** — 在 Prompt 与结果文案中明确：`file_index` / `folder_index` 只对应最近一次列出的候选结果；如果用户提到“之前那组”，模型应先澄清或重新列出，避免误把旧序号应用到新列表。
21. **预览授权 Prompt 约束** — 在 `system_prompt_2.md` 中明确：读取文件内容也需要用户显式同意；用户仅确认“第几个文件/就这个”时，只表示选中目标文件，不等于授权调用 `read_file_content`。
22. **图片文件预览与多模态摘要** — `read_file_content` 现已支持 `.png/.jpg/.jpeg/.webp/.bmp/.gif`，图片文件会返回 `images` 列表；`Agent` 检测到图片结果后，会通过 `LLMClient` 构造 OpenAI-compatible 多模态消息（`image_url` + data URL）调用 LM Studio/Qwen 生成摘要，已用真实 `grade.png` 链路验证通过。
23. **图片标准化编码** — `LLMClient.encode_image_to_data_url()` 现在会先用 Pillow 对图片做标准化：自动应用 EXIF 方向、保持长宽比等比例缩放到最长边上限、并对 MPO 等非常规来源图片转为标准 PNG/JPEG 后再编码；已验证可修复 `IMG_5418.JPG` 这类手机拍摄图在 LM Studio 中的 `failed to process image` 报错。
24. **系统目录探索 Prompt 规则** — `system_prompt_2.md` 已补充：当用户明确询问桌面/下载/文档等系统级目录里有没有某类“相关文件和文件夹”时，若该类别词更像语义类别（如“图片相关”“项目资料”）而不一定出现在真实命名中，模型应优先先看该目录的一级结构，再依据真实子项名称决定是否展开可疑文件夹，而不是立刻拿类别词直接搜索文件名。
25. **PDF 转图预览与多模态摘要** — `read_file_content` 现已支持 PDF：基于 PyMuPDF 将前几页渲染为 PNG，再复用现有图片多模态摘要链路；当前 `L1/L2/L3` 对 PDF 默认对应前 `1/2/3` 页，配置位于 `settings.yaml -> preview.pdf.depth_pages`。
26. **PDF 页数与渲染倍率解耦配置** — 新增 `settings.yaml -> preview.pdf.render_scale` 控制 PDF 转图倍率，与 `llm.local.multimodal.image_max_edge.pdf` 的图片最长边压缩分离，便于后续单独测试字清晰度与模型稳定性。
27. **文本/Excel/PDF 预览深度统一配置化** — `settings.yaml -> preview` 现统一承载不同文件类型的深度参数：文本 `depth_chars` 为 `2000/5000/8000`，Excel `depth_rows` 为 `10/50/100`，PDF `depth_pages` 为 `1/2/3`；`read_file_content` 的 `L1/L2/L3` 仍保持用户语义稳定，但底层阈值已从硬编码迁移为配置读取。
28. **PDF 图片处理失败自动降级重试** — 针对部分 PDF 页面在高分辨率下会触发 LM Studio `failed to process image` 的情况，`Agent._summarize_images()` 现对 PDF/PPT 图片摘要增加按最长边 `默认值 -> 1792 -> 1536 -> 1024` 的自动重试；在当前 `pdf image_max_edge=2048` 配置下，实际生效链路即 `2048 -> 1792 -> 1536 -> 1024`，优先保留 `render_scale=3.0` 的清晰渲染，同时在模型侧失败时自动降采样兜底；已用 `人工智能在烟花爆竹生产中的应用\1.pdf` 的 L3 三页预览真实验证通过。
29. **DOCX 正文纯文字预览** — `read_file_content` 现已支持 `.docx` 的正文段落文字提取，复用现有文本深度与摘要链路；当前仅处理纯文字段落，不处理图片、文本框、页眉页脚等复杂对象，若文档为空或主要由图片组成则返回显式错误提示。
30. **XLSX 首个非空工作表预览** — `read_file_content` 现已支持 `.xlsx`：基于 `openpyxl` 选择首个存在有效内容的工作表，提取前 `L1/L2/L3 = 10/50/100` 条非空行并做基础去噪（清理空行、收缩空白、裁剪超长单元格、移除全空列）；若全部工作表都为空或仅含样式/图表对象，则返回显式空表错误；当前 `.xls` 仍未支持。
31. **PPT 轻量预览第一版** — `read_file_content` 现已支持 `.pptx`：优先通过 PowerPoint COM 导出前 `L1/L2/L3 = 1/2/3` 页幻灯片截图，并复用现有图片多模态摘要链路；若环境缺少 `pywin32` 或 COM 导出失败，则退回 `python-pptx` 提取前几页文字内容；若两条路径都不可用则返回显式错误。
32. **独立 RAG 检索链路第一版** — 新增 `rag/` 模块与 `main_rag.py`，可对预注册知识库目录（当前默认 `study -> C:\Users\Flora\Desktop\LM Study`）执行原文抽取、切块、基于旁路 manifest 的文件级增量更新、ChromaDB 向量写入、chunk 检索、chunk rerank、file 聚合，并通过 `tools/search_knowledge.py` 预留后续接入主 Agent 的工具接口；当前 `file_score` 以 `best_chunk_score` 为主，并返回证据 chunk 摘要。
33. **RAG Embedding 已切换到 LM Studio** — `rag/embeddings.py` 现支持 `local_hash` 与 `lmstudio` 两种 provider；当前默认通过 `http://100.69.36.118:1234/v1` 调用 `text-embedding-qwen3-embedding-0.6b`，并在 embedding 配置变化时自动重建 Chroma collection，避免旧向量与新查询向量混用。
34. **`weseeker` 环境已完成 RAG 实测** — 已在 `conda weseeker` 环境下完成 `main_rag.py list-kb`、`index --kb study --force`、多组 `search` 查询验证；`LM Study` 目录当前可成功索引 10 个支持文件，共 71 个 chunk，另有 1 个 `.doc` 文件因暂不支持提取而跳过。

### 已实现但为 Mock

- **文件发送** — send_file 仅打印日志到控制台，不实际发送

**注意**：项目当前测试环境已切换到 `conda weseeker`，RAG 与主链路验证均以该环境为准（`conda activate weseeker`）


---

## 五、已知问题与待修复项

1. **文档与实现仍有局部不一致** — 核心文档已同步到当前目录结构，但被 `.gitignore` 排除的 `doc/`、`test/` 目录内说明仍以本地维护为主，后续如调整结构需继续手动核对引用
2. **对话历史无上限** — conversation_history 在内存中无限增长，无时间窗口清理
3. **安全仅靠 Prompt** — security_gate.py 为空壳，没有代码层面的工具白名单/路径校验/注入防御
4. **敏感信息裸露** — sensitive_sanitizer.py 为空壳，文件内容未经脱敏直接发给 LLM API
5. **测试体系仍偏脚本化** — 多数测试以脚本输出和手工观察为主，真实 LLM / Everything 依赖较重，尚未形成稳定的自动化回归套件
6. **多模态链路仍缺少临时产物治理** — 当前图片摘要已增加等比例缩放和标准化编码，但后续接入 PDF/PPT 转图时仍需补充临时图片文件清理与更细粒度的尺寸/质量策略
7. **`.doc` 仍未支持内容提取** — `LM Study` 目录中的 `大模型+多模态学习路线.doc` 当前会被 RAG 索引跳过；如后续需要覆盖旧版 Word 文档，需单独补充 `.doc` 解析能力

---

## 六、待实现功能（按优先级）

| 优先级 | 模块 | 说明 |
|--------|------|------|
| **P0** | tool prompt 动态加载 | 实现调用工具前新开上下文、加载对应 tool_prompt 的机制 |
| **P0** | security_gate.py | 工具白名单校验、危险操作拦截、路径安全检查 |
| **P0** | sensitive_sanitizer.py | 正则脱敏（API Key/密码/Token/私钥/连接串） |
| **P1** | 多格式文件预览 | 完善 `_extract_docx` / `_extract_excel` / `_extract_pptx` 的复杂对象与稳定性支持 |
| **P1** | RAG 主链路接入 | 将 `search_knowledge` 接入主 Agent，并设计与 Everything 的双路协同策略 |
| **P1** | 搜索增强 | file_type 参数、sort_by 排序、分页翻页、搜索会话缓存 |
| **P1** | 修复失效测试 | 更新 test_search.py / test_full_workflow.py / test_preview_full.py |
| **P2** | conversation.py | 1 小时时间窗口、任务生命周期管理、消息清理 |
| **P2** | SQLite 持久化 | db.py + models.py 实现对话历史存储 |
| **P2** | path_resolver.py | 独立路径解析模块（当前内联在 everything_search.py 中） |
| **P3** | 微信接口 | wechat_listener.py + message_parser.py + 真实 send_file |
| **P3** | file_inspector.py | 独立的文件元信息读取模块 |
| **P3** | loguru 日志 | 结构化日志、自动轮转 |

---

## 七、架构设计要点

### LLM 调用流程（当前）

```
用户输入
  → Agent.process_message()
    → LLM 第一轮：system_prompt + history + tool_schemas → 意图识别 + 工具调用决策
    → Agent._run_reasoning_loop()：最多5轮
       - 每轮：执行工具调用 → 回填tool结果
       - 若无tool调用或命中早停条件：结束循环
    → （如果是预览）按结果类型额外调用 _summarize_content() / _summarize_images() → 内容摘要
```

### file_index 机制

- Agent 维护 `candidate_files` 列表，每次搜索后缓存结果
- send_file 和 read_file_content 优先接受 `file_index` 参数（序号 1, 2, 3...）
- Agent 内部将序号转为真实路径，避免 LLM 路径幻觉
- 这是一个经过实践验证的关键设计，解决了 LLM 在多轮对话中编造文件路径的问题

### 近期架构收口

- `Agent` 保持外部行为不变，仅调整内部结构：运行时状态改为 `ReasoningState`，工具调用循环迁移到 `ToolExecutor`
- 文件预览链路拆分为路径解析 / 内容提取 / 响应渲染，降低单函数职责复杂度
- 配置加载统一收口到 `core/config_loader.py`，`llm_router.py` 与 `everything_search.py` 复用同一实现
- 工具注册收口到 `core/entities.py` 中的 `ToolSpec` 列表，再派生 `self.tools` 与 `self.tool_functions`
- 异常恢复区分“长期历史”和“一次性系统纠偏”：空响应错误通过 `ErrorEvent` 记录到 `pending_error_event`，仅对下一轮生效一次
- 暂停原因配置收口到 `PauseEvent`：同时承载 `system_instruction` 与 `default_fallback_msg`，澄清失败时直接返回默认兜底文案，不向用户暴露内部 `[WARNING]` 标记
- 文件夹展开能力通过独立工具实现：`list_folder_contents` 使用 Everything `parent:"..."` 查询直属子项，不复用 `search_files` 的搜索语义；为避免模型误填相对路径，当前仅允许先搜索到文件夹，再用 `folder_index` 展开，展开后的目录项直接替换当前 `candidate_files`
- Prompt 额外示范“文件夹 → 子文件夹 → 目标文件”的逐层定位流程，但要求只有在目标文件夹命中具有高置信度时才继续展开，降低近似命中导致的误钻取风险
- Prompt 与工具结果文案都显式声明“序号只对应最近一组结果”，降低模型把旧候选列表序号误用于新候选列表的风险
- 图片预览摘要新增多模态支路：`read_file_content` 若返回 `images`，则由 `LLMClient.build_multimodal_user_message()` 将本地图片标准化后编码为 data URL，并以 OpenAI-compatible `image_url` 结构发送给 LM Studio 进行总结；标准化阶段会保持原始长宽比，仅做整体缩放，不改变图内物体比例
- PDF 预览已改为“转图后复用图片摘要”：`tools/file_summarizer.py` 使用 PyMuPDF 将前几页渲染为 PNG，`Agent` 统一走 `_summarize_images()`；PDF 取页数与转图倍率都从 `settings.yaml` 读取，避免把 `L1/L2/L3` 和具体页数硬编码耦合在一起
- Prompt 新增“系统目录探索”策略：当用户目标是判断桌面/下载/文档等系统目录下是否存在某类相关内容时，先把系统目录当作入口展开一级结构，再根据真实目录名和文件名决定是否继续展开，降低因文件夹名称未包含语义关键词而漏检的概率

---

## 八、配置说明

settings.yaml 关键配置：

```yaml
llm:
  provider: "lmstudio"           # lmstudio / ollama / cloud
  api_base: "http://100.69.36.118:1234"
  api_key: ""                    # 本地 LLM 可不填
  model: ""                      # LM Studio 可不填
  local:
    timeout: 60                  # 本地模型超时（秒）
    temperature: 0.3
    multimodal:
      image_max_edge:
        image: 2048              # 普通照片/截图最长边（等比例缩放）
        pdf: 2105                # PDF 页面截图最长边（按 2.5x 样例页长边设置）
        ppt: 3072                # PPT 页面截图最长边（优先保字）

preview:
  text:
    depth_chars:
      L1: 2000
      L2: 5000
      L3: 8000
  excel:
    depth_rows:
      L1: 10
      L2: 50
      L3: 100
  pdf:
    depth_pages:
      L1: 1
      L2: 2
      L3: 3
    render_scale: 3.0

everything:
  host: "127.0.0.1"
  port: 8080

paths:                           # {username} 运行时自动替换
  desktop: "C:\\Users\\{username}\\Desktop"
  downloads: "C:\\Users\\{username}\\Downloads"
  documents: "C:\\Users\\{username}\\Documents"

sender:
  target: "文件传输助手"

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
    dimension: 1024
  chunk:
    size: 900
    overlap: 150
  retrieval:
    top_k: 30
    max_chunks_per_file: 3
  knowledge_bases:
    study:
      root_path: "C:\\Users\\Flora\\Desktop\\LM Study"
```

---

## 九、更新日志

| 日期 | Commit | 类型 | 内容 |
|------|--------|------|------|
| 2026-03-03 | `3d1004f`, `4826fc1`, `f1ff399`, `c41945d` | 初始化+重构+功能+Bug 修复 | 完成 MVP 初始提交与目录重组；落地 CLI、Agent 主循环、LLM 客户端、Everything 搜索、文件发送（Mock）、文本类文件预览与搜索过滤；新增 file_index 机制，修复 LLM 幻觉导致的文件路径错误。 |
| 2026-03-04 | `24755be`, `e73b52b` | Prompt 重写+功能+修复+文档 | 新增并切换到 `system_prompt_2.md`，重写 `file_search.md` / `file_peek.md` / `file_send.md` / `chat.md`，新增 `task_background.md`；支持本地 LLM（LM Studio/Ollama）、`--debug` 调试模式、`read_file_content` 的 file_index 防幻觉能力，并统一工具命名。 |
| 2026-03-05 ~ 2026-03-10 | 已归档至 `134a01e` | 功能+重构+Prompt+测试+文档+配置 | 归并记录这段时间的连续未提交开发：完成 Agent 最多 5 轮自动工具推理、重复搜索拦截、低增益/空结果早停与最小澄清；修复 Everything FILETIME 转换、失败回滚、非法工具参数显式报错、文本预览重复读取与本地模型 `<think>` / Markdown 噪声问题；新增 `core/config_loader.py`、`core/reasoning_state.py`、`core/tool_executor.py`、`core/entities.py`、`tools/folder_lister.py`，收口 ToolSpec / ErrorEvent / PauseEvent 配置并支持 `list_folder_contents` 文件夹逐层展开；将摘要 Prompt 下沉到 `tools/file_summarizer.py`，同步收紧 `system_prompt_2.md` 中的首次空搜索、候选序号作用域、预览授权和文件夹连续推进规则；补充并迁移测试脚本到 `test/`，同时重写 `README.md`、`AGENTS.md`、`task_background.md`、`WeSeeker-唯寻_技术大纲.md` 以对齐当前目录结构。 |
| 2026-03-10 | `55d73fc` | 配置+清理+文档 | 移除仓库根目录旧版测试/调试脚本的 git 跟踪，仅保留本地 `test/` 目录中的对应脚本；同步更新 `task_background.md`，补记 `134a01e` 的正式归档记录，并调整当前文档维护状态说明。 |
| 2026-03-11 | 未提交 | 功能+测试+文档+依赖 | 为 `read_file_content` 增加图片文件预览结果协议，接入 `LLMClient` 的多模态图片消息构造与 `Agent` 的图片摘要分支；新增 `test/test_image_preview_multimodal.py`，并引入 `Pillow` 用于图片标准化编码、MPO 兼容和等比例缩放；新增 `settings.yaml` 的多模态图片最长边配置（image=2048、pdf=2105、ppt=3072）；同时补充 `system_prompt_2.md` 的系统目录探索规则，指导模型在“桌面/下载/文档里有没有某类相关文件和文件夹”场景下优先先看一级目录结构；在 conda base 环境下完成编译检查、FakeLLM 测试及真实 LM Studio 图片预览链路验证。 |
| 2026-03-12 | `805f15f` | 功能+文档+依赖 | 实现 PDF 预览第一版：`tools/file_summarizer.py` 使用 PyMuPDF 将 PDF 前几页渲染为 PNG，并复用现有图片多模态摘要链路；新增 `preview.pdf.depth_pages`（L1/L2/L3 默认 1/2/3 页）与 `preview.pdf.render_scale` 配置，实现预览深度和实际取页/渲染倍率解耦；同时将文本/Excel 的深度阈值也迁移到 `settings.yaml -> preview`（文本 2000/5000/8000 字，Excel 10/50/100 行）；为 PDF/PPT 图片摘要增加失败后的自动降采样重试，修复部分高分辨率 PDF 页面在 LM Studio 中 `failed to process image` 的问题；同步更新 `system_prompt_2.md`、`requirements.txt` 与 `task_background.md`。 |
| 2026-03-16 | `4c17655` | 功能+测试+文档+依赖 | 为 `read_file_content` 实现 `.docx` 正文纯文字预览，复用现有文本深度与摘要链路；空白文档或主要由图片/复杂对象组成的 Word 文档返回显式错误；新增 `python-docx` 依赖与 `test/test_docx_preview.py`，并使用 `C:\Users\Flora\Desktop\Blade_det prj\总体设计.docx` 完成 base 环境实测。 |
| 2026-03-16 | `3407e96` | 功能+测试+文档+依赖 | 为 `read_file_content` 实现 `.xlsx` 预览第一版：基于 `openpyxl` 自动选择首个非空工作表，提取前若干非空行并做基础去噪，同时对全空工作簿返回显式错误；新增 `openpyxl` 依赖与 `test/test_xlsx_preview.py`，并使用 `C:\Users\Flora\Desktop\研一\副本支部花名册.xlsx` 完成 base 环境实测。 |
| 2026-03-16 | `f107677` | 功能+文档+依赖 | 为 `read_file_content` 实现 `.pptx` 轻量预览第一版：优先使用 PowerPoint COM 导出前几页截图并复用现有图片摘要链路，若缺少 `pywin32` 或 COM 导出失败则退回 `python-pptx` 文字提取；新增 `pywin32`、`python-pptx` 依赖，并同步更新 prompt、README 与 `task_background.md`；同时在 Agent 与 CLI 退出流程中加入会话级临时目录登记与安全清理。 |
| 2026-03-17 | 未提交 | 功能+配置+文档+依赖 | 新增独立 RAG 检索链路：添加 `rag/` 模块、`main_rag.py`、`tools/search_knowledge.py`、`settings.yaml -> rag` 与 `chromadb` 依赖；实现预注册知识库、文件级增量 manifest、原文抽取、切块、chunk rerank、file 聚合与证据 chunk 摘要返回；初版使用 `local_hash` embedding 打通链路。 |
| 2026-03-18 | 未提交 | 功能+测试+文档+配置 | RAG embedding 接入 LM Studio 的 `text-embedding-qwen3-embedding-0.6b`，`rag/embeddings.py` 新增 `lmstudio` provider，索引在 embedding 配置变化时自动重建 collection；测试环境文档统一切换到 `conda weseeker`，并在 `LM Study` 上完成 extractor 全量检查、`index --force` 与多组 `search` 查询实测，当前 10 个支持文件索引成功、1 个 `.doc` 文件因 `unsupported_extension` 被跳过。 |

---

## 十、参考文档

- **技术大纲**：`WeSeeker-唯寻_技术大纲.md` — 完整的系统设计（789 行），包含架构、函数签名、交互流程示例。注意大纲远超当前实现，约 30-35% 已落地。
- **README.md** — 面向使用者的快速上手指南
- **system_prompt.md（旧版）** — 保留作参考，已被 `config/prompts/system_prompt_2.md` 替代
- **doc/terminal_trace_design_v2.md** — 终端追踪链路的分阶段实施设计文档
- **doc/tool_class_refactor.md** / **doc/tool_class_refactor_plan_zh.md** — Tool 类重构的英文说明与中文计划
