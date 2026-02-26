# 项目数据结构文档

本文档详细描述 Alice 聊天机器人和 Turing 测试平台使用的所有数据结构。

## 目录

- [核心数据模型](#核心数据模型)
- [NLP 数据结构](#nlp-数据结构)
- [对话管理数据结构](#对话管理数据结构)
- [数据库模型](#数据库模型)
- [API Schema](#api-schema)
- [配置数据结构](#配置数据结构)
- [缓存数据结构](#缓存数据结构)

---

## 核心数据模型

### 1. 实体类型 (EntityType)

**位置**: `alice/nlp/base.py`

```python
class EntityType(Enum):
    PERSON = "person"           # 人名
    LOCATION = "location"       # 地点
    ORGANIZATION = "organization"  # 机构
    TIME = "time"               # 时间
    DATE = "date"               # 日期
    PRONOUN = "pronoun"         # 代词
    TITLE = "title"             # 称谓
    NUMBER = "number"           # 数字
    EMOTION = "emotion"         # 情感
    GENERAL = "general"         # 通用实体
```

### 2. 命名实体 (Entity)

**位置**: `alice/nlp/base.py`

```python
@dataclass
class Entity:
    text: str                    # 实体文本
    entity_type: EntityType      # 实体类型
    start_pos: int = 0           # 起始位置
    end_pos: int = 0             # 结束位置
    confidence: float = 1.0      # 置信度

    def to_dict() -> Dict:
        {
            'text': str,
            'type': str,         # EntityType.value
            'start': int,
            'end': int,
            'confidence': float,
        }
```

### 3. 句法结构 (SyntaxStructure)

**位置**: `alice/nlp/base.py`

```python
@dataclass
class SyntaxStructure:
    words: List[str]                         # 词列表
    poses: List[str]                         # 词性列表
    subject: str = ""                        # 主语
    predicate: str = ""                      # 谓语
    object: str = ""                         # 宾语
    modifiers: Dict[str, List[str]]          # 修饰语
    dependencies: List[Dict[str, Any]]       # 依存关系

    def to_dict() -> Dict:
        {
            'words': List[str],
            'poses': List[str],
            'subject': str,
            'predicate': str,
            'object': str,
            'modifiers': Dict,
            'dependencies': List[Dict],
        }
```

### 4. NLP 分析结果 (NlpResult)

**位置**: `alice/nlp/base.py`

```python
@dataclass
class NlpResult:
    text: str                    # 原始文本
    tokens: List[str]            # 分词结果
    entities: List[Entity]       # 实体列表
    syntax: Optional[SyntaxStructure]  # 句法结构

    def to_dict() -> Dict:
        {
            'text': str,
            'tokens': List[str],
            'entities': List[Dict],
            'syntax': Dict or None,
        }
```

---

## NLP 数据结构

### 5. LTP 任务类型 (TaskType)

**位置**: `alice/nlp/engines/ltp/models.py`

```python
class TaskType(Enum):
    CWS = auto()      # 中文分词
    POS = auto()      # 词性标注
    NER = auto()      # 命名实体识别
    DEP = auto()      # 依存句法分析
    SDP = auto()      # 语义依存分析
    SRL = auto()      # 语义角色标注
```

### 6. 分词单元 (Token)

**位置**: `alice/nlp/engines/ltp/models.py`

```python
@dataclass(frozen=True)
class Token:
    text: str           # 词文本
    idx: int            # 索引
    start_pos: int      # 起始字符位置
    end_pos: int        # 结束字符位置
```

### 7. 词性标注 (POSTag)

**位置**: `alice/nlp/engines/ltp/models.py`

```python
@dataclass
class POSTag:
    token: Token                    # 分词单元
    pos: str                        # 词性标签
    probability: float = 1.0        # 置信度

    # PKU 标注集
    POS_DESCRIPTIONS = {
        'n': '名词', 'v': '动词', 'a': '形容词', 'd': '副词',
        'm': '数词', 'q': '量词', 'r': '代词', 'p': '介词',
        'c': '连词', 'u': '助词', 'e': '叹词', 'y': '语气词',
        'nh': '人名', 'ni': '机构名', 'ns': '地名',
        'nt': '时间词', 'nz': '其他专名', 'w': '标点符号',
    }
```

### 8. 依存关系 (DependencyRelation)

**位置**: `alice/nlp/engines/ltp/models.py`

```python
@dataclass
class DependencyRelation:
    token: Token            # 依存词
    head_idx: int           # 头部索引 (-1 表示根节点)
    relation: str           # 关系类型

    # LTP 依存关系标注集（14 种）
    RELATION_DESCRIPTIONS = {
        'SBV': '主谓关系', 'VOB': '动宾关系', 'IOB': '间宾关系',
        'FOB': '前置宾语', 'DBL': '兼语', 'ATT': '定中关系',
        'ADV': '状中结构', 'CMP': '动补结构', 'COO': '并列关系',
        'POB': '介宾关系', 'LAD': '左附加关系', 'RAD': '右附加关系',
        'IS': '独立结构', 'HED': '核心关系', 'WP': '标点符号',
    }
```

### 9. 语义角色 (SemanticRole)

**位置**: `alice/nlp/engines/ltp/models.py`

```python
@dataclass
class SemanticRole:
    predicate_idx: int                          # 谓语索引
    predicate: str                              # 谓语文本
    arguments: List[Tuple[str, str, int, int]]  # (角色类型，文本，起始，结束)

    # PropBank 语义角色
    ROLE_DESCRIPTIONS = {
        'A0': '施事', 'A1': '受事', 'A2': '起点/终点/受益人',
        'A3': '起点/受益人', 'A4': '终点', 'A5': '工具/方式',
        'ADV': '附加语', 'TMP': '时间', 'LOC': '地点',
        'MNR': '方式', 'PRP': '目的', 'CAU': '原因',
    }
```

### 10. 语义依存 (SemanticDependency)

**位置**: `alice/nlp/engines/ltp/models.py`

```python
@dataclass
class SemanticDependency:
    head_idx: int           # 头部索引
    dependent_idx: int      # 依存索引
    relation: str           # 关系类型
```

### 11. 语义依存图 (SemanticDependencyGraph)

**位置**: `alice/nlp/engines/ltp/models.py`

```python
@dataclass
class SemanticDependencyGraph:
    edges: List[SemanticDependency]

    def get_heads(idx: int) -> List[int]       # 获取父节点
    def get_dependents(idx: int) -> List[int]  # 获取子节点
```

### 12. LTP 完整分析结果 (LtpFullResult)

**位置**: `alice/nlp/engines/ltp/models.py`

```python
@dataclass
class LtpFullResult:
    text: str                           # 原始文本
    tokens: List[Token]                 # 分词列表
    pos_tags: List[POSTag]              # 词性标注
    entities: List[Entity]              # 命名实体
    dependencies: List[DependencyRelation]  # 依存关系
    semantic_roles: Optional[List[SemanticRole]]  # 语义角色
    semantic_deps: Optional[SemanticDependencyGraph]  # 语义依存
    raw_output: Optional[Any]           # 原始输出

    def to_dict() -> Dict:
        {
            'text': str,
            'tokens': [{'text': str, 'pos': int}],
            'pos_tags': [{'word': str, 'pos': str, 'desc': str}],
            'entities': [{'text': str, 'type': str, 'confidence': float}],
            'dependencies': [{'word': str, 'relation': str, 'head': int, 'desc': str}],
            'semantic_roles': [...],
        }

    def get_main_predicate() -> Optional[str]    # 获取核心谓语
    def get_subjects() -> List[str]              # 获取所有主语
    def get_objects() -> List[str]               # 获取所有宾语
```

---

## 对话管理数据结构

### 13. 脚本意图 (ScriptIntent)

**位置**: `alice/scripts/yaml_script_engine.py`

```python
@dataclass
class ScriptIntent:
    name: str                     # 意图名称
    priority: int = 50            # 优先级 (0-100)
    condition: Optional[Dict]     # 触发条件
    templates: List[str]          # 响应模板
    reassembly_rules: List[str]   # 重组规则
    keyword_only: bool = False    # 仅关键词匹配

    # 统计信息
    usage_count: int = 0
    last_used: Optional[str] = None
```

**优先级分类**:
- P0 (90-100): 非常重要
- P1 (70-89): 实体深度挖掘
- P2 (40-69): 叙事助推
- P3 (0-39): 万能回复

### 14. 意图匹配结果 (IntentMatch)

**位置**: `alice/core/intent_matcher.py`

```python
@dataclass
class IntentMatch:
    intent: str                   # 匹配的意图
    confidence: float             # 置信度
    priority: int                 # 优先级
    script_intent: ScriptIntent   # 脚本意图对象
```

### 15. 插件结果 (PluginResult)

**位置**: `alice/plugins/base_plugin.py`

```python
@dataclass
class PluginResult:
    success: bool                 # 是否成功
    response: Optional[str]       # 响应文本
    metadata: Optional[Dict]      # 元数据
```

### 16. 上下文管理器 (ContextManager)

**位置**: `alice/managers/context_manager.py`

```python
class ContextManager:
    # 对话轮次
    def get_turn_count() -> int
    def get_recent_turns(n: int) -> List[Dict]

    # 时间上下文
    def get_time_context() -> Dict:
        {
            'year': int,
            'month': int,
            'day': int,
            'weekday': int,
            'weekday_name': str,
            'hour': int,
            'minute': int,
            'second': int,
            'category_time': str,  # 早晨/中午/下午/晚上/深夜
        }

    # 用户画像
    def get_user_profile() -> Optional[UserProfile]:
        {
            'name': str,           # 姓名
            'nickname': str,       # 昵称
            'address_form': str,   # 称呼偏好 (你/您)
        }
```

### 17. 热重载结果 (ReloadResult)

**位置**: `alice/utils/hot_reloader.py`

```python
@dataclass
class ReloadResult:
    success: bool                 # 是否成功
    error: Optional[str]          # 错误信息
    script_reloaded: bool         # 脚本是否重载
    rules_reloaded: bool          # 规则是否重载
```

---

## 数据库模型

**位置**: `turing_test/backend/models/__init__.py`

### 18. 用户表 (User)

```python
class User(Base):
    id: int                       # 主键
    username: str                 # 用户名 (唯一)
    invite_code: str              # 邀请码 (唯一)

    # 积分字段
    score: int                    # 当前积分
    total_score_earned: int       # 累计获得积分
    total_score_lost: int         # 累计失去积分
    highest_score: int            # 最高积分
    lowest_score: int             # 最低积分
    risk_preference: str          # 风险偏好 (moderate/conservative/aggressive)

    # 时间戳
    created_at: datetime
    last_login_at: Optional[datetime]

    # 关系
    sessions: List[Session]
    score_history: List[ScoreHistory]
    stats: Optional[UserStats]
```

### 19. 会话表 (Session)

```python
class Session(Base):
    id: int                       # 主键
    user_id: int                  # 外键 -> User.id

    # 会话类型
    opponent_type: str            # 'human' / 'ai' / 'honeypot'
    ai_model_type: Optional[str]  # AI 模型类型 'eliza_basic' / 'eliza_meta' / 'eliza_honeypot'

    # 博弈字段
    is_honeypot: bool             # 是否为蜜罐
    triggered_mid_game: bool      # 是否触发场中判断
    meta_conversation_count: int  # 元对话次数
    confidence_level: Optional[str]  # 'low' / 'mid' / 'high'
    is_correct: Optional[bool]    # 判断是否正确

    # 积分字段
    final_score: Optional[int]    # 最终积分
    score_breakdown: Optional[dict]  # 积分明细 JSON

    # 聊天统计
    turn_count: int               # 对话轮数
    match_duration: Optional[int] # 匹配用时（秒）
    started_at: Optional[datetime]
    ended_at: Optional[datetime]

    # 关系
    user: User
    messages: List[Message]
```

### 20. 消息表 (Message)

```python
class Message(Base):
    id: int                       # 主键
    session_id: int               # 外键 -> Session.id

    # 消息内容
    sender: str                   # 'user' / 'opponent'
    content: str                  # 消息内容

    # 元对话标记
    is_meta_conversation: bool    # 是否为元对话
    meta_keyword: Optional[str]   # 元对话关键词

    # 打字延迟数据（研究用）
    typing_duration: Optional[float]  # 打字持续时间（秒）
    typing_start_time: Optional[datetime]  # 开始打字时间

    # 消息语义特征（研究用，可选）
    word_count: Optional[int]     # 词数
    lexical_entropy: Optional[float]  # 词汇熵
    sentiment_score: Optional[float]  # 情感极性分数（-1 到 1）
    has_identity_keyword: Optional[bool]  # 是否包含身份关键词

    # 时间戳
    created_at: datetime
```

### 21. 积分历史表 (ScoreHistory)

```python
class ScoreHistory(Base):
    id: int                       # 主键
    user_id: int                  # 外键 -> User.id
    session_id: Optional[int]     # 外键 -> Session.id

    # 积分变化
    score_change: int             # 变化值 (+/-)
    score_before: int             # 变化前积分
    score_after: int              # 变化后积分

    # 原因
    reason: str                   # 'session_end' / 'daily_bonus' / 'relief'

    # 时间戳
    created_at: datetime
```

### 22. 用户统计表 (UserStats)

```python
class UserStats(Base):
    id: int                       # 主键
    user_id: int                  # 外键 -> User.id (唯一)

    # 对话统计
    total_sessions: int
    ai_sessions: int
    human_sessions: int
    honeypot_sessions: int

    # 判断准确率
    total_guesses: int
    correct_guesses: int
    accuracy: float

    # 信心等级统计
    low_confidence_count: int
    mid_confidence_count: int
    high_confidence_count: int

    # 元对话统计
    total_meta_conversations: int
    avg_meta_per_session: float
    max_meta_in_one_session: int
    accuracy_with_meta: Optional[float]
    accuracy_without_meta: Optional[float]

    # 场中判断统计
    mid_game_judgments: int
    mid_game_accuracy: float

    # 轮数统计
    avg_turns: float
    min_turns: Optional[int]
    max_turns: Optional[int]

    # 时间统计
    total_chat_time: int          # 秒
    avg_session_duration: float   # 秒

    # 时间戳
    updated_at: datetime
```

---

## API Schema

**位置**: `turing_test/backend/schemas/__init__.py`

### 23. 用户相关 Schema

```python
# 请求
class UserLogin(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=20)

class UserRegister(BaseModel):
    invite_code: str
    username: str = Field(..., min_length=2, max_length=50)

# 响应
class UserResponse(BaseSchema):
    id: int
    username: str
    score: int
    total_score_earned: int
    total_score_lost: int
    highest_score: int
    lowest_score: int
    risk_preference: str
    created_at: datetime
    last_login_at: Optional[datetime]

class UserStatsResponse(BaseSchema):
    total_sessions: int
    ai_sessions: int
    human_sessions: int
    honeypot_sessions: int
    total_guesses: int
    correct_guesses: int
    accuracy: float
    # ... 更多统计字段
```

### 24. 会话相关 Schema

```python
# 请求
class SessionCreate(BaseModel):
    opponent_type: str = Field(..., pattern="^(human|ai|honeypot)$")

# 响应
class SessionResponse(BaseSchema):
    id: int
    user_id: int
    opponent_type: str
    is_honeypot: bool
    triggered_mid_game: bool
    meta_conversation_count: int
    confidence_level: Optional[str]
    is_correct: Optional[bool]
    final_score: Optional[int]
    score_breakdown: Optional[dict]
    turn_count: int
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
```

### 25. 消息相关 Schema

```python
# 请求
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)

# 响应
class MessageResponse(BaseSchema):
    id: int
    session_id: int
    sender: str
    content: str
    is_meta_conversation: bool
    meta_keyword: Optional[str]
    created_at: datetime
```

### 26. 问卷和判断 Schema

```python
class SurveyRequest(BaseModel):
    user_guess: str = Field(..., pattern="^(human|ai)$")
    confidence_level: str = Field(..., pattern="^(low|mid|high)$")
    fluency_rating: int = Field(..., ge=1, le=5)
    reason: Optional[str]

class MidGameJudgmentRequest(BaseModel):
    user_guess: str = Field(..., pattern="^(human|ai)$")

class GameResultResponse(BaseSchema):
    session_id: int
    opponent_type: str
    user_guess: str
    is_correct: bool
    final_score: int
    score_breakdown: dict
```

### 27. WebSocket 消息 Schema

```python
class WSMessage(BaseModel):
    type: str
    data: dict

class ChatMessage(WSMessage):
    type: str = "chat"
    data: dict  # {sender, content, timestamp}

class MatchFoundMessage(WSMessage):
    type: str = "match_found"
    data: dict  # 匹配信息

class TypingMessage(WSMessage):
    type: str = "typing"
    data: dict  # {sender, is_typing}

class ErrorMessage(WSMessage):
    type: str = "error"
    data: dict  # {error_code, message}
```

---

## 配置数据结构

### 28. 配置结构 (config.yaml)

**位置**: `config.yaml`

```yaml
# 通用配置
debug: bool
log_level: str

# 路径配置
paths:
  project_root: str
  alice_dir: str
  turing_dir: str
  log_dir: str
  data_dir: str
  scripts_dir: str

# Alice 配置
alice:
  # 功能开关
  enable_ltp: bool
  enable_ner: bool
  enable_log: bool
  ner_use_ltp: bool
  hot_reload: bool
  hot_reload_mode: str        # auto/manual
  hot_reload_poll_interval: float

  # 文件路径
  script_file: str
  rules_file: str

  # 对话上下文
  context_max_items: int
  conversation_history_max_turns: int
  ltp_cache_size_limit: int
  dialogue_log_max_entries: int

  # 性能配置
  performance_monitor_sample_rate: float
  max_input_length: int
  script_match_timeout: int   # 毫秒
  regex_cache_size: int

  # 预定义响应
  fallback_responses: List[str]
  greeting_responses: List[str]

  # LTP 引擎配置
  ltp:
    enable_cws: bool          # 词分词
    enable_pos: bool          # 词性标注
    enable_ner: bool          # 命名实体识别
    enable_dep: bool          # 依存句法分析
    enable_sdp: bool          # 语义依存分析
    enable_srl: bool          # 语义角色标注
    cache_size: int
    max_length: int

# Turing 测试配置
turing:
  database:
    url: str
  auth:
    invite_code_length: int
  match:
    timeout: int              # 秒
  ai_bot:
    name: str
    typing_delay_base: float
    typing_delay_per_char: float
  session:
    min_chat_turns: int
  server:
    host: str
    port: int
  nlp_service:
    enable_ltp: bool
    cache_size: int
    cache_ttl: int
  bot_pool:
    min_instances: int
    max_instances: int
    idle_timeout: int
    max_concurrent: int
```

---

## 缓存数据结构

### 29. 智能缓存 (IntelligentCache)

**位置**: `alice/cache/intelligent_cache.py`

```python
class IntelligentCache:
    # 内部存储结构
    _cache: OrderedDict[str, Dict[str, Any]] = {
        key: {
            "value": Any,
            "created_at": datetime,
            "ttl": int,  # 秒
        }
    }

    # 统计信息
    _hits: int
    _misses: int
    _evictions: int

    # 方法
    def get(key: str) -> Optional[Any]
    def set(key: str, value: Any, ttl: Optional[int] = None)
    def contains(key: str) -> bool
    def clear()
    def cleanup_expired() -> int
    def get_stats() -> Dict:
        {
            "size": int,
            "max_size": int,
            "hits": int,
            "misses": int,
            "evictions": int,
            "hit_rate": str,  # 百分比
        }
```

---

## 数据流图

### 对话处理数据流

```
用户输入
  │
  ▼
文本预处理 (TextPreprocessor)
  │
  ▼
NLP 流水线 (NlpPipeline)
  ├── 分词 (tokens: List[str])
  ├── 实体识别 (entities: List[Entity])
  └── 句法分析 (syntax: SyntaxStructure)
  │
  ▼
语义信息构建
  {
    'tokens': List[str],
    'entities': List[Tuple[type, text]],
    'syntax': Dict,
    'triples': List[Tuple[subj, pred, obj]],
    'semantic_roles': List[Dict],
    'turn_count': int,
    'time_context': Dict,
    'user_profile': Dict,
  }
  │
  ▼
意图匹配 (IntentMatcher)
  │
  ▼
ScriptIntent
  {
    'name': str,
    'priority': int,
    'condition': Dict,
    'templates': List[str],
  }
  │
  ▼
响应生成 (ResponseGenerator)
  │
  ▼
插件处理 (PluginManager) [可选]
  │
  ▼
最终响应
  │
  ▼
缓存 (IntelligentCache)
  │
  ▼
上下文更新 (ContextManager)
```

### 数据库关系图

```
User (1) ──────< Session (N)
 │                │
 │                │ (1)
 │                ▼
 │           Message (N)
 │
 │ (1)
 │
 ├──────< ScoreHistory (N)
 │
 │ (1)
 │
 └────── UserStats (1)
```

---

## 附录：常用词性标注集 (PKU)

| 标签 | 说明 | 示例 |
|------|------|------|
| n | 名词 | 书、学生 |
| v | 动词 | 跑、学习 |
| a | 形容词 | 好、美丽 |
| d | 副词 | 很、都 |
| m | 数词 | 一、第一 |
| q | 量词 | 个、次 |
| r | 代词 | 我、这 |
| p | 介词 | 在、从 |
| c | 连词 | 和、但是 |
| u | 助词 | 的、了 |
| e | 叹词 | 啊、唉 |
| y | 语气词 | 吗、呢 |
| nh | 人名 | 张三 |
| ni | 机构名 | 清华大学 |
| ns | 地名 | 北京 |
| nt | 时间词 | 今天、明年 |
| w | 标点符号 | ，。？！ |

---

## 附录：依存关系标注集 (LTP)

| 标签 | 全称 | 说明 | 示例 |
|------|------|------|------|
| SBV | Subject-Verb | 主谓关系 | 我←→喜欢 |
| VOB | Verb-Object | 动宾关系 | 喜欢←→你 |
| IOB | Indirect-Object | 间宾关系 | 送←→我 (书) |
| FOB | Fronting-Object | 前置宾语 | 我←→书 (读了) |
| DBL | Double | 兼语 | 请←→你 (来) |
| ATT | Attribute | 定中关系 | (美丽的) 花 |
| ADV | Adverbial | 状中结构 | (非常) 好 |
| CMP | Complement | 动补结构 | 跑←→快 |
| COO | Coordinate | 并列关系 | 你←→和←→我 |
| POB | Preposition-Object | 介宾关系 | 在←→北京 |
| LAD | Left Adjunct | 左附加关系 | (第) 一 |
| RAD | Right Adjunct | 右附加关系 | 孩子←→们 |
| IS | Independent Structure | 独立结构 | 插入语 |
| HED | Head | 核心关系 | 句子核心谓语 |
| WP | Punctuation | 标点符号 | 。？！ |

---

**文档版本**: 1.0  
**最后更新**: 2026 年 2 月 22 日  
**项目**: Alice 聊天机器人 & Turing 测试平台
