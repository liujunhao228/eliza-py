#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice Web 界面
使用 Flask 提供 HTTP API 和简单的 Web 聊天界面
"""

import os
from flask import Flask, request, jsonify, render_template_string
from alice.alice_v2 import AliceBot

app = Flask(__name__)

# 全局 Alice 实例
alice = AliceBot()

# 简单的 HTML 聊天界面
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alice - 好奇的朋友</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .chat-container {
            width: 100%;
            max-width: 600px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        
        .chat-header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .chat-header p {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .chat-messages {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-content {
            max-width: 70%;
            padding: 12px 18px;
            border-radius: 18px;
            line-height: 1.5;
        }
        
        .message.bot .message-content {
            background: white;
            color: #333;
            border-bottom-left-radius: 4px;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }
        
        .message-label {
            font-size: 12px;
            color: #999;
            margin-bottom: 5px;
        }
        
        .message.user .message-label {
            text-align: right;
        }
        
        .chat-input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e9ecef;
            display: flex;
            gap: 10px;
        }
        
        .chat-input {
            flex: 1;
            padding: 12px 18px;
            border: 2px solid #e9ecef;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .chat-input:focus {
            border-color: #667eea;
        }
        
        .chat-send {
            padding: 12px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .chat-send:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        
        .chat-send:active {
            transform: translateY(0);
        }
        
        .typing-indicator {
            display: none;
            padding: 12px 18px;
            background: white;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            width: fit-content;
        }
        
        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: #667eea;
            border-radius: 50%;
            display: inline-block;
            margin: 0 2px;
            animation: bounce 1.4s infinite ease-in-out;
        }
        
        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>🤖 Alice</h1>
            <p>你的好奇朋友</p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                <div>
                    <div class="message-label">Alice</div>
                    <div class="message-content">你好！我是 Alice。有什么想聊的吗？</div>
                </div>
            </div>
            <div class="typing-indicator" id="typingIndicator">
                <span></span><span></span><span></span>
            </div>
        </div>
        
        <div class="chat-input-container">
            <input type="text" class="chat-input" id="chatInput" 
                   placeholder="输入消息..." onkeypress="handleKeyPress(event)">
            <button class="chat-send" onclick="sendMessage()">发送</button>
        </div>
    </div>
    
    <script>
        const chatMessages = document.getElementById('chatMessages');
        const chatInput = document.getElementById('chatInput');
        const typingIndicator = document.getElementById('typingIndicator');
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        function appendMessage(sender, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const label = sender === 'user' ? '你' : 'Alice';
            
            messageDiv.innerHTML = `
                <div>
                    <div class="message-label">${label}</div>
                    <div class="message-content">${content}</div>
                </div>
            `;
            
            // 插入到 typing indicator 之前
            chatMessages.insertBefore(messageDiv, typingIndicator);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function showTyping() {
            typingIndicator.style.display = 'block';
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function hideTyping() {
            typingIndicator.style.display = 'none';
        }
        
        async function sendMessage() {
            const message = chatInput.value.trim();
            if (!message) return;
            
            // 清空输入框
            chatInput.value = '';
            
            // 显示用户消息
            appendMessage('user', message);
            
            // 显示输入指示器
            showTyping();
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                // 隐藏输入指示器
                hideTyping();
                
                // 显示机器人回复
                appendMessage('bot', data.response);
            } catch (error) {
                hideTyping();
                appendMessage('bot', '抱歉，出了点问题。请稍后再试。');
                console.error('Error:', error);
            }
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """渲染聊天界面"""
    return render_template_string(HTML_TEMPLATE)


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
    from datetime import datetime
    
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({
            'error': '缺少 message 字段'
        }), 400
    
    user_input = data['message'].strip()
    
    if not user_input:
        return jsonify({
            'error': '消息不能为空'
        }), 400
    
    # 生成回复
    response = alice.respond(user_input)
    
    return jsonify({
        'response': response,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/reset', methods=['POST'])
def reset():
    """重置对话历史"""
    alice.reset()
    return jsonify({
        'status': 'success',
        'message': '对话已重置'
    })


@app.route('/api/status', methods=['GET'])
def status():
    """获取机器人状态"""
    summary = alice.get_conversation_summary()
    return jsonify({
        'status': 'online',
        'conversation_turns': summary['turns'],
        'recent_entities': summary['recent_entities'],
        'script_usage': summary['script_usage']
    })


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
