#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WeSeeker MVP 完整测试
测试各种搜索场景
"""

import sys
import os
import io

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import Agent

def safe_print(text):
    """安全打印，处理编码问题"""
    try:
        print(text)
    except:
        print(text.encode('utf-8', errors='replace').decode('utf-8'))

def test_agent():
    """测试 Agent 完整流程"""
    print("=" * 60)
    print("WeSeeker Agent 多场景测试")
    print("=" * 60)

    # 测试场景列表
    test_scenarios = [
        {
            "name": "场景1: 精确搜索 + 发送",
            "inputs": [
                "帮我找一下桌面上的打卡文件",
                "发给我"
            ]
        },
        {
            "name": "场景2: 模糊搜索（只有关键词）",
            "inputs": [
                "找一下打卡",
                "发第一个"
            ]
        },
        {
            "name": "场景3: 带后缀搜索",
            "inputs": [
                "搜索打卡.txt",
                "发送"
            ]
        },
        {
            "name": "场景4: 口语化表达",
            "inputs": [
                "我想找桌面上有个打卡的文件",
                "好的，发吧"
            ]
        }
    ]

    for scenario in test_scenarios:
        print(f"\n{'='*60}")
        print(f" {scenario['name']}")
        print("=" * 60)

        # 每个场景使用新的 Agent 实例
        agent = Agent()

        for user_input in scenario['inputs']:
            print(f"\n用户: {user_input}")
            print("-" * 40)

            try:
                response = agent.process_message(user_input)
                # 移除可能导致编码问题的字符
                safe_response = response.replace('✅', '[OK]').replace('❌', '[X]').replace('📄', '[文件]').replace('📏', '[大小]').replace('📅', '[创建]').replace('✏️', '[修改]')
                print(f"文件管家: {safe_response}")
            except Exception as e:
                print(f"错误: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_agent()