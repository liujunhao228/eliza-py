import random
import string
from typing import Optional
from sqlalchemy.orm import Session
from turing_test.backend.models import InviteCode


def generate_invite_code(length: int = 6) -> str:
    """生成随机邀请码（大写字母 + 数字）"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def create_invite_codes(db: Session, count: int = 100, length: int = 6) -> list:
    """批量生成邀请码"""
    codes = []
    for _ in range(count):
        code = generate_invite_code(length)
        # 确保不重复
        while db.query(InviteCode).filter(InviteCode.code == code).first():
            code = generate_invite_code(length)
        
        invite_code = InviteCode(code=code)
        db.add(invite_code)
        codes.append(code)
    
    db.commit()
    return codes


def verify_invite_code(db: Session, code: str) -> Optional[InviteCode]:
    """验证邀请码是否有效且未使用"""
    invite_code = db.query(InviteCode).filter(InviteCode.code == code).first()
    if invite_code and not invite_code.is_used:
        return invite_code
    return None


def use_invite_code(db: Session, code: str) -> bool:
    """标记邀请码为已使用"""
    invite_code = db.query(InviteCode).filter(InviteCode.code == code).first()
    if invite_code:
        invite_code.is_used = True
        db.commit()
        return True
    return False


def get_invite_code_stats(db: Session) -> dict:
    """获取邀请码统计信息"""
    total = db.query(InviteCode).count()
    used = db.query(InviteCode).filter(InviteCode.is_used == True).count()
    return {
        "total": total,
        "used": used,
        "remaining": total - used
    }


def create_user_with_code(db: Session, code: str, nickname: str) -> 'User':
    """使用邀请码创建用户"""
    from models import User
    user = User(
        invite_code=code,
        nickname=nickname or f"访客#{code[-4:]}"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
