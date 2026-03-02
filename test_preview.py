#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试文件预览总结功能
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

from tools.file_summarizer import file_summarizer


def test_text_preview():
    """测试纯文本文件预览"""
    # 使用 system_prompt.md 作为测试文件
    test_file = r"c:\Users\Flora\Desktop\WeSeeker唯寻\WeSeeker\config\prompts\system_prompt.md"

    print("=" * 60)
    print(f"测试文件: {test_file}")
    print("=" * 60)

    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return

    # 测试 L1 深度预览
    print("\n📄 测试 L1 深度预览（默认2000字符）:")
    print("-" * 60)
    result = file_summarizer(test_file, depth="L1")
    print(f"成功: {result['success']}")
    print(f"文件类型: {result['file_type']}")
    print(f"预览方法: {result['preview_method']}")
    if result.get('content'):
        print(f"\n内容预览（前500字符）:\n{result['content'][:500]}...")
    if result.get('metadata'):
        print(f"\n元信息: {result['metadata']}")
    if result.get('error'):
        print(f"错误: {result['error']}")
    print("-" * 60)

    # 测试 L2 深度预览
    print("\n\n📄 测试 L2 深度预览（更多内容）:")
    print("-" * 60)
    result_l2 = file_summarizer(test_file, depth="L2")
    print(f"成功: {result_l2['success']}")
    if result_l2.get('content'):
        print(f"提取字符数: {len(result_l2['content'])}")
        print(f"\n内容预览（前500字符）:\n{result_l2['content'][:500]}...")
    print("-" * 60)


if __name__ == "__main__":
    test_text_preview()
