# WeSeeker 唯寻 - 智能文件管家

一个运行在 Windows 电脑上的智能文件助手，通过自然语言帮你搜索和发送文件。

## 功能特性

- **自然语言交互**：用口语化的方式描述文件，无需记住精确文件名
- **毫秒级搜索**：基于 Everything SDK，实现全盘文件快速检索
- **智能路径识别**：自动理解"桌面"、"下载"、"文档"等位置描述
- **微信发送**：搜索确认后，一键发送到微信「文件传输助手」
- **安全可靠**：只读权限，绝不执行删除、修改等危险操作

## 目录结构

```
WeSeeker/
├── config/
│   └── settings.yaml      # 配置文件
├── core/
│   ├── __init__.py
│   ├── agent.py           # Agent 主循环
│   └── llm_client.py      # LLM 客户端封装
├── tools/
│   ├── __init__.py
│   ├── search.py          # Everything 搜索工具
│   └── sender.py          # 文件发送工具
├── main.py                # CLI 入口
├── test_agent.py          # 测试脚本
└── requirements.txt       # 依赖
```

## 快速开始

### 1. 安装依赖

```bash
cd WeSeeker
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/settings.yaml`，填写你的 API Key：

```yaml
llm:
  api_base: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "你的API_KEY"  # 替换为你的通义千问 API Key
  model: "qwen-plus"
```

### 3. 启动 Everything

确保 [Everything](https://www.voidtools.com/) 软件正在运行，并开启 HTTP 服务：

1. 打开 Everything
2. 菜单：工具 → 选项 → HTTP 服务器
3. 勾选"启用 HTTP 服务器"，端口设为 `8080`

### 4. 运行

```bash
python main.py
```

## 使用示例

```
👤 你: 帮我找一下桌面上的打卡文件

🤖 文件管家: 找到 1 个相关文件：
   ① 打卡.txt — 53.3 KB — 修改于 2025-02-20
   你要哪个？

👤 你: 发给我

🤖 文件管家: 搞定～文件已发送到你的手机微信啦！
```

## 支持的搜索方式

| 输入示例 | 说明 |
|---------|------|
| `帮我找一下桌面上的打卡文件` | 指定路径 + 关键词 |
| `找一下打卡` | 仅关键词，全盘搜索 |
| `搜索打卡.txt` | 带后缀精确搜索 |
| `我想找桌面上有个打卡的文件` | 口语化表达 |

## 配置说明

```yaml
# config/settings.yaml

llm:
  api_base: "https://dashscope.aliyuncs.com/compatible-mode/v1"  # API 地址
  api_key: "YOUR_API_KEY"  # 你的 API Key
  model: "qwen-plus"       # 模型名称

everything:
  host: "127.0.0.1"        # Everything HTTP 服务地址
  port: 8080               # 端口

paths:
  desktop: "C:\\Users\\{username}\\Desktop"
  downloads: "C:\\Users\\{username}\\Downloads"
  documents: "C:\\Users\\{username}\\Documents"

sender:
  target: "文件传输助手"    # 默认发送目标
```

## MVP 功能范围

### 已实现

- [x] 命令行交互入口
- [x] LLM 意图识别 + 工具调用
- [x] Everything 文件搜索
- [x] 文件发送（Mock 实现，打印日志）
- [x] 路径别名映射

### 暂未实现

- [ ] 实际微信发送接口
- [ ] 文件预览功能
- [ ] 敏感文件安全校验
- [ ] 上下文持久化
- [ ] 多平台监听

## 技术栈

- **Python 3.8+**
- **OpenAI SDK**：LLM 调用
- **Everything HTTP API**：文件搜索
- **PyYAML**：配置管理

## 注意事项

1. 确保 Everything 已开启 HTTP 服务
2. API Key 请妥善保管，不要提交到公开仓库
3. 当前发送功能为 Mock 实现，仅打印日志不实际发送

## License

MIT