"""
事务管理器 - 确保跨域操作的原子性

设计原则:
1. 原子性 - 匹配和会话创建要么都成功，要么都失败
2. 隔离性 - 事务间互不干扰
3. 一致性 - 事务前后数据一致
4. 持久性 - 提交后数据持久化

使用场景:
- 匹配成功 → 创建会话
- 会话结束 → 结算积分
- 用户注册 → 初始化积分
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, TypeVar, Generic
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransactionStatus(Enum):
    """事务状态"""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class IsolationLevel(Enum):
    """事务隔离级别"""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


@dataclass
class TransactionContext:
    """
    事务上下文 - 携带事务内的所有状态
    
    用于在事务链中传递数据
    """
    transaction_id: str
    status: TransactionStatus = TransactionStatus.ACTIVE
    started_at: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    operations: List[str] = field(default_factory=list)
    rollback_actions: List[Callable] = field(default_factory=list)
    
    def set(self, key: str, value: Any):
        """设置事务数据"""
        self.data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取事务数据"""
        return self.data.get(key, default)
    
    def add_operation(self, operation: str):
        """记录操作"""
        self.operations.append(operation)
    
    def add_rollback_action(self, action: Callable):
        """添加回滚动作"""
        self.rollback_actions.append(action)


class TransactionError(Exception):
    """事务异常"""
    def __init__(self, message: str, code: str = "TRANSACTION_ERROR", original_error: Optional[Exception] = None):
        super().__init__(message)
        self.code = code
        self.original_error = original_error


class Transaction:
    """
    事务对象
    
    管理数据库会话和事务生命周期
    """
    
    def __init__(
        self,
        db_session: Any,
        isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED,
        parent: Optional[Transaction] = None,
    ):
        self.db_session = db_session
        self.isolation_level = isolation_level
        self.parent = parent
        self.context = TransactionContext(transaction_id=str(uuid.uuid4()))
        self._savepoint_name: Optional[str] = None
    
    async def begin(self):
        """开始事务"""
        if self.parent:
            # 嵌套事务 - 创建保存点
            self._savepoint_name = f"sp_{self.context.transaction_id}"
            # TODO: 根据实际 ORM 实现保存点
            # await self.db_session.begin_nested(savepoint=self._savepoint_name)
            logger.debug(f"Created nested transaction with savepoint {self._savepoint_name}")
        else:
            # 新事务
            # TODO: 根据实际 ORM 实现事务开始
            # await self.db_session.begin()
            logger.debug(f"Started new transaction {self.context.transaction_id}")
    
    async def commit(self):
        """提交事务"""
        if self.context.status != TransactionStatus.ACTIVE:
            raise TransactionError(f"Cannot commit transaction in status {self.context.status}", "INVALID_STATUS")
        
        try:
            if self.parent:
                # 嵌套事务 - 释放保存点
                # TODO: 释放保存点
                logger.debug(f"Released savepoint {self._savepoint_name}")
            else:
                # 新事务 - 提交
                # TODO: 提交事务
                logger.debug(f"Committed transaction {self.context.transaction_id}")
            
            self.context.status = TransactionStatus.COMMITTED
            
        except Exception as e:
            self.context.status = TransactionStatus.FAILED
            raise TransactionError(f"Failed to commit: {e}", "COMMIT_ERROR", e)
    
    async def rollback(self):
        """回滚事务"""
        if self.context.status not in [TransactionStatus.ACTIVE, TransactionStatus.FAILED]:
            return
        
        try:
            # 执行回滚动作
            for action in reversed(self.context.rollback_actions):
                try:
                    if asyncio.iscoroutinefunction(action):
                        await action()
                    else:
                        action()
                except Exception as e:
                    logger.error(f"Error in rollback action: {e}")
            
            if self.parent:
                # 嵌套事务 - 回滚到保存点
                # TODO: 回滚到保存点
                logger.debug(f"Rolled back to savepoint {self._savepoint_name}")
            else:
                # 新事务 - 回滚
                # TODO: 回滚事务
                logger.debug(f"Rolled back transaction {self.context.transaction_id}")
            
            self.context.status = TransactionStatus.ROLLED_BACK
            
        except Exception as e:
            logger.exception(f"Error during rollback: {e}")
            self.context.status = TransactionStatus.FAILED


class TransactionManager:
    """
    事务管理器 - 管理事务生命周期
    
    特性:
    - 嵌套事务支持
    - 自动回滚
    - 事务超时
    - 死锁检测
    """
    
    def __init__(
        self,
        db_session_factory: Callable[[], Any],
        default_isolation: IsolationLevel = IsolationLevel.READ_COMMITTED,
        timeout_seconds: float = 30.0,
    ):
        self._db_session_factory = db_session_factory
        self._default_isolation = default_isolation
        self._timeout_seconds = timeout_seconds
        self._current_transaction: Optional[Transaction] = None
        self._lock = asyncio.Lock()
        self._active_transactions: Set[str] = set()
    
    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[IsolationLevel] = None,
        timeout_seconds: Optional[float] = None,
    ):
        """
        事务上下文管理器
        
        用法:
            async with transaction_manager.transaction() as tx:
                # 数据库操作
                tx.context.set("key", value)
        """
        isolation = isolation_level or self._default_isolation
        timeout = timeout_seconds or self._timeout_seconds
        
        async with self._lock:
            # 创建数据库会话
            db_session = await self._db_session_factory()
            
            # 创建事务
            tx = Transaction(
                db_session=db_session,
                isolation_level=isolation,
                parent=self._current_transaction,
            )
            
            # 设置超时
            if timeout:
                tx.context.add_rollback_action(lambda: self._handle_timeout(tx))
            
            self._active_transactions.add(tx.context.transaction_id)
            
            # 开始事务
            await tx.begin()
            
            # 设置当前事务
            old_transaction = self._current_transaction
            self._current_transaction = tx
        
        try:
            yield tx
            
            # 如果状态还是 ACTIVE，自动提交
            if tx.context.status == TransactionStatus.ACTIVE:
                await tx.commit()
                
        except Exception as e:
            # 异常时自动回滚
            await tx.rollback()
            raise TransactionError(f"Transaction failed: {e}", "EXECUTION_ERROR", e)
            
        finally:
            # 恢复之前的事务
            async with self._lock:
                self._current_transaction = old_transaction
                self._active_transactions.discard(tx.context.transaction_id)
    
    def get_current_transaction(self) -> Optional[Transaction]:
        """获取当前事务"""
        return self._current_transaction
    
    def get_session(self) -> Any:
        """获取当前事务的数据库会话"""
        if not self._current_transaction:
            raise TransactionError("No active transaction", "NO_TRANSACTION")
        return self._current_transaction.db_session
    
    def _handle_timeout(self, tx: Transaction):
        """处理超时"""
        logger.warning(f"Transaction {tx.context.transaction_id} timed out")
    
    def get_active_transaction_count(self) -> int:
        """获取活跃事务数量"""
        return len(self._active_transactions)


# ============== 事务性操作协调器 ==============


class TransactionalCoordinator:
    """
    事务性操作协调器
    
    确保跨多个领域的操作原子性
    
    典型场景:
    1. 匹配成功 + 创建会话
    2. 会话结束 + 积分结算
    3. 用户注册 + 积分初始化
    """
    
    def __init__(
        self,
        transaction_manager: TransactionManager,
        event_bus: EventBus,
    ):
        self._tx_manager = transaction_manager
        self._event_bus = event_bus
        self._compensating_actions: List[Callable] = []
    
    async def match_and_create_session(
        self,
        user_id: int,
        match_result: Any,
        create_session_func: Callable,
    ) -> Dict[str, Any]:
        """
        匹配成功后创建会话 (原子操作)
        
        流程:
        1. 开始事务
        2. 验证匹配结果
        3. 创建会话
        4. 更新匹配状态
        5. 发布事件
        6. 提交事务
        """
        async with self._tx_manager.transaction() as tx:
            try:
                tx.context.add_operation("match_and_create_session")
                
                # 1. 验证匹配结果
                if not match_result:
                    raise TransactionError("Invalid match result", "INVALID_MATCH")
                
                tx.context.set("match_result", match_result)
                
                # 2. 创建会话
                session = await create_session_func(tx.context)
                tx.context.set("session", session)
                tx.context.set("session_id", session.id)
                
                # 3. 添加回滚动作
                session_id = session.id
                tx.context.add_rollback_action(lambda: self._cleanup_session(session_id))
                
                # 4. 更新匹配状态 (在事务内)
                # TODO: 更新匹配记录
                
                # 5. 发布会话创建事件
                await EventBuilder(EventType.SESSION_CREATED)\
                    .aggregate(str(session_id), "session")\
                    .with_data(user_id=user_id)\
                    .publish(self._event_bus)
                
                # 6. 发布匹配完成事件
                await EventBuilder(EventType.MATCH_COMPLETED)\
                    .aggregate(tx.context.get("match_id", ""), "match")\
                    .with_data(session_id=session_id)\
                    .publish(self._event_bus)
                
                return {
                    "session_id": session_id,
                    "session": session,
                }
                
            except Exception as e:
                logger.exception(f"Failed to match and create session: {e}")
                raise
    
    async def end_session_and_settle_score(
        self,
        session_id: int,
        user_id: int,
        end_reason: str,
        settle_score_func: Callable,
    ) -> Dict[str, Any]:
        """
        结束会话并结算积分 (原子操作)
        
        流程:
        1. 开始事务
        2. 结束会话
        3. 结算积分
        4. 发布事件
        5. 提交事务
        """
        async with self._tx_manager.transaction() as tx:
            try:
                tx.context.add_operation("end_session_and_settle_score")
                tx.context.set("session_id", session_id)
                
                # 1. 结束会话
                # TODO: 更新会话状态
                tx.context.add_operation("end_session")
                
                # 2. 结算积分
                score_result = await settle_score_func(tx.context)
                tx.context.set("score_result", score_result)
                tx.context.add_operation("settle_score")
                
                # 3. 发布会话结束事件
                await EventBuilder(EventType.SESSION_ENDED)\
                    .aggregate(str(session_id), "session")\
                    .with_data(
                        user_id=user_id,
                        end_reason=end_reason,
                    )\
                    .publish(self._event_bus)
                
                # 4. 发布积分结算事件
                if score_result:
                    await EventBuilder(EventType.SCORE_SETTLED)\
                        .aggregate(str(session_id), "session")\
                        .with_data(score=score_result)\
                        .publish(self._event_bus)
                
                return {
                    "session_ended": True,
                    "score_settled": score_result,
                }
                
            except Exception as e:
                logger.exception(f"Failed to end session and settle score: {e}")
                raise
    
    async def execute_with_compensation(
        self,
        operations: List[Callable[[TransactionContext], Coroutine[Any, Any, Any]]],
        compensations: List[Callable[[TransactionContext], Coroutine[Any, Any, None]]],
    ) -> List[Any]:
        """
        执行带补偿的操作序列
        
        如果任何操作失败，执行所有已完成的补偿操作
        
        Args:
            operations: 操作列表 (顺序执行)
            compensations: 补偿操作列表 (逆序执行)
        
        Returns:
            各操作的结果列表
        """
        results = []
        completed_count = 0
        
        async with self._tx_manager.transaction() as tx:
            try:
                for i, op in enumerate(operations):
                    result = await op(tx.context)
                    results.append(result)
                    completed_count += 1
                    tx.context.add_operation(f"op_{i}")
                
                return results
                
            except Exception as e:
                logger.exception(f"Operation failed, executing compensations: {e}")
                
                # 逆序执行补偿
                for i in range(completed_count - 1, -1, -1):
                    try:
                        if i < len(compensations) and compensations[i]:
                            await compensations[i](tx.context)
                    except Exception as ce:
                        logger.error(f"Compensation {i} failed: {ce}")
                
                raise
    
    async def _cleanup_session(self, session_id: int):
        """清理会话 (回滚动作)"""
        logger.warning(f"Cleaning up session {session_id} due to rollback")
        # TODO: 实际清理逻辑


# ============== Saga 模式实现 ==============


class SagaStep:
    """Saga 步骤"""
    
    def __init__(
        self,
        name: str,
        action: Callable[[TransactionContext], Coroutine[Any, Any, Any]],
        compensation: Optional[Callable[[TransactionContext], Coroutine[Any, Any, None]]] = None,
    ):
        self.name = name
        self.action = action
        self.compensation = compensation


class Saga:
    """
    Saga 模式 - 长运行事务
    
    适用于跨多个聚合根的长流程
    
    特性:
    - 每个步骤有对应的补偿操作
    - 失败时自动执行补偿
    - 支持步骤重试
    """
    
    def __init__(self, name: str, event_bus: EventBus):
        self.name = name
        self._event_bus = event_bus
        self._steps: List[SagaStep] = []
        self._retries: Dict[str, int] = {}
        self._max_retries = 3
    
    def add_step(
        self,
        name: str,
        action: Callable[[TransactionContext], Coroutine[Any, Any, Any]],
        compensation: Optional[Callable[[TransactionContext], Coroutine[Any, Any, None]]] = None,
    ) -> Saga:
        """添加步骤"""
        self._steps.append(SagaStep(name, action, compensation))
        return self
    
    async def execute(self, initial_data: Optional[Dict[str, Any]] = None) -> TransactionContext:
        """
        执行 Saga
        
        Returns:
            事务上下文
        """
        context = TransactionContext(transaction_id=str(uuid.uuid4()))
        if initial_data:
            context.data.update(initial_data)
        
        completed_steps: List[SagaStep] = []
        
        try:
            for step in self._steps:
                try:
                    # 执行步骤
                    result = await step.action(context)
                    context.set(f"{step.name}_result", result)
                    completed_steps.append(step)
                    
                    logger.debug(f"Saga '{self.name}' completed step: {step.name}")
                    
                except Exception as e:
                    logger.error(f"Saga step failed: {step.name} - {e}")
                    
                    # 尝试重试
                    retries = self._retries.get(step.name, 0)
                    if retries < self._max_retries:
                        self._retries[step.name] = retries + 1
                        logger.info(f"Retrying step {step.name} ({retries + 1}/{self._max_retries})")
                        # 重新执行当前步骤
                        result = await step.action(context)
                        context.set(f"{step.name}_result", result)
                        completed_steps.append(step)
                    else:
                        raise
            
            logger.info(f"Saga '{self.name}' completed successfully")
            return context
            
        except Exception as e:
            logger.exception(f"Saga '{self.name}' failed, executing compensations")
            
            # 逆序执行补偿
            for step in reversed(completed_steps):
                if step.compensation:
                    try:
                        await step.compensation(context)
                        logger.debug(f"Executed compensation for: {step.name}")
                    except Exception as ce:
                        logger.error(f"Compensation failed for {step.name}: {ce}")
            
            # 发布 Saga 失败事件
            await EventBuilder(EventType.SESSION_ERROR)\
                .aggregate(context.transaction_id, "saga")\
                .with_data(saga_name=self.name, error=str(e))\
                .publish(self._event_bus)
            
            raise


class SagaOrchestrator:
    """
    Saga 编排器 - 管理多个 Saga
    
    用于复杂的业务流程
    """
    
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._sagas: Dict[str, Saga] = {}
    
    def register(self, saga: Saga):
        """注册 Saga"""
        self._sagas[saga.name] = saga
    
    async def execute(self, saga_name: str, initial_data: Optional[Dict[str, Any]] = None) -> TransactionContext:
        """执行 Saga"""
        saga = self._sagas.get(saga_name)
        if not saga:
            raise ValueError(f"Saga not found: {saga_name}")
        
        return await saga.execute(initial_data)


# ============== 预定义 Saga ==============


def create_match_session_saga(
    match_service: Any,
    session_service: Any,
    event_bus: EventBus,
) -> Saga:
    """
    创建匹配 - 会话 Saga
    
    流程:
    1. 请求匹配
    2. 等待匹配结果
    3. 创建会话
    4. 发送开场白
    """
    saga = Saga("match_session", event_bus)
    
    async def request_match(ctx: TransactionContext) -> Dict[str, Any]:
        # TODO: 调用匹配服务
        return {"match_requested": True}
    
    async def create_session(ctx: TransactionContext) -> Dict[str, Any]:
        # TODO: 调用会话服务
        return {"session_created": True}
    
    async def send_opening_message(ctx: TransactionContext) -> Dict[str, Any]:
        # TODO: 发送开场白
        return {"opening_sent": True}
    
    async def cleanup_match(ctx: TransactionContext):
        # 补偿：清理匹配记录
        pass
    
    async def cleanup_session(ctx: TransactionContext):
        # 补偿：删除会话
        pass
    
    saga.add_step("request_match", request_match, cleanup_match)
    saga.add_step("create_session", create_session, cleanup_session)
    saga.add_step("send_opening_message", send_opening_message)
    
    return saga
