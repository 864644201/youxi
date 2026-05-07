# 飞行棋（Ludo）实现计划

> **面向 AI 代理的工作者：** 推荐子技能：superpowers:subagent-driven-development 或 superpowers:executing-plans 逐任务实现。

**目标：** 为游戏平台新增第三款游戏——飞行棋（2-4人，掷骰子、撞子、竞速到终点）

**架构：** 继承 `BaseGameRoom` 实现 `LudoRoom`，复用现有 WebSocket 框架和广播机制。棋盘用 15x15 CSS Grid 渲染，前端纯 JS。

**技术栈：** FastAPI + WebSocket + Python（后端），HTML + CSS Grid + JS（前端）

---

## 棋盘设计

### 数据模型

棋盘由两部分组成：
- **外圈路径**：52 个位置（0-51），顺时针绕行，4 边各 13 格
- **各玩家归家道**：6 个位置（终点前的冲刺路径），分别通往中心

```
位置编号（外圈 0-51）：
  蓝方起点 = 0    黄方起点 = 13
  绿方起点 = 26   红方起点 = 39

安全格（不可被撞）：0, 8, 13, 21, 26, 34, 39, 47
```

### 归家道

每方有 6 格归家道（home stretch），走完外圈后进入：
- 蓝方：HOME_BLUE_START(52) → HOME_BLUE_START+5(57) → 终点(58)
- 黄方：HOME_YELLOW_START(59) → HOME_YELLOW_START+5(64) → 终点(65)
- 绿方：HOME_GREEN_START(66) → HOME_GREEN_START+5(71) → 终点(72)
- 红方：HOME_RED_START(73) → HOME_RED_START+5(78) → 终点(79)

每个玩家的棋子位置状态：
- `-2` = 已完成（到达终点）
- `-1` = 在停机坪（yard）
- `0-51` = 在外圈
- `52+` = 在归家道（相对值，需减去 HOME_*_START 得到归家道内偏移）

### 前端棋盘 CSS Grid

15x15 网格，中心 6x6 区域为归家道，四角为各玩家停机坪，外围为路径格。

格子类型：
- `path` — 外圈路径格（白色底）
- `safe` — 安全格（星标）
- `start-{color}` — 各方起点（特殊标记）
- `home-{color}` — 归家道格（彩色底）
- `yard-{color}` — 停机坪（4 个棋位）
- `center` — 中心终点区
- `empty` — 不可见区域

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `games/ludo.py` | LudoRoom 类、棋盘常量、移动/碰撞逻辑 |
| `static/ludo.html` | 飞行棋前端（棋盘渲染、骰子动画、玩家面板） |
| `games/__init__.py` | 注册 LudoRoom 到 GAME_TYPES |
| `server.py` | 添加 `/ludo` 路由、WebSocket 处理飞行棋操作 |
| `static/index.html` | 大厅添加飞行棋卡片 |

---

## 任务

### 任务 1：后端游戏逻辑 — `games/ludo.py`

**文件：**
- 创建：`games/ludo.py`

- [ ] **步骤 1：定义棋盘常量和路径映射**

```python
"""飞行棋游戏逻辑"""
import random
import secrets
import time
from .base import BaseGameRoom

COLORS = ["blue", "yellow", "green", "red"]
COLOR_NAMES = {"blue": "蓝", "yellow": "黄", "green": "绿", "red": "红"}
COLOR_HEX = {"blue": "#3498db", "yellow": "#f0c040", "green": "#2ecc71", "red": "#e74c3c"}

# 外圈起始位置（各玩家从 yard 出发的入口）
START_POS = {"blue": 0, "yellow": 13, "green": 26, "red": 39}

# 安全格（不可被撞）
SAFE_POSITIONS = {0, 8, 13, 21, 26, 34, 39, 47}

# 归家道起始位置
HOME_ENTRY = {"blue": 50, "yellow": 11, "green": 24, "red": 37}
# 注意：HOME_ENTRY 是玩家在走完一圈后、进入归家道之前最后经过的外圈位置
# 当棋子位置 + 骰子值 超过 HOME_ENTRY 时，进入归家道

# 归家道在统一编号中的起始
HOME_START = {"blue": 52, "yellow": 59, "green": 66, "red": 73}
HOME_LEN = 6  # 归家道长度

# 终点位置
FINISHED = -2
YARD = -1

OUTER_LEN = 52

def next_pos(color: str, current: int, steps: int) -> int | None:
    """计算棋子下一步位置。返回 None 表示超出（不能移动）"""
    start = START_POS[color]
    entry = HOME_ENTRY[color]  # 进入归家道前的最后一个外圈位置
    home_s = HOME_START[color]

    if current == YARD:
        # 在停机坪，只有掷出 6 才能出来
        if steps == 6:
            return start
        return None

    if current >= home_s:
        # 在归家道内
        offset = current - home_s
        new_offset = offset + steps
        if new_offset < HOME_LEN:
            return home_s + new_offset
        elif new_offset == HOME_LEN:
            return FINISHED
        else:
            return None  # 超出终点，不能移动

    # 在外圈
    # 计算当前位置距离起点走了多少步
    dist_from_start = (current - start) % OUTER_LEN
    new_dist = dist_from_start + steps

    # 走到归家道入口的距离
    entry_dist = (entry - start) % OUTER_LEN

    if new_dist <= entry_dist:
        # 还在外圈
        return (current + steps) % OUTER_LEN
    else:
        # 进入归家道
        home_offset = new_dist - entry_dist - 1
        if home_offset < HOME_LEN:
            return home_s + home_offset
        elif home_offset == HOME_LEN:
            return FINISHED
        else:
            return None  # 超出
```

- [ ] **步骤 2：实现 LudoRoom 类主体**

```python
class LudoRoom(BaseGameRoom):
    game_type = "ludo"
    game_name = "飞行棋"

    def __init__(self, room_id: str, host_name: str, settings: dict = None):
        super().__init__(room_id, host_name, settings)
        self.phase = "waiting"
        # 每个玩家 4 个棋子: {color: [pos, pos, pos, pos]}
        self.pieces: dict[str, list[int]] = {}
        self.player_colors: dict[str, str] = {}  # name -> color
        self.current_player_index = 0
        self.dice_value = 0
        self.doubles_streak = 0  # 连续掷6次数
        self.must_move = False  # 掷骰后必须移动
        self.events: list[dict] = []
        self.max_players_setting = 4  # 飞行棋默认最多4人

    def _add_event(self, text: str, icon: str = "", event_type: str = "info"):
        t = time.strftime("%H:%M:%S")
        self.events.append({"text": text, "icon": icon, "type": event_type, "time": t})
        if len(self.events) > 100:
            self.events = self.events[-100:]

    def add_player(self, name: str, max_players: int = 4) -> bool:
        if any(p["name"] == name for p in self.players):
            return False
        if len(self.players) >= max_players:
            return False
        reconnect_token = secrets.token_hex(6)
        self.players.append({"name": name, "reconnect_token": reconnect_token})
        return True
```

- [ ] **步骤 3：实现 start_round 和回合管理**

```python
    def start_round(self) -> bool:
        if not self.can_start():
            return False
        self.round_number += 1
        self.phase = "playing"
        self.events = []

        # 分配颜色
        available = list(COLORS)
        random.shuffle(available)
        self.player_colors = {}
        self.pieces = {}
        for i, p in enumerate(self.players):
            color = available[i % len(available)]
            self.player_colors[p["name"]] = color
            self.pieces[color] = [YARD, YARD, YARD, YARD]
            p["alive"] = True

        self.current_player_index = 0
        self.dice_value = 0
        self.doubles_streak = 0
        self.must_move = False
        self._add_event("游戏开始！每人 4 架飞机", "✈️", "system")
        return True

    @property
    def current_player(self) -> dict | None:
        alive = [p for p in self.players if p.get("alive", True)]
        if not alive:
            return None
        self.current_player_index = self.current_player_index % len(alive)
        return alive[self.current_player_index]

    def _get_movable_pieces(self, color: str, dice: int) -> list[int]:
        """返回可以移动的棋子索引列表"""
        result = []
        for i, pos in enumerate(self.pieces[color]):
            if pos == FINISHED:
                continue
            if next_pos(color, pos, dice) is not None:
                result.append(i)
        return result

    def _next_turn(self):
        alive = [p for p in self.players if p.get("alive", True)]
        if len(alive) <= 1:
            if alive:
                self._add_event(f"🏆 {alive[0]['name']} 获胜！", "🏆", "victory")
            self.phase = "finished"
            return
        self.current_player_index = (self.current_player_index + 1) % len(alive)
        self.dice_value = 0
        self.doubles_streak = 0
        self.must_move = False
        cp = self.current_player
        if cp:
            self._add_event(f"轮到 {cp['name']}（{COLOR_NAMES[self.player_colors[cp['name']]]}方）", "🎲", "turn")
```

- [ ] **步骤 4：实现掷骰子和移动逻辑**

```python
    def roll_dice(self, name: str) -> dict:
        cp = self.current_player
        if not cp or cp["name"] != name:
            return {"ok": False, "error": "不是你的回合"}
        if self.must_move:
            return {"ok": False, "error": "请先选择要移动的棋子"}

        dice = random.randint(1, 6)
        self.dice_value = dice
        color = self.player_colors[name]

        result = {"ok": True, "dice": dice, "color": color}

        if dice == 6:
            self.doubles_streak += 1
            if self.doubles_streak >= 3:
                self._add_event(f"{name} 连续三次掷6，跳过回合！", "⚠️", "action")
                self._next_turn()
                result["triple_six_skip"] = True
                return result
            result["roll_again"] = True
        else:
            self.doubles_streak = 0

        movable = self._get_movable_pieces(color, dice)

        if not movable:
            self._add_event(f"{name} 掷出 {dice}，无棋子可移动", "🎲", "action")
            if dice != 6:
                self._next_turn()
            else:
                # 掷6但无子可动，给额外回合
                self.dice_value = 0
            result["no_movable"] = True
            return result

        if len(movable) == 1:
            # 只有一个可移动，自动移动
            return self.move_piece(name, movable[0])

        self.must_move = True
        result["movable_pieces"] = movable
        result["needs_action"] = True
        self._add_event(f"{name} 掷出 {dice}，选择要移动的棋子", "🎲", "action")
        return result

    def move_piece(self, name: str, piece_index: int) -> dict:
        cp = self.current_player
        if not cp or cp["name"] != name:
            return {"ok": False, "error": "不是你的回合"}

        color = self.player_colors[name]
        dice = self.dice_value

        if piece_index < 0 or piece_index >= 4:
            return {"ok": False, "error": "无效的棋子"}

        pos = self.pieces[color][piece_index]
        new_pos = next_pos(color, pos, dice)

        if new_pos is None:
            return {"ok": False, "error": "该棋子无法移动"}

        result = {"ok": True, "piece_index": piece_index, "dice": dice, "color": color}
        self.pieces[color][piece_index] = new_pos

        if new_pos == FINISHED:
            self._add_event(f"{name} 的飞机到达终点！✈️", "🏁", "action")
            result["finished"] = True
        else:
            # 检查撞子
            capture = self._check_capture(color, new_pos)
            if capture:
                result["captured"] = capture
            self._add_event(
                f"{name} 移动飞机到位置 {new_pos}" +
                (f"，撞了 {capture['captured_player']} 的飞机！" if capture else ""),
                "✈️", "action"
            )

        # 检查胜利
        if all(p == FINISHED for p in self.pieces[color]):
            self._add_event(f"🏆 {name} 所有飞机到达终点，获胜！", "🏆", "victory")
            self.phase = "finished"
            result["game_over"] = True
            result["winner"] = name
            return result

        self.must_move = False

        # 掷6额外回合
        if dice == 6:
            self.dice_value = 0
            result["roll_again"] = True
        else:
            self._next_turn()

        return result

    def _check_capture(self, mover_color: str, pos: int) -> dict | None:
        """检查在 pos 位置是否撞了别人的飞机"""
        if pos in SAFE_POSITIONS or pos >= HOME_START.get(mover_color, 999):
            return None
        if pos < 0:
            return None

        for color, pieces in self.pieces.items():
            if color == mover_color:
                continue
            for i, p in enumerate(pieces):
                if p == pos:
                    # 撞了！送回停机坪
                    pieces[i] = YARD
                    pname = next(pl["name"] for pl in self.players
                                if self.player_colors.get(pl["name"]) == color)
                    self._add_event(f"💥 {COLOR_NAMES[mover_color]}方撞了{COLOR_NAMES[color]}方的飞机！", "💥", "action")
                    return {"captured_player": pname, "captured_color": color, "captured_piece": i}
        return None
```

- [ ] **步骤 5：实现 get_state 和 admin 方法**

```python
    def get_state(self, viewer: str = None) -> dict:
        alive = [p for p in self.players if p.get("alive", True)]
        current_name = None
        if alive:
            idx = self.current_player_index % len(alive)
            current_name = alive[idx]["name"]

        players_info = []
        for p in self.players:
            name = p["name"]
            color = self.player_colors.get(name, "")
            pieces = self.pieces.get(color, [YARD]*4)
            finished_count = sum(1 for pos in pieces if pos == FINISHED)
            players_info.append({
                "name": name,
                "alive": p.get("alive", True),
                "color": color,
                "color_name": COLOR_NAMES.get(color, ""),
                "color_hex": COLOR_HEX.get(color, "#888"),
                "pieces": pieces,
                "finished": finished_count,
                "is_current": name == current_name,
            })

        return {
            "game_type": self.game_type,
            "room_id": self.room_id,
            "round": self.round_number,
            "phase": self.phase,
            "host": self.host_name,
            "players": players_info,
            "current_player": current_name,
            "dice": self.dice_value,
            "must_move": self.must_move,
            "events": self.events[-30:],
            "chat": self.chat[-20:],
            "viewer": viewer,
        }

    def admin_get_full_state(self) -> dict:
        state = self.get_state()
        state["pieces_raw"] = {k: list(v) for k, v in self.pieces.items()}
        state["player_colors_raw"] = dict(self.player_colors)
        return state

    def admin_set_chips(self, target_name: str, chips: int) -> bool:
        # 飞行棋没有筹码概念，但保留接口兼容
        return False
```

- [ ] **步骤 6：验证导入无误**

运行：`python -c "from games.ludo import LudoRoom; print('OK')"`
预期：输出 `OK`

---

### 任务 2：服务器集成

**文件：**
- 修改：`games/__init__.py`（注册 LudoRoom）
- 修改：`server.py`（路由 + WebSocket 处理）

- [ ] **步骤 1：注册游戏类型**

修改 `games/__init__.py`，添加 LudoRoom 导入和注册：

```python
from .ludo import LudoRoom

GAME_TYPES = {
    "bull_bull": {"name": "牛牛", "class": BullBullRoom, "min_players": 2, "max_players": 20},
    "monopoly":  {"name": "大富翁", "class": MonopolyRoom, "min_players": 2, "max_players": 8},
    "ludo":      {"name": "飞行棋", "class": LudoRoom, "min_players": 2, "max_players": 4},
}
```

- [ ] **步骤 2：添加 HTTP 路由**

在 `server.py` 中添加：

```python
from games.ludo import LudoRoom

@app.get("/ludo")
async def ludo_page():
    return FileResponse("static/ludo.html")
```

- [ ] **步骤 3：添加 WebSocket 操作处理**

在 `/ws` 的消息处理中，添加飞行棋专用操作：

```python
elif action == "roll_dice":
    # 已有大富翁的 roll_dice，需要根据游戏类型分发
    if isinstance(room, MonopolyRoom):
        result = room.roll_dice(conn["name"])
    elif isinstance(room, LudoRoom):
        result = room.roll_dice(conn["name"])
    # ...

elif action == "move_piece":
    if isinstance(room, LudoRoom):
        piece_index = data.get("piece_index", 0)
        result = room.move_piece(conn["name"], piece_index)
```

注意：现有的 `roll_dice` 处理已经检查 `isinstance(room, MonopolyRoom)`。需要扩展为也处理 `LudoRoom`。关键改动点：

```python
elif action == "roll_dice":
    if isinstance(room, MonopolyRoom):
        result = room.roll_dice(conn["name"])
    elif isinstance(room, LudoRoom):
        result = room.roll_dice(conn["name"])
    else:
        await ws.send_json({"type": "error", "message": "此游戏不支持掷骰子"})
        continue
    # ... broadcast
```

- [ ] **步骤 4：验证服务器启动**

运行：`python -c "import server; print('OK')"`
预期：输出 `OK`

---

### 任务 3：前端棋盘渲染 — `static/ludo.html`

**文件：**
- 创建：`static/ludo.html`

- [ ] **步骤 1：HTML 骨架 + CSS 变量**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>飞行棋</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0f1923;--card:rgba(255,255,255,.06);--border:rgba(255,255,255,.08);
  --gold:#f0c040;--green:#2ecc71;--red:#e74c3c;--blue:#3498db;--yellow:#f0c040;
  --text:#e8e8e8;--muted:rgba(255,255,255,.45);
  --board-bg:#2d5a27;--cell:#e8ebe4;
}
body{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
.container{max-width:1100px;margin:0 auto;padding:12px}
a.back{color:var(--muted);text-decoration:none;font-size:.85em}
/* ... 大厅、等待、游戏布局样式，参考 monopoly.html 模式 */
</style>
</head>
```

- [ ] **步骤 2：15x15 棋盘 CSS Grid 定义**

```css
.board{
  display:grid;
  grid-template-columns:repeat(15, 1fr);
  grid-template-rows:repeat(15, 1fr);
  gap:1px;background:var(--board-bg);border:3px solid #1a3a15;
  border-radius:8px;width:min(90vw, 560px);height:min(90vw, 560px);
  box-shadow:0 4px 24px rgba(0,0,0,.4);position:relative;
}
.cell{background:var(--cell);border-radius:2px;display:flex;align-items:center;justify-content:center;font-size:.6em;position:relative}
.cell.safe{background:#ffeaa7}
.cell.home-blue{background:rgba(52,152,219,.25)}
.cell.home-yellow{background:rgba(240,192,64,.25)}
.cell.home-green{background:rgba(46,204,113,.25)}
.cell.home-red{background:rgba(231,76,60,.25)}
.cell.yard{background:rgba(255,255,255,.05);border-radius:6px}
.cell.center{background:linear-gradient(135deg,#1a3a15,#2d5a27)}
.cell.start-blue{background:rgba(52,152,219,.15)}
.cell.start-yellow{background:rgba(240,192,64,.15)}
.cell.start-green{background:rgba(46,204,113,.15)}
.cell.start-red{background:rgba(231,76,60,.15)}
.pawn{width:18px;height:18px;border-radius:50%;border:2px solid rgba(0,0,0,.3);position:absolute;box-shadow:0 1px 3px rgba(0,0,0,.3);transition:all .3s ease}
.pawn.blue{background:#3498db}.pawn.yellow{background:#f0c040}
.pawn.green{background:#2ecc71}.pawn.red{background:#e74c3c}
.pawn.highlight{box-shadow:0 0 8px var(--gold);animation:pulse 1s infinite}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.2)}}
```

- [ ] **步骤 3：棋盘网格生成 JS**

定义棋盘每个格子的 grid 坐标映射：

```javascript
// 外圈 52 格在 15x15 网格中的 (row, col) 坐标
// bottom row: (14,1)→(14,13), right col: (13,14)→(1,14),
// top row: (0,13)→(0,1), left col: (1,0)→(13,0)
const OUTER_GRID = [
  // 底边 (positions 0-12): 从左下往右
  [14,1],[14,2],[14,3],[14,4],[14,5],[14,6],[14,7],
  [14,8],[14,9],[14,10],[14,11],[14,12],[14,13],
  // 右边 (positions 13-25): 从下往上
  [13,14],[12,14],[11,14],[10,14],[9,14],[8,14],[7,14],
  [6,14],[5,14],[4,14],[3,14],[2,14],[1,14],
  // 顶边 (positions 26-38): 从右往左
  [0,13],[0,12],[0,11],[0,10],[0,9],[0,8],[0,7],
  [0,6],[0,5],[0,4],[0,3],[0,2],[0,1],
  // 左边 (positions 39-51): 从上往下
  [1,0],[2,0],[3,0],[4,0],[5,0],[6,0],[7,0],
  [8,0],[9,0],[10,0],[11,0],[12,0],[13,0],
];

// 各方归家道坐标 (6 格)
const HOME_GRID = {
  blue:   [[13,7],[12,7],[11,7],[10,7],[9,7],[8,7]],
  yellow: [[7,13],[7,12],[7,11],[7,10],[7,9],[7,8]],
  green:  [[1,7],[2,7],[3,7],[4,7],[5,7],[6,7]],
  red:    [[7,1],[7,2],[7,3],[7,4],[7,5],[7,6]],
};

// 停机坪坐标 (每方 4 个棋位)
const YARD_GRID = {
  blue:   [[11,1],[11,3],[13,1],[13,3]],
  yellow: [[11,11],[11,13],[13,11],[13,13]],
  green:  [[1,11],[1,13],[3,11],[3,13]],
  red:    [[1,1],[1,3],[3,1],[3,3]],
};

// 中心终点
const CENTER = [[7,6],[7,7],[7,8],[6,7],[8,7],[7,7]];
```

- [ ] **步骤 4：buildBoard 和 renderBoard 函数**

```javascript
function buildBoard() {
  const b = document.getElementById('board');
  b.innerHTML = '';

  // 外圈格
  for (let i = 0; i < 52; i++) {
    const [r, c] = OUTER_GRID[i];
    const d = document.createElement('div');
    d.className = 'cell';
    d.style.gridRow = r + 1; d.style.gridColumn = c + 1;
    d.dataset.pos = i;
    // 安全格、起点标记
    if (SAFE_POSITIONS.has(i)) d.classList.add('safe');
    for (const [color, start] of Object.entries(START_POS)) {
      if (i === start) d.classList.add('start-' + color);
    }
    d.innerHTML = `<span style="font-size:.6em;opacity:.4">${i}</span>`;
    b.appendChild(d);
  }

  // 归家道格
  for (const [color, coords] of Object.entries(HOME_GRID)) {
    coords.forEach(([r, c], idx) => {
      const d = document.createElement('div');
      d.className = `cell home-${color}`;
      d.style.gridRow = r + 1; d.style.gridColumn = c + 1;
      b.appendChild(d);
    });
  }

  // 停机坪
  for (const [color, coords] of Object.entries(YARD_GRID)) {
    coords.forEach(([r, c], idx) => {
      const d = document.createElement('div');
      d.className = `cell yard yard-${color}`;
      d.style.gridRow = r + 1; d.style.gridColumn = c + 1;
      d.dataset.yard = `${color}-${idx}`;
      d.onclick = () => handleYardClick(color, idx);
      b.appendChild(d);
    });
  }

  // 中心区域
  const ctr = document.createElement('div');
  ctr.className = 'cell center';
  ctr.style.gridRow = '7 / 10'; ctr.style.gridColumn = '7 / 10';
  ctr.innerHTML = '<span style="font-size:1.4em;font-weight:900;color:var(--gold)">✈️</span>';
  b.appendChild(ctr);
}

function renderBoard(s) {
  // 清除旧棋子
  document.querySelectorAll('.pawn').forEach(p => p.remove());
  document.querySelectorAll('.hl').forEach(c => c.classList.remove('hl'));

  s.players.forEach(p => {
    const color = p.color;
    p.pieces.forEach((pos, idx) => {
      let target;
      if (pos === -2) {
        // 已完成 — 放在中心
        target = findEmptyCenter();
      } else if (pos === -1) {
        // 在停机坪
        const [r, c] = YARD_GRID[color][idx];
        target = document.querySelector(`.cell[data-yard="${color}-${idx}"]`);
      } else if (pos >= 52) {
        // 在归家道
        const offset = pos - HOME_START[color];
        const [r, c] = HOME_GRID[color][offset];
        target = document.querySelector(`.cell.home-${color}`);
        // 通过坐标找
      } else {
        // 在外圈
        target = document.querySelector(`.cell[data-pos="${pos}"]`);
      }
      if (target) {
        const pawn = document.createElement('div');
        pawn.className = `pawn ${color}`;
        // 可移动时高亮
        if (s.must_move && s.current_player === s.viewer && p.name === s.viewer) {
          pawn.classList.add('highlight');
        }
        pawn.onclick = () => movePiece(idx);
        target.appendChild(pawn);
      }
    });
  });
}
```

- [ ] **步骤 5：骰子和动作 UI**

```javascript
function renderActions(s) {
  const el = document.getElementById('actPanel');
  const cp = s.players.find(p => p.is_current);
  const myTurn = cp && cp.name === myName;

  if (s.phase === 'finished') {
    const w = s.players.find(p => p.finished === 4);
    el.innerHTML = `<div class="act" style="text-align:center">
      <h3>🏆 ${w ? w.name + ' 获胜!' : '游戏结束'}</h3>
      ${myName === s.host ? '<button class="btn btn-blue" onclick="startGame()">再来一局</button>' : ''}
    </div>`;
    return;
  }

  if (!myTurn) {
    el.innerHTML = `<div class="act"><p style="text-align:center;color:var(--muted)">
      等待 ${cp ? cp.name : '...'} 掷骰子</p></div>`;
    return;
  }

  if (s.must_move) {
    const me = s.players.find(p => p.name === myName);
    el.innerHTML = `<div class="act"><h3>掷出 ${s.dice} — 点击棋子移动</h3></div>`;
    return;
  }

  el.innerHTML = `<div class="act"><div class="act-btns">
    <button class="btn btn-blue btn-lg" onclick="rollDice()">掷骰子 🎲</button>
  </div></div>`;
}

function rollDice() { send({ action: 'roll_dice' }); }
function movePiece(idx) { send({ action: 'move_piece', piece_index: idx }); }
```

- [ ] **步骤 6：WS 连接和状态处理**

复用 `monopoly.html` 的 WS 连接模式（connect, reconnect, send, handleMsg）。

关键差异：
- `game_type: 'ludo'` 创建房间
- 房间列表只显示 `game_type === 'ludo'` 的房间
- 动画：掷骰子后如果有唯一可移动棋子，自动播放移动动画

---

### 任务 4：大厅更新

**文件：**
- 修改：`static/index.html`

- [ ] **步骤 1：添加飞行棋游戏卡片**

在 `games-grid` 中添加第三张卡片：

```html
<div class="game-card" onclick="location.href='/ludo'">
  <div class="gc-icon">✈️</div>
  <div class="gc-name">飞行棋</div>
  <div class="gc-desc">经典飞行棋，掷骰子竞速，撞回对手飞机，最先到达终点获胜！2-4人对战。</div>
  <div class="gc-meta">
    <span>👥 2-4人</span>
    <span>🎯 经典飞行棋</span>
  </div>
  <a class="gc-btn" href="/ludo">进入游戏</a>
</div>
```

- [ ] **步骤 2：房间列表添加飞行棋标签**

在 `renderRoomList` 函数中添加飞行棋的路由和 badge：

```javascript
const href = r.game_type === 'monopoly' ? '/monopoly'
  : r.game_type === 'ludo' ? '/ludo' : '/bull-bull';
// ...
rc-badge 中添加 ludo 样式
```

CSS 添加：
```css
.rc-badge.ludo { background: rgba(46,204,113,.2); color: #2ecc71; }
```

---

### 任务 5：集成测试

- [ ] **步骤 1：启动服务器验证所有路由**

运行：`python server.py`
访问：`http://localhost:8000`（大厅）、`/ludo`（飞行棋页面）
预期：所有页面正常加载，无报错

- [ ] **步骤 2：创建飞行棋房间并开始游戏**

1. 打开两个浏览器窗口
2. 都访问 `/ludo`，创建/加入同一房间
3. 房主点击开始
4. 验证：棋盘渲染正确，4色棋子在停机坪，骰子可掷

- [ ] **步骤 3：测试核心玩法**

1. 掷骰子 → 需要掷6才能出子
2. 掷6后飞机到起点
3. 继续掷骰移动
4. 测试撞子（让一个棋子追上另一个玩家的棋子）
5. 测试安全格（不可被撞）
6. 测试归家道进入
7. 测试胜利条件

- [ ] **步骤 4：Commit**

```bash
git add games/ludo.py games/__init__.py server.py static/ludo.html static/index.html
git commit -m "feat: 新增飞行棋游戏 - 2-4人对战，撞子竞速"
```

---

## NOT in scope

- 飞行棋的音效（属于平台增强计划）
- 飞行棋的后台管理（属于平台增强计划）
- 飞行棋的交易系统（飞行棋不需要）
- AI 对手（后续考虑）
