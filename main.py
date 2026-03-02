#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WeSeeker MVP - 命令行入口
文件管家 CLI 交互界面
"""

import sys
import os
import io

# 设置标准输出编码为 UTF-8（解决 Windows 控制台中文显示问题）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from WeSeeker.core.agent import Agent


def print_welcome():
    """打印欢迎信息"""
    print("""
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     🔍 欢迎使用文件管家 WeSeeker                      ║
║                                                       ║
║     我可以帮你：                                      ║
║     • 搜索本地文件（通过 Everything）                 ║
║     • 发送文件到微信                                  ║
║                                                       ║
║     输入「退出」或「quit」结束对话                    ║
║     输入「清空」或「clear」清空对话历史               ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
""")


def main():
    """主函数"""
    print_welcome()

    # 初始化 Agent
    try:
        agent = Agent()
        print("✅ Agent 初始化成功\n")
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        print("请检查配置文件 config/settings.yaml 是否正确")
        sys.exit(1)

    # 交互循环
    while True:
        try:
            # 获取用户输入
            user_input = input("👤 你: ").strip()

            # 检查退出命令
            if user_input.lower() in ["退出", "quit", "exit", "q"]:
                print("\n👋 再见！有问题随时找我～")
                break

            # 检查清空命令
            if user_input.lower() in ["清空", "clear", "cls"]:
                agent.clear_history()
                print("🧹 对话历史已清空\n")
                continue

            # 跳过空输入
            if not user_input:
                continue

            # 处理消息
            print("\n🤖 文件管家: ", end="")
            response = agent.process_message(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 出错了: {e}")
            print("请稍后重试\n")


if __name__ == "__main__":
    main()