"""
依赖注入容器 - 管理服务生命周期和依赖关系

设计原则:
1. 显式依赖 - 所有依赖通过构造函数或容器注入
2. 单一实例 - 服务在容器内单例管理
3. 作用域管理 - 支持请求级作用域
4. 自动解析 - 基于类型自动解析依赖

移除全局单例:
- event_bus -> 通过容器获取
- session_state_manager -> 通过容器获取
- manager (ConnectionManager) -> 通过容器获取
- match_service -> 通过容器获取
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Generic,
    get_type_hints, get_origin, get_args,
)
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceScope(Enum):
    """服务作用域"""
    SINGLETON = "singleton"      # 单例，容器生命周期
    SCOPED = "scoped"            # 作用域，请求生命周期
    TRANSIENT = "transient"      # 瞬态，每次创建新实例


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    service_type: Type
    implementation_type: Optional[Type] = None
    instance: Optional[Any] = None
    factory: Optional[Callable] = None
    scope: ServiceScope = ServiceScope.SINGLETON
    dependencies: List[Type] = field(default_factory=list)
    
    def resolve_type(self) -> Type:
        """解析实现类型"""
        return self.implementation_type or self.service_type


class DependencyResolutionError(Exception):
    """依赖解析异常"""
    pass


class CircularDependencyError(DependencyResolutionError):
    """循环依赖异常"""
    pass


class ServiceContainer:
    """
    依赖注入容器
    
    特性:
    - 自动依赖解析
    - 作用域管理
    - 生命周期管理
    - 循环依赖检测
    """
    
    def __init__(self, parent: Optional[ServiceContainer] = None):
        self._parent = parent
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._disposed = False
        self._resolution_stack: Set[Type] = set()  # 用于循环依赖检测
    
    def register(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        scope: ServiceScope = ServiceScope.SINGLETON,
        instance: Optional[T] = None,
        factory: Optional[Callable[..., T]] = None,
    ) -> ServiceContainer:
        """
        注册服务
        
        Args:
            service_type: 服务类型 (接口/抽象类)
            implementation_type: 实现类型
            scope: 服务作用域
            instance: 单例实例 (用于外部创建的对象)
            factory: 工厂函数
        
        Returns:
            self (支持链式调用)
        """
        if self._disposed:
            raise RuntimeError("Cannot register services on disposed container")
        
        # 验证
        if implementation_type is None and instance is None and factory is None:
            implementation_type = service_type
        
        # 创建描述符
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            instance=instance,
            factory=factory,
            scope=scope,
        )
        
        self._services[service_type] = descriptor
        
        # 如果是单例实例，立即缓存
        if instance is not None and scope == ServiceScope.SINGLETON:
            self._instances[service_type] = instance
        
        logger.debug(f"Registered service: {service_type.__name__} (scope={scope.value})")
        
        return self
    
    def register_singleton(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
    ) -> ServiceContainer:
        """注册单例服务"""
        return self.register(service_type, implementation_type, ServiceScope.SINGLETON)
    
    def register_scoped(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
    ) -> ServiceContainer:
        """注册作用域服务"""
        return self.register(service_type, implementation_type, ServiceScope.SCOPED)
    
    def register_transient(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
    ) -> ServiceContainer:
        """注册瞬态服务"""
        return self.register(service_type, implementation_type, ServiceScope.TRANSIENT)
    
    def register_instance(
        self,
        service_type: Type[T],
        instance: T,
    ) -> ServiceContainer:
        """注册实例"""
        return self.register(service_type, instance=instance, scope=ServiceScope.SINGLETON)
    
    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        scope: ServiceScope = ServiceScope.TRANSIENT,
    ) -> ServiceContainer:
        """注册工厂"""
        return self.register(service_type, factory=factory, scope=scope)
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        解析服务
        
        Args:
            service_type: 服务类型
        
        Returns:
            服务实例
        """
        if self._disposed:
            raise RuntimeError("Cannot resolve services from disposed container")
        
        # 检查循环依赖
        if service_type in self._resolution_stack:
            raise CircularDependencyError(f"Circular dependency detected: {service_type.__name__}")
        
        # 查找描述符
        descriptor = self._get_descriptor(service_type)
        
        if descriptor is None:
            # 尝试自动创建
            if inspect.isclass(service_type):
                return self._auto_create(service_type)
            raise DependencyResolutionError(f"Service not registered: {service_type}")
        
        # 根据作用域返回实例
        if descriptor.scope == ServiceScope.SINGLETON:
            return self._resolve_singleton(descriptor)
        elif descriptor.scope == ServiceScope.SCOPED:
            return self._resolve_scoped(descriptor)
        else:  # TRANSIENT
            return self._resolve_transient(descriptor)
    
    def _get_descriptor(self, service_type: Type) -> Optional[ServiceDescriptor]:
        """获取服务描述符"""
        if service_type in self._services:
            return self._services[service_type]
        if self._parent:
            return self._parent._get_descriptor(service_type)
        return None
    
    def _resolve_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """解析单例"""
        service_type = descriptor.service_type
        
        if service_type in self._instances:
            return self._instances[service_type]
        
        instance = self._create_instance(descriptor)
        self._instances[service_type] = instance
        return instance
    
    def _resolve_scoped(self, descriptor: ServiceDescriptor) -> Any:
        """解析作用域实例"""
        # 作用域实例在当前容器缓存
        if descriptor.service_type in self._instances:
            return self._instances[descriptor.service_type]
        
        instance = self._create_instance(descriptor)
        self._instances[descriptor.service_type] = instance
        return instance
    
    def _resolve_transient(self, descriptor: ServiceDescriptor) -> Any:
        """解析瞬态实例"""
        return self._create_instance(descriptor)
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建实例"""
        # 使用工厂
        if descriptor.factory:
            return self._invoke_factory(descriptor.factory)
        
        # 使用已有实例
        if descriptor.instance:
            return descriptor.instance
        
        # 创建新实例
        impl_type = descriptor.resolve_type()
        return self._instantiate(impl_type)
    
    def _instantiate(self, cls: Type) -> Any:
        """实例化类型"""
        # 添加到解析栈 (循环依赖检测)
        self._resolution_stack.add(cls)
        
        try:
            # 获取构造函数参数
            sig = inspect.signature(cls.__init__)
            parameters = sig.parameters
            
            # 解析依赖
            kwargs = {}
            for name, param in parameters.items():
                if name == 'self':
                    continue
                
                param_type = self._get_parameter_type(cls, name)
                if param_type:
                    kwargs[name] = self.resolve(param_type)
                elif param.default is not inspect.Parameter.empty:
                    kwargs[name] = param.default
            
            # 创建实例
            instance = cls(**kwargs)
            logger.debug(f"Created instance: {cls.__name__}")
            return instance
            
        finally:
            self._resolution_stack.remove(cls)
    
    def _get_parameter_type(self, cls: Type, param_name: str) -> Optional[Type]:
        """获取参数类型"""
        try:
            hints = get_type_hints(cls.__init__)
            return hints.get(param_name)
        except Exception:
            return None
    
    def _invoke_factory(self, factory: Callable) -> Any:
        """调用工厂函数"""
        sig = inspect.signature(factory)
        kwargs = {}
        
        for name, param in sig.parameters.items():
            param_type = self._get_factory_parameter_type(factory, name)
            if param_type:
                kwargs[name] = self.resolve(param_type)
            elif param.default is not inspect.Parameter.empty:
                kwargs[name] = param.default
        
        return factory(**kwargs)
    
    def _get_factory_parameter_type(self, factory: Callable, param_name: str) -> Optional[Type]:
        """获取工厂参数类型"""
        try:
            hints = get_type_hints(factory)
            return hints.get(param_name)
        except Exception:
            return None
    
    def _auto_create(self, cls: Type) -> Any:
        """自动创建类型实例"""
        # 检查是否有已注册的依赖
        try:
            return self._instantiate(cls)
        except DependencyResolutionError:
            raise
    
    def resolve_all(self, service_type: Type[T]) -> List[T]:
        """解析所有匹配的服务"""
        results = []
        for type_, descriptor in self._services.items():
            if self._is_assignable(type_, service_type):
                results.append(self.resolve(type_))
        return results
    
    def _is_assignable(self, impl_type: Type, service_type: Type) -> bool:
        """检查类型是否可赋值"""
        try:
            return issubclass(impl_type, service_type)
        except TypeError:
            return False
    
    def create_scope(self) -> ServiceContainer:
        """创建新的作用域"""
        return ServiceContainer(parent=self)
    
    def dispose(self):
        """释放容器"""
        self._disposed = True
        self._instances.clear()
        self._resolution_stack.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()


# ============== 异步服务容器 ==============


class AsyncServiceContainer:
    """
    异步服务容器
    
    支持异步工厂和异步初始化
    """
    
    def __init__(self, parent: Optional[AsyncServiceContainer] = None):
        self._parent = parent
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._async_factories: Dict[Type, Callable] = {}
        self._disposed = False
        self._resolution_stack: Set[Type] = set()
    
    def register(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        scope: ServiceScope = ServiceScope.SINGLETON,
        instance: Optional[T] = None,
        factory: Optional[Callable[..., T]] = None,
        async_factory: Optional[Callable[..., Coroutine[Any, Any, T]]] = None,
    ) -> AsyncServiceContainer:
        """注册服务"""
        if self._disposed:
            raise RuntimeError("Cannot register services on disposed container")

        if implementation_type is None and instance is None and factory is None and async_factory is None:
            implementation_type = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            instance=instance,
            factory=factory,
            scope=scope,
        )

        self._services[service_type] = descriptor

        if instance is not None and scope == ServiceScope.SINGLETON:
            self._instances[service_type] = instance

        if async_factory:
            self._async_factories[service_type] = async_factory

        logger.debug(f"Registered service: {service_type.__name__} (scope={scope.value})")
        return self

    def register_async_factory(
        self,
        service_type: Type[T],
        async_factory: Callable[..., Coroutine[Any, Any, T]],
    ) -> AsyncServiceContainer:
        """
        注册异步工厂
        
        Args:
            service_type: 服务类型
            async_factory: 异步工厂函数
            
        Returns:
            容器实例
        """
        return self.register(service_type, async_factory=async_factory)
    
    async def resolve(self, service_type: Type[T]) -> T:
        """异步解析服务"""
        if self._disposed:
            raise RuntimeError("Cannot resolve services from disposed container")
        
        if service_type in self._resolution_stack:
            raise CircularDependencyError(f"Circular dependency detected: {service_type.__name__}")
        
        descriptor = self._get_descriptor(service_type)
        
        if descriptor is None:
            if inspect.isclass(service_type):
                return await self._auto_create(service_type)
            raise DependencyResolutionError(f"Service not registered: {service_type}")
        
        if descriptor.scope == ServiceScope.SINGLETON:
            return await self._resolve_singleton(descriptor)
        elif descriptor.scope == ServiceScope.SCOPED:
            return await self._resolve_scoped(descriptor)
        else:
            return await self._resolve_transient(descriptor)
    
    def _get_descriptor(self, service_type: Type) -> Optional[ServiceDescriptor]:
        if service_type in self._services:
            return self._services[service_type]
        if self._parent:
            return self._parent._get_descriptor(service_type)
        return None
    
    async def _resolve_singleton(self, descriptor: ServiceDescriptor) -> Any:
        service_type = descriptor.service_type
        if service_type in self._instances:
            return self._instances[service_type]
        instance = await self._create_instance(descriptor)
        self._instances[service_type] = instance
        return instance
    
    async def _resolve_scoped(self, descriptor: ServiceDescriptor) -> Any:
        if descriptor.service_type in self._instances:
            return self._instances[descriptor.service_type]
        instance = await self._create_instance(descriptor)
        self._instances[descriptor.service_type] = instance
        return instance
    
    async def _resolve_transient(self, descriptor: ServiceDescriptor) -> Any:
        return await self._create_instance(descriptor)
    
    async def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        # 异步工厂
        if descriptor.service_type in self._async_factories:
            return await self._async_factories[descriptor.service_type]()
        
        # 同步工厂
        if descriptor.factory:
            return self._invoke_factory(descriptor.factory)
        
        # 实例
        if descriptor.instance:
            return descriptor.instance
        
        # 创建
        impl_type = descriptor.resolve_type()
        return await self._instantiate(impl_type)
    
    async def _instantiate(self, cls: Type) -> Any:
        self._resolution_stack.add(cls)
        try:
            sig = inspect.signature(cls.__init__)
            kwargs = {}
            
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue
                
                param_type = self._get_parameter_type(cls, name)
                if param_type:
                    kwargs[name] = await self.resolve(param_type)
                elif param.default is not inspect.Parameter.empty:
                    kwargs[name] = param.default
            
            instance = cls(**kwargs)
            
            # 检查是否有异步初始化方法
            if hasattr(instance, 'initialize') and asyncio.iscoroutinefunction(instance.initialize):
                await instance.initialize()
            
            logger.debug(f"Created instance: {cls.__name__}")
            return instance
        finally:
            self._resolution_stack.remove(cls)
    
    def _get_parameter_type(self, cls: Type, param_name: str) -> Optional[Type]:
        try:
            hints = get_type_hints(cls.__init__)
            return hints.get(param_name)
        except Exception:
            return None
    
    def _invoke_factory(self, factory: Callable) -> Any:
        sig = inspect.signature(factory)
        kwargs = {}
        for name, param in sig.parameters.items():
            param_type = self._get_factory_parameter_type(factory, name)
            if param_type:
                kwargs[name] = self._resolve_sync(param_type)
            elif param.default is not inspect.Parameter.empty:
                kwargs[name] = param.default
        return factory(**kwargs)
    
    def _resolve_sync(self, service_type: Type) -> Any:
        """同步解析 (用于工厂参数)"""
        descriptor = self._get_descriptor(service_type)
        if descriptor and service_type in self._instances:
            return self._instances[service_type]
        raise DependencyResolutionError(f"Cannot synchronously resolve: {service_type}")
    
    def _get_factory_parameter_type(self, factory: Callable, param_name: str) -> Optional[Type]:
        try:
            hints = get_type_hints(factory)
            return hints.get(param_name)
        except Exception:
            return None
    
    async def _auto_create(self, cls: Type) -> Any:
        return await self._instantiate(cls)
    
    def create_scope(self) -> AsyncServiceContainer:
        """创建作用域"""
        return AsyncServiceContainer(parent=self)
    
    def dispose(self):
        self._disposed = True
        self._instances.clear()
        self._resolution_stack.clear()


# ============== FastAPI 集成 ==============


def create_container() -> AsyncServiceContainer:
    """
    创建根容器

    注册所有核心服务
    """
    container = AsyncServiceContainer()

    # 注册基础设施服务
    from turing_test.backend.infrastructure.events.event_bus import EventBus, event_bus
    from turing_test.backend.infrastructure.cqrs.cqrs import CommandBus, QueryBus, TransactionManager
    from turing_test.backend.infrastructure.messaging.message_router import MessageRouter, MessageQueue, ConnectionManager
    from turing_test.backend.infrastructure.transaction.transaction_manager import TransactionalCoordinator

    # 事件总线 (单例)
    container.register_instance(EventBus, event_bus)

    # 命令/查询总线
    container.register_singleton(CommandBus)
    container.register_singleton(QueryBus)

    # 消息组件
    container.register_singleton(MessageQueue)
    container.register_singleton(MessageRouter)
    container.register_singleton(ConnectionManager)

    # 注册 Repository 接口到实现
    from turing_test.backend.infrastructure.repositories import (
        MatchRepositoryImpl,
        RoomRepositoryImpl,
        UserSessionRepositoryImpl,
        ScoreRepositoryImpl,
    )
    from turing_test.backend.domain.repositories import (
        MatchRepository,
        RoomRepository,
        UserSessionRepository,
        ScoreRepository,
    )

    # 应用服务
    from turing_test.backend.application.match_service import MatchApplicationService
    from turing_test.backend.application.room_service import RoomApplicationService
    from turing_test.backend.application.session_service import SessionApplicationService

    # 事件处理器
    from turing_test.backend.infrastructure.events.event_handlers import (
        MatchEventHandler,
        RoomEventHandler,
    )

    # 注意：应用服务和事件处理器的完整注册需要在应用启动时完成
    # 因为它们需要依赖工作单元和具体的服务实例
    # 这里只注册类型，实际解析在请求作用域中进行

    return container


@asynccontextmanager
async def request_scope(container: AsyncServiceContainer):
    """
    请求作用域上下文管理器
    
    用法:
        async with request_scope(container) as scope:
            service = await scope.resolve(ServiceType)
    """
    scope = container.create_scope()
    try:
        yield scope
    finally:
        scope.dispose()


# ============== 依赖注入装饰器 ==============


def inject(func):
    """
    依赖注入装饰器
    
    自动解析函数参数
    
    用法:
        @inject
        async def handle(service1: Service1, service2: Service2):
            ...
    """
    async def wrapper(*args, **kwargs):
        # 获取容器 (从全局或上下文)
        container = kwargs.pop('_container', None)
        if not container:
            # 尝试从上下文获取
            container = get_current_container()
        
        if not container:
            raise RuntimeError("No container available for injection")
        
        # 解析参数
        hints = get_type_hints(func)
        for name, type_ in hints.items():
            if name not in kwargs and name != 'return':
                kwargs[name] = await container.resolve(type_)
        
        return await func(*args, **kwargs)
    
    return wrapper


# 全局容器上下文
_current_container: Optional[AsyncServiceContainer] = None


def set_current_container(container: AsyncServiceContainer):
    """设置当前容器"""
    global _current_container
    _current_container = container


def get_current_container() -> Optional[AsyncServiceContainer]:
    """获取当前容器"""
    return _current_container
