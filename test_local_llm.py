#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
本地 LLM 连接测试脚本
简单问答测试，验证本地 LLM 服务是否正常工作
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.llm_router import LLMClient, load_config


def test_simple_chat():
    """测试简单对话"""
    print("=" * 50)
    print("🧪 本地 LLM 连接测试")
    print("=" * 50)

    # 加载配置
    config = load_config()
    llm_config = config.get("llm", {})

    print(f"\n📋 当前配置:")
    print(f"  Provider: {llm_config.get('provider', 'auto')}")
    print(f"  API Base: {llm_config.get('api_base', '')}")
    print(f"  Model: {llm_config.get('model', '')}")

    # 初始化客户端
    print("\n🔌 正在连接...")
    try:
        client = LLMClient(config)
        print(f"✅ 连接成功!")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

    # 简单问答测试
    print("\n💬 发送测试消息: '你好，请简单介绍一下自己'")
    print("-" * 50)

    try:
        response = client.chat(
            messages=[
                {"role": "system", "content": "你是文件管家，一个智能文件助手。"},
                {"role": "user", "content": "你好，请简单介绍一下自己"}
            ]
        )

        content = client.get_response_content(response)
        if content:
            print(f"🤖 LLM 回复:\n{content}")
            print("-" * 50)
            print("✅ 测试通过! 本地 LLM 工作正常")
            return True
        else:
            print("⚠️ LLM 返回为空")
            return False

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def test_with_tools():
    """测试工具调用（如果支持）"""
    print("\n" + "=" * 50)
    print("🧪 工具调用测试（可选）")
    print("=" * 50)

    try:
        from tools.everything_search import SEARCH_TOOL_SCHEMA

        client = LLMClient()

        print("\n💬 发送消息: '帮我找一下桌面上的文档'（应触发搜索工具）")
        print("-" * 50)

        response = client.chat(
            messages=[
                {"role": "system", "content": "你是文件管家，帮助用户搜索文件。"},
                {"role": "user", "content": "帮我找一下桌面上的文档"}
            ],
            tools=[SEARCH_TOOL_SCHEMA]
        )

        tool_calls = client.get_tool_calls(response)
        if tool_calls:
            print(f"✅ 工具调用正常!")
            for tc in tool_calls:
                print(f"  调用: {tc.function.name}")
                print(f"  参数: {tc.function.arguments}")
        else:
            content = client.get_response_content(response)
            print(f"📝 普通回复:\n{content}")
            print("\n⚠️ 未触发工具调用（可能是模型不支持 function calling）")

    except Exception as e:
        print(f"❌ 工具测试失败: {e}")


def interactive_mode():
    """交互模式"""
    print("\n" + "=" * 50)
    print("💬 交互测试模式（输入 'quit' 退出）")
    print("=" * 50)

    try:
        client = LLMClient()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return

    history = []

    while True:
        try:
            user_input = input("\n👤 你: ").strip()
            if user_input.lower() in ["quit", "exit", "q", "退出"]:
                print("👋 再见!")
                break
            if not user_input:
                continue

            history.append({"role": "user", "content": user_input})

            print("🤖 LLM: ", end="", flush=True)
            response = client.chat(messages=history)
            content = client.get_response_content(response)

            if content:
                print(content)
                history.append({"role": "assistant", "content": content})
            else:
                print("(无回复)")

        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试本地 LLM 连接")
    parser.add_argument("--interactive", "-i", action="store_true", help="进入交互模式")
    parser.add_argument("--tools", "-t", action="store_true", help="测试工具调用")
    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    else:
        success = test_simple_chat()
        if args.tools:
            test_with_tools()

        if not success:
            sys.exit(1)
