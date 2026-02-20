#!/usr/bin/env python3
"""测试配置项是否被正确使用"""

from alice.alice_v2 import AliceBot
from alice.config import ENABLE_LOGGING_BY_DEFAULT, ENABLE_LTP_BY_DEFAULT, ENABLE_NER_BY_DEFAULT, NER_USE_LTP_BY_DEFAULT

print("=" * 50)
print("配置文件默认值:")
print(f"  ENABLE_LOGGING_BY_DEFAULT: {ENABLE_LOGGING_BY_DEFAULT}")
print(f"  ENABLE_LTP_BY_DEFAULT: {ENABLE_LTP_BY_DEFAULT}")
print(f"  ENABLE_NER_BY_DEFAULT: {ENABLE_NER_BY_DEFAULT}")
print(f"  NER_USE_LTP_BY_DEFAULT: {NER_USE_LTP_BY_DEFAULT}")

print("\n" + "=" * 50)
print("AliceBot 实例实际使用的值:")
bot = AliceBot()
print(f"  bot.enable_logging: {bot.enable_logging}")
print(f"  bot.dialogue_engine.use_ltp: {bot.dialogue_engine.use_ltp}")
print(f"  bot.dialogue_engine.enable_ner: {bot.dialogue_engine.enable_ner}")
print(f"  bot.dialogue_engine.ner_use_ltp: {bot.dialogue_engine.ner_use_ltp}")

print("\n" + "=" * 50)
print("验证结果:")
assert bot.enable_logging == ENABLE_LOGGING_BY_DEFAULT, "enable_logging 未使用配置值"
assert bot.dialogue_engine.use_ltp == ENABLE_LTP_BY_DEFAULT, "use_ltp 未使用配置值"
assert bot.dialogue_engine.enable_ner == ENABLE_NER_BY_DEFAULT, "enable_ner 未使用配置值"
assert bot.dialogue_engine.ner_use_ltp == NER_USE_LTP_BY_DEFAULT, "ner_use_ltp 未使用配置值"
print("[OK] 所有配置项都被正确使用!")
