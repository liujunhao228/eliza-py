"""
创建领域模型表结构

新表:
- bot_configs (Bot 配置元数据)
- matches (匹配记录)
- rooms (对话空间)
- room_participants (对话参与者)
- messages (消息)
- user_sessions (用户会话)
- session_scores (会话积分)
- score_breakdown_items (积分明细分项)

依赖：无 (全新表)
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'create_domain_models'
down_revision = None  # 初始迁移，无父版本
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === 创建 bot_configs 表 ===
    op.create_table(
        'bot_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('bot_type', sa.String(length=20), nullable=False, comment='normal/honeypot'),
        sa.Column('level', sa.String(length=20), nullable=False, comment='lv1_newbie/lv2_typical/lv3_logic'),
        sa.Column('script_path', sa.String(length=255), nullable=False, comment='YAML 脚本文件路径'),
        sa.Column('lua_module', sa.String(length=100), nullable=True, comment='Lua 模块名'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bot_configs_name', 'bot_configs', ['name'], unique=True)
    op.create_index('ix_bot_configs_is_active', 'bot_configs', ['is_active'], unique=False)

    # === 创建 matches 表 ===
    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=True),
        sa.Column('user_score_snapshot', sa.Integer(), nullable=False, comment='用户积分快照'),
        sa.Column('preferences', sa.JSON(), nullable=True, comment='匹配偏好设置'),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending', comment='pending/matched/failed/cancelled/timeout'),
        sa.Column('opponent_type', sa.String(length=20), nullable=True, comment='human/bot/honeypot'),
        sa.Column('matched_opponent_id', sa.Integer(), nullable=True),
        sa.Column('bot_config_id', sa.Integer(), nullable=True),
        sa.Column('bot_level', sa.String(length=20), nullable=True, comment='lv1_newbie/lv2_typical/lv3_logic'),
        sa.Column('is_honeypot', sa.Boolean(), nullable=False, default=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['matched_opponent_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['bot_config_id'], ['bot_configs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_matches_user_id', 'matches', ['user_id'], unique=False)
    op.create_index('ix_matches_room_id', 'matches', ['room_id'], unique=True)
    op.create_index('ix_matches_status', 'matches', ['status'], unique=False)
    op.create_index('ix_matches_requested_at', 'matches', ['requested_at'], unique=False)
    op.create_index('ix_matches_status_requested', 'matches', ['status', 'requested_at'], unique=False)
    op.create_index('ix_matches_user_status', 'matches', ['user_id', 'status'], unique=False)

    # === 创建 rooms 表 ===
    op.create_table(
        'rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=20), nullable=False, comment='human_vs_bot/human_vs_human/honeypot'),
        sa.Column('status', sa.String(length=20), nullable=False, default='active', comment='active/ended/timeout'),
        sa.Column('end_reason', sa.String(length=30), nullable=True),
        sa.Column('total_turns', sa.Integer(), nullable=False, default=0),
        sa.Column('meta_count', sa.Integer(), nullable=False, default=0),
        sa.Column('first_leaver_id', sa.Integer(), nullable=True, comment='先离开的用户 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['first_leaver_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rooms_match_id', 'rooms', ['match_id'], unique=True)
    op.create_index('ix_rooms_status', 'rooms', ['status'], unique=False)
    op.create_index('ix_rooms_created_at', 'rooms', ['created_at'], unique=False)
    op.create_index('ix_rooms_ended_at', 'rooms', ['ended_at'], unique=False)
    op.create_index('ix_rooms_status_created', 'rooms', ['status', 'created_at'], unique=False)
    op.create_index('ix_rooms_type_status', 'rooms', ['type', 'status'], unique=False)

    # === 创建 room_participants 表 ===
    op.create_table(
        'room_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('bot_config_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False, comment='user/opponent/bot'),
        sa.Column('bot_level', sa.String(length=20), nullable=True),
        sa.Column('is_honeypot', sa.Boolean(), nullable=False, default=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('left_reason', sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bot_config_id'], ['bot_configs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_room_participants_room_id', 'room_participants', ['room_id'], unique=False)
    op.create_index('ix_room_participants_user_id', 'room_participants', ['user_id'], unique=False)
    op.create_index('ix_room_participants_room_user', 'room_participants', ['room_id', 'user_id'], unique=True)
    op.create_index('ix_room_participants_left_at', 'room_participants', ['left_at'], unique=False)

    # === 创建 messages 表 ===
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('sender_type', sa.String(length=20), nullable=False, comment='user/bot'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_meta', sa.Boolean(), nullable=False, default=False),
        sa.Column('meta_keyword', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_messages_room_id', 'messages', ['room_id'], unique=False)
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'], unique=False)
    op.create_index('ix_messages_is_meta', 'messages', ['is_meta'], unique=False)
    op.create_index('ix_messages_created_at', 'messages', ['created_at'], unique=False)
    op.create_index('ix_messages_room_created', 'messages', ['room_id', 'created_at'], unique=False)
    op.create_index('ix_messages_room_sender', 'messages', ['room_id', 'sender_id'], unique=False)

    # === 创建 user_sessions 表 ===
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=True),
        sa.Column('user_turn_count', sa.Integer(), nullable=False, default=0),
        sa.Column('total_turns', sa.Integer(), nullable=False, default=0),
        sa.Column('is_user_turn', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_message_id', sa.Integer(), nullable=True),
        sa.Column('user_guess', sa.String(length=10), nullable=True, comment='human/ai'),
        sa.Column('confidence', sa.String(length=10), nullable=True, comment='low/mid/high'),
        sa.Column('is_mid_game', sa.Boolean(), nullable=False, default=False),
        sa.Column('judgment_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('final_score', sa.Integer(), nullable=True),
        sa.Column('score_settled', sa.Boolean(), nullable=False, default=False),
        sa.Column('score_settled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bonus_pending', sa.Boolean(), nullable=False, default=False),
        sa.Column('bonus_claimed', sa.Boolean(), nullable=False, default=False),
        sa.Column('bonus_claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='active'),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_reason', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'], unique=False)
    op.create_index('ix_user_sessions_room_id', 'user_sessions', ['room_id'], unique=False)
    op.create_index('ix_user_sessions_match_id', 'user_sessions', ['match_id'], unique=True)
    op.create_index('ix_user_sessions_status', 'user_sessions', ['status'], unique=False)
    op.create_index('ix_user_sessions_created_at', 'user_sessions', ['created_at'], unique=False)
    op.create_index('ix_user_sessions_judgment_submitted_at', 'user_sessions', ['judgment_submitted_at'], unique=False)
    op.create_index('ix_user_sessions_user_room', 'user_sessions', ['user_id', 'room_id'], unique=True)
    op.create_index('ix_user_sessions_status_user', 'user_sessions', ['status', 'user_id'], unique=False)
    op.create_index('ix_user_sessions_room_user', 'user_sessions', ['room_id', 'user_id'], unique=False)

    # === 创建 session_scores 表 ===
    op.create_table(
        'session_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_session_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('base_score', sa.Integer(), nullable=False, default=0),
        sa.Column('confidence_multiplier', sa.Float(), nullable=False, default=1.0),
        sa.Column('meta_multiplier', sa.Float(), nullable=False, default=1.0),
        sa.Column('mid_game_multiplier', sa.Float(), nullable=False, default=1.0),
        sa.Column('entry_fee', sa.Integer(), nullable=False, default=2),
        sa.Column('turn_penalty', sa.Integer(), nullable=False, default=0),
        sa.Column('opponent_bonus', sa.Integer(), nullable=False, default=0),
        sa.Column('final_score', sa.Integer(), nullable=False),
        sa.Column('base_settled', sa.Boolean(), nullable=False, default=False),
        sa.Column('base_settled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bonus_pending', sa.Boolean(), nullable=False, default=False),
        sa.Column('bonus_claimed', sa.Boolean(), nullable=False, default=False),
        sa.Column('bonus_claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opponent_guess', sa.String(length=10), nullable=True),
        sa.Column('opponent_confidence', sa.String(length=10), nullable=True),
        sa.Column('opponent_is_correct', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_session_id'], ['user_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_session_scores_user_session_id', 'session_scores', ['user_session_id'], unique=True)
    op.create_index('ix_session_scores_user_id', 'session_scores', ['user_id'], unique=False)
    op.create_index('ix_session_scores_room_id', 'session_scores', ['room_id'], unique=False)
    op.create_index('ix_session_scores_user_created', 'session_scores', ['user_id', 'created_at'], unique=False)

    # === 创建 score_breakdown_items 表 ===
    op.create_table(
        'score_breakdown_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_score_id', sa.Integer(), nullable=False),
        sa.Column('item_type', sa.String(length=30), nullable=False, comment='base/confidence/meta/mid_game/entry/penalty/bonus'),
        sa.Column('item_name', sa.String(length=50), nullable=False, comment='人类可读名称'),
        sa.Column('multiplier', sa.Float(), nullable=True, comment='倍率项的倍率值'),
        sa.Column('amount', sa.Integer(), nullable=False, comment='金额'),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['session_score_id'], ['session_scores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_score_breakdown_items_session_score_id', 'score_breakdown_items', ['session_score_id'], unique=False)
    op.create_index('ix_score_breakdown_items_type', 'score_breakdown_items', ['session_score_id', 'item_type'], unique=False)


def downgrade() -> None:
    # 按相反顺序删除表
    op.drop_table('score_breakdown_items')
    op.drop_table('session_scores')
    op.drop_table('user_sessions')
    op.drop_table('messages')
    op.drop_table('room_participants')
    op.drop_table('rooms')
    op.drop_table('matches')
    op.drop_table('bot_configs')
