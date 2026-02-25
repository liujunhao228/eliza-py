#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本上下文模块

提供统一的脚本上下文对象，封装所有脚本执行所需的数据。

本模块不依赖任何 alice 其他模块，确保 scripting 包的独立性。

设计目标:
- 统一数据接口：Lua 和 YAML 脚本使用相同的上下文结构
- 安全访问：提供只读模式和变量隔离
- 易于序列化：支持转换为字典格式供脚本语言访问
- 无外部依赖：所有字段都是基本类型或标准库类型
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import copy


@dataclass
class ScriptContext:
    """
    统一脚本上下文
    
    封装所有脚本执行所需的数据，提供安全的访问接口。
    
    所有字段都是基本类型或标准库类型，不依赖任何外部模块。
    
    使用示例:
        # 创建上下文
        ctx = ScriptContext(
            text="你好，我叫小明",
            tokens=["你好", "，", "我", "叫", "小明"],
            entities=[("PERSON", "小明")],
            turn_count=5,
        )
        
        # 访问数据
        print(ctx.text)  # "你好，我叫小明"
        print(ctx.get("entities"))  # [("PERSON", "小明")]
        
        # 设置脚本变量（脚本间共享）
        ctx.set_variable("user_mood", "happy")
        
        # 创建只读副本（安全传递给脚本）
        frozen_ctx = ctx.freeze()
    """
    
    # =========================================================================
    # 输入数据
    # =========================================================================
    
    #: 原始输入文本
    text: str = ""
    
    #: 分词结果
    tokens: List[str] = field(default_factory=list)
    
    #: 命名实体列表 [(类型，文本), ...]
    entities: List[Tuple[str, str]] = field(default_factory=list)
    
    #: 句法分析结果
    syntax: Optional[Dict[str, Any]] = None
    
    #: 词性标注列表 [(词，词性), ...]
    pos_tags: List[Tuple[str, str]] = field(default_factory=list)
    
    #: 依存句法关系
    dependencies: List[Dict[str, Any]] = field(default_factory=list)

    #: 主谓宾三元组 [(主语，谓语，宾语), ...]
    triples: List[Tuple[str, str, str]] = field(default_factory=list)

    #: 语义角色标注
    semantic_roles: List[Dict[str, Any]] = field(default_factory=list)

    #: 语义依存关系
    semantic_deps: List[Dict[str, Any]] = field(default_factory=list)
    
    # =========================================================================
    # 对话上下文
    # =========================================================================
    
    #: 对话轮数
    turn_count: int = 0
    
    #: 最近对话轮次 [{"user_input": ..., "bot_response": ...}, ...]
    recent_turns: List[Dict[str, str]] = field(default_factory=list)
    
    #: 时间上下文
    time_context: Dict[str, Any] = field(default_factory=dict)
    
    #: 用户画像
    user_profile: Dict[str, Any] = field(default_factory=dict)
    
    # =========================================================================
    # 脚本执行状态
    # =========================================================================
    
    #: 已匹配的脚本 ID 列表
    matched_scripts: List[str] = field(default_factory=list)
    
    #: 脚本变量（脚本间共享）
    variables: Dict[str, Any] = field(default_factory=dict)
    
    #: 只读标志
    _readonly: bool = field(default=False, repr=False)
    
    # =========================================================================
    # 数据访问方法
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（供脚本访问）

        返回的字典包含所有可公开访问的上下文数据，适合传递给 Lua/YAML 脚本。

        Returns:
            上下文字典
        """
        return {
            # 输入数据
            'text': self.text,
            'tokens': self.tokens.copy(),
            'entities': self.entities.copy(),
            'pos_tags': self.pos_tags.copy(),
            'dependencies': self.dependencies.copy(),
            'syntax': copy.deepcopy(self.syntax) if self.syntax else None,
            'triples': self.triples.copy(),
            'semantic_roles': copy.deepcopy(self.semantic_roles),
            'semantic_deps': copy.deepcopy(self.semantic_deps),

            # 对话上下文
            'turn_count': self.turn_count,
            'recent_turns': [turn.copy() for turn in self.recent_turns],
            'time_context': self.time_context.copy(),
            'user_profile': self.user_profile.copy(),

            # 脚本执行状态
            'matched_scripts': self.matched_scripts.copy(),
            'variables': self.variables.copy(),
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        安全获取上下文值
        
        Args:
            key: 键名
            default: 默认值
            
        Returns:
            对应的值，不存在时返回默认值
        """
        data = self.to_dict()
        return data.get(key, default)
    
    def has(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键名
            
        Returns:
            是否存在
        """
        return key in self.to_dict()
    
    # =========================================================================
    # 变量管理方法
    # =========================================================================
    
    def set_variable(self, key: str, value: Any) -> None:
        """
        设置脚本变量
        
        脚本变量在所有脚本间共享，可用于脚本间通信。
        
        Args:
            key: 变量名
            value: 变量值
            
        Raises:
            RuntimeError: 当上下文处于只读模式时
        """
        if self._readonly:
            raise RuntimeError("上下文处于只读模式，无法修改变量")
        self.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """
        获取脚本变量
        
        Args:
            key: 变量名
            default: 默认值
            
        Returns:
            变量值
        """
        return self.variables.get(key, default)
    
    def has_variable(self, key: str) -> bool:
        """
        检查变量是否存在
        
        Args:
            key: 变量名
            
        Returns:
            是否存在
        """
        return key in self.variables
    
    def remove_variable(self, key: str) -> bool:
        """
        移除变量
        
        Args:
            key: 变量名
            
        Returns:
            是否成功移除
        """
        if key in self.variables:
            del self.variables[key]
            return True
        return False
    
    def clear_variables(self) -> None:
        """清空所有脚本变量"""
        self.variables.clear()
    
    # =========================================================================
    # 上下文变换
    # =========================================================================
    
    def freeze(self) -> 'ScriptContext':
        """
        创建只读副本

        只读副本无法修改，适合安全地传递给脚本执行。

        Returns:
            只读上下文副本
        """
        frozen = ScriptContext(
            text=self.text,
            tokens=self.tokens.copy(),
            entities=self.entities.copy(),
            pos_tags=self.pos_tags.copy(),
            dependencies=self.dependencies.copy(),
            syntax=copy.deepcopy(self.syntax) if self.syntax else None,
            triples=self.triples.copy(),
            semantic_roles=copy.deepcopy(self.semantic_roles),
            semantic_deps=copy.deepcopy(self.semantic_deps),
            turn_count=self.turn_count,
            recent_turns=[turn.copy() for turn in self.recent_turns],
            time_context=self.time_context.copy(),
            user_profile=self.user_profile.copy(),
            matched_scripts=self.matched_scripts.copy(),
            variables=self.variables.copy(),
        )
        frozen._readonly = True
        return frozen
    
    def merge(self, other: 'ScriptContext') -> 'ScriptContext':
        """
        合并另一个上下文

        另一个上下文的值会覆盖当前上下文的同名值。

        Args:
            other: 要合并的上下文

        Returns:
            合并后的新上下文
        """
        return ScriptContext(
            text=other.text or self.text,
            tokens=other.tokens or self.tokens,
            entities=other.entities or self.entities,
            pos_tags=other.pos_tags or self.pos_tags,
            dependencies=other.dependencies or self.dependencies,
            syntax=other.syntax or self.syntax,
            triples=other.triples or self.triples,
            semantic_roles=other.semantic_roles or self.semantic_roles,
            semantic_deps=other.semantic_deps or self.semantic_deps,
            turn_count=other.turn_count or self.turn_count,
            recent_turns=other.recent_turns or self.recent_turns,
            time_context=other.time_context or self.time_context,
            user_profile=other.user_profile or self.user_profile,
            matched_scripts=self.matched_scripts + other.matched_scripts,
            variables={**self.variables, **other.variables},
        )
    
    # =========================================================================
    # 便捷访问方法
    # =========================================================================
    
    def get_entity_by_type(self, entity_type: str) -> List[str]:
        """
        根据类型获取实体
        
        Args:
            entity_type: 实体类型
            
        Returns:
            实体文本列表
        """
        return [
            text for etype, text in self.entities 
            if etype.upper() == entity_type.upper()
        ]
    
    def get_first_entity(self, entity_type: Optional[str] = None) -> Optional[str]:
        """
        获取第一个实体
        
        Args:
            entity_type: 实体类型（可选）
            
        Returns:
            实体文本，不存在时返回 None
        """
        if not self.entities:
            return None
        
        if entity_type:
            for etype, text in self.entities:
                if etype.upper() == entity_type.upper():
                    return text
            return None
        
        return self.entities[0][1] if self.entities else None
    
    def has_entity(self, entity_type: str) -> bool:
        """
        检查是否包含指定类型的实体
        
        Args:
            entity_type: 实体类型
            
        Returns:
            是否包含
        """
        return any(
            etype.upper() == entity_type.upper() 
            for etype, _ in self.entities
        )
    
    def get_subject(self) -> Optional[str]:
        """获取主语"""
        if self.syntax:
            return self.syntax.get('subject')
        return None
    
    def get_predicate(self) -> Optional[str]:
        """获取谓语"""
        if self.syntax:
            return self.syntax.get('predicate')
        return None
    
    def get_object(self) -> Optional[str]:
        """获取宾语"""
        if self.syntax:
            return self.syntax.get('object')
        return None

    def get_triples(self) -> List[Tuple[str, str, str]]:
        """获取三元组列表"""
        return self.triples

    def get_semantic_roles(self) -> List[Dict[str, Any]]:
        """获取语义角色列表"""
        return self.semantic_roles

    def get_semantic_deps(self) -> List[Dict[str, Any]]:
        """获取语义依存列表"""
        return self.semantic_deps

    def get_time(self, key: str, default: Any = None) -> Any:
        """
        获取时间上下文值
        
        Args:
            key: 时间键名（如 "hour", "weekday"）
            default: 默认值
            
        Returns:
            时间值
        """
        return self.time_context.get(key, default)
    
    def get_user_info(self, key: str, default: Any = None) -> Any:
        """
        获取用户画像值
        
        Args:
            key: 画像键名（如 "name", "nickname"）
            default: 默认值
            
        Returns:
            画像值
        """
        return self.user_profile.get(key, default)
    
    # =========================================================================
    # 调试和序列化
    # =========================================================================
    
    def is_readonly(self) -> bool:
        """检查是否为只读模式"""
        return self._readonly
    
    def summary(self) -> Dict[str, Any]:
        """
        获取上下文摘要
        
        Returns:
            摘要字典
        """
        return {
            'text_length': len(self.text),
            'token_count': len(self.tokens),
            'entity_count': len(self.entities),
            'turn_count': self.turn_count,
            'has_syntax': self.syntax is not None,
            'variable_count': len(self.variables),
            'is_readonly': self._readonly,
        }
    
    def __repr__(self) -> str:
        return (
            f"ScriptContext(text={self.text!r}, "
            f"tokens={len(self.tokens)}, "
            f"entities={len(self.entities)}, "
            f"turn_count={self.turn_count})"
        )
