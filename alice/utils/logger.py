#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志记录模块
提供结构化的日志记录功能
"""

import logging
import os
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "alice",
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（None 表示只输出到控制台）
        level: 日志级别
        format_string: 日志格式字符串
        
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 默认格式
    if format_string is None:
        format_string = (
            '%(asctime)s | %(name)s | %(levelname)-8s | %(message)s'
        )
    
    formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class DialogueLogger:
    """对话日志记录器"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        初始化对话日志记录器
        
        Args:
            log_dir: 日志目录
        """
        self.log_dir = log_dir
        self._ensure_log_dir()
        
        # 创建日志文件（按日期命名）
        today = datetime.now().strftime('%Y-%m-%d')
        self.log_file = os.path.join(log_dir, f"dialogue_{today}.log")
        
        # 设置日志记录器
        self.logger = setup_logger(
            name="alice.dialogue",
            log_file=self.log_file,
            level=logging.INFO,
            format_string='%(message)s'
        )
        
        # 性能日志记录器
        self.perf_logger = setup_logger(
            name="alice.performance",
            log_file=os.path.join(log_dir, f"performance_{today}.log"),
            level=logging.INFO
        )
        
        # 错误日志记录器
        self.error_logger = setup_logger(
            name="alice.error",
            log_file=os.path.join(log_dir, f"error_{today}.log"),
            level=logging.ERROR
        )
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def log_dialogue(self, user_input: str, bot_response: str, 
                     session_id: str = "default"):
        """
        记录对话
        
        Args:
            user_input: 用户输入
            bot_response: 机器人回复
            session_id: 会话 ID
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = f"""
{'='*60}
时间：{timestamp}
会话：{session_id}
{'-'*60}
用户：{user_input}
{'-'*60}
Alice: {bot_response}
{'='*60}
"""
        self.logger.info(log_entry)
    
    def log_performance(self, event: str, duration_ms: float, 
                        extra_info: dict = None):
        """
        记录性能数据
        
        Args:
            event: 事件名称
            duration_ms: 耗时（毫秒）
            extra_info: 额外信息
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            'timestamp': timestamp,
            'event': event,
            'duration_ms': round(duration_ms, 2)
        }
        
        if extra_info:
            log_entry.update(extra_info)
        
        self.perf_logger.info(str(log_entry))
    
    def log_error(self, error: Exception, context: dict = None):
        """
        记录错误
        
        Args:
            error: 异常对象
            context: 上下文信息
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            'timestamp': timestamp,
            'error_type': type(error).__name__,
            'error_message': str(error),
        }
        
        if context:
            log_entry.update(context)
        
        self.error_logger.error(f"错误：{log_entry}", exc_info=True)
    
    def get_today_dialogues(self) -> list:
        """
        获取今天的对话记录
        
        Returns:
            对话记录列表
        """
        if not os.path.exists(self.log_file):
            return []
        
        dialogues = []
        current_dialogue = {}
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('时间：'):
                    if current_dialogue:
                        dialogues.append(current_dialogue)
                    current_dialogue = {'timestamp': line.replace('时间：', '')}
                elif line.startswith('用户：'):
                    current_dialogue['user'] = line.replace('用户：', '')
                elif line.startswith('Alice:'):
                    current_dialogue['bot'] = line.replace('Alice:', '').strip()
        
        if current_dialogue:
            dialogues.append(current_dialogue)
        
        return dialogues


class ConversationExporter:
    """对话导出器"""
    
    def __init__(self, dialogue_logger: DialogueLogger):
        """
        初始化导出器
        
        Args:
            dialogue_logger: 对话日志记录器
        """
        self.logger = dialogue_logger
    
    def export_to_json(self, output_file: str) -> str:
        """
        导出对话为 JSON
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            输出文件路径
        """
        import json
        
        dialogues = self.logger.get_today_dialogues()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_dialogues': len(dialogues),
                'dialogues': dialogues
            }, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def export_to_text(self, output_file: str) -> str:
        """
        导出对话为文本
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            输出文件路径
        """
        dialogues = self.logger.get_today_dialogues()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Alice 对话记录\n")
            f.write(f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总对话数：{len(dialogues)}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, dialogue in enumerate(dialogues, 1):
                f.write(f"[对话 {i}]\n")
                f.write(f"时间：{dialogue.get('timestamp', 'N/A')}\n")
                f.write(f"用户：{dialogue.get('user', 'N/A')}\n")
                f.write(f"Alice: {dialogue.get('bot', 'N/A')}\n")
                f.write("\n" + "-" * 40 + "\n\n")
        
        return output_file


# 使用示例
if __name__ == "__main__":
    # 创建日志记录器
    logger = DialogueLogger(log_dir="logs")
    
    # 记录对话
    logger.log_dialogue("你好", "你好！很高兴和你聊天。")
    logger.log_dialogue("今天天气不错", "是啊，适合出去走走。")
    
    # 记录性能
    logger.log_performance("response_generation", 150.5)
    
    # 记录错误
    try:
        raise ValueError("测试错误")
    except Exception as e:
        logger.log_error(e, {'context': 'test'})
    
    print(f"日志已记录到：{logger.log_file}")
