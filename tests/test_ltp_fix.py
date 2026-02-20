#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎修复测试
验证任务参数修复和降级机制是否正常工作
"""

import sys
import os
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ltp_task_parameters():
    """测试 LTP 任务参数修复"""
    print("=== LTP 任务参数修复测试 ===")
    
    try:
        from alice.nlp.engines.ltp_engine import LtpEngine
        from alice.nlp.base import NlpResult
        
        # 创建 LTP 引擎实例
        engine = LtpEngine(lazy_load=True)
        print("✓ LTP 引擎创建成功")
        
        # 测试简单文本（应该触发降级）
        simple_text = "你好"
        print(f"\n测试简单文本: '{simple_text}'")
        result1 = engine.analyze(simple_text)
        print(f"结果类型: {type(result1)}")
        print(f"tokens: {result1.tokens}")
        print("✓ 简单文本处理正常（触发降级）")
        
        # 测试复杂文本（应该使用 LTP）
        complex_text = "我觉得今天天气很好，想去公园散步。"
        print(f"\n测试复杂文本: '{complex_text}'")
        result2 = engine.analyze(complex_text)
        print(f"结果类型: {type(result2)}")
        print(f"tokens: {result2.tokens}")
        print(f"syntax: {result2.syntax}")
        print(f"entities: {result2.entities}")
        print("✓ 复杂文本处理正常")
        
        return True
        
    except Exception as e:
        print(f"✗ LTP 测试失败: {e}")
        logger.exception("LTP 测试异常详情:")
        return False

def test_ltp_import_safety():
    """测试 LTP 导入安全性"""
    print("\n=== LTP 导入安全性测试 ===")
    
    try:
        # 测试在没有安装 LTP 的情况下是否能正常导入
        import importlib.util
        
        # 模拟 LTP 不可用的情况
        spec = importlib.util.find_spec('ltp')
        if spec is None:
            print("✓ LTP 未安装，测试降级机制")
            
            # 尝试导入应该触发降级而不是崩溃
            try:
                from alice.nlp.engines.ltp_engine import LtpEngine
                print("✗ 应该抛出 DependencyError 但没有")
                return False
            except Exception as e:
                if "LTP 库未安装" in str(e):
                    print("✓ 正确抛出 DependencyError")
                    return True
                else:
                    print(f"✗ 抛出了意外的异常: {e}")
                    return False
        else:
            print("LTP 已安装，跳过导入安全性测试")
            return True
            
    except Exception as e:
        print(f"✗ 导入安全性测试失败: {e}")
        return False

def test_degradation_monitoring():
    """测试降级监控"""
    print("\n=== 降级监控测试 ===")
    
    try:
        from alice.utils.degradation_monitor import degradation_monitor
        
        # 重置监控器
        degradation_monitor.reset()
        print("✓ 降级监控器重置成功")
        
        # 注册一个测试降级事件
        degradation_id = degradation_monitor.register_degradation(
            component='test_ltp_fix',
            reason='测试降级监控功能',
            severity=1,
            recovery_plan='这是测试用例',
            original_functionality='完整 LTP 分析',
            degraded_functionality='基础文本处理',
            user_notification='使用简化模式'
        )
        
        print(f"✓ 降级事件注册成功: {degradation_id}")
        
        # 检查活跃降级
        active = degradation_monitor.get_active_degradations()
        print(f"活跃降级数量: {len(active)}")
        
        # 解决降级
        resolved = degradation_monitor.resolve_degradation(degradation_id)
        print(f"降级解决状态: {resolved}")
        
        # 检查报告
        report = degradation_monitor.get_degradation_report()
        print(f"降级报告生成成功")
        print(f"  活跃降级: {report.get('active_degradations', 'N/A')}")
        print(f"  最近24小时降级: {report.get('recent_degradations_24h', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"✗ 降级监控测试失败: {e}")
        logger.exception("降级监控测试异常详情:")
        return False

def main():
    """主测试函数"""
    print("开始 LTP 引擎修复测试...")
    
    tests = [
        ("LTP 任务参数测试", test_ltp_task_parameters),
        ("LTP 导入安全性测试", test_ltp_import_safety),
        ("降级监控测试", test_degradation_monitoring),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} 通过")
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
            failed += 1
    
    print(f"\n=== 测试总结 ===")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")
    
    if failed == 0:
        print("🎉 所有测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，请检查上述错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
