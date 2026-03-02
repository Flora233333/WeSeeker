#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WeSeeker MVP 测试脚本
测试各种搜索场景
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.search import search_files, format_file_size

def test_search():
    """测试搜索功能"""
    print("=" * 60)
    print("测试 Everything 搜索功能")
    print("=" * 60)

    # 测试用例
    test_cases = [
        ("打卡", None, "精确关键词搜索"),
        ("打卡.txt", None, "带后缀精确搜索"),
        ("打卡", "desktop", "指定桌面路径搜索"),
        ("打卡", "桌面", "中文路径别名搜索"),
    ]

    for keyword, path, desc in test_cases:
        print(f"\n>>> 测试: {desc}")
        print(f"    关键词: {keyword}, 路径: {path}")
        print("-" * 40)

        try:
            results = search_files(keyword, path, max_results=5)
            if results:
                print(f"    找到 {len(results)} 个结果:")
                for i, f in enumerate(results, 1):
                    print(f"      {i}. {f['name']}")
                    print(f"         路径: {f['path']}")
                    print(f"         大小: {format_file_size(f['size'])}")
                    print(f"         修改: {f['modified']}")
            else:
                print("    未找到结果")
        except Exception as e:
            print(f"    错误: {e}")

    print("\n" + "=" * 60)
    print("搜索测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_search()