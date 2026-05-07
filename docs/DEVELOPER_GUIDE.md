# 游戏集合开发者指南

## 项目结构

```
111/
├── server.py                 # FastAPI WebSocket 服务器
├── games/
│   ├── __init__.py
│   ├── base.py              # 游戏基类
│   ├── bull_bull.py         # 牛牛游戏实现
│   ├── monopoly.py          # 大富翁游戏实现
│   └── ludo.py              # 飞行棋游戏实现
├── static/
│   ├── index.html           # 游戏大厅
│   ├── bull_bull.html       # 牛牛游戏页面
│   ├── monopoly.html        # 大富翁游戏页面
│   ├── ludo.html            # 飞行棋游戏页面
│   ├── admin.html           # 管理后台
│   └── js/
│       └── game-common.js   # 前端公共库
├── game_server_improvements.py  # 后端改进模块
├── tests/
│   └── test_games.py        # 单元测试
├── docs/
│   ├── API.md               # API 文档
│   └── DEVELOPER_GUIDE.md   # 本文件
└── OPTIMIZATION_PLAN.md     # 优化计划
```

## 快速开始

### 安装依赖

```bash
pip install fastapi uvicorn python-multipart
```

### 运行服务器

```bash
python server.py
```

服务器将在 `http://localhost:8000` 启动。

### 访问游戏

- 游戏大厅：`http://localhost:8000/`
- 牛牛：`http://localhost:8000/bull-bull`
- 大富翁：`http://localhost:8000/monopoly`
- 飞行棋：`http://localhost:8000/ludo`
- 管理后台：`http://localhost:8000/admin`

## 核心概念

### 游戏基类 (games/base.py)

所有游戏继承自 `BaseGameRoom`：

```python
class BaseGameRoom:
    def __init__(self, room_id, host_name, settings=None):
        self.room_id = room_id
        self.host_name = host_name
        self.phase = "waiting"  # waiting, playing, finished
        self.players = []
        self.round_number = 0
    
    def add_player(self, name, max_players=20):
        """添加玩家"""
        pass
    
    def start_round(self):
        """开始新一轮"""
        pass
    
    def get_state(self, viewer=None):
        """获取游戏状态"""
        pass
```

### 后端改进模块 (game_server_improvements.py)

#### 验证器 (Validators)

```python
from game_server_improvements import Validators, ValidationError

# 验证玩家名称
try:
    Validators.validate_player_name("player1")
except ValidationError as e:
    print(f"验证失败: {e.message}")

# 验证金额
try:
    Validators.validate_amount(100)
except ValidationError as e:
    print(f"验证失败: {e.message}")
```

#### 权限检查 (PermissionChecker)

```python
from game_server_improvements import PermissionChecker, PermissionError

# 检查玩家是否在房间中
try:
    PermissionChecker.check_player_in_room(room, "player1")
except PermissionError as e:
    print(f"权限错误: {e.message}")

# 检查是否是房主
try:
    PermissionChecker.check_is_host(room, "player1")
except PermissionError as e:
    print(f"权限错误: {e.message}")
```

#### 操作日志 (OperationLogger)

```python
from game_server_improvements import OperationLogger

# 记录成功操作
OperationLogger.log_action(
    room_id="ABC123",
    player_name="player1",
    action="place_bet",
    result="success",
    details={"amount": 100}
)

# 记录错误
try:
    # 某个操作
    pass
except Exception as e:
    OperationLogger.log_error(
        room_id="ABC123",
        player_name="player1",
        action="place_bet",
        error=e
    )
```

#### 错误响应 (ErrorResponse)

```python
from game_server_improvements import ErrorResponse, ValidationError

# 生成验证错误响应
error_resp = ErrorResponse.validation_error(
    "玩家名称长度必须在1-20之间",
    field="name"
)
await ws.send_json(error_resp)
```

### 前端公共库 (static/js/game-common.js)

#### WebSocket 客户端

```javascript
// 创建客户端
const client = new GameWSClient("ws://localhost:8000/ws");

// 发送消息并等待确认
client.sendWithAck({
    action: "place_bet",
    amount: 100
}, timeout=5000).then(response => {
    console.log("操作成功:", response);
}).catch(error => {
    console.error("操作失败:", error);
});

// 监听游戏状态更新
client.on("game_state", (state) => {
    console.log("游戏状态:", state);
});

// 监听错误
client.on("error", (error) => {
    console.error("错误:", error);
});
```

#### 状态管理

```javascript
// 创建状态管理器
const state = new GameState();

// 订阅状态变化
state.subscribe((newState) => {
    console.log("状态已更新:", newState);
});

// 更新状态
state.setState({
    phase: "playing",
    players: [...]
});
```

#### 验证器

```javascript
// 验证玩家名称
try {
    Validators.validatePlayerName("player1");
} catch (error) {
    console.error("验证失败:", error);
}

// 验证金额
try {
    Validators.validateAmount(100);
} catch (error) {
    console.error("验证失败:", error);
}
```

## 添加新游戏

### 1. 创建游戏类

在 `games/` 目录创建新文件，例如 `games/new_game.py`：

```python
from games.base import BaseGameRoom

class NewGameRoom(BaseGameRoom):
    def __init__(self, room_id, host_name, settings=None):
        super().__init__(room_id, host_name, settings)
        self.game_type = "new_game"
    
    def start_round(self):
        self.phase = "playing"
        # 初始化游戏逻辑
    
    def get_state(self, viewer=None):
        return {
            "room_id": self.room_id,
            "game_type": self.game_type,
            "phase": self.phase,
            "players": self.players
        }
```

### 2. 注册游戏类型

在 `games/__init__.py` 中注册：

```python
from games.new_game import NewGameRoom

GAME_TYPES = {
    "new_game": {
        "name": "新游戏",
        "min_players": 2,
        "max_players": 8,
        "class": NewGameRoom
    }
}
```

### 3. 创建前端页面

在 `static/` 目录创建 `new_game.html`，引入 `game-common.js`：

```html
<!DOCTYPE html>
<html>
<head>
    <title>新游戏</title>
    <script src="js/game-common.js"></script>
</head>
<body>
    <div id="app"></div>
    <script>
        const client = new GameWSClient("ws://localhost:8000/ws");
        // 游戏逻辑
    </script>
</body>
</html>
```

### 4. 在服务器中添加路由

在 `server.py` 中添加：

```python
@app.get("/new-game")
async def new_game_page():
    return FileResponse(Path(__file__).parent / "static" / "new_game.html")
```

## 测试

### 运行单元测试

```bash
pytest tests/test_games.py -v
```

### 测试覆盖范围

- 游戏逻辑测试：`TestBullBullHand`, `TestBullBullRoom`, `TestMonopolyRoom`, `TestLudoRoom`
- 输入验证测试：`TestValidators`

### 添加新测试

在 `tests/test_games.py` 中添加测试类：

```python
class TestNewGame:
    def test_room_creation(self):
        room = NewGameRoom("room1", "host1")
        assert room.room_id == "room1"
        assert room.host_name == "host1"
    
    def test_add_player(self):
        room = NewGameRoom("room1", "host1")
        assert room.add_player("player1")
        assert len(room.players) == 1
```

## 性能优化

### 增量状态更新

使用 `StateManager` 实现增量状态更新，减少网络传输：

```python
from game_server_improvements import StateManager

state_manager = StateManager()

# 获取状态变化
delta = state_manager.get_state_delta(
    room_id="ABC123",
    last_version=1,
    state={"version": 2, "data": {...}}
)

# 只发送变化的部分
await ws.send_json({
    "type": "state_delta",
    "data": delta
})
```

### 消息确认机制

前端使用 `sendWithAck()` 确保消息被服务器处理：

```javascript
// 自动重试，超时 5 秒
client.sendWithAck({
    action: "place_bet",
    amount: 100
}, timeout=5000);
```

## 调试

### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 查看操作日志

操作日志存储在 SQLite 数据库中：

```bash
sqlite3 game_data.db
SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT 10;
```

## 常见问题

### Q: 如何添加新的游戏操作？

A: 在游戏类中添加方法，然后在 `server.py` 的 WebSocket 处理器中添加对应的 action 处理。

### Q: 如何处理玩家断线重连？

A: 使用 `reconnect_token` 机制。玩家加入房间时获得 token，断线后可用 token 重新连接。

### Q: 如何扩展验证规则？

A: 在 `game_server_improvements.py` 的 `Validators` 类中添加新的验证方法。

### Q: 如何添加新的权限检查？

A: 在 `game_server_improvements.py` 的 `PermissionChecker` 类中添加新的检查方法。

## 最佳实践

1. **始终验证输入**：使用 `Validators` 类验证所有用户输入
2. **检查权限**：使用 `PermissionChecker` 类检查操作权限
3. **记录操作**：使用 `OperationLogger` 记录所有重要操作
4. **统一错误处理**：使用 `ErrorResponse` 返回统一格式的错误
5. **编写测试**：为新功能编写单元测试
6. **文档更新**：更新 API 文档和开发指南

## 相关文档

- [API 文档](API.md)
- [优化计划](../OPTIMIZATION_PLAN.md)
- [代码审查](../REVIEW.md)
