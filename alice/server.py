#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice Web 界面
使用 Flask 提供 HTTP API 和简单的 Web 聊天界面

支持多 Bot 实例:
- 每个 Bot 实例有独立的脚本配置
- 所有 Bot 实例共享 NLP 服务

支持热重载：
- 自动模式：监听 YAML 文件变化自动重载
- 手动模式：调用 /api/reload API 触发重载
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
from alice.bots import get_registry, BotRegistry, BotInstance
from alice.exceptions import (
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    InitializationError,
    ConfigurationError,
)
from alice.utils.sanitizer import sanitize_text

logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局 Bot 注册中心实例（懒加载）
_registry: Optional[BotRegistry] = None
_default_bot_name: str = "alice"


def get_registry_instance(bot_names: Optional[List[str]] = None) -> BotRegistry:
    """
    获取或创建 Bot 注册中心实例（懒加载）
    
    Args:
        bot_names: 要加载的 Bot 名称列表，None 则加载默认 Bot
        
    Returns:
        Bot 注册中心实例
    """
    global _registry, _default_bot_name
    
    if _registry is None:
        _registry = get_registry()
        
        # 加载默认 Bot
        if bot_names is None or len(bot_names) == 0:
            bot_names = [_default_bot_name]
        
        for name in bot_names:
            try:
                config_path = f"config/bots/{name}.yaml"
                _registry.register_from_yaml(config_path)
                logger.info(f"Bot[{name}] 已从配置文件加载")
            except Exception as e:
                logger.warning(f"从配置文件加载 Bot[{name}] 失败：{e}，使用默认配置创建")
                try:
                    _registry.register_bot(
                        name=name,
                        script_file="alice/scripts/demo.yaml",
                        rules_file="alice/scripts/rules/mapping.yaml",
                    )
                except Exception as e2:
                    logger.error(f"创建 Bot[{name}] 失败：{e2}")
        
        logger.info(f"Bot 注册中心已创建，已加载 {len(_registry.list_bots())} 个 Bot")
    
    return _registry


def get_bot(bot_name: Optional[str] = None) -> Optional[BotInstance]:
    """
    获取 Bot 实例
    
    Args:
        bot_name: Bot 名称，None 则返回默认 Bot
        
    Returns:
        Bot 实例
    """
    registry = get_registry_instance()
    if bot_name:
        return registry.get_bot(bot_name)
    return registry.get_default_bot()


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    聊天 API

    Request JSON:
        {
            "message": "用户输入的消息",
            "bot": "Bot 名称（可选，默认使用 alice）",
            "context": {
                "sessionId": "会话 ID（可选）",
                "history": [{"role": "user|assistant", "content": "消息内容"}]（可选）
            }
        }

    Response JSON:
        {
            "response": "Bot 的回复",
            "bot": "Bot 名称",
            "latency": 延迟毫秒数
        }
    """
    data = request.get_json()

    if not data or 'message' not in data:
        logger.warning(
            "请求缺少 message 字段",
            extra={'component': 'server', 'remote_addr': request.remote_addr}
        )
        return jsonify({
            'error': '缺少 message 字段'
        }), 400

    user_input = data['message'].strip()
    bot_name = data.get('bot', 'alice')
    context = data.get('context', {})

    # 记录会话 ID（用于未来上下文追踪）
    session_id = context.get('sessionId')
    if session_id:
        logger.debug(f"会话 ID: {session_id}")

    bot = get_bot(bot_name)
    if bot is None:
        return jsonify({
            'error': f'Bot[{bot_name}] 不存在'
        }), 404

    if not user_input:
        start_time = time.time()
        response = bot.respond("")
        latency = int((time.time() - start_time) * 1000)
        return jsonify({
            'response': response,
            'bot': bot.name,
            'latency': latency
        })

    try:
        start_time = time.time()
        response = bot.respond(user_input)
        latency = int((time.time() - start_time) * 1000)
        
        logger.info(
            "请求处理成功",
            extra={
                'component': 'server',
                'action': 'chat',
                'bot': bot.name,
                'input_length': len(user_input),
                'input_preview': sanitize_text(user_input[:50]),
                'response_length': len(response),
                'latency_ms': latency,
            }
        )

        return jsonify({
            'response': response,
            'bot': bot.name,
            'latency': latency
        })

    except (InputValidationError, ScriptMatchingError) as e:
        logger.warning(
            "业务异常",
            extra={
                'component': 'server',
                'error_type': type(e).__name__,
                'bot': bot.name,
                'input_preview': sanitize_text(user_input[:50]),
            }
        )
        return jsonify({
            'response': str(e.message if hasattr(e, 'message') else str(e)),
            'bot': bot.name,
            'timestamp': datetime.now().isoformat()
        })

    except ResponseGenerationError as e:
        logger.error(
            "响应生成失败",
            extra={
                'component': 'server',
                'error_type': type(e).__name__,
                'bot': bot.name,
                'input_preview': sanitize_text(user_input[:50]),
            },
            exc_info=True,
        )
        return jsonify({
            'response': '系统出现故障，请稍后再试',
            'bot': bot.name,
            'timestamp': datetime.now().isoformat()
        }), 500

    except Exception as e:
        logger.critical(
            "未预期的错误",
            extra={
                'component': 'server',
                'error_type': type(e).__name__,
                'bot': bot.name,
                'input_preview': sanitize_text(user_input[:50]),
            },
            exc_info=True,
        )
        return jsonify({
            'response': '系统出现未知错误，请稍后再试',
            'bot': bot.name,
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/bots', methods=['GET'])
def list_bots():
    """获取所有可用的 Bot 列表"""
    registry = get_registry_instance()
    bots = registry.get_all_bots()
    bot_list = []
    for name, bot in bots.items():
        bot_list.append({
            'name': bot.name,
            'display_name': bot.display_name,
            'description': bot.config.description,
            'initialized': bot._initialized,
        })
    return jsonify({
        'bots': bot_list,
        'total': len(bot_list)
    })


@app.route('/api/reset', methods=['POST'])
def reset():
    """重置对话历史"""
    bot_name = request.args.get('bot', None)
    bot = get_bot(bot_name)
    
    if bot is None:
        return jsonify({
            'error': f'Bot[{bot_name}] 不存在'
        }), 404
    
    bot.reset()
    logger.info(f"Bot[{bot.name}] 对话已重置", extra={'component': 'server', 'action': 'reset'})
    return jsonify({
        'status': 'success',
        'message': '对话已重置',
        'bot': bot.name
    })


@app.route('/api/status', methods=['GET'])
def status():
    """获取机器人状态"""
    bot_name = request.args.get('bot', None)
    bot = get_bot(bot_name)
    
    if bot is None:
        return jsonify({
            'error': f'Bot[{bot_name}] 不存在'
        }), 404
    
    stats = bot.get_stats()
    return jsonify({
        'status': 'online',
        'bot': bot.name,
        'stats': stats
    })


@app.route('/api/reload', methods=['POST'])
def reload():
    """
    热重载配置文件

    Query Parameters:
        - bot: Bot 名称（可选，默认使用默认 Bot）
        - type: 重载类型 (all|scripts|rules)，默认：all

    Response JSON:
        {
            "success": true/false,
            "script_reloaded": true/false,
            "rules_reloaded": true/false,
            "error": "错误信息（如果有）"
        }
    """
    bot_name = request.args.get('bot', None)
    bot = get_bot(bot_name)
    
    if bot is None:
        return jsonify({
            'error': f'Bot[{bot_name}] 不存在'
        }), 404
    
    reload_type = request.args.get('type', 'all')

    try:
        if reload_type == 'scripts':
            result = bot.reload_scripts()
        elif reload_type == 'rules':
            result = bot.reload_rules()
        else:
            result = bot.reload_all()

        logger.info(
            f"Bot[{bot.name}] 配置文件重载完成 - 类型：{reload_type}, 成功：{result.success}",
            extra={'component': 'server', 'action': 'reload'}
        )

        return jsonify({
            'success': result.success,
            'script_reloaded': result.script_reloaded,
            'rules_reloaded': result.rules_reloaded,
            'error': result.error,
            'bot': bot.name,
        })

    except Exception as e:
        logger.error(
            f"Bot[{bot.name}] 配置文件重载失败：{e}",
            extra={'component': 'server', 'action': 'reload'},
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': str(e),
            'bot': bot.name,
        }), 500


@app.route('/api/hot-reload/status', methods=['GET'])
def hot_reload_status():
    """获取热重载器状态"""
    bot_name = request.args.get('bot', None)
    bot = get_bot(bot_name)
    
    if bot is None:
        return jsonify({
            'error': f'Bot[{bot_name}] 不存在'
        }), 404
    
    status = bot.get_hot_reload_status()
    return jsonify(status)


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False, bot_names: Optional[List[str]] = None):
    """
    运行 Web 服务器

    Args:
        host: 监听地址
        port: 监听端口
        debug: 是否开启调试模式
        bot_names: 要加载的 Bot 名称列表，None 则加载默认 Bot
    """
    # 预加载 Bot
    registry = get_registry_instance(bot_names)
    loaded_bots = registry.list_bots()

    # 配置 CORS
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3003')
    CORS(app, origins=[origin.strip() for origin in cors_origins.split(',')])

    print(f"🚀 Alice Web 服务器启动中...")
    print(f"📍 访问地址：http://localhost:{port}")
    print(f"🤖 已加载 Bot: {', '.join(loaded_bots)}")
    print(f"💬 开始聊天吧！\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
