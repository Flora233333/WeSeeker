# WeSeeker-唯寻_技术大纲

## 一、系统概述

### 1.1 项目简介

WeSeeker 唯寻 是一个运行在 Windows PC 端的智能文件管理 Agent，该 Agent 监听聊天软件消息（如飞书，微信，WhatsApp 等） 基于 LLM API 通过用户的自然语言来理解用户的文件需求。在本地文件系统中智能搜索，精准定位文件，返回搜索结果，可通过询问式对话来定位用户模糊的文件，在用户确认后通过聊天软件界面将文件发送给用户，以安全、高效地方式完成文件传输。

### 1.2 核心功能特性

| 特性               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **模糊匹配**       | 理解同义词、缩写、拼音、错别字，<br />理解类型别名映射如"表格"→xlsx、"幻灯片"→pptx ，以及搜索无结果时的自动关键词变换重试策略 |
| **自然语言理解**   | 解析模糊描述、口语化表达、不完整句子，可理解识别"那个"、"刚才"、"最新的"等指代词 |
| **智能文件推理**   | 基于上下文、时间线索、文件类型多维度匹配，多结果排序展示     |
| **内容预览确认**   | PPT截图、PDF摘要、Excel生成预览图/总结，避免发错文件，知晓何时调用工具完成预览 |
| **路径智能映射**   | 理解"桌面上的""下载里的""D盘的"等位置描述，自动映射到实际系统路径 |
| **人机协作确认**   | 不确定时系统主动询问，提供智能选项（动态意图识别）           |
| **上下文窗口管理** | 时间窗口（1h）+ 任务生命周期管理，任务完成即清理             |
| **反思与可信控制** | 每轮输出基于确定性证据做出的反思并决策；<br />若证据不足则降级为澄清问题/扩大范围/展示候选，禁止编造任何文件与路径 |
| **模块化工具体系** | 采用 System Prompt + Function Calling 模式，LLM 根据对话上下文自主选择工具调用；<br />工具函数按职责分离为独立模块（搜索、预览、发送、安全），便于维护和测试<br />工具的功能和调用名字会在System prompt展示，调用该工具后，会进一步上传工具的具体prompt<br />LLM需根据工具调用prompt，正确的使用工具，填写参数（此举是为了防止上下文过长使得LLM产生幻觉） |

### 1.3 安全性设计原则

| **原则**             | **说明**                                                     |
| -------------------- | ------------------------------------------------------------ |
| **只读文件系统**     | Agent  对文件系统仅有 读取 和 搜索 权限，严禁任何写入、删除、移动、重命名操作 |
| **最小权限原则**     | LLM  仅能调用白名单内的工具函数，所有工具均为只读型          |
| **人在回路（HITL）** | 所有关键动作（发送文件、查看内容总结）均需用户显式确认       |
| **隐私性**           | 在进行内容查看总结时替换所有敏感信息（如密码/证件号/密钥/Token 替换为 `[REDACTED]`等）<br />即在发送给LLM API前，对于敏感信息需本地脱敏处理 |
| **安全防御**         | 指令注入攻击过滤                                             |

---

## 二、技术选型与依赖

| 组件              | 推荐方案                                                     | 备注                                  |
| ----------------- | ------------------------------------------------------------ | ------------------------------------- |
| **APP消息监听**   | 目前先抽象出来类，分离出整体架构，留出接口                   | -                                     |
| **消息发送**      | 同上，留出接口，基于不同APP来继承                            | 支持文本、图片、文件                  |
| **LLM 后端**      | OpenAI-compatible API（如 Qwen / Kimi / DeepSeek）           | 统一 OpenAI 格式的 SDK 调用，方便切换 |
| **文件搜索**      | Everything SDK（通过 Everything 软件的网络HTTP 端口搜索）    | 毫秒级全盘搜索                        |
| **文件预览/提取** | `python-pptx`、`python-docx`、`PyMuPDF`、`openpyxl`、`Pillow` | 本地解析，提取前面部分段落给API总结   |
| **上下文持久化**  | SQLite来保存每一次任务的本地会话记录<br />在时间窗口内同时任务未结束，则使用同一存储空间<br />如果超出时间窗口或任务结束，则下一次任务将新开存储空间 | 轻量、零部署                          |
| **配置管理**      | YAML / TOML 配置config文件                                   | 可热重载                              |
| **日志记录**      | `loguru`                                                     | 结构化日志、自动轮转                  |

---

## 三、架构设计

每个工具是一个独立模块，拥有自己的 system prompt 片段、可调用的 tools 列表和安全策略。

系统会初始化PC端本机的一些个人信息，如用户名等（以方便后续路径搜索）

系统首先要进行意图识别：

1. 文件查找
2. 文件内容预览
3. 文件发送
4. 聊天对话

### 3.1 目录结构

```
WeSeeker/
├── config/
│   ├── settings.yaml            # 全局配置（API key等）
│   ├── prompts/
│       ├── system_prompt.md     # 基础系统 prompt
│       ├── chat.md              # 闲聊 prompt
│       └── tool_prompts/
│       	├── ile_search.md   # 文件搜索 prompt
│       	├── file_peek.md    # 文件预览 prompt
│       	└── file_send.md    # 文件确认与发送 prompt
├── core/
│   ├── agent.py                 # Agent 主循环 & 调度
│   ├── conversation.py          # 上下文管理器 & 状态机
│   ├── llm_router.py            # LLM 调用封装 & function calling
│   ├── security_gate.py         # 安全指令过滤器
│   └── sensitive_sanitizer.py   # 敏感文件预筛 & 本地脱敏器
│
├── tools/
│   ├── everything_search.py     # Everything SDK 封装
│   ├── file_inspector.py        # 文件元信息读取
│   ├── file_summarizer.py       # 文件内容摘要
│   ├── file_sender.py           # 消息 & 文件发送
│   └── path_resolver.py         # 路径智能解析（如"桌面"→实际路径）
│
├── listeners/
│   ├── wechat_listener.py       # 消息监听主循环
│   └── message_parser.py        # 消息预处理
│
├── storage/
│   ├── db.py                    # SQLite 会话持久化
│   └── models.py                # 数据模型
│
└── main.py                      # 入口
```

### 3.2 各个模式以及工具详细设计

#### 1: file_search（文件搜索）

| **属性** | **内容**                                                     |
| -------- | ------------------------------------------------------------ |
| 触发条件 | 用户消息中包含文件名、文件类型、路径描述（如[桌面上的]，[下载里的]）、[找/发/要/给我]等动词 |
| 依赖工具 | everything_search（Everything SDK 封装）、path_resolver（路径解析器） |
| 调用函数 | search_files(keywords, path, max_results, sort_by)<br />keywords：搜索关键词，可含通配符如 *.pptx（处理后给Everything搜索的）；<br />path：推测搜索的目录路径，如 "C:\\Users\\xxx\\Desktop\\"（处理后给Everything搜索的）；<br />max_results：最大返回结果数；<br />sort_by：排序方式，如时间，大小，首字母； |
| 输出格式 | 匹配文件列表，含：文件名（含后缀）、完整路径、文件大小(>1MB的单位用MB，小于的用KB)、创建时间、最后修改时间 （年月日时分） |
| 交互模式 | 单一匹配 → 直接展示信息等待确认；多匹配 → 展示 Top(max_results) 列表让用户选择（由于排序原因，如果目标数量超过max_results，系统需支持翻页，直到显示完所有的相关文件（此处无需接入LLM直接回复下一页））；零匹配 → 询问用户补充描述，询问对话式收集信息 |
| 路径映射 | [桌面]→ C:\Users\{username}\Desktop；[下载]→  C:\Users\{username}\Downloads；[文档]→ C:\Users\{username}\Documents；其他常用路径可配置 |

---

#### 2: file_preview（文件内容预览）

| **属性**  | **内容**                                                     |
| --------- | ------------------------------------------------------------ |
| 触发条件  | 用户请求查看文件内容、不确定是否为目标文件、要求总结/概要/截图、[看看里面是什么]，[帮我看看内容]等 |
| 依赖工具  | text_reader（读取txt/md/json/csv/py等）、docx_reader、xlsx_reader、pptx_previewer（截取前N页为图片）、pdf_reader |
| 调用函数  | file_summarizer() 详见函数补充说明                           |
| Token控制 | 文本类：默认读取前 2000 字符供 LLM 摘要；PDF：截取前 3 页为图片发送；Excel：读取表头 + 前 10 行；用户可要求「看更多」时逐步加载；图片类直接发送缩略图；其他未包含的文件仅提供元信息 |
| 确认机制  | 批量预览（5个文件内容查看）需先告知用户预计 Token 消耗并获得同意 |
| 输出格式  | 文字摘要（100-300字）或截图图片，附文件基本信息              |

---

#### 3: file_send（文件发送）

| **属性**   | **内容**                                                     |
| ---------- | ------------------------------------------------------------ |
| 触发条件   | 用户确认发送（yes/yep/是的/好的/对/发吧/可以/没错/就是这个/OK 等） |
| 依赖工具   | send_file（调用接口发送文件）                                |
| 调用函数   | send_file() 详见函数补充说明                                 |
| 前置检查   | 文件是否存在且可读、文件大小是否超过发送限制（通常 100MB）、是否为潜在危险文件类型等 |
| 确认语义   | LLM  解析用户回复的语义，而非关键词匹配。支持肯定、否定、犹豫、追问等多种语态 |
| 发送后反馈 | 发送成功/失败的状态反馈，并进行消息回复，失败时给出原因和建议 |

发送前生成文件信息卡片：

```
候选文件确定 → 发送文件信息卡片：
  ┌──────────────────────────────┐
  │ 📄 文件名：报告Q3.pptx       │
  │ 📏 大小：4.2 MB              │
  │ 📅 创建：2025-01-15 14:30    │
  │ ✏️ 修改：2025-02-20 09:15    │
  │ 📂 路径：D:\Work\Reports\    │
  │                              │
  │ 确认发送吗？(是/否)           │
  └──────────────────────────────┘
→ 等待用户确认 → 执行发送 → 反馈结果
```

---

#### 4: chat（通用对话）

| **属性** | **内容**                                                     |
| -------- | ------------------------------------------------------------ |
| 触发条件 | 非文件操作类消息，如闲聊、帮助请求、功能询问                 |
| 调用函数 | chat() 详见函数补充说明                                      |
| 功能     | 回答关于 Agent 功能的问题、引导用户使用正确的命令格式、处理无法理解的消息 |
| 风格     | 友好的管家语气，中文为主，可夹带适当 emoji 增加亲切感，保持管家人设，可以回答一般性问题。同时作为意图不明确时的 fallback |

---

#### 5: security（安全校验）

| **属性** | **内容**                                                     |
| -------- | ------------------------------------------------------------ |
| 触发条件 | 所有涉及文件操作的指令均经过此校验；涉及敏感路径或文件类型时自动检查 |
| 调用函数 | security_check() 详见函数补充说明                            |
| 校验内容 | 指令是否包含危险操作（删除/修改/移动）、路径是否在允许范围内 |
| 敏感路径 | 系统盘 Windows 目录、AppData、Program Files、SSH 密钥目录、密码管理器存储等 |

### 3.3 函数补充说明

#### 一、file_summarizer() —— 文件内容预览与摘要

##### 1.1执行流程

```
LLM (Function Calling)
  │
  │  调用
  ▼
search_files()          ← 暴露给 LLM 的 Tool 函数（参数是 LLM 友好的语义参数）
  │
  │  内部转换：语义参数 → Everything 查询语法
  │  内部调用：安全校验、排除路径过滤、结果缓存
  ▼
EverythingSearch.search()  ← 底层封装（参数是 Everything HTTP API 原生参数）
  │
  │  HTTP 请求
  ▼
Everything HTTP Server (http://localhost:8080)
```

1. LLM 生成的参数是"语义级"的（keyword、文件类型描述），不是 Everything 查询语法
2. 底层需要做查询语法拼接、excluded_paths 过滤、安全校验，这些不应暴露给 LLM
3. 底层可以被其他模块复用（如 get_next_page 翻页时直接调底层，不走 LLM）

| 参数名      | 变更原因                                                     |
| ----------- | ------------------------------------------------------------ |
| `keyword`   | 查询关键词，可含通配符                                       |
| `file_type` | 从 `keyword` 中拆出。原设计让 LLM 把类型写进 keyword（如 `*.pptx`），但实测 LLM 经常写错格式（如写成 `.pptx` 或 `pptx文件`）。独立为参数后，代码层统一处理格式 |
| `path`      | 支持中文别名直接传入（如"桌面"），代码层调 path_resolver 解析，不再要求 LLM 自己先调 resolve_path |
| `sort_by`   | 对Everything HTTP API搜索结果的排序方式，如时间，大小，首字母； |

### 1.2 函数实现说明

```python
def search_files(
    keyword: str,
    file_type: str = "",
    path: str = "",
    max_results: int = 10,
    sort_by: str = "date_modified",
) -> dict:
    """
    LLM Tool 函数：搜索本地文件。
    
    本函数负责：
    1. 参数预处理（路径解析、类型格式化、查询语法构造）
    2. 调用底层 EverythingSearch
    3. 过滤排除路径
    4. 缓存结果（供翻页使用）
    5. 格式化返回
    
    Returns:
        {
            "success": bool,
            "total_found": int,          # Everything 返回的总匹配数
            "displayed_count": int,      # 本次实际返回的条数
            "has_more": bool,            # 是否还有更多结果（支撑翻页提示）
            "search_session_id": str,    # 搜索会话ID（翻页用）
            "files": [
                {
                    "index": int,            # 序号（从1开始，跨页连续）
                    "name": str,             # 文件名（含后缀）
                    "full_path": str,        # 完整路径
                    "directory": str,        # 所在目录
                    "extension": str,        # 扩展名（如 ".pptx"）
                    "size_bytes": int,       # 原始字节数
                    "size_display": str,     # 人类可读大小（如 "4.2 MB"）
                    "date_created": str,     # 创建时间 "2025-01-15 14:30"
                    "date_modified": str,    # 修改时间 "2025-02-20 09:15"
                },
                ...
            ],
            "query_used": str,           # 实际发给 Everything 的查询串（调试用）
            "error": str | None,
        }
    """
    
    # ═══ 1. 参数预处理 ═══
    
    # 1a. 路径解析：中文别名 → 实际路径
    resolved_path = None
    if path:
        resolved_path, sort_hint = path_resolver.resolve(path)
        if sort_hint and sort_by == "date_modified":
            sort_by = sort_hint  # 如"最近的" → 强制按修改时间排序
    
    # 1b. 文件类型格式化
    ext_filter = ""
    if file_type:
        # 统一处理：去掉点号、去掉空格、分割多类型
        types = [t.strip().lstrip(".") for t in file_type.split(",") if t.strip()]
        if len(types) == 1:
            ext_filter = f"ext:{types[0]}"
        elif len(types) > 1:
            ext_filter = "ext:" + ";".join(types)  # Everything 语法：ext:xlsx;csv
    
    # 1c. 构造 Everything 查询串
    query = _build_everything_query(keyword, ext_filter, resolved_path)
    
    # ═══ 2. 调用底层搜索 ═══
    
    raw_results, total_count = await everything_search.search(
        query=query,
        max_results=max_results + 20,  # 多取一些，因为要过滤 excluded_paths
        sort_by=_map_sort_to_everything(sort_by),
    )
    
    # ═══ 3. 过滤排除路径 ═══
    
    filtered = [r for r in raw_results if not _is_excluded_path(r.full_path)]
    
    # ═══ 4. 截取 + 缓存 ═══
    
    display_results = filtered[:max_results]
    remaining = filtered[max_results:]
    
    session_id = _cache_search_results(
        all_results=filtered,
        displayed_count=len(display_results),
        query=query,
    )
    
    # ═══ 5. 格式化返回 ═══
    
    return {
        "success": True,
        "total_found": total_count,
        "displayed_count": len(display_results),
        "has_more": len(remaining) > 0,
        "search_session_id": session_id,
        "files": [_format_file_result(r, idx + 1) for idx, r in enumerate(display_results)],
        "query_used": query,
        "error": None,
    }
```

### 1.3 查询构造函数（将LLM提取的关键词与位置等转换成 Everything HTTP API 查询语法

```python
def _build_everything_query(keyword: str, ext_filter: str, path: str | None) -> str:
    """
    将 LLM 给的语义参数转换为 Everything 查询语法。
    
    Everything HTTP API 查询语法参考：
    - 关键词直接写，多个词之间是 AND 关系
    - path:"C:\Users\xxx\Desktop\"  路径约束
    - ext:pptx                       扩展名过滤
    - ext:xlsx;csv                   多扩展名用分号
    - *.pptx                         通配符（用户可能直接写）
    - !path:"C:\Windows\"            排除路径（用 ! 前缀）
    
    示例转换：
    用户说"桌面上的报告PPT" 
    → keyword="报告", file_type="pptx", path="桌面"
    → 解析后: path="C:\Users\xxx\Desktop\"
    → 最终查询: 'path:"C:\\Users\\xxx\\Desktop\\" ext:pptx 报告'
    """
    parts = []
    
    # 路径约束
    if path:
        # 确保路径以 \ 结尾
        if not path.endswith("\\"):
            path += "\\"
        parts.append(f'path:"{path}"')
    
    # 扩展名过滤
    if ext_filter:
        parts.append(ext_filter)
    
    # 关键词（如果用户已经写了通配符如 *.pptx，保持原样）
    if keyword:
        # 清理：去掉 LLM 可能添加的引号
        keyword = keyword.strip('"').strip("'")
        parts.append(keyword)
    
    return " ".join(parts)
```

### 1.4 排序映射

```python
def _map_sort_to_everything(sort_by: str) -> int:
    """
    将语义排序参数映射到 Everything HTTP API 的 sort 参数值。
    
    Everything HTTP API sort 参数（数值）：
    1  = Name ascending
    2  = Name descending
    3  = Path ascending
    4  = Path descending
    5  = Size ascending
    6  = Size descending
    7  = Extension ascending
    8  = Extension descending
    9  = Type name ascending  (暂不使用)
    10 = Type name descending (暂不使用)
    11 = Date created ascending
    12 = Date created descending
    13 = Date modified ascending
    14 = Date modified descending
    15 = Attributes ascending  (暂不使用)
    16 = Attributes descending (暂不使用)
    17 = Date recently changed ascending  (暂不使用)
    18 = Date recently changed descending (暂不使用)
    19 = Run count ascending   (暂不使用)
    20 = Run count descending  (暂不使用)
    21 = Date recently run ascending (暂不使用)
    22 = Date recently run descending (暂不使用)
    
    我们只用 descending，因为用户通常要"最新/最大/首字母Z→A"
    """
    mapping = {
        "date_modified": 14,   # 最近修改的在前
        "date_created": 12,    # 最近创建的在前
        "size": 6,             # 最大的在前
        "name": 1,             # 按名称 A→Z
    }
    return mapping.get(sort_by, 14)  # 默认按修改时间降序
```

#### 二、file_summarizer() —— 文件内容预览与摘要

##### 2.1 主函数设计

```python
def file_summarizer(
    file_path: str,           # 文件完整路径
    depth: str = "L1",        # 预览深度: "L1"(默认) / "L2"(详细) / "L3"(全量)
    max_chars: int = 2000,    # 文本类最大读取字符数（L1默认2000，L2→8000，L3→不限）
    max_pages: int = 3,       # PPT/PDF 最大预览页数（L1默认3，L2→6，L3→不限）
    max_rows: int = 10,       # Excel 最大预览行数（L1默认10，L2→30，L3→不限）
) -> dict:
    """
    根据文件类型自动选择预览策略，提取内容并返回结构化结果。
    
    本函数不直接调用 LLM，仅做本地内容提取。
    提取结果返回给 LLM 后，由 LLM 生成口语化摘要回复用户。
    
    Returns:
        {
            "success": bool,
            "file_type": str,           # 识别出的文件类型类别
            "preview_method": str,      # 使用的预览方法
            "content": str | None,      # 提取的文本内容（文本类）
            "images": list[str] | None, # 生成的预览图路径列表（PPT/图片类）
            "metadata": {               # 附加元信息
                "total_pages": int,     # 总页数（PPT/PDF）
                "sheet_names": list,    # Sheet名列表（Excel）
                "word_count": int,      # 总字数估算
                "has_more": bool,       # 是否还有未展示的内容
            },
            "estimated_tokens": int,    # 本次提取预计消耗的 token 数
            "error": str | None,        # 错误信息
        }
    """
```

##### 2.2 内部分支逻辑

```
file_summarizer 接收 file_path
    │
    ├─ 判断文件扩展名 → 路由到对应提取器
    │
    ├─ .txt / .md / .py / .json / .csv / .log / .yaml / .xml / .ini
    │     → _extract_text(file_path, max_chars)
    │     → 读取前 max_chars 个字符，返回原文+LLM总结
    │
    ├─ .docx
    │     → _extract_docx(file_path, max_chars)
    │     → python-docx 提取：标题列表 + 正文前 max_chars 字符
    │     → 读取前 max_chars 个字符，交给 LLM 摘要，返回总结
    │
    ├─ .pptx
    │     → _extract_pptx(file_path, max_pages)
    │     → 生成前 max_pages 页截图（PNG）放入临时目录，发送给LLM总结
    │     → 发送给LLM总结描述，返回图片词描述
    │
    ├─ .xlsx / .xls
    │     → _extract_xlsx(file_path, max_rows)
    │     → openpyxl 提取：所有 sheet 名 + 第一个 sheet 的表头和前 max_rows 行
    │     → 以格式化文本表格形式返回
    │
    ├─ .pdf
    │     → _extract_pdf(file_path, max_pages, max_chars)
    │     → PyMuPDF 提取前 max_pages 页文字
    │     → 若文字提取为空（扫描件），则截图返回
    │
    ├─ .jpg / .jpeg / .png / .gif / .bmp / .webp
    │     → _extract_image(file_path)
    │     → 生成缩略图（长边不超过 800px），返回 images=[缩略图路径]
    │     → content 为空（图片无需文字摘要）
    │
    └─ 其他（.exe / .zip / .dll / 未知）
          → 返回 success=True, content=None, preview_method="metadata_only"
          → 仅提供文件元信息，不尝试读取内容
```

##### 2.3 预览深度等级对照

| 深度 | 触发方式                       | 文本类 max_chars | PPT/PDF max_pages | Excel max_rows | 需确认 |
| ---- | ------------------------------ | ---------------- | ------------------ | -------------- | ------ |
| L1   | 默认                           | 2000             | 3                  | 10             | 否     |
| L2   | 用户说"详细看看"/"多看点"      | 8000             | 6                  | 30             | 否     |
| L3   | 用户说"全部内容"/"完整的"      | 不限制           | 全部               | 全部           | **是** |

> L3 需先告知用户预计 token 消耗，获得确认后再执行。

#### 三、send_file() —— 文件发送

##### 3.1 主函数设计

```python
def send_file(
    file_path: str,            # 文件完整路径
    target_chat: str = None,   # 发送目标聊天窗口（默认从config读取，如"文件传输助手"）
) -> dict:
    """
    通过消息接口发送文件到指定聊天窗口。
    
    注意：此函数只负责"执行发送"这个动作本身。
    确认流程（展示文件卡片、等待用户确认）由 Agent 调度层 + LLM 协作完成，
    不在本函数内处理。
    
    前置条件（由调用方在调用前检查）：
    - 用户已明确确认发送意图
    - 文件路径已通过 security_check 校验
    
    Returns:
        {
            "success": bool,
            "file_path": str,          # 发送的文件路径
            "file_name": str,          # 文件名
            "file_size": int,          # 文件大小(bytes)
            "send_duration_ms": int,   # 发送耗时(毫秒)
            "error": str | None,       # 失败原因
            "error_code": str | None,  # 错误码，用于 LLM 给出针对性建议
        }
    
    错误码定义：
        "FILE_NOT_FOUND"      - 文件不存在或已被移动
        "FILE_TOO_LARGE"      - 超过发送大小限制（默认100MB）
        "FILE_LOCKED"         - 文件被其他程序占用，无法读取
        "CHAT_NOT_FOUND"      - 找不到目标聊天窗口
        "SEND_TIMEOUT"        - 发送超时（大文件场景）
        "APP_NOT_RUNNING"     - 消息APP未运行
        "UNKNOWN_ERROR"       - 未知错误
    """
```

##### 3.2 内部执行流程

```
send_file 接收 file_path
    │
    ├─ ① 前置校验
    │     ├─ 文件是否存在 → 不存在返回 FILE_NOT_FOUND
    │     ├─ 文件大小是否超限 → 超过 100MB 返回 FILE_TOO_LARGE
    │     ├─ 文件是否可读（尝试 open） → 被锁定返回 FILE_LOCKED
    │     └─ 消息APP是否在运行 → 未运行返回 APP_NOT_RUNNING
    │
    ├─ ② 定位聊天窗口
    │     └─ 通过消息接口找到 target_chat 窗口 → 找不到返回 CHAT_NOT_FOUND
    │
    ├─ ③ 执行发送
    │     ├─ 调用消息接口的 SendFiles(file_path) 
    │     ├─ 设置超时（根据文件大小动态计算，最低30秒，每10MB加15秒）
    │     └─ 超时返回 SEND_TIMEOUT
    │
    └─ ④ 返回结果
          └─ 记录发送耗时，返回 success=True
```

#### 四、chat() —— 通用对话

##### 4.1 主函数设计

```python
def chat(
    user_message: str,         # 用户原始消息
    conversation_context: list # 当前对话上下文（时间窗口内的历史消息）
) -> dict:
    """
    通用对话处理。当 LLM 意图识别判定用户消息不属于文件操作时，
    走此函数进行对话回复。
    
    实际上 chat 模式不是一个"工具函数"，而是 LLM 的直接回复模式。
    当意图识别为"聊天"时，不调用任何 tool，LLM 直接生成文本回复。
    
    此处定义的是 chat 模式下的行为约束和 prompt 加载逻辑：
    
    行为约束：
    1. 保持文件管家的人设，不脱离角色
    2. 可以回答一般性知识问题，但会适时引导回文件管理主题
    3. 对于明显超出能力范围的请求（如写代码、翻译长文），
       礼貌说明自己的定位并建议使用其他工具
    4. 用户问"你能做什么"时，列出核心功能
    5. 对话风格：简洁、友好、带管家语气
    
    Returns:
        {
            "response_text": str,       # LLM 生成的回复文本
            "suggested_actions": list,  # 可选的建议操作提示
            "intent_confidence": float, # 意图识别置信度（用于调试）
        }
    """
```

##### 4.2 chat 模式典型场景处理

| 场景 | 用户输入示例 | 期望行为 |
| --- | --- | --- |
| 功能询问 | "你能干什么" / "帮助" | 列出核心功能：搜索、预览、发送 |
| 闲聊 | "你好" / "今天天气怎么样" | 简短友好回应，轻度引导回主题 |
| 超范围请求 | "帮我写一篇作文" | 说明定位，建议使用其他工具 |
| 模糊意图 | "那个文件" / "刚才的" | 结合上下文尝试理解，若有候选文件则确认；无上下文则追问 |
| 反馈/抱怨 | "找错了" / "不是这个" | 道歉并引导用户补充描述，重新搜索 |

#### 五、security_check() —— 安全校验

##### 5.1 主函数设计

```python
def security_check(
    action: str,               # 要执行的操作类型: "read" | "preview" | "send" | "search"
    file_path: str = None,     # 涉及的文件路径（search 时可为 None）
    tool_name: str = None,     # LLM 请求调用的工具名
    tool_params: dict = None,  # LLM 请求的工具参数
) -> dict:
    """
    统一安全校验入口。所有文件操作在执行前必须通过此检查。
    
    校验链（按顺序执行，任一失败即拒绝）：
    1. 工具白名单校验 —— tool_name 是否在允许列表中
    2. 危险操作拦截 —— 参数中是否含 delete/modify/execute 等危险词
    3. 路径安全校验 —— file_path 是否在允许访问范围内，是否含路径穿越
    4. 敏感文件预筛 —— 扩展名/文件名/目录是否命中敏感规则
    5. 注入攻击检测 —— 用户原始消息是否含注入特征（此项在 Agent 层做，不在此函数）
    
    Returns:
        {
            "allowed": bool,           # 是否允许执行
            "reason": str | None,      # 拒绝原因（allowed=False 时）
            "requires_confirmation": bool,  # 是否需要用户额外确认
            "requires_sanitization": bool,  # 是否需要内容脱敏后再送 LLM
            "sensitivity_level": str,  # "normal" | "sensitive" | "high_sensitive"
            "warning_message": str | None,  # 需要提醒用户的信息
        }
    """
```

##### 5.2 校验链详细逻辑

```
security_check 接收 action, file_path, tool_name, tool_params
    │
    ├─ ① 工具白名单校验
    │     ├─ 允许的工具: search_files, get_file_info, file_summarizer,
    │     │   send_file, send_message, send_image, chat
    │     └─ tool_name 不在白名单 → allowed=False, reason="未授权的工具调用"
    │
    ├─ ② 危险操作词检测
    │     ├─ 扫描 tool_params 的所有值（递归，包括嵌套）
    │     ├─ 禁止词: delete, remove, rm, del, move, rename, mv,
    │     │   write, modify, edit, overwrite, execute, exec, run,
    │     │   cmd, powershell, bash, shell, format, mkfs
    │     └─ 命中 → allowed=False, reason="检测到禁止操作: {词}"（检测到后系统直接注入安全prompt）
    │
    ├─ ③ 路径安全校验（仅当 file_path 不为 None 时）
    │     ├─ 路径规范化：resolve() 消除 ../ ./ 等
    │     ├─ 符号链接解析：若是 symlink，解析真实路径后再校验
    │     ├─ 白名单目录校验：是否在 allowed_roots 配置的目录下
    │     │     allowed_roots 默认: Desktop, Documents, Downloads, Pictures 及用户自定义盘
    │     ├─ 黑名单路径拦截:
    │     │     C:\Windows\, C:\Program Files\, C:\ProgramData\,
    │     │     $Recycle.Bin, .git, node_modules
    │     └─ 路径穿越检测：参数中含 ".." → 拒绝（检测到后系统直接注入安全prompt）
    │
    ├─ ④ 敏感文件预筛（仅当 action 为 "read" 或 "preview" 时）
    │     ├─ 高风险扩展名: .pem, .key, .env, .pfx, .credential, .htpasswd, .netrc
    │     ├─ 敏感文件名关键词: password, secret, credential, api_key, 密码, 密钥
    │     ├─ 敏感目录: .ssh, .aws, .gnupg, AppData\*\Credential*
    │     ├─ 命中任一 → sensitivity_level="sensitive", requires_sanitization=True
    │     └─ 提示用户："这个文件可能包含敏感信息，已自动隐藏处理"（（检测到后系统直接注入安全prompt））
    │
    └─ ⑤ 返回校验结果
```

**脱敏效果示例：**

```
原始文件内容（本地读取，绝不外送）：
┌──────────────────────────────────────────────────────┐
│ # config.yaml                                        │
│ database:                                            │
│   host: 192.168.1.100                                │
│   password: Sup3r$ecret!2025                         │
│ api:                                                 │
│   openai_key: sk-proj-abc123def456ghi789xyz          │
│   secret: my-very-secret-value-1234567890            │
└──────────────────────────────────────────────────────┘

脱敏后内容（这份才会发送到 LLM API）：
┌──────────────────────────────────────────────────────┐
│ # config.yaml                                        │
│ database:                                            │
│   host: 192.168.1.100                                │
│   password: [REDACTED:password]                      │
│ api:                                                 │
│   openai_key: [REDACTED:api_key]                     │
│   secret: [REDACTED:secret]                          │
└──────────────────────────────────────────────────────┘

LLM 看到脱敏内容后仍然能理解文件结构，可以回复用户：
"这是一个配置文件，包含数据库连接和 API 密钥配置，其中有 3 处敏感信息已隐藏。"
```

---

##  四、典型交互流程示例

### 场景 1：精确查找并发送

```
👤 用户：把桌面上的项目报告发给我

🤖 管家：[调用 search_files: keyword="项目报告", path="Desktop"]
         找到了这个文件：
         
         📄 文件名：项目报告_2025Q1.pptx
         📏 大小：4.2 MB
         📅 创建：2025-01-15 14:30
         ✏️ 修改：2025-02-20 09:15
         
         要发给你吗？

👤 用户：嗯发吧

🤖 管家：[调用 send_file] 
         发好啦～还需要什么？
```

### 场景 2：模糊搜索 + 预览确认

```
👤 用户：帮我找一下上周做的那个数据分析的文件

🤖 管家：[调用 search_files: keyword="数据分析", sort="date_modified"]
         找到 3 个相关文件：
         1. 数据分析报告_v2.xlsx — 2.1MB — 2月18日修改
         2. 用户数据分析.ipynb — 156KB — 2月17日修改  
         3. Q4数据分析.docx — 890KB — 2月14日修改
         
         你要的是哪个呀？

👤 用户：不太确定，第一个是什么内容？

🤖 管家：[调用 file_summarizer: "数据分析报告_v2.xlsx"]
         这个 Excel 有 3 个 sheet：
         - "销售数据"：包含1-3月的销售额、环比增长率等
         - "用户画像"：用户年龄分布、地域统计
         - "趋势图表"：几个图表
         
         看着像是你要的吗？

👤 用户：对对就是这个

🤖 管家：📄 数据分析报告_v2.xlsx — 2.1MB — 2月18日修改
         确认发送？

👤 用户：yep

🤖 管家：[发送文件] 搞定～
```

### 场景 3：批量查看确认

```
👤 用户：我记得做了好几个版本的设计稿，帮我找找

🤖 管家：[搜索] 找到 5 个包含"设计稿"的文件，
         需要我查看一下这些文件内容帮你区分吗？
         大概会多用一点额度（约 5000 tokens）。

👤 用户：行，帮我看看

🤖 管家：[逐个预览，返回摘要]
         看完了，给你整理一下：
         1. 设计稿_v1.pdf — 首版方案，主色蓝色系，12页
         2. 设计稿_v2.pdf — 改了配色，换成绿色系，15页
         3. 设计稿_final.pdf — 终稿，加了动画效果，18页
         4. 设计稿_客户反馈版.pdf — 根据反馈改的，标注了修改处
         5. 设计稿_备份.pdf — 和v2内容一样，应该是备份
         
         你需要哪个（些）？

👤 用户：把 final 和反馈版都发给我

🤖 管家：好的，两个文件：
         📄 设计稿_final.pptx — 5.8MB
         📄 设计稿_客户反馈版.pptx — 6.1MB
         共 11.9MB，确认发送？

👤 用户：发！

🤖 管家：[send_file 逐个发送] 两个文件都发好了～
```

