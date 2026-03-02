#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件预览功能完整测试
测试流程: 搜索文件 → 预览内容 → LLM总结
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

from core.agent import Agent


def test_preview_workflow():
    """测试完整的预览工作流程"""
    print("=" * 70)
    print("🧪 测试文件预览功能")
    print("=" * 70)

    # 初始化 Agent
    try:
        agent = Agent()
        print("\n✅ Agent 初始化成功\n")
    except Exception as e:
        print(f"\n❌ Agent 初始化失败: {e}")
        return

    # 测试文件路径
    test_file = r"c:\Users\Flora\Desktop\WeSeeker唯寻\WeSeeker\config\prompts\system_prompt.md"

    print("-" * 70)
    print(f"📝 测试文件: {test_file}")
    print("-" * 70)

    # 测试 L1 深度预览
    print("\n🔍 测试 L1 深度预览（默认2000字符）:")
    print("-" * 70)
    result = agent._execute_preview(test_file, depth="L1")
    print(result)
    print("-" * 70)

    # 测试 L2 深度预览
    print("\n\n🔍 测试 L2 深度预览（更多内容）:")
    print("-" * 70)
    result_l2 = agent._execute_preview(test_file, depth="L2")
    print(result_l2)
    print("-" * 70)

    print("\n✅ 测试完成!")


if __name__ == "__main__":
    test_preview_workflow()
