#!/usr/bin/env python3
"""调试脚本 - 测试 LTP 分析和意图匹配"""

from alice.nlp.engines.ltp.engine import LtpEngine
from alice.scripts.yaml_script_engine import YAMLScriptEngine
from pathlib import Path

# 测试 LTP 分析
print("=" * 60)
print("测试 LTP 分析")
print("=" * 60)

engine = LtpEngine()
result = engine.analyze('你认识蔡徐坤吗？')

print(f'Tokens: {result.tokens}')
print(f'Entities: {[(e.text, e.entity_type.value) for e in result.entities]}')
print(f'Syntax dict: {result.syntax.to_dict() if result.syntax else None}')

# 测试意图匹配
print("\n" + "=" * 60)
print("测试意图匹配")
print("=" * 60)

script_file = Path(__file__).parent / "alice" / "scripts" / "demo.yaml"
print(f"脚本文件：{script_file}")

script_engine = YAMLScriptEngine(script_file=str(script_file))

# 构建上下文
semantic_info = {
    'tokens': result.tokens,
    'entities': [(e.entity_type.value, e.text) for e in result.entities],
    'syntax': result.syntax.to_dict() if result.syntax else None,
}

print(f"语义信息：{semantic_info}")

# 匹配意图
match = script_engine.match('你认识蔡徐坤吗？', semantic_info)
print(f"匹配结果：{match}")

if match:
    print(f"匹配意图：{match.name}")
    print(f"优先级：{match.priority}")
    print(f"模板：{match.templates}")
else:
    print("未匹配到任何意图！")
    
# 检查各个意图的条件
print("\n" + "=" * 60)
print("检查各意图条件")
print("=" * 60)

for intent_name, intent in script_engine.intents.items():
    print(f"\n意图：{intent_name}")
    print(f"  条件：{intent.condition}")
    condition_result = script_engine._check_condition(intent, '你认识蔡徐坤吗？', semantic_info)
    print(f"  条件检查结果：{condition_result}")
