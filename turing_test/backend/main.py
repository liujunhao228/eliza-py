from fastapi import FastAPI, WebSocket, Depends, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
from datetime import datetime
import os
import platform

from turing_test.backend.database import engine, get_db, Base

# MIME 类型映射，避免使用 mimetypes 模块读取 Windows 注册表
MIME_TYPES = {
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml; charset=utf-8',
    '.ico': 'image/x-icon',
    '.html': 'text/html; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
}

# 仅在 Windows 上使用自定义静态文件类，避免 mimetypes 读取注册表的权限问题
if platform.system() == 'Windows':
    class FixedStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):
            # 防止路径遍历攻击
            if '..' in path or path.startswith('/'):
                raise HTTPException(status_code=404, detail="File not found")
            
            full_path = os.path.join(self.directory, path)
            
            # 确保文件在指定目录内
            real_dir = os.path.realpath(self.directory)
            real_path = os.path.realpath(full_path)
            if not real_path.startswith(real_dir):
                raise HTTPException(status_code=404, detail="File not found")
            
            if not os.path.isfile(real_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            # 获取文件扩展名和 MIME 类型
            _, ext = os.path.splitext(path)
            media_type = MIME_TYPES.get(ext.lower(), 'application/octet-stream')
            
            # 读取文件并返回响应
            with open(real_path, 'rb') as f:
                content = f.read()
            
            return Response(content=content, media_type=media_type)
else:
    FixedStaticFiles = StaticFiles
from turing_test.backend.models import User, Session as SessionModel, Message, SurveyResult, InviteCode
from turing_test.backend.schemas import (
    InviteCodeLogin, UserLogin, MessageSend,
    SurveySubmit, MatchRequest, MatchStatus
)
from turing_test.backend.auth import verify_invite_code, use_invite_code, create_user_with_code
from turing_test.backend.matcher import match_engine
from turing_test.backend.websocket import manager, handle_chat_message, handle_human_message

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="图灵测试社交实验平台")

# 应用启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    await match_engine.start_timeout_checker()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    await match_engine.stop_timeout_checker()

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（CSS/JS）
app.mount("/css", FixedStaticFiles(directory=os.path.join(FRONTEND_DIR, 'css')), name="css")


# ==================== 页面路由 ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'), media_type='text/html')


@app.get("/lobby", response_class=HTMLResponse)
async def lobby():
    return FileResponse(os.path.join(FRONTEND_DIR, 'lobby.html'), media_type='text/html')


@app.get("/chat", response_class=HTMLResponse)
async def chat():
    return FileResponse(os.path.join(FRONTEND_DIR, 'chat.html'), media_type='text/html')


@app.get("/result", response_class=HTMLResponse)
async def result():
    return FileResponse(os.path.join(FRONTEND_DIR, 'result.html'), media_type='text/html')


@app.get("/profile", response_class=HTMLResponse)
async def profile():
    return FileResponse(os.path.join(FRONTEND_DIR, 'profile.html'), media_type='text/html')


# ==================== API 路由 ====================

@app.post("/api/login")
async def login(data: InviteCodeLogin, db: Session = Depends(get_db)):
    """验证邀请码"""
    invite_code = verify_invite_code(db, data.code)
    if not invite_code:
        raise HTTPException(status_code=400, detail="邀请码无效或已使用")
    return {"valid": True, "code": data.code}


@app.post("/api/register")
async def register(data: UserLogin, db: Session = Depends(get_db)):
    """使用邀请码注册/登录"""
    # 验证邀请码
    invite_code = verify_invite_code(db, data.code)
    if not invite_code:
        raise HTTPException(status_code=400, detail="邀请码无效或已使用")
    
    # 标记为已使用
    use_invite_code(db, data.code)
    
    # 创建用户
    user = User(
        invite_code=data.code,
        nickname=data.nickname or f"访客#{data.code[-4:]}"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "nickname": user.nickname,
        "invite_code": data.code
    }


@app.get("/api/user/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "id": user.id,
        "nickname": user.nickname,
        "created_at": user.created_at.isoformat()
    }


@app.get("/api/user/{user_id}/history")
async def get_user_history(user_id: int, db: Session = Depends(get_db)):
    """获取用户对话历史"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id
    ).order_by(SessionModel.started_at.desc()).limit(50).all()

    history = []
    for s in sessions:
        # 检查是否有问卷
        survey = db.query(SurveyResult).filter(SurveyResult.session_id == s.id).first()
        history.append({
            "id": s.id,
            "opponent_type": s.opponent_type,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "survey_submitted": survey is not None
        })

    return history


@app.post("/api/match")
async def start_matching(data: MatchRequest, db: Session = Depends(get_db)):
    """开始匹配"""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 加入匹配队列
    status, session_id, opponent_type = await match_engine.join_queue(
        data.user_id, db
    )
    
    if status == 'waiting':
        return {"status": "waiting", "message": "正在匹配对手..."}
    elif status == 'found_human':
        # 注册会话到连接管理器
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        manager.register_session(session_id, data.user_id, session.opponent_id)
        return {
            "status": "found",
            "session_id": session_id,
            "opponent_type": opponent_type
        }
    else:  # found_ai
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        manager.register_session(session_id, data.user_id, None)
        return {
            "status": "found",
            "session_id": session_id,
            "opponent_type": opponent_type
        }


@app.post("/api/match/ai")
async def match_ai_directly(data: MatchRequest, db: Session = Depends(get_db)):
    """直接匹配 AI"""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    session_id, opponent_type = await match_engine.match_ai(data.user_id, db)
    manager.register_session(session_id, data.user_id, None)
    
    return {
        "status": "found",
        "session_id": session_id,
        "opponent_type": opponent_type
    }


@app.get("/api/session/{session_id}")
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """获取会话信息"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取消息历史
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at).all()
    
    return {
        "id": session.id,
        "opponent_type": session.opponent_type,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "is_ai": m.is_ai,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    }


@app.post("/api/session/{session_id}/end")
async def end_session(session_id: int, db: Session = Depends(get_db)):
    """结束会话"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session.status = 'completed'
    session.ended_at = datetime.utcnow()
    db.commit()
    
    # 从连接管理器中清理
    if session_id in manager.session_users:
        for user_id in manager.session_users[session_id]:
            manager.disconnect(user_id)
    
    return {"status": "completed", "session_id": session_id}


@app.post("/api/survey")
async def submit_survey(data: SurveySubmit, db: Session = Depends(get_db)):
    """提交问卷"""
    # 获取会话信息
    session = db.query(SessionModel).filter(SessionModel.id == data.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 创建问卷记录
    survey = SurveyResult(
        session_id=data.session_id,
        user_guess=data.user_guess,
        fluency_rating=data.fluency_rating,
        reason=data.reason
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)

    # 如果是真人模式，尝试获取对方的判断结果（彩蛋）
    opponent_guess = None
    opponent_reason = None
    
    if session.opponent_type == 'human' and session.opponent_id:
        # 查找对方的问卷记录
        opponent_survey = db.query(SurveyResult).filter(
            SurveyResult.session_id == data.session_id,
            SurveyResult.id != survey.id
        ).first()
        
        if opponent_survey:
            opponent_guess = opponent_survey.user_guess
            opponent_reason = opponent_survey.reason
            # 更新当前问卷记录，保存对方的判断
            survey.opponent_guess = opponent_guess
            survey.opponent_reason = opponent_reason
            db.commit()

    # 判断是否正确
    is_correct = (
        (data.user_guess == 'ai' and session.opponent_type == 'ai') or
        (data.user_guess == 'human' and session.opponent_type == 'human')
    )

    return {
        "id": survey.id,
        "session_id": survey.session_id,
        "user_guess": survey.user_guess,
        "opponent_type": session.opponent_type,
        "is_correct": is_correct,
        "opponent_guess": opponent_guess,
        "opponent_reason": opponent_reason
    }


@app.get("/api/stats/{user_id}")
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    """获取用户统计"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 统计会话
    total_sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id
    ).count()

    ai_sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.opponent_type == 'ai'
    ).count()

    human_sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.opponent_type == 'human'
    ).count()

    # 统计问卷
    surveys = db.query(SurveyResult).join(SessionModel).filter(
        SessionModel.user_id == user_id
    ).all()

    correct_count = sum(
        1 for s in surveys
        if (s.user_guess == 'ai' and s.session.opponent_type == 'ai') or
           (s.user_guess == 'human' and s.session.opponent_type == 'human')
    )

    return {
        "total_sessions": total_sessions,
        "ai_sessions": ai_sessions,
        "human_sessions": human_sessions,
        "total_guesses": len(surveys),
        "correct_guesses": correct_count,
        "accuracy": round(correct_count / len(surveys) * 100, 1) if surveys else 0
    }


@app.get("/api/match/status")
async def get_match_status():
    """获取匹配队列状态"""
    return match_engine.get_queue_status()


@app.get("/api/match/wait-time/{user_id}")
async def get_user_wait_time(user_id: int):
    """获取用户当前等待时间"""
    wait_time = match_engine.get_user_wait_time(user_id)
    if wait_time is None:
        return {"waiting": False, "wait_time": 0}
    return {
        "waiting": True,
        "wait_time": round(wait_time, 1),
        "timeout_in": max(0, MATCH_TIMEOUT - wait_time)
    }


# ==================== 管理员 API ====================

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """管理员后台页面"""
    return FileResponse(os.path.join(FRONTEND_DIR, 'admin.html'), media_type='text/html')


@app.get("/api/admin/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    """获取管理员统计数据"""
    # 统计会话
    total_sessions = db.query(SessionModel).count()
    human_sessions = db.query(SessionModel).filter(SessionModel.opponent_type == 'human').count()
    ai_sessions = db.query(SessionModel).filter(SessionModel.opponent_type == 'ai').count()
    completed_surveys = db.query(SurveyResult).count()
    
    # 在线用户数（通过连接管理器）
    online_users = len(manager.active_connections)
    
    return {
        "total_sessions": total_sessions,
        "human_sessions": human_sessions,
        "ai_sessions": ai_sessions,
        "completed_surveys": completed_surveys,
        "online_users": online_users
    }


@app.get("/api/admin/invite-codes")
async def get_invite_codes_stats(db: Session = Depends(get_db)):
    """获取邀请码统计"""
    total = db.query(InviteCode).count()
    used = db.query(InviteCode).filter(InviteCode.is_used == True).count()
    return {
        "total": total,
        "used": used,
        "remaining": total - used
    }


@app.get("/api/admin/recent-sessions")
async def get_recent_sessions(limit: int = 10, db: Session = Depends(get_db)):
    """获取最近的会话记录"""
    sessions = db.query(SessionModel).order_by(
        SessionModel.started_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "opponent_id": s.opponent_id,
            "opponent_type": s.opponent_type,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None
        }
        for s in sessions
    ]


@app.get("/api/admin/export/{data_type}")
async def export_data(data_type: str, db: Session = Depends(get_db)):
    """导出数据为 CSV"""
    import csv
    import io
    
    if data_type == 'messages':
        messages = db.query(Message).order_by(Message.created_at.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '会话 ID', '发送者 ID', '是否 AI', '内容', '时间'])
        for m in messages:
            writer.writerow([m.id, m.session_id, m.sender_id or 'AI', m.is_ai, m.content, m.created_at])
        content = output.getvalue()
        media_type = 'text/csv'
        filename = 'messages.csv'
        
    elif data_type == 'surveys':
        surveys = db.query(SurveyResult).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '会话 ID', '用户判断', '流畅度评分', '理由', '对方判断', '对方理由', '时间'])
        for s in surveys:
            writer.writerow([s.id, s.session_id, s.user_guess, s.fluency_rating, s.reason, s.opponent_guess or '', s.opponent_reason or '', s.created_at])
        content = output.getvalue()
        media_type = 'text/csv'
        filename = 'surveys.csv'
        
    elif data_type == 'sessions':
        sessions = db.query(SessionModel).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '用户 ID', '对手 ID', '对手类型', '状态', '开始时间', '结束时间'])
        for s in sessions:
            writer.writerow([s.id, s.user_id, s.opponent_id, s.opponent_type, s.status, s.started_at, s.ended_at])
        content = output.getvalue()
        media_type = 'text/csv'
        filename = 'sessions.csv'
        
    elif data_type == 'users':
        users = db.query(User).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '邀请码', '昵称', '创建时间'])
        for u in users:
            writer.writerow([u.id, u.invite_code, u.nickname, u.created_at])
        content = output.getvalue()
        media_type = 'text/csv'
        filename = 'users.csv'
        
    else:
        raise HTTPException(status_code=400, detail="无效的数据类型")
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/api/admin/invite-codes/generate")
async def generate_invite_codes(data: dict, db: Session = Depends(get_db)):
    """生成新的邀请码"""
    from auth import create_invite_codes
    
    count = data.get('count', 10)
    if count < 1 or count > 100:
        raise HTTPException(status_code=400, detail="数量必须在 1-100 之间")
    
    codes = create_invite_codes(db, count)
    return {"generated": len(codes), "codes": codes[:10]}  # 只返回前 10 个


@app.get("/api/admin/invite-codes/list")
async def list_invite_codes(db: Session = Depends(get_db)):
    """获取邀请码列表"""
    codes = db.query(InviteCode).order_by(InviteCode.created_at.desc()).limit(100).all()
    return {
        "codes": [
            {
                "code": c.code,
                "is_used": c.is_used,
                "created_at": c.created_at.isoformat()
            }
            for c in codes
        ]
    }


# ==================== WebSocket 路由 ====================

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    """WebSocket 连接"""
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "chat":
                content = data.get("content", "")
                if content:
                    await handle_chat_message(user_id, content, db)
            
            elif msg_type == "human_chat":
                # 真人之间的消息
                content = data.get("content", "")
                if content:
                    await handle_human_message(user_id, content, db)
            
            elif msg_type == "typing":
                # 转发"正在输入"状态
                session_id = manager.get_user_session(user_id)
                if session_id:
                    await manager.broadcast_to_session(session_id, {
                        "type": "typing",
                        "user_id": user_id
                    })
            
            elif msg_type == "stop_typing":
                session_id = manager.get_user_session(user_id)
                if session_id:
                    await manager.broadcast_to_session(session_id, {
                        "type": "stop_typing",
                        "user_id": user_id
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
