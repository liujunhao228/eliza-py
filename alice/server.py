#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice Web 界面
使用 Flask 提供 HTTP API 和简单的 Web 聊天界面

支持热重载：
- 自动模式：监听 YAML 文件变化自动重载
- 手动模式：调用 /api/reload API 触发重载
"""

import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from alice.alice_v2 import AliceBot
from alice.exceptions import (
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    InitializationError,
)
from alice.utils.sanitizer import sanitize_text
from config import settings

logger = logging.getLogger(__name__)

app = Flask(__name__)

# 模板目录
TEMPLATE_DIR = Path(__file__).parent / "templates"

# 全局 Alice 实例（懒加载）
_alice_instance = None


def get_alice_instance() -> AliceBot:
    """获取或创建 Alice 实例（懒加载）"""
    global _alice_instance
    if _alice_instance is None:
        try:
            _alice_instance = AliceBot(
                enable_hot_reload=settings.alice.hot_reload,
                hot_reload_mode=settings.alice.hot_reload_mode,
            )
            logger.info("Alice 实例已创建")
            # 显示热重载状态
            hot_reload_status = _alice_instance.get_hot_reload_status()
            if hot_reload_status.get("enabled", False):
                logger.info(f"热重载已启用 (模式：{hot_reload_status.get('mode', 'auto')})")
        except Exception as e:
            logger.error(
                "Alice 实例创建失败",
                extra={
                    'component': 'server',
                    'error_type': type(e).__name__,
                },
                exc_info=True,
            )
            raise InitializationError(
                "Alice 实例初始化失败",
                context={'error_type': type(e).__name__}
            ) from e
    return _alice_instance


@app.route('/')
def index():
    """渲染聊天界面"""
    return render_template('chat.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    聊天 API

    Request JSON:
        {
            "message": "用户输入的消息"
        }

    Response JSON:
        {
            "response": "Alice 的回复",
            "timestamp": "时间戳"
        }
    """
    alice = get_alice_instance()
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

    if not user_input:
        # 空输入交给核心层处理，保持一致性
        response = alice.respond("")
        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat()
        })

    try:
        # 生成回复
        response = alice.respond(user_input)
        logger.info(
            "请求处理成功",
            extra={
                'component': 'server',
                'action': 'chat',
                'input_length': len(user_input),
                'input_preview': sanitize_text(user_input[:50]),
                'response_length': len(response),
            }
        )

        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat()
        })

    except (InputValidationError, ScriptMatchingError) as e:
        # 业务异常，返回友好提示
        logger.warning(
            "业务异常",
            extra={
                'component': 'server',
                'error_type': type(e).__name__,
                'input_preview': sanitize_text(user_input[:50]),
            }
        )
        return jsonify({
            'response': str(e.message if hasattr(e, 'message') else str(e)),
            'timestamp': datetime.now().isoformat()
        })

    except ResponseGenerationError as e:
        # 响应生成错误
        logger.error(
            "响应生成失败",
            extra={
                'component': 'server',
                'error_type': type(e).__name__,
                'input_preview': sanitize_text(user_input[:50]),
            },
            exc_info=True,
        )
        return jsonify({
            'response': '系统出现故障，请稍后再试',
            'timestamp': datetime.now().isoformat()
        }), 500

    except Exception as e:
        # 未预期的错误
        logger.critical(
            "未预期的错误",
            extra={
                'component': 'server',
                'error_type': type(e).__name__,
                'input_preview': sanitize_text(user_input[:50]),
            },
            exc_info=True,
        )
        return jsonify({
            'response': '系统出现未知错误，请稍后再试',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    """重置对话历史"""
    alice = get_alice_instance()
    alice.reset()
    logger.info("对话已重置", extra={'component': 'server', 'action': 'reset'})
    return jsonify({
        'status': 'success',
        'message': '对话已重置'
    })


@app.route('/api/status', methods=['GET'])
def status():
    """获取机器人状态"""
    alice = get_alice_instance()
    summary = alice.get_conversation_summary()
    return jsonify({
        'status': 'online',
        'conversation_turns': summary.get('turns', 0),
        'recent_entities': summary.get('recent_entities', []),
        'script_usage': summary.get('script_usage', {})
    })


@app.route('/api/reload', methods=['POST'])
def reload():
    """
    热重载配置文件

    Query Parameters:
        - type: 重载类型 (all|scripts|rules)，默认：all

    Response JSON:
        {
            "success": true/false,
            "script_reloaded": true/false,
            "rules_reloaded": true/false,
            "error": "错误信息（如果有）"
        }
    """
    alice = get_alice_instance()
    reload_type = request.args.get('type', 'all')

    try:
        if reload_type == 'scripts':
            result = alice.reload_scripts()
        elif reload_type == 'rules':
            result = alice.reload_rules()
        else:
            result = alice.reload_all()

        logger.info(
            f"配置文件重载完成 - 类型：{reload_type}, 成功：{result.success}",
            extra={'component': 'server', 'action': 'reload'}
        )

        return jsonify({
            'success': result.success,
            'script_reloaded': result.script_reloaded,
            'rules_reloaded': result.rules_reloaded,
            'error': result.error,
        })

    except Exception as e:
        logger.error(
            f"配置文件重载失败：{e}",
            extra={'component': 'server', 'action': 'reload'},
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@app.route('/api/hot-reload/status', methods=['GET'])
def hot_reload_status():
    """获取热重载器状态"""
    alice = get_alice_instance()
    status = alice.get_hot_reload_status()
    return jsonify(status)


def run_server(host='0.0.0.0', port=5000, debug=False):
    """
    运行 Web 服务器

    Args:
        host: 监听地址
        port: 监听端口
        debug: 是否开启调试模式
    """
    print(f"🚀 Alice Web 服务器启动中...")
    print(f"📍 访问地址：http://localhost:{port}")
    print(f"💬 开始聊天吧！\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
