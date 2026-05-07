# 游戏集合 API 文档

## 概述

游戏集合提供 WebSocket 实时通信接口和 HTTP REST API。所有游戏通过统一的 WebSocket 协议进行状态同步和操作处理。

## HTTP REST API

### 游戏类型

**GET** `/api/game-types`

获取所有支持的游戏类型。

**响应示例：**
```json
{
  "types": {
    "bull_bull": {
      "name": "牛牛",
      "min_players": 2,
      "max_players": 8
    },
    "monopoly": {
      "name": "大富翁",
      "min_players": 2,
      "max_players": 6
    },
    "ludo": {
      "name": "飞行棋",
      "min_players": 2,
      "max_players": 4
    }
  }
}
```

### 房间列表

**GET** `/api/rooms`

获取所有等待中的房间（未开始游戏）。

**响应示例：**
```json
{
  "rooms": [
    {
      "room_id": "ABC123",
      "game_type": "bull_bull",
      "game_name": "牛牛",
      "host": "player1",
      "player_count": 2,
      "players": ["player1", "player2"],
      "max_players": 8,
      "bet_mode": "经典模式",
      "bet_mode_key": "classic",
      "initial_chips": 1000,
      "base_bet": 10
    }
  ]
}
```

### 用户注册

**POST** `/api/register`

注册新用户。

**请求体：**
```json
{
  "name": "player1",
  "password": "password123"
}
```

**响应示例：**
```json
{
  "ok": true,
  "name": "player1"
}
```

**错误响应：**
```json
{
  "ok": false,
  "error": "昵称已被注册"
}
```

### 用户登录

**POST** `/api/login`

用户登录。

**请求体：**
```json
{
  "name": "player1",
  "password": "password123"
}
```

**响应示例：**
```json
{
  "ok": true,
  "name": "player1"
}
```

### 排行榜

**GET** `/api/leaderboard`

获取玩家排行榜（按胜场数排序）。

**响应示例：**
```json
{
  "leaderboard": [
    {
      "name": "player1",
      "total_games": 50,
      "total_wins": 35,
      "win_rate": 70.0
    }
  ]
}
```

## WebSocket 协议

### 连接

连接到 `ws://localhost:8000/ws`

### 消息格式

所有消息为 JSON 格式，包含 `action` 字段指定操作类型。

**通用错误响应：**
```json
{
  "type": "error",
  "code": "VALIDATION_ERROR",
  "message": "玩家名称长度必须在1-20之间",
  "details": {
    "field": "name"
  },
  "timestamp": "2026-05-07T10:30:00.000000"
}
```

### 房间操作

#### 创建房间

**请求：**
```json
{
  "action": "create_room",
  "name": "player1",
  "game_type": "bull_bull",
  "settings": {
    "bet_mode": "classic",
    "initial_chips": 1000,
    "base_bet": 10
  }
}
```

**响应：**
```json
{
  "type": "room_created",
  "room_id": "ABC123",
  "name": "player1",
  "game_type": "bull_bull",
  "reconnect_token": "token_xxx"
}
```

#### 加入房间

**请求：**
```json
{
  "action": "join_room",
  "name": "player2",
  "room_id": "ABC123",
  "reconnect_token": ""
}
```

**响应：**
```json
{
  "type": "room_joined",
  "room_id": "ABC123",
  "name": "player2",
  "game_type": "bull_bull",
  "reconnected": false,
  "reconnect_token": "token_yyy"
}
```

#### 开始游戏

**请求：**
```json
{
  "action": "start_game"
}
```

#### 获取游戏状态

**请求：**
```json
{
  "action": "get_state"
}
```

**响应：**
```json
{
  "type": "game_state",
  "data": {
    "room_id": "ABC123",
    "game_type": "bull_bull",
    "phase": "playing",
    "round_number": 1,
    "players": [
      {
        "name": "player1",
        "chips": 950,
        "hand": [
          {"suit": "spades", "rank": "A"},
          {"suit": "hearts", "rank": "K"}
        ]
      }
    ]
  }
}
```

### 牛牛游戏操作

#### 确认手牌

**请求：**
```json
{
  "action": "confirm_cards"
}
```

#### 下注

**请求：**
```json
{
  "action": "place_bet",
  "bet_action": "call",
  "amount": 50
}
```

**bet_action 选项：** `call`（跟注）、`raise`（加注）、`fold`（弃牌）、`all_in`（全押）

#### 设置运气值

**请求：**
```json
{
  "action": "set_luck",
  "target": "player2",
  "luck": 5
}
```

### 大富翁游戏操作

#### 掷骰子

**请求：**
```json
{
  "action": "roll_dice"
}
```

#### 购买地产

**请求：**
```json
{
  "action": "buy_property"
}
```

#### 跳过购买（启动拍卖）

**请求：**
```json
{
  "action": "skip_buy"
}
```

#### 拍卖出价

**请求：**
```json
{
  "action": "bid_auction",
  "amount": 100
}
```

#### 拍卖放弃

**请求：**
```json
{
  "action": "pass_auction"
}
```

#### 建房

**请求：**
```json
{
  "action": "buy_house",
  "position": 5
}
```

#### 卖房

**请求：**
```json
{
  "action": "sell_house",
  "position": 5
}
```

#### 抵押地产

**请求：**
```json
{
  "action": "mortgage_property",
  "position": 5
}
```

#### 赎回地产

**请求：**
```json
{
  "action": "unmortgage_property",
  "position": 5
}
```

#### 支付监狱罚款

**请求：**
```json
{
  "action": "pay_jail_fine"
}
```

#### 使用出狱卡

**请求：**
```json
{
  "action": "use_jail_card"
}
```

#### 提议交易

**请求：**
```json
{
  "action": "propose_trade",
  "target": "player2",
  "offer": {
    "cash": 100,
    "properties": [5, 6]
  },
  "request": {
    "cash": 200,
    "properties": [10]
  }
}
```

#### 接受交易

**请求：**
```json
{
  "action": "accept_trade"
}
```

#### 拒绝交易

**请求：**
```json
{
  "action": "reject_trade"
}
```

### 飞行棋游戏操作

#### 移动棋子

**请求：**
```json
{
  "action": "move_piece",
  "piece_index": 0
}
```

### 聊天

**请求：**
```json
{
  "action": "chat",
  "message": "Hello everyone!"
}
```

## 错误代码

| 代码 | 说明 |
|------|------|
| `VALIDATION_ERROR` | 输入验证失败 |
| `STATE_ERROR` | 游戏状态错误 |
| `AUTH_ERROR` | 认证失败 |
| `PERMISSION_ERROR` | 权限不足 |
| `INTERNAL_ERROR` | 内部服务器错误 |

## 状态码

| 状态 | 说明 |
|------|------|
| `waiting` | 等待玩家加入 |
| `betting` | 下注阶段（牛牛） |
| `playing` | 游戏进行中 |
| `finished` | 游戏已结束 |

## 验证规则

### 玩家名称
- 长度：1-20 字符
- 允许：字母、数字、下划线、中文

### 金额
- 范围：0-999999
- 类型：整数

### 房间ID
- 长度：至少 6 字符
- 格式：字母数字组合

### 消息
- 长度：1-200 字符
- 类型：字符串
