#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 机器人池测试脚本

测试 AliceBot 池的功能，包括：
- Bot 池初始化
- Bot 实例获取和释放
- 响应生成
- 打字延迟模拟
- 负载均衡
"""

import asyncio
import sys
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, "F:/eliza-py")


async def test_bot_pool_initialization():
    """测试 Bot 池初始化"""
    print("\n" + "=" * 60)
    print("测试 1: Bot 池初始化")
    print("=" * 60)

    try:
        from alice.services.shared_nlp_service import SharedNLPService
        from turing_test.backend.bot_pool import AliceBotPool

        # 初始化 NLP 服务
        print("正在初始化 NLP 服务...")
        nlp_service = SharedNLPService()
        print("✅ NLP 服务初始化成功")

        # 初始化 Bot 池
        print("正在初始化 Bot 池...")
        bot_pool = AliceBotPool(
            nlp_service=nlp_service,
            min_instances=2,
            max_instances=5,
            idle_timeout=60,
            script_file="alice/scripts/demo.yaml",
            rules_file="alice/scripts/rules/mapping.yaml",
        )
        print("✅ Bot 池初始化成功")

        # 获取统计信息
        stats = bot_pool.get_stats()
        print(f"📊 Bot 池统计:")
        print(f"   总实例数：{stats['total_instances']}")
        print(f"   可用实例数：{stats['available_instances']}")
        print(f"   忙碌实例数：{stats['busy_instances']}")

        # 关闭 Bot 池
        bot_pool.shutdown()
        print("✅ Bot 池已关闭")

        return True

    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


async def test_bot_response_generation():
    """测试 Bot 响应生成"""
    print("\n" + "=" * 60)
    print("测试 2: Bot 响应生成")
    print("=" * 60)

    try:
        from alice.services.shared_nlp_service import SharedNLPService
        from turing_test.backend.bot_pool import AliceBotPool

        # 初始化
        nlp_service = SharedNLPService()
        bot_pool = AliceBotPool(
            nlp_service=nlp_service,
            min_instances=2,
            max_instances=5,
            script_file="alice/scripts/demo.yaml",
            rules_file="alice/scripts/rules/mapping.yaml",
        )

        # 测试消息
        test_messages = [
            "你好",
            "你是谁？",
            "今天天气怎么样？",
            "你喜欢什么？",
            "再见",
        ]

        print("\n开始测试响应生成:")
        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. 用户：{message}")

            # 获取 Bot
            bot = bot_pool.acquire(timeout=5.0)
            if not bot:
                print("   ❌ 无法获取 Bot 实例")
                continue

            try:
                # 生成响应
                start_time = time.time()
                response = bot.respond(message)
                elapsed = time.time() - start_time

                print(f"   AI: {response}")
                print(f"   响应时间：{elapsed:.3f}秒")

            finally:
                # 释放 Bot
                bot_pool.release(bot)

        # 获取统计信息
        stats = bot_pool.get_stats()
        print(f"\n📊 最终统计:")
        print(f"   总获取次数：{stats['pool_stats']['total_acquires']}")
        print(f"   总释放次数：{stats['pool_stats']['total_releases']}")
        print(f"   总创建次数：{stats['pool_stats']['total_creates']}")

        # 关闭
        bot_pool.shutdown()
        print("\n✅ 测试完成")

        return True

    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ai_bot_service():
    """测试 AI Bot 服务"""
    print("\n" + "=" * 60)
    print("测试 3: AI Bot 服务（含打字延迟）")
    print("=" * 60)

    try:
        from turing_test.backend.services.ai_bot_service import AIBotService

        # 初始化服务
        print("正在初始化 AI Bot 服务...")
        service = AIBotService()
        await service.initialize()
        print("✅ AI Bot 服务初始化成功")

        # 测试消息
        test_messages = [
            "你好，很高兴见到你",
            "你能帮我做什么？",
            "你喜欢聊天吗？",
        ]

        print("\n开始测试响应生成（含打字延迟）:")
        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. 用户：{message}")

            # 获取响应
            start_time = time.time()
            response, delay = await service.get_response(message, simulate_typing=True)
            total_time = time.time() - start_time

            print(f"   AI: {response}")
            print(f"   打字延迟：{delay:.2f}秒")
            print(f"   总时间：{total_time:.2f}秒")

        # 获取统计信息
        stats = service.get_pool_stats()
        print(f"\n📊 Bot 池统计:")
        print(f"   总实例数：{stats.get('total_instances', 0)}")
        print(f"   可用实例数：{stats.get('available_instances', 0)}")
        print(f"   忙碌实例数：{stats.get('busy_instances', 0)}")

        # 关闭服务
        await service.shutdown()
        print("\n✅ AI Bot 服务已关闭")

        return True

    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


async def test_concurrent_requests():
    """测试并发请求"""
    print("\n" + "=" * 60)
    print("测试 4: 并发请求测试")
    print("=" * 60)

    try:
        from turing_test.backend.services.ai_bot_service import AIBotService

        # 初始化服务
        print("正在初始化 AI Bot 服务...")
        service = AIBotService()
        await service.initialize()
        print("✅ AI Bot 服务初始化成功")

        # 并发请求
        async def make_request(request_id: int):
            """发送请求"""
            message = f"你好，这是请求 {request_id}"
            start_time = time.time()

            try:
                response, delay = await service.get_response(message, simulate_typing=False)
                elapsed = time.time() - start_time
                return {
                    "request_id": request_id,
                    "success": True,
                    "elapsed": elapsed,
                    "response_length": len(response),
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": str(e),
                }

        # 创建并发任务
        num_requests = 5
        print(f"\n发送 {num_requests} 个并发请求...")
        tasks = [make_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        # 显示结果
        print("\n请求结果:")
        for result in results:
            if result["success"]:
                print(f"   请求 {result['request_id']}: ✅ 成功 ({result['elapsed']:.3f}秒)")
            else:
                print(f"   请求 {result['request_id']}: ❌ 失败 ({result['error']})")

        # 获取统计信息
        stats = service.get_pool_stats()
        print(f"\n📊 Bot 池统计:")
        print(f"   总实例数：{stats.get('total_instances', 0)}")
        print(f"   忙碌实例数：{stats.get('busy_instances', 0)}")
        print(f"   总获取次数：{stats['pool_stats']['total_acquires']}")

        # 关闭服务
        await service.shutdown()
        print("\n✅ 测试完成")

        return True

    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("AI 机器人池测试套件")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(("Bot 池初始化", await test_bot_pool_initialization()))
    results.append(("Bot 响应生成", await test_bot_response_generation()))
    results.append(("AI Bot 服务", await test_ai_bot_service()))
    results.append(("并发请求", await test_concurrent_requests()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")

    print(f"\n总计：{passed}/{total} 测试通过")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
