# WeSeeker 唯寻 — 项目任务背景

> 本文件是新会话的上下文载入口，用于快速了解项目现状。请持续维护。
> 最后更新：2026-03-10

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
| 配置管理 | PyYAML（config/settings.yaml） | 使用中 |
| 文件预览 | python-pptx / python-docx / PyMuPDF / openpyxl / Pillow | 未引入 |
| 日志 | loguru | 未引入 |
| 数据持久化 | SQLite | 未引入 |
| 消息监听 | 微信/飞书接口 | 未引入 |

当前 requirements.txt 仅有 3 个依赖：`openai`, `requests`, `pyyaml`

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
│   ├── file_summarizer.py             # 文件预览（~369行）             ⚠️ 仅文本类
│   ├── folder_lister.py               # 文件夹直属内容列举              ✅ 已实现（新增）
│   ├── file_inspector.py              # 文件元信息                      ❌ 空壳
│   └── path_resolver.py               # 路径智能解析                    ❌ 空壳
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
├── test/
│   ├── test_iterative_tool_loop.py    # 连续工具推理与默认兜底文案测试（FakeLLM）
│   ├── test_real_fallback_e2e.py      # 真实 LLM API 澄清/兜底 E2E（可注入澄清失败）
│   ├── test_list_folder_contents.py   # 文件夹展开与目录候选复用测试
│   ├── test_empty_response_event.py   # 空响应事件一次性注入测试
│   ├── test_everything_timestamp.py   # FILETIME 时间戳转换测试
│   ├── test_search_combinations.py    # Everything 组合关键词搜索观察脚本
│   ├── test_filter.py                 # 文件过滤规则测试
│   ├── test_preview.py                # 文本预览基础测试脚本
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

### 已实现但为 Mock

- **文件发送** — send_file 仅打印日志到控制台，不实际发送

**注意**：项目测试时需要在conda的base环境中进行，只有base环境才安装了项目所需依赖（conda activate base）


---

## 五、已知问题与待修复项

1. **文档与实现仍有局部不一致** — 部分说明文档曾使用旧文件路径；当前已同步核心文档，但其他散落文档仍需持续核对 `doc/`、`test/` 等新目录引用
2. **对话历史无上限** — conversation_history 在内存中无限增长，无时间窗口清理
3. **安全仅靠 Prompt** — security_gate.py 为空壳，没有代码层面的工具白名单/路径校验/注入防御
4. **敏感信息裸露** — sensitive_sanitizer.py 为空壳，文件内容未经脱敏直接发给 LLM API
5. **file_summarizer.py 中有废弃 schema** — 底部的 PREVIEW_TOOL_SCHEMA 标记了 DEPRECATED，实际使用 agent.py 中的版本，但未删除

---

## 六、待实现功能（按优先级）

| 优先级 | 模块 | 说明 |
|--------|------|------|
| **P0** | tool prompt 动态加载 | 实现调用工具前新开上下文、加载对应 tool_prompt 的机制 |
| **P0** | security_gate.py | 工具白名单校验、危险操作拦截、路径安全检查 |
| **P0** | sensitive_sanitizer.py | 正则脱敏（API Key/密码/Token/私钥/连接串） |
| **P1** | 多格式文件预览 | 实现 _extract_docx / _extract_excel / _extract_pptx / _extract_pdf |
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
    → （如果是预览）LLM 额外调用 _summarize_content() → 内容摘要
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

everything:
  host: "127.0.0.1"
  port: 8080

paths:                           # {username} 运行时自动替换
  desktop: "C:\\Users\\{username}\\Desktop"
  downloads: "C:\\Users\\{username}\\Downloads"
  documents: "C:\\Users\\{username}\\Documents"

sender:
  target: "文件传输助手"
```

---

## 九、更新日志

| 日期 | Commit | 类型 | 内容 |
|------|--------|------|------|
| 2026-03-03 | `3d1004f`, `4826fc1`, `f1ff399`, `c41945d` | 初始化+重构+功能+Bug 修复 | 完成 MVP 初始提交与目录重组；落地 CLI、Agent 主循环、LLM 客户端、Everything 搜索、文件发送（Mock）、文本类文件预览与搜索过滤；新增 file_index 机制，修复 LLM 幻觉导致的文件路径错误。 |
| 2026-03-04 | `24755be`, `e73b52b` | Prompt 重写+功能+修复+文档 | 新增并切换到 `system_prompt_2.md`，重写 `file_search.md` / `file_peek.md` / `file_send.md` / `chat.md`，新增 `task_background.md`；支持本地 LLM（LM Studio/Ollama）、`--debug` 调试模式、`read_file_content` 的 file_index 防幻觉能力，并统一工具命名。 |
| 2026-03-05 | 未提交 | 功能+Bug 修复+测试+文档 | 实现 Agent 最多 5 轮自动工具推理、重复搜索拦截、低增益/空结果早停与最小澄清追问；新增 `test_iterative_tool_loop.py` 与 `test_real_fallback_e2e.py`，补充 `<iterative_tool_reasoning>` prompt 规则并更新背景文档；当时的澄清失败兜底采用 `[WARNING]` 前缀方案。 |
| 2026-03-06 | 未提交 | Bug 修复+重构+测试+文档 | 修复 Everything FILETIME 时间转换；新增 `core/config_loader.py`、`core/reasoning_state.py`、`core/tool_executor.py`，完成不改功能的可维护性重构；在 `base` 环境跑通 `test_iterative_tool_loop.py`、`test_everything_timestamp.py`、`test_real_fallback_e2e.py`。 |
| 2026-03-07 | 未提交 | 文档+Bug 修复+重构+测试 | 新增 `terminal_trace_design_v2.md`；修复失败 turn 回滚、非法工具参数显式报错、Markdown 保守清理等健壮性问题；移除运行时代码中的 `sys.path` 注入、修复文本预览二次整文件读取，并将全部测试脚本迁移到 `test/` 目录后完成多项回归验证与 `compileall` 检查。 |
| 2026-03-08 | 未提交 | 重构+Bug 修复+测试+文档 | 新增 `core/entities.py` 与 `工具类代码重构(用英文).md`，完成 Tool 类重构阶段一并更新 `AGENTS.md`；调整最终回复链路以保留模型原始 Markdown；新增并强化 `test/test_empty_response_event.py`；将 `ToolSpec`、`ErrorEvent`、`PauseEvent` 等配置逐步收口到 `core/entities.py`，并在 `task_background.md` 补充会话协作约定。 |
| 2026-03-09 | 未提交 | 重构+功能+测试+Prompt+文档 | `PauseEvent` 新增 `default_fallback_msg`，澄清失败/空响应兜底文案完全迁入 `core/entities.py`，删除 `Agent._build_warning_fallback()`，并改为直接向用户返回 fallback 文案、不暴露 `[WARNING]` 前缀；收紧 `system_prompt_2.md` 的自动搜索规则，要求第一次 `search_files` 无结果就引导用户补充线索，并补充“文件夹 → 子文件夹 → 目标文件”的连续推进示例；新增基于 Everything `parent:"绝对路径"` 的 `list_folder_contents` 工具，支持列出文件夹直属子项并复用 `candidate_files`，且为避免模型误填相对路径，当前强制先 `search_files` 再用 `folder_index` 展开；补充 `test/test_list_folder_contents.py`，在 `base` 环境跑通 `python -m test.test_list_folder_contents` 与 `python -m test.test_iterative_tool_loop`。 |
| 2026-03-10 | 未提交 | 测试+Prompt+文档+重构 | 新增 `test/test_search_combinations.py`，用于人工观察 Everything 在多词组合关键词与不同路径约束下的实际返回结果；并在 Prompt 与搜索/文件夹结果文案中补充“序号只对应最近一组结果”的提示，降低旧序号误用风险；同时将文件内容总结的 Prompt 组装从 `core/agent.py` 下沉到 `tools/file_summarizer.py`，由工具模块统一维护摘要提示模板；进一步收紧文件夹连续推进规则，要求只有在搜索结果对目标文件夹是唯一且高置信度命中时才允许继续展开；并补充“读取文件内容需要用户显式同意，单纯确认序号不等于允许预览”的 Prompt 约束；同步更新 `task_background.md`。 |
| 2026-03-10 | 未提交 | 文档 | 按当前实际目录重写 `README.md`、`AGENTS.md`、`task_background.md`、`WeSeeker-唯寻_技术大纲.md` 的结构说明，统一 `doc/`、`test/`、`test/debug_llm_messages.py`、`doc/tool_class_refactor*.md` 等新路径，并为主要文件/文件夹补充用途描述。 |

---

## 十、参考文档

- **技术大纲**：`WeSeeker-唯寻_技术大纲.md` — 完整的系统设计（789 行），包含架构、函数签名、交互流程示例。注意大纲远超当前实现，约 30-35% 已落地。
- **README.md** — 面向使用者的快速上手指南
- **system_prompt.md（旧版）** — 保留作参考，已被 `config/prompts/system_prompt_2.md` 替代
- **doc/terminal_trace_design_v2.md** — 终端追踪链路的分阶段实施设计文档
- **doc/tool_class_refactor.md** / **doc/tool_class_refactor_plan_zh.md** — Tool 类重构的英文说明与中文计划
