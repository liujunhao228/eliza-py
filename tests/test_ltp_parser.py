#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 依存句法分析模块测试
"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alice.utils.ltp_parser import LTPParser, SyntaxBasedReassemblyEngine, parse_sentence, get_main_components


class TestLTPParser(unittest.TestCase):
    """LTP 分析器测试"""

    def setUp(self):
        """测试前准备"""
        self.parser = LTPParser()
        self.test_sentences = [
            "我觉得今天很开心",
            "我和朋友去了一家新餐厅",
            "他说的话让我很感动",
            "我希望能够改变现状",
        ]

    def test_parser_initialization(self):
        """测试分析器初始化"""
        self.assertIsInstance(self.parser, LTPParser)
        print(f"\nLTP 可用状态：{self.parser.available}")

    def test_parse_sentence(self):
        """测试句子分析"""
        for sentence in self.test_sentences:
            structure = self.parser.parse(sentence)
            self.assertIsNotNone(structure, f"分析失败：{sentence}")
            self.assertIsInstance(structure.words, list)
            print(f"\n原句：{sentence}")
            print(f"  词语：{structure.words}")
            print(f"  主语：{structure.subject}")
            print(f"  谓语：{structure.predicate}")
            print(f"  宾语：{structure.object}")

    def test_get_main_structure(self):
        """测试获取主干结构"""
        for sentence in self.test_sentences:
            main = self.parser.get_main_structure(sentence)
            self.assertIsInstance(main, dict)
            self.assertIn('subject', main)
            self.assertIn('predicate', main)
            self.assertIn('object', main)
            print(f"\n{sentence} -> 主谓宾：{main['subject']} | {main['predicate']} | {main['object']}")

    def test_get_modifiers(self):
        """测试获取修饰语"""
        sentence = "我非常开心地去了一个很漂亮的餐厅"
        modifiers = self.parser.get_modifiers(sentence)
        print(f"\n修饰语测试：{sentence}")
        print(f"  修饰语：{modifiers}")

    def test_dependency_tree(self):
        """测试依存句法树"""
        sentence = "我觉得今天很开心"
        tree = self.parser.get_dependency_tree(sentence)
        print(f"\n依存树测试：{sentence}")
        if tree:
            print(f"  词语：{tree['words']}")
            for dep in tree.get('dependencies', [])[:5]:  # 只显示前 5 个
                print(f"  {dep['word']} --[{dep['dep']}]--> {dep['head_word']}")


class TestSyntaxBasedReassemblyEngine(unittest.TestCase):
    """句法重组引擎测试"""

    def setUp(self):
        """测试前准备"""
        self.parser = LTPParser()
        self.reassembly_engine = SyntaxBasedReassemblyEngine(self.parser)

    def test_reassemble_with_syntax(self):
        """测试基于句法的重组"""
        test_cases = [
            ("我觉得今天很开心", "为什么{SUBJ}{PRED}{OBJ}？"),
            ("我和朋友去了餐厅", "{SUBJ}和谁{PRED}了{OBJ}？"),
            ("他希望改变现状", "{SUBJ}为什么{PRED}{OBJ}？"),
        ]

        for sentence, template in test_cases:
            response = self.reassembly_engine.reassemble_with_syntax(sentence, template)
            print(f"\n原句：{sentence}")
            print(f"模板：{template}")
            print(f"重组：{response}")
            self.assertTrue(len(response) > 0)

    def test_generate_syntax_question(self):
        """测试生成句法问句"""
        sentences = [
            "我觉得很累",
            "他和同事吵架了",
            "我想学习编程",
        ]

        for sentence in sentences:
            for q_type in ['why', 'what', 'how']:
                question = self.reassembly_engine.generate_syntax_question(sentence, q_type)
                print(f"\n原句：{sentence} | 类型：{q_type}")
                print(f"问句：{question}")

    def test_extract_focus_point(self):
        """测试提取焦点"""
        test_cases = [
            "我昨天去了一个新开的餐厅",
            "她是一个很善良的人",
            "工作压力让我很焦虑",
        ]

        for sentence in test_cases:
            focus = self.reassembly_engine.extract_focus_point(sentence)
            print(f"\n原句：{sentence}")
            print(f"焦点：{focus}")


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函数测试"""

    def test_parse_sentence_function(self):
        """测试便捷函数 parse_sentence"""
        structure = parse_sentence("我喜欢编程")
        if structure:
            print(f"\n便捷函数测试：{structure.words}")
            print(f"  主谓宾：{structure.subject} | {structure.predicate} | {structure.object}")

    def test_get_main_components_function(self):
        """测试便捷函数 get_main_components"""
        components = get_main_components("他希望改变自己")
        print(f"\n主干成分：{components}")


class TestReassemblyWithSyntax(unittest.TestCase):
    """重组引擎句法支持测试"""

    def setUp(self):
        """测试前准备"""
        from alice.utils.reassembly import ReassemblyEngine
        self.parser = LTPParser()
        self.reassembly_engine = ReassemblyEngine()

    def test_syntax_placeholders(self):
        """测试句法占位符替换"""
        # 设置句法结构
        syntax_structure = {
            'subject': '我',
            'predicate': '觉得',
            'object': '开心',
        }

        test_cases = [
            ("为什么{SUBJ}{PRED}{OBJ}？", "为什么你觉得开心？"),
            ("{SUBJ}是因为什么{PRED}{OBJ}？", "你是因为什么觉得开心？"),
        ]

        for template, expected_pattern in test_cases:
            result = self.reassembly_engine.reassemble(
                components=[],
                reassembly_rule=template,
                syntax_structure=syntax_structure
            )
            print(f"\n模板：{template}")
            print(f"结果：{result}")
            # 验证代词转换（我→你）
            self.assertIn('你', result)


class TestLTPIntegration(unittest.TestCase):
    """LTP 集成测试"""

    def test_full_pipeline(self):
        """测试完整处理流程"""
        from alice.core import AliceBot

        # 测试不启用 LTP
        bot_normal = AliceBot(enable_ltp=False)
        response = bot_normal.respond("我今天很开心")
        print(f"\n普通模式：{response}")

        # 测试启用 LTP（如果可用）
        try:
            bot_ltp = AliceBot(enable_ltp=True)
            response = bot_ltp.respond("我今天很开心")
            print(f"LTP 模式：{response}")
        except Exception as e:
            print(f"LTP 模式测试跳过：{e}")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestLTPParser))
    suite.addTests(loader.loadTestsFromTestCase(TestSyntaxBasedReassemblyEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestReassemblyWithSyntax))
    suite.addTests(loader.loadTestsFromTestCase(TestLTPIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    print("=" * 60)
    print("LTP 依存句法分析模块测试")
    print("=" * 60)
    run_tests()
