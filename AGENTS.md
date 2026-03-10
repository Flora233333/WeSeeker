# AGENTS.md - WeSeeker 开发指南

本文件为代码代理（agentic coding agents）提供开发规范和运行指南。

---

## 1. 环境要求

- **Python**: 3.8+
- **运行时环境**: conda base 环境 (`conda activate base`)
- **依赖安装**: `pip install -r requirements.txt`
- **Everything**: 需开启 HTTP 服务（默认端口 8080）

---

## 2. 运行命令

### 2.1 启动应用

```bash
# 标准启动
python main.py

# 调试模式（显示工具调用信息）
python main.py --debug
python main.py -d
```

### 2.2 测试运行

```bash
# 使用 conda base 环境运行测试（必需）
conda run --no-capture-output -n base python -m test.test_iterative_tool_loop

# 运行单个测试文件
conda run --no-capture-output -n base python -m test.test_real_fallback_e2e

# 其他常用测试
conda run --no-capture-output -n base python -m test.test_everything_timestamp
conda run --no-capture-output -n base python -m test.test_filter
conda run --no-capture-output -n base python -m test.test_preview
conda run --no-capture-output -n base python -m test.test_search

# 轻量语法检查
python -m compileall core tools test main.py
```

> **注意**: 测试必须在 conda base 环境中运行，因为只有 base 环境安装了项目依赖。

---

## 3. 代码风格指南

### 3.1 项目结构

```
WeSeeker/
├── config/           # 配置文件和 prompts
│   ├── settings.yaml
│   └── prompts/
│       ├── system_prompt.md
│       ├── system_prompt_2.md
│       ├── chat.md
│       └── tool_prompts/
├── core/             # 核心业务逻辑
│   ├── agent.py
│   ├── config_loader.py
│   ├── conversation.py
│   ├── security_gate.py
│   ├── sensitive_sanitizer.py
│   ├── llm_router.py
│   ├── reasoning_state.py
│   ├── tool_executor.py
│   ├── entities.py
│   └── ...
├── tools/            # 工具模块
│   ├── everything_search.py
│   ├── file_inspector.py
│   ├── file_sender.py
│   ├── file_summarizer.py
│   ├── folder_lister.py
│   └── path_resolver.py
├── doc/              # 设计文档与专项说明
├── listeners/        # 消息监听（空壳）
├── storage/          # 持久化（空壳）
├── test/             # 测试与调试脚本
└── main.py           # CLI 入口
```

### 3.2 导入规范

```python
# 标准库
import json
import os
import sys

# 第三方库
from openai import OpenAI
import yaml
import requests

# 本地模块（使用绝对导入）
from core.agent import Agent
from core.entities import ToolSpec
from tools.everything_search import search_files
from tools.file_sender import send_file, SEND_TOOL_SCHEMA
```

- 使用绝对导入避免循环依赖
- 第三方库导入在前，本地模块在后
- 按字母排序同一类别的导入

### 3.3 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| 模块/文件 | 小写下划线 | `everything_search.py`, `llm_router.py` |
| 类名 | 大驼峰 | `class Agent:`, `class LLMClient:` |
| 函数/方法 | 小写下划线 | `def search_files()`, `def _execute_search()` |
| 常量 | 全大写下划线 | `MAX_TOOL_ROUNDS = 5` |
| 私有方法 | 前缀下划线 | `def _build_messages():` |

### 3.4 函数设计

- **单一职责**: 每个函数只做一件事
- **参数控制**: 建议 ≤ 5 个参数；超过 5 个使用配置对象
- **返回值**: 使用字典返回结构化数据，包含 `success` 字段
- **文档字符串**: 简洁描述功能，标注参数和返回值

```python
def search_files(
    keyword: str,
    path: Optional[str] = None,
    max_results: int = 20
) -> List[Dict]:
    """
    使用 Everything 搜索文件

    Args:
        keyword: 搜索关键词
        path: 搜索路径约束（可选）
        max_results: 最大返回结果数

    Returns:
        文件信息列表，每个元素包含 name, path, size, modified
    """
```

### 3.5 类型注解

- 使用类型注解提高代码可读性
- 常用类型: `str`, `int`, `bool`, `List[Dict]`, `Optional[str]`, `Dict[str, Any]`
- 复杂函数必须添加返回类型注解

### 3.6 错误处理

- 使用 try-except 包装可能失败的操作
- 返回结构化错误信息（包含 `success: False` 和 `error` 字段）
- 避免 bare except，捕获具体异常类型

```python
try:
    result = search_files(keyword, path, max_results)
except requests.exceptions.ConnectionError:
    raise Exception("Everything 服务未启动，请确认 Everything 是否在运行")
except Exception as e:
    raise Exception(f"搜索出错: {str(e)}")
```

### 3.7 Tool Schema 定义

工具函数需要定义 JSON Schema 供 LLM Function Calling 使用。当前 `Agent` 内部已通过 `core/entities.py` 中的 `ToolSpec(name, schema, handler)` 统一注册工具，避免分别维护 `self.tools` 和 `self.tool_functions`：

```python
@dataclass
class ToolSpec:
    name: str
    schema: dict
    handler: Callable[..., str]

SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "搜索本地文件...",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "..."},
                ...
            },
            "required": ["keyword"]
        }
    }
}

self.tool_specs = [
    ToolSpec("search_files", SEARCH_TOOL_SCHEMA, self._execute_search),
    ToolSpec("send_file", SEND_TOOL_SCHEMA, self._execute_send),
    ToolSpec("read_file_content", PREVIEW_TOOL_SCHEMA, self._execute_read_file),
]
```

### 3.8 配置管理

- 所有配置放在 `config/settings.yaml`
- 使用 `{username}` 占位符自动替换用户名
- 避免硬编码路径或 API 地址

```yaml
llm:
  provider: "lmstudio"
  api_base: "http://100.69.36.118:1234"

paths:
  desktop: "C:\\Users\\{username}\\Desktop"
```

### 3.9 日志与调试

- 使用 `--debug` 模式输出调试信息
- 打印格式: `[调试] 描述: 内容`
- 避免使用 print 进行生产日志

### 3.10 注释规范

- **不添加任何注释**，除非：
  - 解释复杂的业务逻辑
  - 标注 TODO 或 FIXME
- 代码本身应该是自解释的

---

## 4. 安全原则

1. **运行时只读文件系统**: 产品运行时禁止任何写入、删除、移动操作；开发阶段允许修改项目代码，但不要实现会修改用户文件系统的能力
2. **敏感信息脱敏**: 密码、密钥等需在发送给 LLM 前脱敏
3. **路径安全校验**: 禁止访问系统目录和敏感路径
4. **人在回路**: 发送文件必须经过用户确认

---

## 5. 开发流程

1. 阅读 `task_background.md` 了解项目当前进度
2. 阅读 `WeSeeker-唯寻_技术大纲.md` 了解完整设计
3. 修改代码后更新 `task_background.md` 的相关章节
4. 使用 `conda run --no-capture-output -n base python <test>` 验证
5. 若涉及工具架构重构，可参考 `doc/tool_class_refactor.md` 与 `doc/tool_class_refactor_plan_zh.md`

---

## 6. 关键文件

| 文件 | 作用 |
|------|------|
| `task_background.md` | 项目任务背景和维护日志 |
| `WeSeeker-唯寻_技术大纲.md` | 完整技术设计文档 |
| `config/settings.yaml` | 全局配置 |
| `config/prompts/system_prompt_2.md` | 系统提示词（当前使用） |
| `core/entities.py` | 轻量实体定义（如 ToolSpec、ErrorEvent） |
| `doc/tool_class_refactor.md` | Tool 类重构说明（英文） |
| `doc/tool_class_refactor_plan_zh.md` | Tool 类重构计划（中文） |
