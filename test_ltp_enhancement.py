#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎完善测试
================

测试 LTP 4.1.4 标注集完整性：
- 词性标注集（27 种 863 标注集）
- 语义角色类型（22 种）
- 依存句法关系（14 种）
- 语义依存关系（4 大类）
"""

import pytest
from alice.nlp.engines.ltp.models import (
    POSTag,
    Token,
    DependencyRelation,
    SemanticRole,
    SemanticDependency,
)
from alice.nlp.engines.ltp.validators import (
    PosTagValidator,
    DependencyValidator,
    SemanticRoleValidator,
    SemanticDepValidator,
)
from alice.nlp.engines.ltp.config import (
    POS_TAG_SET,
    SEMANTIC_ROLE_SET,
    DEPENDENCY_RELATION_SET,
    NER_ENTITY_MAPPING,
)


# =============================================================================
# 词性标注集测试
# =============================================================================

class TestPosTagSet:
    """词性标注集测试（863 标注集，29 种）"""

    def test_pos_tag_count(self):
        """测试词性标注集数量"""
        # 29 种：包含所有 863 标注集词性
        assert len(POS_TAG_SET) >= 27, f"期望至少 27 种词性，实际 {len(POS_TAG_SET)} 种"

    def test_all_27_pos_tags(self):
        """测试全部 27 种词性标签存在"""
        # 核心 27 种 863 标注集
        core_tags = {
            # 实词 - 体词
            'n', 'nd', 'nh', 'ni', 'nl', 'ns', 'nt', 'nz',
            'v', 'a', 'b', 'm', 'q', 'r',
            # 实词 - 谓词
            'd', 'z',
            # 虚词
            'p', 'c', 'u',
            # 其他
            'e', 'o', 'wp',
            # 语素/词缀
            'h', 'k', 'g',
            # 特殊
            'i', 'j', 'ws', 'x',
        }
        # 确保所有核心词性都在集合中
        assert core_tags.issubset(POS_TAG_SET), "缺少核心词性标签"

    def test_pos_validator_valid_tags(self):
        """测试有效词性标签验证"""
        tokens = [
            Token('美丽', 0, 0, 2),
            Token('跑', 1, 2, 3),
            Token('的', 2, 3, 4),
        ]
        pos_tags = [
            POSTag(tokens[0], 'a'),    # 形容词
            POSTag(tokens[1], 'v'),    # 动词
            POSTag(tokens[2], 'u'),    # 助词
        ]
        invalid = PosTagValidator.validate(pos_tags)
        assert len(invalid) == 0, f"期望无无效标签，实际：{invalid}"

    def test_pos_validator_invalid_tag(self):
        """测试无效词性标签检测"""
        tokens = [Token('测试', 0, 0, 2)]
        pos_tags = [POSTag(tokens[0], 'invalid_tag')]
        invalid = PosTagValidator.validate(pos_tags)
        assert len(invalid) == 1
        assert invalid[0] == (0, 'invalid_tag')

    def test_pos_is_valid_pos(self):
        """测试 POSTag.is_valid_pos 方法"""
        assert POSTag.is_valid_pos('a') is True
        assert POSTag.is_valid_pos('v') is True
        assert POSTag.is_valid_pos('invalid') is False

    def test_pos_categories(self):
        """测试词性分类"""
        # 体词
        assert 'n' in PosTagValidator.POS_CATEGORIES['体词']
        assert 'nh' in PosTagValidator.POS_CATEGORIES['体词']
        # 谓词
        assert 'v' in PosTagValidator.POS_CATEGORIES['谓词']
        assert 'a' in PosTagValidator.POS_CATEGORIES['谓词']
        # 虚词
        assert 'p' in PosTagValidator.POS_CATEGORIES['虚词']
        assert 'c' in PosTagValidator.POS_CATEGORIES['虚词']


# =============================================================================
# 语义角色类型测试
# =============================================================================

class TestSemanticRoleSet:
    """语义角色类型测试（22 种）"""

    def test_semantic_role_count(self):
        """测试语义角色数量"""
        # 至少 22 种标准角色
        assert len(SEMANTIC_ROLE_SET) >= 22, f"期望至少 22 种角色，实际 {len(SEMANTIC_ROLE_SET)} 种"

    def test_all_22_roles(self):
        """测试全部 22 种语义角色存在"""
        # 22 种标准语义角色
        core_roles = {
            # 核心论元
            'ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4',
            # 附加角色
            'ADV', 'BNF', 'CND', 'CRD', 'DGR', 'DIR', 'DIS',
            'EXT', 'FRQ', 'LOC', 'MNR', 'PRP', 'QTY',
            'TMP', 'TPC',
            # 特殊角色
            'PRD', 'PSR', 'PSE',
        }
        # 确保所有核心角色都在集合中
        assert core_roles.issubset(SEMANTIC_ROLE_SET), "缺少核心语义角色"

    def test_role_validator_valid_roles(self):
        """测试有效语义角色验证"""
        roles = [
            SemanticRole(
                predicate_idx=0,
                predicate='跑',
                arguments=[
                    ('ARG0', '小明', 0, 2),
                    ('ADV', '快速地', 2, 5),
                    ('LOC', '公园', 5, 7),
                ]
            ),
        ]
        invalid = SemanticRoleValidator.validate(roles)
        assert len(invalid) == 0, f"期望无无效角色，实际：{invalid}"

    def test_role_validator_invalid_role(self):
        """测试无效语义角色检测"""
        roles = [
            SemanticRole(
                predicate_idx=0,
                predicate='测试',
                arguments=[
                    ('INVALID_ROLE', '测试文本', 0, 4),
                ]
            ),
        ]
        invalid = SemanticRoleValidator.validate(roles)
        assert len(invalid) == 1
        assert invalid[0] == (0, 'INVALID_ROLE', '测试文本')

    def test_role_is_valid_role(self):
        """测试 SemanticRole.is_valid_role 方法"""
        assert SemanticRole.is_valid_role('ARG0') is True
        assert SemanticRole.is_valid_role('BNF') is True  # 受益人
        assert SemanticRole.is_valid_role('TPC') is True  # 话题
        assert SemanticRole.is_valid_role('INVALID') is False

    def test_role_categories(self):
        """测试语义角色分类"""
        # 核心论元
        assert 'ARG0' in SemanticRoleValidator.ROLE_CATEGORIES['核心论元']
        assert 'ARG1' in SemanticRoleValidator.ROLE_CATEGORIES['核心论元']
        # 附加角色
        assert 'ADV' in SemanticRoleValidator.ROLE_CATEGORIES['附加角色']
        assert 'BNF' in SemanticRoleValidator.ROLE_CATEGORIES['附加角色']
        # 特殊角色
        assert 'PRD' in SemanticRoleValidator.ROLE_CATEGORIES['特殊角色']


# =============================================================================
# 依存句法关系测试
# =============================================================================

class TestDependencyRelationSet:
    """依存句法关系测试（14 种标准关系）"""

    def test_dependency_count(self):
        """测试依存关系数量"""
        assert len(DEPENDENCY_RELATION_SET) == 14, f"期望 14 种关系，实际 {len(DEPENDENCY_RELATION_SET)} 种"

    def test_all_14_relations(self):
        """测试全部 14 种依存关系存在"""
        expected_relations = {
            'SBV', 'VOB', 'IOB', 'FOB', 'DBL',
            'ATT', 'ADV', 'CMP', 'COO', 'POB',
            'LAD', 'RAD', 'IS', 'HED',
        }
        assert DEPENDENCY_RELATION_SET == expected_relations

    def test_dependency_validator_valid_relations(self):
        """测试有效依存关系验证"""
        tokens = [
            Token('我', 0, 0, 1),
            Token('爱', 1, 1, 2),
            Token('中国', 2, 2, 4),
        ]
        dependencies = [
            DependencyRelation(tokens[0], 1, 'SBV'),  # 主谓
            DependencyRelation(tokens[1], -1, 'HED'),  # 核心
            DependencyRelation(tokens[2], 1, 'VOB'),  # 动宾
        ]
        invalid = DependencyValidator.validate(dependencies)
        assert len(invalid) == 0, f"期望无无效关系，实际：{invalid}"

    def test_dependency_validator_invalid_relation(self):
        """测试无效依存关系检测"""
        tokens = [Token('测试', 0, 0, 2)]
        dependencies = [
            DependencyRelation(tokens[0], -1, 'INVALID_REL')
        ]
        invalid = DependencyValidator.validate(dependencies)
        assert len(invalid) == 1
        assert invalid[0] == (0, 'INVALID_REL')

    def test_dependency_categories(self):
        """测试依存关系分类"""
        # 主干关系
        assert 'SBV' in DependencyValidator.RELATION_CATEGORIES['主干关系']
        assert 'VOB' in DependencyValidator.RELATION_CATEGORIES['主干关系']
        # 修饰关系
        assert 'ATT' in DependencyValidator.RELATION_CATEGORIES['修饰关系']
        assert 'ADV' in DependencyValidator.RELATION_CATEGORIES['修饰关系']


# =============================================================================
# 语义依存关系测试
# =============================================================================

class TestSemanticDependencySet:
    """语义依存关系测试（4 大类）"""

    def test_core_roles_count(self):
        """测试核心角色数量（16 种）"""
        assert len(SemanticDepValidator.CORE_ROLES) == 16

    def test_event_relations_count(self):
        """测试事件关系数量（3 种）"""
        assert len(SemanticDepValidator.EVENT_RELATIONS) == 3
        assert 'eCOO' in SemanticDepValidator.EVENT_RELATIONS
        assert 'ePREC' in SemanticDepValidator.EVENT_RELATIONS
        assert 'eSUCC' in SemanticDepValidator.EVENT_RELATIONS

    def test_dependency_markers_count(self):
        """测试依附标记数量（4 种）"""
        assert len(SemanticDepValidator.DEPENDENCY_MARKERS) == 4
        assert 'mPUNC' in SemanticDepValidator.DEPENDENCY_MARKERS
        assert 'mNEG' in SemanticDepValidator.DEPENDENCY_MARKERS

    def test_validate_relation_core_role(self):
        """测试核心角色验证"""
        assert SemanticDepValidator.validate_relation('AGT') is True
        assert SemanticDepValidator.validate_relation('PAT') is True
        assert SemanticDepValidator.validate_relation('LOC') is True

    def test_validate_relation_event(self):
        """测试事件关系验证"""
        assert SemanticDepValidator.validate_relation('eCOO') is True
        assert SemanticDepValidator.validate_relation('ePREC') is True
        assert SemanticDepValidator.validate_relation('eSUCC') is True

    def test_validate_relation_reverse(self):
        """测试反关系验证"""
        assert SemanticDepValidator.validate_relation('rEXP') is True
        assert SemanticDepValidator.validate_relation('rLOC') is True
        assert SemanticDepValidator.validate_relation('rAGT') is True

    def test_validate_relation_nested(self):
        """测试嵌套关系验证"""
        assert SemanticDepValidator.validate_relation('dCONT') is True
        assert SemanticDepValidator.validate_relation('dPAT') is True
        assert SemanticDepValidator.validate_relation('dLOC') is True

    def test_validate_relation_marker(self):
        """测试依附标记验证"""
        assert SemanticDepValidator.validate_relation('mPUNC') is True
        assert SemanticDepValidator.validate_relation('mNEG') is True
        assert SemanticDepValidator.validate_relation('mRELA') is True

    def test_validate_relation_invalid(self):
        """测试无效语义依存关系"""
        assert SemanticDepValidator.validate_relation('INVALID') is False
        assert SemanticDepValidator.validate_relation('rINVALID') is False

    def test_get_category(self):
        """测试关系分类"""
        assert SemanticDepValidator.get_category('AGT') == '语义周边角色'
        assert SemanticDepValidator.get_category('eCOO') == '事件关系'
        assert SemanticDepValidator.get_category('mNEG') == '语义依附标记'
        assert SemanticDepValidator.get_category('rEXP') == '反关系'
        assert SemanticDepValidator.get_category('dCONT') == '嵌套关系'

    def test_semantic_dependency_edge_validation(self):
        """测试语义依存边验证"""
        edges = [
            SemanticDependency(head_idx=0, dependent_idx=1, relation='AGT'),
            SemanticDependency(head_idx=1, dependent_idx=2, relation='PAT'),
            SemanticDependency(head_idx=2, dependent_idx=3, relation='eCOO'),
        ]
        invalid = SemanticDepValidator.validate(edges)
        assert len(invalid) == 0

    def test_semantic_dependency_edge_validation_invalid(self):
        """测试无效语义依存边验证"""
        edges = [
            SemanticDependency(head_idx=0, dependent_idx=1, relation='INVALID'),
        ]
        invalid = SemanticDepValidator.validate(edges)
        assert len(invalid) == 1
        assert invalid[0] == (0, 'INVALID')


# =============================================================================
# NER 标签映射测试
# =============================================================================

class TestNERMapping:
    """NER 标签映射测试"""

    def test_core_entities(self):
        """测试核心实体映射（3 种）"""
        assert NER_ENTITY_MAPPING['Nh'] == 'PERSON'
        assert NER_ENTITY_MAPPING['Ni'] == 'ORGANIZATION'
        assert NER_ENTITY_MAPPING['Ns'] == 'LOCATION'

    def test_extended_entities(self):
        """测试扩展实体映射"""
        assert NER_ENTITY_MAPPING['nt'] == 'TIME'
        assert NER_ENTITY_MAPPING['nd'] == 'DATE'
        assert NER_ENTITY_MAPPING['nz'] == 'GENERAL'


# =============================================================================
# 集成测试
# =============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_pos_tag_set_coverage(self):
        """测试完整词性标注集覆盖率"""
        # 确保所有 27 种词性都能通过验证
        for pos in POS_TAG_SET:
            assert POSTag.is_valid_pos(pos), f"词性 {pos} 未通过验证"

    def test_full_semantic_role_set_coverage(self):
        """测试完整语义角色集覆盖率"""
        # 确保所有 22 种角色都能通过验证
        for role in SEMANTIC_ROLE_SET:
            assert SemanticRole.is_valid_role(role), f"角色 {role} 未通过验证"

    def test_full_dependency_set_coverage(self):
        """测试完整依存关系集覆盖率"""
        # 确保所有 14 种关系都能通过验证
        for relation in DEPENDENCY_RELATION_SET:
            assert DependencyValidator.is_valid(relation), f"关系 {relation} 未通过验证"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
