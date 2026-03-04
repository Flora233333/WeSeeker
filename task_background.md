# WeSeeker 唯寻 — 项目任务背景

> 本文件是新会话的上下文载入口，用于快速了解项目现状。请持续维护。
> 最后更新：2026-03-04

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
│   ├── agent.py                       # Agent 主循环（~380行）         ✅ 已实现
│   ├── llm_router.py                  # LLM 客户端封装（~191行）       ✅ 已实现
│   ├── conversation.py                # 上下文管理器                    ❌ 空壳
│   ├── security_gate.py               # 安全指令过滤器                  ❌ 空壳
│   └── sensitive_sanitizer.py         # 敏感信息脱敏器                  ❌ 空壳
├── tools/
│   ├── everything_search.py           # Everything 搜索（~263行）      ✅ 已实现
│   ├── file_sender.py                 # 文件发送（~95行）              ⚠️ Mock 实现
│   ├── file_summarizer.py             # 文件预览（~369行）             ⚠️ 仅文本类
│   ├── file_inspector.py              # 文件元信息                      ❌ 空壳
│   └── path_resolver.py               # 路径智能解析                    ❌ 空壳
├── listeners/
│   ├── wechat_listener.py             # 微信监听                        ❌ 空壳
│   └── message_parser.py              # 消息解析                        ❌ 空壳
├── storage/
│   ├── db.py                          # SQLite 持久化                   ❌ 空壳
│   └── models.py                      # 数据模型                        ❌ 空壳
├── main.py                            # CLI 入口                        ✅ 已实现
├── debug_llm_messages.py              # 调试脚本（追踪 LLM 消息链）
├── test_*.py                          # 测试文件（7个，3个已失效）
├── requirements.txt
├── README.md
├── WeSeeker-唯寻_技术大纲.md          # 技术设计文档（789行，完整蓝图）
└── task_background.md                 # 项目任务背景（新会话载入口）← 本文件
```

---

## 四、当前已实现的功能

### 核心链路（可工作）

1. **CLI 交互** — main.py 提供命令行入口，支持 `--debug` 调试模式、退出/清空命令
2. **Agent 调度** — 用户输入 → LLM 意图识别 → 工具调用 → 结果回传 → 自然语言回复
3. **LLM 多提供商** — 支持 lmstudio / ollama / cloud 三种模式，通过 settings.yaml 中 `provider` 字段切换
4. **文件搜索** — 通过 Everything HTTP API 进行关键词+路径搜索，自动过滤系统垃圾文件（.lnk/.tmp/desktop.ini 等）
5. **文本文件预览** — 支持 .txt/.md/.py/.json/.csv/.log/.yaml 等 25+ 种文本格式，多编码兼容（UTF-8/GBK/GB2312/UTF-16），三级深度 L1/L2/L3
6. **file_index 防幻觉** — 搜索结果缓存在 Agent.candidate_files，LLM 用序号引用文件而非编造路径
7. **LLM 二次摘要** — 文件内容提取后，额外调一次 LLM 生成口语化总结

### 已实现但为 Mock

- **文件发送** — send_file 仅打印日志到控制台，不实际发送

---

## 五、已知问题与待修复项

1. **3 个测试文件已失效**：
   - `test_search.py` — 导入 `tools.search`（已重命名为 `tools.everything_search`）
   - `test_full_workflow.py` — 调用 `agent._execute_preview()`（已重命名为 `_execute_read_file`）
   - `test_preview_full.py` — 同上
2. **system_prompt.md（v1）与实际不符** — 列了 11 个工具但只有 3 个存在，包含 PIN 验证、脱敏等未实现的功能描述。已由 system_prompt_2.md 替代，但代码中 `llm_router.py` 的 `load_system_prompt()` 仍加载旧版
3. **对话历史无上限** — conversation_history 在内存中无限增长，无时间窗口清理
4. **安全仅靠 Prompt** — security_gate.py 为空壳，没有代码层面的工具白名单/路径校验/注入防御
5. **敏感信息裸露** — sensitive_sanitizer.py 为空壳，文件内容未经脱敏直接发给 LLM API
6. **file_summarizer.py 中有废弃 schema** — 底部的 PREVIEW_TOOL_SCHEMA 标记了 DEPRECATED，实际使用 agent.py 中的版本，但未删除

---

## 六、待实现功能（按优先级）

| 优先级 | 模块 | 说明 |
|--------|------|------|
| **P0** | 切换 system_prompt_2.md | 修改 llm_router.py 中 load_system_prompt() 加载新版 prompt |
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
    → Agent._execute_tool_calls() → 执行对应工具函数
    → LLM 第二轮：tool_result 回传 → 生成自然语言回复
    → （如果是预览）LLM 第三轮：_summarize_content() → 内容摘要
```

### LLM 调用流程（计划改造）

```
用户输入
  → LLM 第一轮：system_prompt_2 + history → 意图识别 + 决定调用哪个工具
  → 新开上下文：加载对应 tool_prompt + 相关上下文 → LLM 生成精确的工具参数
  → 执行工具
  → LLM 结果轮：tool_result → 生成用户回复
```

### file_index 机制

- Agent 维护 `candidate_files` 列表，每次搜索后缓存结果
- send_file 和 read_file_content 优先接受 `file_index` 参数（序号 1, 2, 3...）
- Agent 内部将序号转为真实路径，避免 LLM 路径幻觉
- 这是一个经过实践验证的关键设计，解决了 LLM 在多轮对话中编造文件路径的问题

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
| 2026-03-03 | `3d1004f` | 初始化 | MVP 初始提交：CLI 入口、Agent 主循环、LLM 客户端、Everything 搜索、文件发送（Mock）、配置管理 |
| 2026-03-03 | `4826fc1` | 重构 | 按技术大纲重组目录：重命名核心模块（llm_client→llm_router, search→everything_search, sender→file_sender），新增空壳模块（conversation/security_gate/sensitive_sanitizer/listeners/storage 等），建立 prompts 目录结构 |
| 2026-03-03 | `f1ff399` | Bug 修复 | 修复 LLM 幻觉导致文件路径错误：send_file 新增 file_index 参数，LLM 用序号引用文件而非自行拼接路径，从 candidate_files 缓存获取真实路径 |
| 2026-03-03 | `c41945d` | 功能 | 实现文件预览总结：file_summarizer.py 支持文本类文件提取（多编码、三级深度），新增搜索结果过滤（排除 .lnk/.tmp/desktop.ini 等），Agent 集成预览工具 + LLM 摘要，补充 file_peek.md，新增 4 个测试脚本 |
| 2026-03-04 | `e73b52b` | 功能+修复 | 多维度增强：支持本地 LLM（LM Studio/Ollama），新增 --debug 调试模式，System Prompt 新增纯文本输出约束，read_file_content 支持 file_index 防幻觉，统一工具名（file_summarizer→read_file_content） |
| 2026-03-04 | `24755be` | Prompt 重写+文档 | 新增 system_prompt_2.md（修正工具列表/参数/移除未实现功能描述），重写 file_search.md / file_peek.md / file_send.md（完整工具调用指南），重写 chat.md（6 类场景处理），新增 task_background.md（项目任务背景+维护规范） |

---

## 十、参考文档

- **技术大纲**：`WeSeeker-唯寻_技术大纲.md` — 完整的系统设计（789 行），包含架构、函数签名、交互流程示例。注意大纲远超当前实现，约 30-35% 已落地。
- **README.md** — 面向使用者的快速上手指南
- **system_prompt.md（旧版）** — 保留作参考，已被 system_prompt_2.md 替代
- **weseeker_system_prompt.md**（项目根目录上层）— 早期独立版本的系统提示词，与 system_prompt.md 内容近似
