#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试文件过滤功能
验证 .lnk 和其他系统文件被正确排除
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

from tools.everything_search import _is_excluded_file


def test_filter():
    """测试文件过滤规则"""
    print("=" * 60)
    print("🧪 文件过滤规则测试")
    print("=" * 60)

    # 测试用例：(文件名, 是否应该被排除)
    test_cases = [
        # 快捷方式
        ("document.lnk", True),
        ("shortcut.LNK", True),
        ("file.lnk", True),

        # 系统文件
        ("Thumbs.db", True),
        ("thumbs.db", True),
        ("desktop.ini", True),
        ("DESKTOP.INI", True),
        (".DS_Store", True),
        ("Folder.jpg", True),
        ("AlbumArtSmall.jpg", True),

        # Office 临时文件
        ("~$document.docx", True),
        ("~$temp_file.xlsx", True),

        # 临时文件
        ("file.tmp", True),
        ("file.temp", True),
        ("file.bak", True),
        ("file.old", True),

        # 正常文件（应该保留）
        ("document.txt", False),
        ("file.md", False),
        ("script.py", False),
        ("data.json", False),
        ("report.docx", False),
        ("table.xlsx", False),
        ("presentation.pptx", False),
        ("document.pdf", False),
        ("image.jpg", False),
        ("photo.png", False),

        # 特殊：名字包含但不等于系统文件的
        ("my_thumbs.db.txt", False),
        ("desktop.ini.bak", True),  # 扩展名是 .bak
        ("not_a_link.lnk.txt", False),
    ]

    print("\n测试结果:\n")
    passed = 0
    failed = 0

    for file_name, should_exclude in test_cases:
        result = _is_excluded_file(file_name)
        status = "✅" if result == should_exclude else "❌"
        expected = "排除" if should_exclude else "保留"
        actual = "排除" if result else "保留"

        if result == should_exclude:
            passed += 1
        else:
            failed += 1

        print(f"{status} {file_name:25} | 期望: {expected:4} | 实际: {actual:4}")

    print("\n" + "-" * 60)
    print(f"总计: {len(test_cases)} 个测试用例")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_filter()
    sys.exit(0 if success else 1)
