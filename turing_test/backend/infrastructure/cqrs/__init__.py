"""
CQRS 模块 - 命令和查询分离
"""

from turing_test.backend.infrastructure.cqrs.cqrs import (
    # 基类
    Command,
    Query,
    CommandHandler,
    QueryHandler,
    CommandResult,
    
    # 总线
    CommandBus,
    QueryBus,
    
    # 中间件
    CommandMiddleware,
    TransactionMiddleware,
    
    # 事务
    TransactionManager,
    Transaction,
    
    # 内置命令
    RequestMatchCommand,
    CancelMatchCommand,
    CreateSessionCommand,
    EndSessionCommand,
    SubmitJudgmentCommand,
    ClaimBonusCommand,
    
    # 内置查询
    GetMatchStatusQuery,
    GetSessionQuery,
    GetUserSessionsQuery,
    GetScoreQuery,
    GetSessionMessagesQuery,
    GetScoreHistoryQuery,
)

__all__ = [
    # 基类
    'Command',
    'Query',
    'CommandHandler',
    'QueryHandler',
    'CommandResult',
    
    # 总线
    'CommandBus',
    'QueryBus',
    
    # 中间件
    'CommandMiddleware',
    'TransactionMiddleware',
    
    # 事务
    'TransactionManager',
    'Transaction',
    
    # 内置命令
    'RequestMatchCommand',
    'CancelMatchCommand',
    'CreateSessionCommand',
    'EndSessionCommand',
    'SubmitJudgmentCommand',
    'ClaimBonusCommand',
    
    # 内置查询
    'GetMatchStatusQuery',
    'GetSessionQuery',
    'GetUserSessionsQuery',
    'GetScoreQuery',
    'GetSessionMessagesQuery',
    'GetScoreHistoryQuery',
]
