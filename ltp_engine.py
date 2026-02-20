#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎直接访问入口
====================

提供直接访问 LTP 引擎的便捷接口。

任务启用开关配置说明:
- 默认值来自 alice.config 模块（LTP_ENABLE_* 系列配置项）
- 可在 alice/config.py 中统一修改所有 LTP 任务的启用状态

使用示例:
    # 方式 1: 命令行交互
    python ltp_engine.py

    # 方式 2: Python 代码调用
    from ltp_engine import get_ltp_engine, LtpEngine
    engine = get_ltp_engine()
    result = engine.analyze_full("小明在北京大学读书")
    print(result.to_json())

    # 方式 3: 便捷函数
    from ltp_engine import segment, pos_tag, extract_entities, parse_dependencies
    tokens = segment("今天天气很好")
    entities = extract_entities("小明在北京大学读书")
"""

import argparse
import json
import logging
import sys
from typing import List, Optional, Tuple

from alice.nlp.engines.ltp import LtpEngine, LtpConfig, LtpFullResult
from alice.nlp.base import Entity
from alice.config import (
    LTP_ENABLE_CWS,
    LTP_ENABLE_POS,
    LTP_ENABLE_NER,
    LTP_ENABLE_DEP,
    LTP_ENABLE_SDP,
    LTP_ENABLE_SRL,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局引擎实例
_engine: Optional[LtpEngine] = None


def get_ltp_engine() -> LtpEngine:
    """
    获取 LTP 引擎单例实例

    Returns:
        配置好的 LTP 引擎实例
    """
    global _engine
    if _engine is None:
        # 创建配置：从 alice.config 读取默认启用状态
        config = LtpConfig(
            enable_cws=LTP_ENABLE_CWS,   # 中文分词
            enable_pos=LTP_ENABLE_POS,   # 词性标注
            enable_ner=LTP_ENABLE_NER,   # 命名实体识别
            enable_dep=LTP_ENABLE_DEP,   # 依存句法分析
            enable_sdp=LTP_ENABLE_SDP,   # 语义依存分析
            enable_srl=LTP_ENABLE_SRL,   # 语义角色标注
        )
        _engine = LtpEngine(
            model_path=config.model_path,
            device=config.device,
            batch_size=config.batch_size,
            max_length=config.max_length,
        )
        logger.info("LTP 引擎已初始化 (CWS+POS+NER+DEP)")
    return _engine


def analyze(text: str) -> LtpFullResult:
    """
    分析文本

    Args:
        text: 待分析文本

    Returns:
        完整分析结果
    """
    engine = get_ltp_engine()
    return engine.analyze_full(text)


def segment(text: str) -> List[str]:
    """
    分词

    Args:
        text: 待分词文本

    Returns:
        分词结果列表
    """
    engine = get_ltp_engine()
    return engine.segment(text)


def pos_tag(text: str) -> List[Tuple[str, str]]:
    """
    词性标注

    Args:
        text: 待标注文本

    Returns:
        (词，词性) 元组列表
    """
    engine = get_ltp_engine()
    return engine.pos_tag(text)


def extract_entities(text: str) -> List[Entity]:
    """
    命名实体识别

    Args:
        text: 待识别文本

    Returns:
        实体列表
    """
    engine = get_ltp_engine()
    return engine.extract_entities(text)


def parse_dependencies(text: str):
    """
    依存句法分析

    Args:
        text: 待分析文本

    Returns:
        依存关系列表
    """
    engine = get_ltp_engine()
    return engine.parse_dependency(text)


def extract_triples(text: str):
    """
    提取主谓宾三元组

    Args:
        text: 待分析文本

    Returns:
        (主语，谓语，宾语) 元组列表
    """
    engine = get_ltp_engine()
    return engine.extract_triples(text)


def format_result(result: LtpFullResult) -> str:
    """
    格式化输出分析结果

    Args:
        result: 分析结果

    Returns:
        格式化后的字符串
    """
    lines = []
    lines.append(f"原文：{result.text}")
    lines.append("-" * 50)

    # 分词
    if result.tokens:
        tokens_str = " / ".join([t.text for t in result.tokens])
        lines.append(f"分词：{tokens_str}")

    # 词性标注
    if result.pos_tags:
        pos_str = " / ".join([f"{p.token.text}/{p.pos}" for p in result.pos_tags])
        lines.append(f"词性：{pos_str}")

    # 命名实体
    if result.entities:
        entity_str = ", ".join([f"{e.text}({e.type})" for e in result.entities])
        lines.append(f"实体：{entity_str}")

    # 依存关系
    if result.dependencies:
        lines.append("依存关系:")
        for dep in result.dependencies:
            head_text = result.tokens[dep.head_idx].text if dep.head_idx >= 0 else "ROOT"
            lines.append(f"  {dep.token.text} --[{dep.relation}]--> {head_text}")

    # 三元组
    triples = extract_triples(result.text)
    if triples:
        lines.append("三元组:")
        for subj, pred, obj in triples:
            lines.append(f"  ({subj}, {pred}, {obj})")

    return "\n".join(lines)


def run_cli():
    """命令行交互模式"""
    print("=" * 60)
    print("LTP 引擎 - 自然语言分析工具")
    print("=" * 60)
    print("功能：分词 / 词性标注 / 命名实体识别 / 依存句法分析")
    print("输入 'quit' 或 'exit' 退出\n")

    while True:
        try:
            user_input = input("请输入文本：").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            if not user_input:
                continue

            result = analyze(user_input)
            print("\n" + format_result(result) + "\n")

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"错误：{e}\n")
            logger.error(f"分析失败：{e}", exc_info=True)


def run_web(host: str = '0.0.0.0', port: int = 5001):
    """
    Web API 模式

    提供 RESTful API:
    - POST /analyze - 完整分析
    - POST /segment - 分词
    - POST /pos - 词性标注
    - POST /entities - 实体识别
    - POST /dependencies - 依存分析
    - POST /triples - 三元组提取
    """
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("错误：Flask 未安装，请先安装：pip install flask")
        sys.exit(1)

    app = Flask(__name__)

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok', 'engine': 'ltp'})

    @app.route('/analyze', methods=['POST'])
    def api_analyze():
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': '缺少 text 参数'}), 400
        try:
            result = analyze(text)
            return jsonify(result.to_dict())
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/segment', methods=['POST'])
    def api_segment():
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': '缺少 text 参数'}), 400
        try:
            tokens = segment(text)
            return jsonify({'tokens': tokens})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/pos', methods=['POST'])
    def api_pos():
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': '缺少 text 参数'}), 400
        try:
            tags = pos_tag(text)
            return jsonify({'tags': [{'word': w, 'pos': p} for w, p in tags]})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/entities', methods=['POST'])
    def api_entities():
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': '缺少 text 参数'}), 400
        try:
            entities = extract_entities(text)
            return jsonify({
                'entities': [
                    {'text': e.text, 'type': e.type, 'start': e.start, 'end': e.end}
                    for e in entities
                ]
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/dependencies', methods=['POST'])
    def api_dependencies():
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': '缺少 text 参数'}), 400
        try:
            deps = parse_dependencies(text)
            return jsonify({
                'dependencies': [
                    {
                        'token': d.token.text,
                        'token_idx': d.token.idx,
                        'head': d.head_token.text,
                        'head_idx': d.head_idx,
                        'relation': d.relation
                    }
                    for d in deps
                ]
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/triples', methods=['POST'])
    def api_triples():
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': '缺少 text 参数'}), 400
        try:
            triples = extract_triples(text)
            return jsonify({
                'triples': [{'subject': s, 'predicate': p, 'object': o} for s, p, o in triples]
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    print(f"Web API 启动于 http://{host}:{port}")
    print("可用端点:")
    print("  POST /analyze       - 完整分析")
    print("  POST /segment       - 分词")
    print("  POST /pos           - 词性标注")
    print("  POST /entities      - 实体识别")
    print("  POST /dependencies  - 依存分析")
    print("  POST /triples       - 三元组提取")
    app.run(host=host, port=port, debug=False)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='LTP 引擎直接访问入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ltp_engine.py                    # 命令行交互模式
  python ltp_engine.py --web              # Web API 模式 (默认端口 5001)
  python ltp_engine.py --web --port 8080  # Web API 模式 (端口 8080)

Python 调用示例:
  from ltp_engine import analyze, segment, pos_tag, extract_entities
  result = analyze("小明在北京大学读书")
  tokens = segment("今天天气很好")
  entities = extract_entities("张三在清华大学工作")
        """
    )

    parser.add_argument(
        '--web',
        action='store_true',
        help='以 Web API 模式运行'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Web API 监听地址 (默认：0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5001,
        help='Web API 监听端口 (默认：5001)'
    )

    args = parser.parse_args()

    if args.web:
        run_web(host=args.host, port=args.port)
    else:
        run_cli()


if __name__ == "__main__":
    main()
