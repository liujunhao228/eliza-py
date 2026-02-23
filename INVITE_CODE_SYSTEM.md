# 邀请码系统使用文档

## 概述

邀请码系统提供了完整的邀请码生成、验证、使用和管理功能，用于图灵测试平台的用户准入控制。

## 核心功能

### 1. 邀请码生成

#### 特点
- **自动去重**: 使用排除易混淆字符的字符集 (排除 0/O, 1/I/L)
- **批量生成**: 支持一次性生成最多 1000 个唯一邀请码
- **自定义前缀/后缀**: 支持添加前缀和后缀
- **批次管理**: 批量生成的邀请码自动分配批次 ID

#### 生成规则
- 默认长度：6 位 (可在 config.yaml 中配置)
- 字符集：`ABCDEFGHJKMNPQRSTUVWXYZ23456789`
- 支持自定义长度：4-20 位

### 2. 邀请码验证

验证时检查以下条件:
- ✅ 邀请码是否存在
- ✅ 是否处于激活状态
- ✅ 是否过期
- ✅ 是否达到最大使用次数

### 3. 邀请码使用

- 自动记录使用者和使用时间
- 支持多次使用 (通过 max_uses 配置)
- 自动更新使用状态

### 4. 邀请码管理

- 启用/禁用邀请码
- 删除邀请码
- 按批次查询
- 统计分析

---

## API 接口

### 认证相关

#### 1. 用户登录/注册
```
POST /api/auth/login
```

**请求体:**
```json
{
  "invite_code": "ABC123"
}
```

**说明:**
- 如果邀请码有效且未使用，自动创建新用户
- 如果邀请码已存在用户，返回已有用户信息

---

#### 2. 用户注册
```
POST /api/auth/register
```

**请求体:**
```json
{
  "invite_code": "ABC123",
  "username": "我的用户名"
}
```

---

#### 3. 验证邀请码
```
GET /api/auth/verify/{invite_code}
```

---

### 邀请码管理

#### 1. 创建单个邀请码
```
POST /api/invite-codes/create
```

**请求体:**
```json
{
  "code": "CUSTOM123",      // 可选，自定义邀请码
  "length": 8,              // 可选，自动生成时的长度
  "prefix": "VIP",          // 可选，前缀
  "suffix": "2024",         // 可选，后缀
  "max_uses": 1,            // 最大使用次数，-1 表示无限
  "expire_days": 30,        // 可选，过期天数
  "note": "VIP 用户邀请码"    // 可选，备注
}
```

**响应:**
```json
{
  "id": 1,
  "code": "VIPABC123",
  "is_active": true,
  "is_used": false,
  "max_uses": 1,
  "current_uses": 0,
  "used_at": null,
  "expire_at": "2026-03-25T05:41:27",
  "batch_id": null,
  "note": "VIP 用户邀请码",
  "created_at": "2026-02-23T05:41:27",
  "updated_at": "2026-02-23T05:41:27"
}
```

---

#### 2. 批量创建邀请码
```
POST /api/invite-codes/batch
```

**请求体:**
```json
{
  "count": 100,
  "length": 6,
  "prefix": "",
  "suffix": "",
  "max_uses": 1,
  "expire_days": 7,
  "note": "活动邀请码"
}
```

**响应:**
```json
{
  "batch_id": "batch_20260223_054127_0061b95e",
  "count": 100,
  "codes": ["ABC123", "DEF456", ...]
}
```

---

#### 3. 查询邀请码列表
```
GET /api/invite-codes/list?is_active=true&is_used=false&limit=50&offset=0
```

**查询参数:**
- `is_active`: 筛选激活状态 (true/false)
- `is_used`: 筛选使用状态 (true/false)
- `batch_id`: 筛选批次
- `limit`: 限制数量 (1-500)
- `offset`: 偏移量

---

#### 4. 查询邀请码详情
```
GET /api/invite-codes/{id}
```

---

#### 5. 禁用邀请码
```
POST /api/invite-codes/{id}/disable
```

---

#### 6. 启用邀请码
```
POST /api/invite-codes/{id}/enable
```

---

#### 7. 删除邀请码
```
DELETE /api/invite-codes/{id}
```

---

#### 8. 获取统计信息
```
GET /api/invite-codes/stats
```

**响应:**
```json
{
  "total": 100,
  "active": 80,
  "used": 50,
  "expired": 5,
  "disabled": 20,
  "available": 30,
  "batches": 5
}
```

---

#### 9. 查询批次邀请码
```
GET /api/invite-codes/batch/{batch_id}
```

---

## 使用示例

### Python 代码示例

```python
from turing_test.backend.services.invite_code_service import (
    InviteCodeService,
    InviteCodeGenerator
)

# 生成单个邀请码
code = InviteCodeGenerator.generate(length=8)
print(f"生成的邀请码：{code}")

# 批量生成
codes = InviteCodeGenerator.generate_batch(count=100, length=6)
print(f"生成了 {len(codes)} 个邀请码")

# 使用服务创建邀请码
async with async_session_maker() as db:
    service = InviteCodeService(db)
    
    # 创建单个
    invite_code = await service.create(
        length=8,
        max_uses=1,
        expire_days=30,
        note="测试邀请码"
    )
    
    # 批量创建
    batch = await service.create_batch(
        count=100,
        length=6,
        expire_days=7
    )
    
    # 验证
    result = await service.verify("ABC123")
    if result["valid"]:
        print("邀请码有效")
    else:
        print(f"邀请码无效：{result['message']}")
    
    # 使用
    use_result = await service.use("ABC123", user_id=1)
    
    # 统计
    stats = await service.get_stats()
    print(f"可用邀请码：{stats['available']}")
```

### cURL 示例

```bash
# 创建单个邀请码
curl -X POST http://localhost:8000/api/invite-codes/create \
  -H "Content-Type: application/json" \
  -d '{"length": 8, "max_uses": 1, "expire_days": 30}'

# 批量创建 100 个邀请码
curl -X POST http://localhost:8000/api/invite-codes/batch \
  -H "Content-Type: application/json" \
  -d '{"count": 100, "length": 6}'

# 查询统计
curl http://localhost:8000/api/invite-codes/stats

# 验证邀请码
curl http://localhost:8000/api/auth/verify/ABC123
```

---

## 数据库模型

### InviteCode 表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| code | VARCHAR(20) | 邀请码 (唯一) |
| is_active | BOOLEAN | 是否激活 |
| is_used | BOOLEAN | 是否已使用 |
| used_by_user_id | INTEGER | 使用者 ID |
| used_at | DATETIME | 使用时间 |
| batch_id | VARCHAR(50) | 批次 ID |
| max_uses | INTEGER | 最大使用次数 (-1 无限) |
| current_uses | INTEGER | 当前使用次数 |
| expire_at | DATETIME | 过期时间 |
| note | VARCHAR(200) | 备注 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

## 配置项

在 `config.yaml` 中可配置:

```yaml
turing:
  auth:
    invite_code_length: 6     # 默认邀请码长度
    initial_score: 100        # 新用户初始积分
```

---

## 最佳实践

### 1. 邀请码策略

- **单次使用**: `max_uses: 1` - 适用于付费用户
- **多次使用**: `max_uses: 10` - 适用于推广人员
- **无限使用**: `max_uses: -1` - 适用于公开邀请
- **设置过期**: `expire_days: 30` - 避免长期无效码

### 2. 批次管理

批量生成时自动创建批次 ID，便于:
- 追踪不同渠道的邀请码
- 按批次统计使用率
- 批量禁用/启用

### 3. 安全建议

- 定期清理过期邀请码
- 监控异常使用模式
- 对敏感操作记录日志
- 生产环境使用更长的邀请码 (8 位+)

---

## 文件结构

```
turing_test/backend/
├── api/
│   ├── auth.py              # 认证 API (已更新)
│   └── invite_code.py       # 邀请码管理 API (新增)
├── models/
│   └── __init__.py          # 数据模型 (已更新 InviteCode)
├── schemas/
│   └── __init__.py          # Pydantic Schema (已更新)
├── services/
│   └── invite_code_service.py  # 邀请码服务 (新增)
└── test_invite_codes.py     # 测试脚本 (新增)
```

---

## 测试

运行测试脚本:

```bash
python turing_test/backend/test_invite_codes.py
```

测试覆盖:
- ✅ 邀请码生成器 (单个/批量/唯一性)
- ✅ 邀请码服务 (创建/验证/使用/查询/统计)
- ✅ API 端点说明

---

## 常见问题

### Q: 如何生成自定义邀请码？
A: 在创建时指定 `code` 参数:
```json
{"code": "MYCODE123"}
```

### Q: 邀请码可以重复使用吗？
A: 默认 `max_uses: 1`，设置更大的值或 `-1` 允许多次使用。

### Q: 如何禁用一批邀请码？
A: 通过批次 ID 查询后批量禁用:
```bash
GET /api/invite-codes/batch/{batch_id}
```

### Q: 邀请码过期后会自动删除吗？
A: 不会，过期后只是验证失败，需要手动清理。

---

## 更新日志

### 2026-02-23
- ✅ 新增 InviteCode 数据库模型
- ✅ 新增 InviteCodeService 服务
- ✅ 新增 InviteCodeGenerator 生成器
- ✅ 更新认证 API 使用新的验证机制
- ✅ 新增邀请码管理 API
- ✅ 新增测试脚本
