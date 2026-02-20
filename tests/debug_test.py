from alice.nlp.sentiment.rule_engine import RuleSentimentEngine

engine = RuleSentimentEngine()

strong_result = engine.analyze("我非常开心")
moderate_result = engine.analyze("比较开心")
weak_result = engine.analyze("有点开心")

print(f"我非常开心: score={strong_result.score}, metadata={strong_result.metadata}")
print(f"  intensity={engine.get_intensity(strong_result)}")

print(f"比较开心：score={moderate_result.score}, metadata={moderate_result.metadata}")
print(f"  intensity={engine.get_intensity(moderate_result)}")

print(f"有点开心：score={weak_result.score}, metadata={weak_result.metadata}")
print(f"  intensity={engine.get_intensity(weak_result)}")
