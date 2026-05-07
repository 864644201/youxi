# 平台增强实现计划

> **面向 AI 代理的工作者：** 推荐子技能：superpowers:subagent-driven-development 或 superpowers:executing-plans 逐任务实现。

**目标：** 增强游戏平台——添加简易用户系统（昵称记忆 + 密码）、全局排行榜、以及优化管理员后台（支持大富翁和飞行棋的专属管理功能）

**架构：** 用户系统使用 SQLite 存储，昵称作为主键 + 可选密码哈希。排行榜从 `player_stats` 表聚合。管理后台扩展为多游戏感知，根据 `game_type` 动态渲染对应管理面板。

**技术栈：** FastAPI + SQLite（后端），HTML + JS（前端），bcrypt-free 哈希（使用 hashlib 避免额外依赖）

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `server.py` | 用户注册/登录 API、排行榜 API、管理后台 WS 扩展 |
| `static/index.html` | 大厅添加登录区域、排行榜入口 |
| `static/admin.html` | 重写详情渲染，支持大富翁/飞行棋专属管理面板 |
| `games/monopoly.py` | 添加 `admin_set_position` 方法（管理员设置玩家位置） |
| `games/ludo.py` | 添加 `admin_set_piece_position` 方法（管理员设置棋子位置） |

---

## 任务

### 任务 1：简易用户系统 — `server.py`

**文件：**
- 修改：`server.py`

- [ ] **步骤 1：添加用户表和注册/登录 API**

在 `_init_db()` 中添加用户表：

```python
c.execute("""CREATE TABLE IF NOT EXISTS users (
    name TEXT PRIMARY KEY,
    password_hash TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    last_login TEXT DEFAULT (datetime('now','localtime')),
    total_games INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0
)""")
```

在 `import` 区域添加：

```python
import hashlib
```

添加辅助函数：

```python
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
```

在页面路由区域之后、WebSocket 之前添加 REST API：

```python
@app.post("/api/register")
async def api_register(req: dict):
    name = req.get("name", "").strip()
    password = req.get("password", "").strip()
    if not name or len(name) > 12:
        return {"ok": False, "error": "昵称需1-12个字符"}
    if not password or len(password) < 4:
        return {"ok": False, "error": "密码至少4个字符"}
    existing = _db_fetch("SELECT name FROM users WHERE name = ?", (name,), fetchall=False)
    if existing:
        return {"ok": False, "error": "昵称已被注册"}
    _db_execute("INSERT INTO users (name, password_hash) VALUES (?, ?)", (name, _hash_password(password)))
    return {"ok": True, "name": name}


@app.post("/api/login")
async def api_login(req: dict):
    name = req.get("name", "").strip()
    password = req.get("password", "").strip()
    user = _db_fetch("SELECT * FROM users WHERE name = ?", (name,), fetchall=False)
    if not user:
        return {"ok": False, "error": "用户不存在"}
    if user["password_hash"] != _hash_password(password):
        return {"ok": False, "error": "密码错误"}
    _db_execute("UPDATE users SET last_login = datetime('now','localtime') WHERE name = ?", (name,))
    return {"ok": True, "name": name}


@app.get("/api/leaderboard")
async def api_leaderboard():
    rows = _db_fetch(
        """SELECT name, total_games, total_wins,
           CASE WHEN total_games > 0 THEN ROUND(CAST(total_wins AS FLOAT) / total_games * 100, 1) ELSE 0 END as win_rate
           FROM users WHERE total_games > 0
           ORDER BY total_wins DESC, win_rate DESC LIMIT 20"""
    )
    return {"leaderboard": [dict(r) for r in (rows or [])]}
```

- [ ] **步骤 2：游戏结束时更新用户统计**

在 `log_game_result` 函数末尾，遍历所有玩家更新 users 表：

```python
for p in room.players:
    _db_execute(
        """UPDATE users SET total_games = total_games + 1, last_seen = datetime('now','localtime')
           WHERE name = ?""",
        (p["name"],)
    )
    if p["name"] == winner_name:
        _db_execute("UPDATE users SET total_wins = total_wins + 1 WHERE name = ?", (p["name"],))
```

需要确保 `log_game_result` 对所有游戏类型都有效。当前它只被 Bull Bull 调用。需要让 Monopoly 和 Ludo 结束时也调用。修改 `_check_bankruptcy` 方法中的胜利检测处（`games/monopoly.py`），在 `self.phase = "finished"` 之后让 server 调用 `log_game_result`。

在 `server.py` 的 `broadcast_room` 中检测游戏结束：

```python
async def broadcast_room(room_id: str):
    if room_id not in rooms or room_id not in player_rooms:
        return
    room = rooms[room_id]
    # ... existing code ...
    # 游戏结束时记录结果
    if room.phase == "finished" and not getattr(room, '_result_logged', False):
        winner = None
        for p in room.players:
            if p.get("alive", True):
                winner = p["name"]
                break
        if winner:
            log_game_result(room, winner)
        room._result_logged = True
    await broadcast_admin()
```

- [ ] **步骤 3：验证 API**

运行：`python -c "import server; print('OK')"`
预期：输出 `OK`

---

### 任务 2：大厅集成登录和排行榜 — `static/index.html`

**文件：**
- 修改：`static/index.html`

- [ ] **步骤 1：添加登录区域**

在大厅页面顶部添加登录/注册卡片（在现有游戏卡片之前）：

```html
<div class="user-bar" id="userBar" style="text-align:center;margin-bottom:20px">
  <div id="loggedOut" style="display:inline-flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:center">
    <input type="text" id="uName" placeholder="昵称" maxlength="12" style="width:100px">
    <input type="password" id="uPass" placeholder="密码" style="width:100px">
    <button class="btn btn-sm btn-blue" onclick="doRegister()">注册</button>
    <button class="btn btn-sm btn-outline" onclick="doLogin()">登录</button>
  </div>
  <div id="loggedIn" style="display:none">
    <span style="color:var(--gold)">👤 <span id="dispName"></span></span>
    <button class="btn btn-sm btn-outline" onclick="doLogout()" style="margin-left:8px">退出</button>
  </div>
</div>
```

- [ ] **步骤 2：添加排行榜入口**

在游戏卡片区域之后添加：

```html
<div style="text-align:center;margin-top:24px">
  <button class="btn btn-outline" onclick="toggleLeaderboard()">排行榜 🏆</button>
</div>
<div id="lbPanel" style="display:none;max-width:500px;margin:16px auto">
  <div style="background:var(--card);border-radius:12px;padding:16px;border:1px solid var(--border)">
    <h3 style="color:var(--gold);margin-bottom:10px">排行榜</h3>
    <div id="lbContent">加载中...</div>
  </div>
</div>
```

- [ ] **步骤 3：添加 JS 逻辑**

```javascript
// 用户系统
let currentUser = sessionStorage.getItem('currentUser') || '';

function initUser() {
  if (currentUser) {
    document.getElementById('loggedOut').style.display = 'none';
    document.getElementById('loggedIn').style.display = '';
    document.getElementById('dispName').textContent = currentUser;
  }
}

async function doRegister() {
  const name = document.getElementById('uName').value.trim();
  const pass = document.getElementById('uPass').value.trim();
  if (!name || !pass) return toast('请输入昵称和密码');
  const r = await fetch('/api/register', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({name, password: pass}) });
  const d = await r.json();
  if (d.ok) { currentUser = name; sessionStorage.setItem('currentUser', name); initUser(); toast('注册成功!'); }
  else toast(d.error);
}

async function doLogin() {
  const name = document.getElementById('uName').value.trim();
  const pass = document.getElementById('uPass').value.trim();
  if (!name || !pass) return toast('请输入昵称和密码');
  const r = await fetch('/api/login', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({name, password: pass}) });
  const d = await r.json();
  if (d.ok) { currentUser = name; sessionStorage.setItem('currentUser', name); initUser(); toast('登录成功!'); }
  else toast(d.error);
}

function doLogout() { currentUser = ''; sessionStorage.removeItem('currentUser'); document.getElementById('loggedOut').style.display = ''; document.getElementById('loggedIn').style.display = 'none'; }

async function toggleLeaderboard() {
  const p = document.getElementById('lbPanel');
  if (p.style.display !== 'none') { p.style.display = 'none'; return; }
  p.style.display = '';
  try {
    const r = await fetch('/api/leaderboard');
    const d = await r.json();
    const lb = d.leaderboard || [];
    document.getElementById('lbContent').innerHTML = lb.length ? `<table style="width:100%;font-size:.85em;border-collapse:collapse">
      <thead><tr style="opacity:.5"><th style="text-align:left;padding:4px">#</th><th style="text-align:left;padding:4px">玩家</th><th style="padding:4px">场次</th><th style="padding:4px">胜场</th><th style="padding:4px">胜率</th></tr></thead>
      <tbody>${lb.map((p,i) => `<tr><td style="padding:4px;color:${i<3?'var(--gold)':'inherit'}">${i+1}</td><td style="padding:4px">${esc(p.name)}</td><td style="padding:4px;text-align:center">${p.total_games}</td><td style="padding:4px;text-align:center;color:var(--green)">${p.total_wins}</td><td style="padding:4px;text-align:center">${p.win_rate}%</td></tr>`).join('')}</tbody></table>` : '暂无数据';
  } catch(e) { document.getElementById('lbContent').textContent = '加载失败'; }
}

initUser();
```

- [ ] **步骤 4：自动填充昵称**

在创建房间时，如果用户已登录，自动填入昵称。在 `createRoom` 等函数中：

```javascript
// 页面加载时自动填充
if (currentUser) {
  const ci = document.getElementById('cName');
  const ji = document.getElementById('jName');
  if (ci) ci.value = currentUser;
  if (ji) ji.value = currentUser;
}
```

- [ ] **步骤 5：Commit**

```bash
git add server.py static/index.html
git commit -m "feat: 添加简易用户系统和排行榜"
```

---

### 任务 3：管理后台优化 — `static/admin.html` + `server.py`

**文件：**
- 修改：`static/admin.html`
- 修改：`server.py`

- [ ] **步骤 1：后台总览支持多游戏类型**

修改 `admin.html` 的 `renderOverview` 函数，在房间卡片中显示游戏类型徽章：

```javascript
// 替换 renderOverview 中的房间卡片渲染
const GAME_BADGES = {
  bull_bull: { name: '牛牛', color: '#e74c3c' },
  monopoly: { name: '大富翁', color: '#2ecc71' },
  ludo: { name: '飞行棋', color: '#3498db' },
};

// 在 renderOverview 的 grid.innerHTML 中：
grid.innerHTML = d.map(r => {
  const badge = GAME_BADGES[r.game_type] || { name: r.game_type, color: '#888' };
  return `<div class="room-card" onclick="enterRoom('${r.room_id}')">
    <div class="rc-actions"><button class="del-btn" onclick="event.stopPropagation();deleteRoom('${r.room_id}')" title="删除房间">&times;</button></div>
    <div class="rc-header">
      <span class="rc-id">${r.room_id}</span>
      <span style="font-size:.65em;padding:2px 8px;border-radius:6px;background:${badge.color}33;color:${badge.color}">${badge.name}</span>
      <span class="rc-phase phase-${r.phase}">${r.phase_name}</span>
    </div>
    <div class="rc-info">
      房主: ${esc(r.host)} · 第${r.round}轮<br>
      玩家: ${r.player_count}人${r.bet_mode ? ' · ' + r.bet_mode : ''}${r.pot ? ' · 奖池: ' + r.pot : ''}
    </div>
    <div class="rc-players">${r.players.map(p=>`<span class="rc-player-tag">${esc(p)}</span>`).join('')}</div>
  </div>`;
}).join('');
```

- [ ] **步骤 2：大富翁管理面板 — 渲染详情**

修改 `renderDetail` 函数，根据 `game_type` 分发：

```javascript
function renderDetail() {
  const s = detailState;
  if (!s) return;
  if (s.game_type === 'monopoly') return renderMonopolyDetail(s);
  if (s.game_type === 'ludo') return renderLudoDetail(s);
  // 默认：牛牛
  renderBullBullDetail(s);
}
```

将现有的 `renderDetail` 逻辑重命名为 `renderBullBullDetail`。

添加大富翁详情渲染：

```javascript
function renderMonopolyDetail(s) {
  document.getElementById('detailTitle').innerHTML = `房间 ${s.room_id} <span class="rc-phase phase-${s.phase}" style="font-size:.6em;vertical-align:middle">${
    {waiting:'等待中',playing:'游戏中',finished:'已结束'}[s.phase]||s.phase}</span> · 大富翁`;

  const playersGrid = document.getElementById('playersGrid');
  playersGrid.innerHTML = s.players.map((p, pi) => {
    const props = (p.properties || []).map(pr =>
      `<span style="display:inline-block;padding:1px 5px;border-radius:3px;font-size:.65em;background:${pr.group_color || '#666'};color:#fff;margin:1px">${pr.name}${pr.houses > 0 ? ' ' + pr.houses + '🏠' : ''}${pr.mortgaged ? ' 💤' : ''}</span>`
    ).join('');
    const tags = [p.name === s.host ? '<span class="p-tag">房主</span>' : '', p.in_jail ? '<span class="p-tag" style="color:#e74c3c">监狱</span>' : '', !p.alive ? '<span class="p-tag" style="color:#888">破产</span>' : ''].filter(Boolean).join('');
    return `<div class="p-card${!p.alive ? ' folded' : ''}">
      <div class="p-head"><span class="p-name">${esc(p.name)}${tags}</span><span class="p-chips">💰 $${p.cash}</span></div>
      <div class="p-asset" style="font-size:.75em;opacity:.5;margin-bottom:6px">总资产 $${p.total_asset} · 位置 ${p.position}</div>
      <div style="margin-bottom:6px">${props || '<span style="opacity:.3;font-size:.8em">无地产</span>'}</div>
      <div class="p-controls">
        <div class="cg"><label>现金:</label><input type="number" class="ci" id="ci${pi}" value="${p.cash}" min="0"><button class="sb" onclick="setCash('${esc(p.name)}',document.getElementById('ci${pi}').value)">改</button></div>
        ${p.name !== s.host ? `<button class="sb dan" onclick="kickP('${esc(p.name)}')">踢出</button>` : ''}
      </div>
    </div>`;
  }).join('');
}
```

- [ ] **步骤 3：飞行棋管理面板 — 渲染详情**

```javascript
const LUDO_COLORS = { blue: '#3498db', yellow: '#f0c040', green: '#2ecc71', red: '#e74c3c' };
const LUDO_NAMES = { blue: '蓝', yellow: '黄', green: '绿', red: '红' };

function renderLudoDetail(s) {
  document.getElementById('detailTitle').innerHTML = `房间 ${s.room_id} <span class="rc-phase phase-${s.phase}" style="font-size:.6em;vertical-align:middle">${
    {waiting:'等待中',playing:'游戏中',finished:'已结束'}[s.phase]||s.phase}</span> · 飞行棋`;

  const playersGrid = document.getElementById('playersGrid');
  playersGrid.innerHTML = s.players.map(p => {
    const col = LUDO_COLORS[p.color] || '#888';
    const colName = LUDO_NAMES[p.color] || p.color || '?';
    const pieces = (p.pieces || []).map((pos, i) => {
      let label = '';
      if (pos === -2) label = '✅';
      else if (pos === -1) label = '🏠';
      else if (pos >= 52) label = `🏁${pos - (p.color ? {blue:52,yellow:59,green:66,red:73}[p.color] : 0)}`;
      else label = `格${pos}`;
      return `<span style="font-size:.7em;padding:2px 5px;background:rgba(255,255,255,.05);border-radius:4px;margin:1px;display:inline-block">✈${i+1}: ${label}</span>`;
    }).join('');
    return `<div class="p-card${!p.alive ? ' folded' : ''}">
      <div class="p-head"><span class="p-name"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${col}"></span> ${esc(p.name)} (${colName}方)</span><span style="font-size:.8em">完成: ${p.finished}/4</span></div>
      <div style="margin:6px 0">${pieces}</div>
      <div class="p-controls">
        ${p.name !== s.host ? `<button class="sb dan" onclick="kickP('${esc(p.name)}')">踢出</button>` : ''}
      </div>
    </div>`;
  }).join('');
}
```

- [ ] **步骤 4：服务器端 admin 支持 — 现金编辑兼容所有游戏**

当前 `admin_set_chips` 在大富翁中编辑的是 `player_cash`，牛牛中编辑的是 `chips`。需要确保 admin WS 中 `admin_set_chips` 对所有游戏类型都工作。

在 `server.py` 的 `admin_set_chips` handler 中，添加日志：

```python
elif action == "admin_set_chips":
    rid = msg.get("room_id", "").strip().upper()
    if rid not in rooms:
        continue
    room = rooms[rid]
    target = msg.get("target", "")
    chips = msg.get("chips", 0)
    success = room.admin_set_chips(target, chips)
    if success:
        log_admin_action("set_chips", rid, target, {"chips": chips})
        await broadcast_room(rid)
```

现有代码已经可以工作（MonopolyRoom.admin_set_chips 返回 True/False），只需确保前端调用的是正确的字段名。

- [ ] **步骤 5：后台添加大富翁下一轮和强制结算按钮支持**

修改 `admin.html` 的下一轮/强制结算按钮逻辑，根据游戏类型显示不同按钮：

```javascript
function renderDetail() {
  const s = detailState;
  if (!s) return;

  // 根据游戏类型调整动作按钮
  const actions = document.querySelector('.detail-header .actions');
  if (s.game_type === 'monopoly') {
    actions.innerHTML = `<button class="sb pri" onclick="doNextRound()">下一轮</button>`;
  } else if (s.game_type === 'ludo') {
    actions.innerHTML = `<button class="sb pri" onclick="doNextRound()">下一轮</button>`;
  } else {
    actions.innerHTML = `<button class="sb pri" onclick="doNextRound()">下一轮</button><button class="sb" onclick="doForceFinish()">强制结算</button>`;
  }

  if (s.game_type === 'monopoly') return renderMonopolyDetail(s);
  if (s.game_type === 'ludo') return renderLudoDetail(s);
  renderBullBullDetail(s);
}
```

- [ ] **步骤 6：Commit**

```bash
git add static/admin.html server.py
git commit -m "feat: 管理后台支持大富翁和飞行棋"
```

---

## NOT in scope

- 用户头像/头像上传（复杂度高，收益低）
- 社交功能（好友系统、私聊）
- 游戏内购买/虚拟货币
- 完整 OAuth 登录（过重，局域网场景不需要）
- 游戏回放/录像系统
