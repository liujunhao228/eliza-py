#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 NER 修复效果"""

from ltp_engine import analyze

test_cases = [
    ("我叫蔡徐坤。", "人名测试"),
    ("他在北京工作。", "地名测试"),
    ("小明在北京大学读书。", "机构名测试"),
    ("张三在上海的阿里巴巴工作。", "多实体测试"),
    ("2023 年一月一日是元旦。", "时间测试"),
]

print("=" * 60)
print("NER 命名实体识别测试")
print("=" * 60)

for text, description in test_cases:
    result = analyze(text)
    entities = [(e.text, e.entity_type.name) for e in result.entities]
    print(f"\n{description}: {text}")
    print(f"  识别实体：{entities if entities else '无'}")

print("\n" + "=" * 60)
