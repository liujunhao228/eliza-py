"""
依赖注入模块
"""

from turing_test.backend.infrastructure.di.container import (
    ServiceContainer,
    AsyncServiceContainer,
    ServiceScope,
    DependencyResolutionError,
    CircularDependencyError,
    create_container,
    request_scope,
    inject,
    set_current_container,
    get_current_container,
)

__all__ = [
    'ServiceContainer',
    'AsyncServiceContainer',
    'ServiceScope',
    'DependencyResolutionError',
    'CircularDependencyError',
    'create_container',
    'request_scope',
    'inject',
    'set_current_container',
    'get_current_container',
]
