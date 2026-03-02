#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整功能测试 - 模拟对话流程
测试: 搜索文件 → 预览总结
"""

import sys
import os
import io

# 设置标准输出编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from WeSeeker.core.agent import Agent


def simulate_conversation():
    """模拟完整对话流程"""
    print("=" * 70)
    print("🧪 完整功能测试 - 搜索 + 预览总结")
    print("=" * 70)

    # 初始化 Agent
    try:
        agent = Agent()
        print("\n✅ Agent 初始化成功\n")
    except Exception as e:
        print(f"\n❌ Agent 初始化失败: {e}")
        return

    # 对话步骤 1: 搜索 system_prompt.md 文件
    print("-" * 70)
    print("👤 用户: 帮我找一下 system_prompt.md 文件")
    print("-" * 70)

    response1 = agent.process_message("帮我找一下 system_prompt.md 文件")
    print(f"\n🤖 文件管家: {response1}\n")

    # 对话步骤 2: 预览第3个文件（真正的 md 文件）
    print("-" * 70)
    print("👤 用户: 帮我看看第3个文件的内容，总结一下")
    print("-" * 70)

    # 直接调用预览工具查看原始输出
    print("\n[调试] 直接调用预览工具:")
    preview_result = agent._execute_preview(
        r"C:\Users\Flora\Desktop\WeSeeker唯寻\WeSeeker\config\prompts\system_prompt.md",
        depth="L2"
    )
    print(f"预览结果长度: {len(preview_result)} 字符")
    print(f"预览结果前500字符:\n{preview_result[:500]}...")

    print("\n" + "-" * 70)
    print("通过 Agent 调用:")
    response2 = agent.process_message("帮我看看第3个文件的内容，总结一下")
    print(f"\n🤖 文件管家: {response2}\n")

    print("=" * 70)
    print("✅ 测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    simulate_conversation()
