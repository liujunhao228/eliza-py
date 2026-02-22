import asyncio
import random
from datetime import datetime
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from turing_test.backend.models import Session as SessionModel
from config import settings


class MatchEngine:
    """匹配引擎 - 管理用户匹配队列"""

    def __init__(self):
        # 等待匹配的用户队列 (按等待时间排序)
        self.waiting_queue: list[int] = []  # 存储 user_id
        # 用户等待开始时间
        self.wait_start_time: Dict[int, datetime] = {}
        # 锁，防止并发问题
        self._lock = asyncio.Lock()

    async def join_queue(self, user_id: int, db: Session) -> Tuple[str, Optional[int], Optional[str], int]:
        """
        用户加入匹配队列

        Returns:
            (状态, session_id, opponent_type, match_duration)
            状态：'found_human' - 找到真人，'found_ai' - 匹配AI，'waiting' - 继续等待
        """
        async with self._lock:
            now = datetime.utcnow()

            # 检查是否有其他人在等待（真人优先匹配）
            if self.waiting_queue:
                # 找到第一个等待的用户
                other_user_id = self.waiting_queue.pop(0)

                # 再次检查对方是否还在等待（双重确认）
                if other_user_id not in self.wait_start_time:
                    # 对方已经不在等待队列，当前用户加入队列
                    self.waiting_queue.append(user_id)
                    self.wait_start_time[user_id] = now
                    return ('waiting', None, None, 0)

                # 生成匹配延迟（真人AI使用相同分布）
                match_delay = self._get_match_delay()
                
                # 等待延迟
                await asyncio.sleep(match_delay)

                # 创建真人-真人的会话
                session = SessionModel(
                    user_id=user_id,
                    opponent_type='human',
                    opponent_id=other_user_id,
                    status='active',
                    match_duration=int(match_delay),
                    started_at=now
                )
                db.add(session)
                db.flush()  # 获取 session.id

                # 为对方创建会话记录
                other_session = SessionModel(
                    user_id=other_user_id,
                    opponent_type='human',
                    opponent_id=user_id,
                    status='active',
                    match_duration=int(match_delay),
                    started_at=now
                )
                db.add(other_session)

                db.commit()

                # 清理等待时间记录
                if other_user_id in self.wait_start_time:
                    del self.wait_start_time[other_user_id]

                return ('found_human', session.id, 'human', int(match_delay))

            else:
                # 队列为空，需要等待
                self.waiting_queue.append(user_id)
                self.wait_start_time[user_id] = now

                # 生成匹配延迟（真人AI使用相同分布）
                match_delay = self._get_match_delay()
                
                # 等待延迟
                await asyncio.sleep(match_delay)

                # 延迟期间检查是否有人加入队列
                if len(self.waiting_queue) > 1:
                    # 有人加入，匹配真人
                    # 找到队列中除了自己之外的人
                    other_user_id = None
                    for uid in self.waiting_queue:
                        if uid != user_id:
                            other_user_id = uid
                            break
                    
                    if other_user_id is None:
                        # 只有自己，匹配AI
                        if user_id in self.wait_start_time:
                            del self.wait_start_time[user_id]
                        if user_id in self.waiting_queue:
                            self.waiting_queue.remove(user_id)
                        
                        session = SessionModel(
                            user_id=user_id,
                            opponent_type='ai',
                            opponent_id=None,
                            status='active',
                            match_duration=int(match_delay),
                            started_at=now
                        )
                        db.add(session)
                        db.commit()
                        
                        return ('found_ai', session.id, 'ai', int(match_delay))
                    
                    # 移除双方
                    if other_user_id in self.waiting_queue:
                        self.waiting_queue.remove(other_user_id)
                    if user_id in self.waiting_queue:
                        self.waiting_queue.remove(user_id)
                    if other_user_id in self.wait_start_time:
                        del self.wait_start_time[other_user_id]
                    if user_id in self.wait_start_time:
                        del self.wait_start_time[user_id]
                    
                    # 创建真人-真人会话
                    session = SessionModel(
                        user_id=user_id,
                        opponent_type='human',
                        opponent_id=other_user_id,
                        status='active',
                        match_duration=int(match_delay),
                        started_at=now
                    )
                    db.add(session)
                    db.flush()
                    
                    # 为对方创建会话记录
                    other_session = SessionModel(
                        user_id=other_user_id,
                        opponent_type='human',
                        opponent_id=user_id,
                        status='active',
                        match_duration=int(match_delay),
                        started_at=now
                    )
                    db.add(other_session)
                    
                    db.commit()
                    
                    return ('found_human', session.id, 'human', int(match_delay))
                
                else:
                    # 仍然只有自己，匹配AI
                    if user_id in self.wait_start_time:
                        del self.wait_start_time[user_id]
                    if user_id in self.waiting_queue:
                        self.waiting_queue.remove(user_id)
                    
                    session = SessionModel(
                        user_id=user_id,
                        opponent_type='ai',
                        opponent_id=None,
                        status='active',
                        match_duration=int(match_delay),
                        started_at=now
                    )
                    db.add(session)
                    db.commit()
                    
                    return ('found_ai', session.id, 'ai', int(match_delay))

    def _get_match_delay(self) -> float:
        """
        生成匹配延迟（真人AI使用相同分布）
        
        分布设计：
        - 50%: 0-3秒（快速匹配）
        - 30%: 3-8秒（正常匹配）
        - 15%: 8-15秒（稍慢）
        - 5%: 15-30秒（较慢）
        
        Returns:
            匹配延迟时间（秒）
        """
        r = random.random()
        
        if r < 0.5:
            # 50%: 0-3秒
            return random.uniform(0, 3)
        elif r < 0.8:
            # 30%: 3-8秒
            return random.uniform(3, 8)
        elif r < 0.95:
            # 15%: 8-15秒
            return random.uniform(8, 15)
        else:
            # 5%: 15-30秒
            return random.uniform(15, 30)

    def leave_queue(self, user_id: int):
        """用户离开匹配队列"""
        if user_id in self.waiting_queue:
            self.waiting_queue.remove(user_id)
        if user_id in self.wait_start_time:
            del self.wait_start_time[user_id]

    def get_queue_status(self) -> dict:
        """获取队列状态"""
        now = datetime.utcnow()
        waiting_info = []
        for uid in self.waiting_queue:
            if uid in self.wait_start_time:
                wait_time = (now - self.wait_start_time[uid]).total_seconds()
                waiting_info.append({
                    "user_id": uid,
                    "wait_time": round(wait_time, 1)
                })

        return {
            "waiting_count": len(self.waiting_queue),
            "waiting_users": waiting_info
        }

    def get_user_wait_time(self, user_id: int) -> Optional[float]:
        """获取用户已等待的时间（秒）"""
        if user_id not in self.wait_start_time:
            return None
        now = datetime.utcnow()
        return (now - self.wait_start_time[user_id]).total_seconds()


# 全局匹配引擎实例
match_engine = MatchEngine()