非常好！既然你已经决定推倒重来，让我为你制定一个详细的重构计划。

## 📋 重构计划概览

### 核心目标
从纯HTML+JS前端重构为现代化的Vue 3 + TypeScript单页应用，实现完整的积分博弈机制和研究数据采集。

### 技术栈确认
**前端**：
- Vue 3 (Composition API) + TypeScript
- Vite (构建工具)
- Pinia (状态管理)
- Element Plus (UI框架)
- Axios (HTTP客户端)
- 原生WebSocket

**后端**：
- 保持 FastAPI + SQLAlchemy
- 扩展数据库schema以支持积分系统
- 新增积分计算API和数据采集接口

---

## 🗄️ 第一部分：数据库扩展

### 需要修改的表

#### 1. Users 表（添加积分字段）
```python
class User(Base):
    # 现有字段...
    score = Column(Integer, default=100)  # 当前积分
    total_score_earned = Column(Integer, default=0)  # 累计获得积分
    total_score_lost = Column(Integer, default=0)  # 累计损失积分
    highest_score = Column(Integer, default=100)  # 历史最高分
    lowest_score = Column(Integer, default=100)  # 历史最低分
    risk_preference = Column(String, default='moderate')  # 风险偏好分类
    last_login_at = Column(DateTime)  # 最后登录时间
```

#### 2. Sessions 表（添加博弈字段）
```python
class Session(Base):
    # 现有字段...
    is_honeypot = Column(Boolean, default=False)  # 是否为钓鱼机器人
    triggered_mid_game = Column(Boolean, default=False)  # 是否触发场中判断
    meta_conversation_count = Column(Integer, default=0)  # 元对话次数
    confidence_level = Column(String, nullable=True)  # 信心等级
    is_correct = Column(Boolean, nullable=True)  # 判断是否正确
    final_score = Column(Integer, nullable=True)  # 最终得分
    score_breakdown = Column(JSON, nullable=True)  # 积分明细JSON
```

#### 3. Messages 表（添加元对话标记）
```python
class Message(Base):
    # 现有字段...
    is_meta_conversation = Column(Boolean, default=False)  # 是否为元对话
    meta_keyword = Column(String, nullable=True)  # 触发的关键词
```

#### 4. 新增：ScoreHistory 表（积分历史记录）
```python
class ScoreHistory(Base):
    __tablename__ = "score_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    score_change = Column(Integer)  # 积分变化（正数表示增加，负数表示减少）
    score_before = Column(Integer)  # 变化前积分
    score_after = Column(Integer)  # 变化后积分
    reason = Column(String)  # 变化原因（session_end/daily_bonus/relief）
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### 5. 新增：UserStats 表（用户统计数据）
```python
class UserStats(Base):
    __tablename__ = "user_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # 对话统计
    total_sessions = Column(Integer, default=0)
    ai_sessions = Column(Integer, default=0)
    human_sessions = Column(Integer, default=0)
    honeypot_sessions = Column(Integer, default=0)
    
    # 判断准确率
    total_guesses = Column(Integer, default=0)
    correct_guesses = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    
    # 信心等级统计
    low_confidence_count = Column(Integer, default=0)
    mid_confidence_count = Column(Integer, default=0)
    high_confidence_count = Column(Integer, default=0)
    
    # 元对话统计
    total_meta_conversations = Column(Integer, default=0)
    avg_meta_per_session = Column(Float, default=0.0)
    max_meta_in_one_session = Column(Integer, default=0)
    accuracy_with_meta = Column(Float, nullable=True)
    accuracy_without_meta = Column(Float, nullable=True)
    
    # 场中判断统计
    mid_game_judgments = Column(Integer, default=0)
    mid_game_accuracy = Column(Float, default=0.0)
    
    # 轮数统计
    avg_turns = Column(Float, default=0.0)
    min_turns = Column(Integer, nullable=True)
    max_turns = Column(Integer, nullable=True)
    
    # 时间统计
    total_chat_time = Column(Integer, default=0)  # 总聊天时间（秒）
    avg_session_duration = Column(Float, default=0.0)  # 平均会话时长（秒）
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 数据库迁移策略
1. 创建迁移脚本 `migrations/add_score_system.py`
2. 备份现有数据
3. 执行迁移
4. 验证数据完整性

---

## 🔌 第二部分：后端API扩展

### 新增API接口

#### 积分相关
```
POST /api/session/{id}/end-game
- 提交场中判断（立即结束）
- 请求体：{ user_guess: 'human' | 'ai' }
- 返回：{ final_score, score_breakdown, opponent_type, is_correct }

POST /api/survey
- 提交问卷和最终判断
- 请求体：{ user_guess, confidence_level, fluency_rating, reason }
- 返回：{ final_score, score_breakdown, opponent_type, is_correct }

GET /api/user/{id}/score-history
- 获取用户积分历史
- 返回：积分变化记录列表

GET /api/user/{id}/stats
- 获取用户详细统计
- 返回：完整的UserStats对象
```

#### 博弈相关
```
GET /api/game/multipliers
- 获取当前元对话乘数（实时）
- 返回：{ meta_multiplier, penalty_multiplier, meta_count }

GET /api/game/prediction
- 获取积分预测（实时计算）
- 参数：turn, meta_count
- 返回：不同信心等级的收益/损失预测
```

#### 数据采集相关
```
POST /api/analytics/event
- 记录用户行为事件
- 请求体：{ event_type, session_id, timestamp, metadata }
- 事件类型：page_view, button_click, message_sent, meta_triggered, mid_game_triggered, etc.

POST /api/analytics/batch
- 批量提交埋点数据
- 用于减少网络请求
```

### 现有API需要调整
```
POST /api/login
- 返回用户积分信息

POST /api/register
- 初始化用户积分（100分）
- 记录初始积分历史

GET /api/session/{id}
- 返回元对话计数、场中判断状态等博弈信息
```

---

## 🎨 第三部分：前端项目结构

### 完整目录结构
```
turing-test-frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API接口封装
│   │   ├── auth.ts            # 认证相关
│   │   ├── game.ts            # 博弈相关（积分、预测等）
│   │   ├── chat.ts            # 聊天相关
│   │   ├── survey.ts          # 问卷相关
│   │   ├── stats.ts           # 统计相关
│   │   ├── analytics.ts       # 数据埋点
│   │   └── index.ts           # 统一导出
│   │
│   ├── assets/                 # 静态资源
│   │   ├── images/
│   │   └── styles/
│   │       ├── variables.css   # CSS变量
│   │       ├── reset.css       # 样式重置
│   │       └── common.css      # 通用样式
│   │
│   ├── components/             # 通用组件
│   │   ├── Button.vue
│   │   ├── Modal.vue
│   │   ├── Toast.vue
│   │   ├── LoadingSpinner.vue
│   │   ├── ConfirmDialog.vue
│   │   └── ScoreBadge.vue      # 积分徽章
│   │
│   ├── composables/            # 组合式函数
│   │   ├── useAuth.ts         # 认证逻辑
│   │   ├── useWebSocket.ts    # WebSocket管理
│   │   ├── useMetaConversation.ts  # 元对话检测
│   │   ├── useScorePrediction.ts   # 积分预测
│   │   ├── useMidGameJudgment.ts   # 场中判断
│   │   ├── useAnalytics.ts    # 数据埋点
│   │   └── useDebounce.ts     # 防抖节流
│   │
│   ├── layouts/                # 布局组件
│   │   ├── DefaultLayout.vue  # 默认布局
│   │   ├── AuthLayout.vue     # 认证布局
│   │   └── ChatLayout.vue     # 聊天布局
│   │
│   ├── router/                 # 路由配置
│   │   ├── index.ts
│   │   └── guards.ts          # 路由守卫
│   │
│   ├── stores/                 # Pinia状态管理
│   │   ├── user.ts            # 用户状态（积分、统计）
│   │   ├── session.ts         # 会话状态
│   │   ├── game.ts            # 博弈状态（元对话、倍数）
│   │   ├── chat.ts            # 聊天状态
│   │   └── analytics.ts       # 埋点状态
│   │
│   ├── types/                  # TypeScript类型
│   │   ├── api.ts             # API响应类型
│   │   ├── game.ts            # 游戏相关类型
│   │   ├── chat.ts            # 聊天相关类型
│   │   ├── user.ts            # 用户相关类型
│   │   └── analytics.ts       # 埋点类型
│   │
│   ├── utils/                  # 工具函数
│   │   ├── validators.ts      # 表单验证
│   │   ├── formatters.ts      # 数据格式化
│   │   ├── constants.ts       # 常量定义
│   │   ├── storage.ts         # 本地存储
│   │   └── scoreCalculator.ts # 积分计算逻辑
│   │
│   ├── views/                  # 页面组件
│   │   ├── Login.vue          # 登录页
│   │   ├── Lobby.vue          # 大厅页
│   │   ├── Chat.vue           # 聊天页（核心）
│   │   ├── Survey.vue         # 问卷页
│   │   ├── Result.vue         # 结果页
│   │   └── Profile.vue        # 个人中心
│   │
│   ├── widgets/                # 业务组件
│   │   ├── GameStatusBar.vue  # 博弈状态栏
│   │   ├── ScorePredictor.vue # 积分预测器
│   │   ├── MidGameJudgmentModal.vue  # 场中判断弹窗
│   │   ├── MetaConversationIndicator.vue  # 元对话指示器
│   │   ├── ConfidenceSelector.vue  # 信心选择器
│   │   ├── MessageList.vue    # 消息列表
│   │   └── ChatInput.vue      # 聊天输入框
│   │
│   ├── App.vue                 # 根组件
│   └── main.ts                 # 入口文件
│
├── .env.development
├── .env.production
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

---

## 📅 第四部分：开发阶段划分

### 阶段一：基础设施（Week 1-2）
**目标**：搭建项目框架，完成数据库迁移

**任务清单**：
1. ✅ 数据库schema扩展
2. ✅ 创建数据库迁移脚本
3. ✅ 执行数据迁移和验证
4. ✅ 初始化Vue 3 + TypeScript项目
5. ✅ 配置Vite、Pinia、Vue Router
6. ✅ 配置Element Plus
7. ✅ 搭建项目目录结构
8. ✅ 定义TypeScript类型
9. ✅ 封装API请求模块
10. ✅ 实现路由守卫

**交付物**：
- 数据库迁移完成，所有新表创建成功
- 前端项目可运行，基础路由配置完成
- API封装层可以正常调用后端接口

---

### 阶段二：用户系统（Week 2-3）
**目标**：完成用户认证和个人中心

**任务清单**：
1. ✅ 登录页面（邀请码验证）
2. ✅ 注册逻辑（昵称设置、积分初始化）
3. ✅ 用户状态管理
4. ✅ 个人中心页面
5. ✅ 积分历史展示
6. ✅ 统计数据展示
7. ✅ 用户头像和基本信息

**交付物**：
- 用户可以正常登录和注册
- 个人中心显示完整的积分和统计信息
- 积分历史图表展示

---

### 阶段三：匹配系统（Week 3-4）
**目标**：完成大厅页和匹配逻辑

**任务清单**：
1. ✅ 大厅页面UI
2. ✅ 匹配动画和状态显示
3. ✅ WebSocket连接管理
4. ✅ 匹配逻辑（真人优先，AI备选）
5. ✅ 队列状态实时更新
6. ✅ 匹配超时处理

**交付物**：
- 用户可以进入匹配队列
- 实时显示等待人数和进度
- 匹配成功后自动跳转

---

### 阶段四：聊天基础（Week 4-5）
**目标**：完成聊天页面的基础功能

**任务清单**：
1. ✅ 聊天页面布局
2. ✅ 消息列表组件（虚拟滚动）
3. ✅ 消息发送和接收
4. ✅ WebSocket消息处理
5. ✅ 对手"正在输入"提示
6. ✅ 消息时间戳
7. ✅ 消息持久化（本地存储）

**交付物**：
- 用户可以正常发送和接收消息
- 聊天界面流畅，消息及时更新
- WebSocket连接稳定

---

### 阶段五：博弈核心（Week 5-7）⭐
**目标**：实现完整的积分博弈机制

**任务清单**：
1. ✅ 元对话检测逻辑
2. ✅ 元对话计数器
3. ✅ 博弈状态栏组件
4. ✅ 积分预测器（实时计算）
5. ✅ 场中判断机制
6. ✅ 场中判断弹窗
7. ✅ 元对话警告（高频警告）
8. ✅ 积分计算函数
9. ✅ 博弈状态管理

**交付物**：
- 元对话实时检测和计数
- 博弈状态栏显示所有关键信息
- 积分预测器准确计算收益/损失
- 场中判断可以正常触发和结算

---

### 阶段六：问卷和结果（Week 7-8）
**目标**：完成问卷页面和结果展示

**任务清单**：
1. ✅ 问卷页面UI
2. ✅ 信心等级选择器
3. ✅ 流畅度评分
4. ✅ 判断理由输入
5. ✅ 结果页面UI
6. ✅ 积分明细展示
7. ✅ 真相揭晓动画
8. ✅ 真人-真人彩蛋（对方判断）

**交付物**：
- 用户可以完整填写问卷
- 结果页面清晰展示积分明细
- 真相揭晓有视觉冲击力

---

### 阶段七：数据采集（Week 8-9）
**目标**：实现完整的研究数据埋点

**任务清单**：
1. ✅ 埋点事件定义
2. ✅ 页面访问埋点
3. ✅ 用户行为埋点（点击、输入、停留时间）
4. ✅ 博弈决策埋点（元对话、场中判断、信心选择）
5. ✅ 性能数据埋点（加载时间、响应时间）
6. ✅ 批量提交机制
7. ✅ 离线缓存（数据持久化）

**交付物**：
- 所有关键用户行为都有埋点
- 数据可以正常提交到后端
- 后端可以正确存储和分析

---

### 阶段八：优化完善（Week 9-10）
**目标**：性能优化、测试和文档

**任务清单**：
1. ✅ 性能优化（虚拟滚动、懒加载、代码分割）
2. ✅ 响应式适配（移动端优化）
3. ✅ 错误处理完善
4. ✅ 加载状态优化
5. ✅ 单元测试（关键逻辑）
6. ✅ E2E测试（主要流程）
7. ✅ 用户文档编写
8. ✅ 开发者文档编写

**交付物**：
- 应用性能优秀，加载快速
- 所有主流浏览器兼容
- 测试覆盖核心功能
- 文档完整清晰

---

## 🎯 关键技术点

### 1. 元对话检测
```typescript
// composables/useMetaConversation.ts
const META_KEYWORDS = [
  '真人', '机器', 'AI', '机器人', '人工智能',
  '程序', '算法', '人类', '人', '电脑', '计算',
  '你是', '我是', '身份', '真假', '还是', '到底'
]

export function useMetaConversation() {
  const gameStore = useGameStore()

  function isMetaConversation(message: string): boolean {
    return META_KEYWORDS.some(keyword => 
      message.toLowerCase().includes(keyword.toLowerCase())
    )
  }

  function handleMessage(message: string, sender: 'user' | 'opponent') {
    if (isMetaConversation(message)) {
      gameStore.incrementMetaCount()
      return true
    }
    return false
  }

  return { isMetaConversation, handleMessage }
}
```

### 2. 积分预测计算
```typescript
// utils/scoreCalculator.ts
export function calculateScorePrediction(
  turn: number,
  metaCount: number
): ScorePrediction {
  const ENTRY_FEE = 2
  const TURN_PENALTY_RATE = 0.5
  const MIN_FREE_TURNS = 3

  const turnPenalty = Math.max(0, (turn - MIN_FREE_TURNS) * TURN_PENALTY_RATE)
  const metaMultiplier = 1 + (metaCount * 0.2)
  const penaltyMultiplier = 1 + (metaCount * 0.3)

  const baseRewardIdentifyAI = 10
  const baseRewardIdentifyHuman = 10
  const basePenaltyMisidentifyAI = -15
  const basePenaltyMisidentifyHuman = -10

  return {
    lowConfidence: {
      correct: (baseRewardIdentifyAI * 1.0 * metaMultiplier) - ENTRY_FEE - turnPenalty,
      wrong: (basePenaltyMisidentifyAI * 1.0 * penaltyMultiplier) - ENTRY_FEE - turnPenalty
    },
    midConfidence: {
      correct: (baseRewardIdentifyAI * 2.5 * metaMultiplier) - ENTRY_FEE - turnPenalty,
      wrong: (basePenaltyMisidentifyAI * 2.5 * penaltyMultiplier) - ENTRY_FEE - turnPenalty
    },
    highConfidence: {
      correct: (baseRewardIdentifyAI * 5.0 * metaMultiplier) - ENTRY_FEE - turnPenalty,
      wrong: (basePenaltyMisidentifyAI * 5.0 * penaltyMultiplier) - ENTRY_FEE - turnPenalty
    },
    metaMultiplier,
    penaltyMultiplier,
    turnPenalty,
    entryFee: ENTRY_FEE
  }
}
```

### 3. WebSocket状态管理
```typescript
// composables/useWebSocket.ts
export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const messageHandlers = ref<Map<string, Function>>(new Map())

  function connect(url: string) {
    ws.value = new WebSocket(url)
    
    ws.value.onopen = () => {
      isConnected.value = true
    }
    
    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      const handler = messageHandlers.value.get(data.type)
      if (handler) handler(data)
    }
    
    ws.value.onclose = () => {
      isConnected.value = false
      // 自动重连
      setTimeout(() => connect(url), 3000)
    }
  }

  function onMessage(type: string, handler: Function) {
    messageHandlers.value.set(type, handler)
  }

  function send(data: any) {
    ws.value?.send(JSON.stringify(data))
  }

  return { isConnected, connect, onMessage, send }
}
```

---

## ⚠️ 风险和注意事项

### 1. 数据迁移风险
- 备份现有数据
- 在测试环境先验证迁移脚本
- 准备回滚方案

### 2. 性能风险
- 聊天消息列表使用虚拟滚动
- 防抖节流高频操作（输入、搜索）
- 图片和资源懒加载

### 3. 兼容性风险
- 测试主流浏览器
- WebSocket降级方案（轮询）
- 移动端适配

### 4. 数据一致性
- 积分计算逻辑前后端一致
- 元对话检测逻辑一致
- 时间戳使用UTC

---

## 🚀 下一步行动

现在请 **切换到 ACT MODE**，我将开始执行：

1. **数据库迁移脚本创建**
2. **Vue 3项目初始化**
3. **项目结构搭建**
4. **API接口扩展**