# 大富翁进一步优化实现计划

> **面向 AI 代理的工作者：** 推荐子技能：superpowers:subagent-driven-development 或 superpowers:executing-plans 逐任务实现。

**目标：** 为大富翁添加玩家交易系统和游戏音效，提升游戏策略深度和沉浸感

**架构：** 交易系统在后端 MonopolyRoom 中添加 `propose_trade`/`accept_trade`/`reject_trade` 方法，通过 `pending_action` 机制管理。音效系统纯前端实现，使用 Web Audio API 生成合成音效（无需音频文件）。

**技术栈：** FastAPI + WebSocket（后端交易逻辑），Web Audio API（前端音效），HTML + JS（前端交易 UI）

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `games/monopoly.py` | 添加交易方法（propose/accept/reject/cancel） |
| `server.py` | 添加 `propose_trade`/`accept_trade`/`reject_trade` WS 操作 |
| `static/monopoly.html` | 添加交易 UI 面板 + 音效系统 |

---

## 任务

### 任务 1：后端交易系统 — `games/monopoly.py`

**文件：**
- 修改：`games/monopoly.py`

- [ ] **步骤 1：添加交易状态和方法**

在 `MonopolyRoom.__init__` 中添加：

```python
# 交易系统
self.trade: dict | None = None  # 当前活跃交易
```

在 `_next_turn` 方法中（清理阶段），添加：

```python
self.trade = None
```

在类中添加以下方法：

```python
def propose_trade(self, proposer: str, target: str, offer: dict, request: dict) -> dict:
    """发起交易提议
    offer: {"cash": int, "properties": [int, ...]}
    request: {"cash": int, "properties": [int, ...]}
    """
    cp = self.current_player
    if not cp or cp["name"] != proposer:
        return {"ok": False, "error": "不是你的回合"}
    if proposer == target:
        return {"ok": False, "error": "不能和自己交易"}
    if self.trade and not self.trade.get("ended"):
        return {"ok": False, "error": "已有进行中的交易"}
    if self.pending_action:
        return {"ok": False, "error": "请先处理当前操作"}

    target_alive = any(p["name"] == target and p.get("alive", True) for p in self.players)
    if not target_alive:
        return {"ok": False, "error": "目标玩家不存在或已破产"}

    offer_cash = offer.get("cash", 0)
    offer_props = offer.get("properties", [])
    req_cash = request.get("cash", 0)
    req_props = request.get("properties", [])

    # 验证 proposer 拥有 offer 的地产
    for idx in offer_props:
        if self.properties.get(idx) != proposer:
            return {"ok": False, "error": f"你不拥有 {BOARD_SPACES[idx]['name']}"}
        if self.houses.get(idx, 0) > 0:
            return {"ok": False, "error": f"请先拆除 {BOARD_SPACES[idx]['name']} 的房子"}

    # 验证 target 拥有 request 的地产
    for idx in req_props:
        if self.properties.get(idx) != target:
            return {"ok": False, "error": f"{target} 不拥有 {BOARD_SPACES[idx]['name']}"}
        if self.houses.get(idx, 0) > 0:
            return {"ok": False, "error": f"{target} 的 {BOARD_SPACES[idx]['name']} 还有房子"}

    # 验证现金
    if offer_cash > self.player_cash.get(proposer, 0):
        return {"ok": False, "error": "你的现金不足"}
    if req_cash > self.player_cash.get(target, 0):
        return {"ok": False, "error": f"{target} 的现金不足"}

    self.trade = {
        "proposer": proposer,
        "target": target,
        "offer": {"cash": offer_cash, "properties": offer_props},
        "request": {"cash": req_cash, "properties": req_props},
        "ended": False,
    }

    offer_desc = []
    if offer_cash > 0: offer_desc.append(f"${offer_cash}")
    for idx in offer_props: offer_desc.append(BOARD_SPACES[idx]["name"])
    req_desc = []
    if req_cash > 0: req_desc.append(f"${req_cash}")
    for idx in req_props: req_desc.append(BOARD_SPACES[idx]["name"])

    self._add_event(
        f"{proposer} 向 {target} 发起交易: {'+'.join(offer_desc) or '无'} ↔ {'+'.join(req_desc) or '无'}",
        "🤝", "trade"
    )
    return {"ok": True, "trade": self.trade}

def accept_trade(self, name: str) -> dict:
    if not self.trade or self.trade.get("ended"):
        return {"ok": False, "error": "没有进行中的交易"}
    if self.trade["target"] != name:
        return {"ok": False, "error": "这不是发给你的交易"}

    t = self.trade
    proposer = t["proposer"]
    target = t["target"]

    # 再次验证
    for idx in t["offer"]["properties"]:
        if self.properties.get(idx) != proposer:
            self.trade["ended"] = True
            return {"ok": False, "error": "交易条件已不满足"}
    for idx in t["request"]["properties"]:
        if self.properties.get(idx) != target:
            self.trade["ended"] = True
            return {"ok": False, "error": "交易条件已不满足"}
    if t["offer"]["cash"] > self.player_cash.get(proposer, 0):
        self.trade["ended"] = True
        return {"ok": False, "error": "对方现金不足"}
    if t["request"]["cash"] > self.player_cash.get(target, 0):
        self.trade["ended"] = True
        return {"ok": False, "error": "你的现金不足"}

    # 执行交易
    self.player_cash[proposer] -= t["offer"]["cash"]
    self.player_cash[proposer] += t["request"]["cash"]
    self.player_cash[target] -= t["request"]["cash"]
    self.player_cash[target] += t["offer"]["cash"]

    for idx in t["offer"]["properties"]:
        self.properties[idx] = target
    for idx in t["request"]["properties"]:
        self.properties[idx] = proposer

    self.trade["ended"] = True
    self._add_event(f"{target} 接受了 {proposer} 的交易！🤝", "🤝", "trade")
    return {"ok": True, "accepted": True}

def reject_trade(self, name: str) -> dict:
    if not self.trade or self.trade.get("ended"):
        return {"ok": False, "error": "没有进行中的交易"}
    if self.trade["target"] != name:
        return {"ok": False, "error": "这不是发给你的交易"}
    self.trade["ended"] = True
    self._add_event(f"{name} 拒绝了交易", "❌", "trade")
    return {"ok": True, "rejected": True}

def cancel_trade(self, name: str) -> dict:
    if not self.trade or self.trade.get("ended"):
        return {"ok": False, "error": "没有进行中的交易"}
    if self.trade["proposer"] != name:
        return {"ok": False, "error": "只有发起者能取消"}
    self.trade["ended"] = True
    self._add_event(f"{name} 取消了交易", "❌", "trade")
    return {"ok": True, "cancelled": True}
```

- [ ] **步骤 2：更新 get_state 返回交易信息**

在 `get_state` 方法返回的字典中添加：

```python
"trade": self.trade if self.trade and not self.trade.get("ended") else None,
```

- [ ] **步骤 3：验证导入**

运行：`python -c "from games.monopoly import MonopolyRoom; print('OK')"`
预期：输出 `OK`

---

### 任务 2：服务器集成 — `server.py`

**文件：**
- 修改：`server.py`

- [ ] **步骤 1：添加交易 WebSocket 操作**

在 `/ws` 的消息处理中，大富翁操作区域（`unmortgage_property` 之后）添加：

```python
elif action == "propose_trade":
    conn = connections.get(ws_id)
    if not conn:
        continue
    room = rooms.get(conn["room"])
    if not room:
        continue
    target = msg.get("target", "")
    offer = msg.get("offer", {"cash": 0, "properties": []})
    request = msg.get("request", {"cash": 0, "properties": []})
    result = room.propose_trade(conn["name"], target, offer, request)
    if result.get("ok"):
        await broadcast_room(conn["room"])
    else:
        await ws.send_json({"type": "error", "message": result.get("error", "交易失败")})

elif action == "accept_trade":
    conn = connections.get(ws_id)
    if not conn:
        continue
    room = rooms.get(conn["room"])
    if not room:
        continue
    result = room.accept_trade(conn["name"])
    if result.get("ok"):
        await broadcast_room(conn["room"])
    else:
        await ws.send_json({"type": "error", "message": result.get("error", "接受交易失败")})

elif action == "reject_trade":
    conn = connections.get(ws_id)
    if not conn:
        continue
    room = rooms.get(conn["room"])
    if not room:
        continue
    result = room.reject_trade(conn["name"])
    if result.get("ok"):
        await broadcast_room(conn["room"])

elif action == "cancel_trade":
    conn = connections.get(ws_id)
    if not conn:
        continue
    room = rooms.get(conn["room"])
    if not room:
        continue
    result = room.cancel_trade(conn["name"])
    if result.get("ok"):
        await broadcast_room(conn["room"])
```

- [ ] **步骤 2：验证服务器启动**

运行：`python -c "import server; print('OK')"`
预期：输出 `OK`

---

### 任务 3：前端交易 UI 和音效 — `static/monopoly.html`

**文件：**
- 修改：`static/monopoly.html`

- [ ] **步骤 1：添加音效系统**

在 `<script>` 开头（WS 连接之前）添加音效模块：

```javascript
// ---- 音效系统（Web Audio API 合成） ----
const SFX = (() => {
  let ctx = null;
  function getCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    return ctx;
  }
  function play(freq, duration, type = 'sine', vol = 0.15) {
    try {
      const c = getCtx(), o = c.createOscillator(), g = c.createGain();
      o.type = type; o.frequency.value = freq;
      g.gain.setValueAtTime(vol, c.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);
      o.connect(g); g.connect(c.destination);
      o.start(); o.stop(c.currentTime + duration);
    } catch(e) {}
  }
  return {
    dice() { play(800, 0.08, 'square', 0.1); setTimeout(() => play(1200, 0.08, 'square', 0.1), 80); setTimeout(() => play(600, 0.12, 'square', 0.08), 160); },
    buy() { play(523, 0.1); setTimeout(() => play(659, 0.1), 100); setTimeout(() => play(784, 0.15), 200); },
    rent() { play(400, 0.15, 'sawtooth', 0.08); setTimeout(() => play(300, 0.2, 'sawtooth', 0.06), 150); },
    money() { play(1047, 0.06, 'sine', 0.1); setTimeout(() => play(1319, 0.06, 'sine', 0.1), 60); },
    jail() { play(200, 0.3, 'sawtooth', 0.12); setTimeout(() => play(150, 0.4, 'sawtooth', 0.1), 200); },
    bankruptcy() { for (let i = 0; i < 5; i++) setTimeout(() => play(400 - i * 60, 0.2, 'sawtooth', 0.1), i * 150); },
    victory() { [523,659,784,1047].forEach((f,i) => setTimeout(() => play(f, 0.2, 'sine', 0.12), i * 150)); },
    auction() { play(660, 0.1, 'triangle', 0.1); setTimeout(() => play(880, 0.15, 'triangle', 0.1), 120); },
    card() { play(700, 0.08, 'sine', 0.1); setTimeout(() => play(900, 0.12, 'sine', 0.08), 80); },
    trade() { play(523, 0.08); setTimeout(() => play(784, 0.12), 100); },
    capture() { play(300, 0.15, 'square', 0.12); setTimeout(() => play(200, 0.2, 'square', 0.1), 150); },
  };
})();
```

- [ ] **步骤 2：在游戏状态变化时触发音效**

在 `handleMsg` 的 `game_state` case 中，根据前后状态差异播放音效。在 `const prevGs=gs;` 之后、`gs=m.data;` 之后添加音效判断：

```javascript
// 音效触发
if (prevGs && gs) {
  // 骰子变化
  if (gs.dice && gs.dice[0] > 0 && prevGs.dice && (prevGs.dice[0] !== gs.dice[0] || prevGs.dice[1] !== gs.dice[1])) {
    SFX.dice();
  }
  // 事件日志新增
  if (gs.events && prevGs.events && gs.events.length > prevGs.events.length) {
    const ev = gs.events[gs.events.length - 1];
    if (ev.type === 'buy') SFX.buy();
    else if (ev.type === 'money') SFX.rent();
    else if (ev.type === 'bankruptcy') SFX.bankruptcy();
    else if (ev.type === 'victory') SFX.victory();
    else if (ev.type === 'auction') SFX.auction();
    else if (ev.type === 'card') SFX.card();
    else if (ev.type === 'trade') SFX.trade();
    else if (ev.type === 'build') SFX.money();
    else if (ev.type === 'mortgage') SFX.money();
    else if (ev.type === 'action' && ev.text && ev.text.includes('监狱')) SFX.jail();
  }
  // 现金增加
  if (prevGs.players && gs.players) {
    gs.players.forEach(p => {
      const prev = prevGs.players.find(pp => pp.name === p.name);
      if (prev && p.cash > prev.cash + 100 && p.name === myName) SFX.money();
    });
  }
}
```

- [ ] **步骤 3：添加交易 UI — 交易面板**

在 `renderActions` 函数末尾（掷骰子按钮之后），添加交易按钮。在 `el.innerHTML=...` 那行之前，在 `extra` 变量后追加：

```javascript
// 交易按钮（非自己回合也可以发起）
if (s.phase === 'playing' && me && me.alive && !s.pending_action && !(s.auction && !s.auction.ended)) {
  const others = s.players.filter(p => p.alive && p.name !== myName && !(s.trade && s.trade.target === myName && !s.trade.ended));
  if (others.length > 0) {
    extra += '<div style="margin-top:10px"><button class="btn btn-sm btn-outline" onclick="showTradePanel()">发起交易 🤝</button></div>';
  }
}
```

- [ ] **步骤 4：添加交易弹窗 HTML**

在 `monopoly.html` 的 `</body>` 之前，添加交易弹窗：

```html
<!-- 交易弹窗 -->
<div id="tradeOverlay" style="display:none" class="overlay" onclick="if(event.target===this)closeTrade()"></div>
<div id="tradePanel" style="display:none" class="prop-popup" style="min-width:340px;max-width:420px">
</div>
```

- [ ] **步骤 5：添加交易 JS 逻辑**

在 JS 文件的 `// ---- Actions ----` 部分之前添加：

```javascript
// ---- 交易系统 ----
let tradeSelection = { target: '', offerProps: new Set(), reqProps: new Set() };

function showTradePanel() {
  if (!gs) return;
  const others = gs.players.filter(p => p.alive && p.name !== myName);
  if (!others.length) return;
  const me = gs.players.find(p => p.name === myName);
  const panel = document.getElementById('tradePanel');
  const overlay = document.getElementById('tradeOverlay');
  overlay.style.display = '';
  panel.style.display = '';

  let html = '<div class="prop-popup"><h3 style="color:var(--gold);margin-bottom:12px">发起交易</h3>';
  html += '<div style="margin-bottom:10px"><label style="font-size:.85em;color:var(--muted)">交易对象:</label><br>';
  html += '<select id="tradeTarget" style="width:100%;padding:8px;margin-top:4px;border-radius:6px;background:rgba(255,255,255,.08);color:#fff;border:1px solid var(--border)">';
  others.forEach(p => html += `<option value="${esc(p.name)}">${esc(p.name)} ($${p.cash})</option>`);
  html += '</select></div>';

  // 我方出价
  html += '<div style="margin-bottom:10px;padding:10px;background:rgba(46,204,113,.08);border-radius:8px"><strong style="font-size:.85em;color:var(--green)">你出价</strong>';
  html += '<div style="margin-top:6px"><input type="number" id="tradeOfferCash" value="0" min="0" step="10" style="width:100px;padding:4px;border-radius:4px;background:rgba(255,255,255,.06);color:#fff;border:1px solid var(--border);text-align:center"> $</div>';
  if (me && me.properties && me.properties.length > 0) {
    html += '<div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:6px">';
    me.properties.forEach(pr => {
      if (pr.houses === 0 && !pr.mortgaged) {
        html += `<label style="font-size:.75em;cursor:pointer"><input type="checkbox" class="trade-offer-prop" value="${pr.index}"> <span style="background:${pr.group_color};padding:1px 5px;border-radius:3px;color:#fff">${pr.name}</span></label> `;
      }
    });
    html += '</div>';
  }
  html += '</div>';

  // 对方出价
  html += '<div style="margin-bottom:10px;padding:10px;background:rgba(231,76,60,.08);border-radius:8px"><strong style="font-size:.85em;color:var(--red)">你要对方</strong>';
  html += '<div style="margin-top:6px"><input type="number" id="tradeReqCash" value="0" min="0" step="10" style="width:100px;padding:4px;border-radius:4px;background:rgba(255,255,255,.06);color:#fff;border:1px solid var(--border);text-align:center"> $</div>';
  html += '<div id="tradeReqProps" style="display:flex;flex-wrap:wrap;gap:3px;margin-top:6px"></div>';
  html += '</div>';

  html += '<div style="display:flex;gap:8px;justify-content:center"><button class="btn btn-green" onclick="sendTrade()">发起交易</button><button class="btn btn-outline" onclick="closeTrade()">取消</button></div></div>';
  panel.innerHTML = html;

  // 当选择交易对象时更新对方地产列表
  document.getElementById('tradeTarget').onchange = updateTradeTargetProps;
  updateTradeTargetProps();
}

function updateTradeTargetProps() {
  const targetName = document.getElementById('tradeTarget').value;
  const target = gs.players.find(p => p.name === targetName);
  const container = document.getElementById('tradeReqProps');
  if (!target || !target.properties || target.properties.length === 0) {
    container.innerHTML = '<span style="font-size:.75em;color:var(--muted)">对方无地产</span>';
    return;
  }
  container.innerHTML = target.properties.filter(pr => pr.houses === 0 && !pr.mortgaged).map(pr =>
    `<label style="font-size:.75em;cursor:pointer"><input type="checkbox" class="trade-req-prop" value="${pr.index}"> <span style="background:${pr.group_color};padding:1px 5px;border-radius:3px;color:#fff">${pr.name}</span></label> `
  ).join('');
}

function sendTrade() {
  const target = document.getElementById('tradeTarget').value;
  const offerCash = parseInt(document.getElementById('tradeOfferCash').value) || 0;
  const reqCash = parseInt(document.getElementById('tradeReqCash').value) || 0;
  const offerProps = [...document.querySelectorAll('.trade-offer-prop:checked')].map(el => parseInt(el.value));
  const reqProps = [...document.querySelectorAll('.trade-req-prop:checked')].map(el => parseInt(el.value));
  if (offerCash === 0 && offerProps.length === 0 && reqCash === 0 && reqProps.length === 0) {
    toast('请至少设置一项交易内容'); return;
  }
  send({ action: 'propose_trade', target, offer: { cash: offerCash, properties: offerProps }, request: { cash: reqCash, properties: reqProps } });
  closeTrade();
}

function closeTrade() {
  document.getElementById('tradeOverlay').style.display = 'none';
  document.getElementById('tradePanel').style.display = 'none';
}
```

- [ ] **步骤 6：渲染收到的交易请求**

在 `renderActions` 函数开头（拍卖判断之后），添加收到交易的处理：

```javascript
// 收到交易请求
if (s.trade && s.trade.target === myName && !s.trade.ended) {
  const t = s.trade;
  const offerParts = [];
  if (t.offer.cash > 0) offerParts.push(`$${t.offer.cash}`);
  (t.offer.properties || []).forEach(idx => offerParts.push(BS[idx].name));
  const reqParts = [];
  if (t.request.cash > 0) reqParts.push(`$${t.request.cash}`);
  (t.request.properties || []).forEach(idx => reqParts.push(BS[idx].name));

  el.innerHTML = `<div class="act" style="text-align:center">
    <h3 style="color:var(--gold)">🤝 交易请求</h3>
    <p style="font-size:.85em;margin:8px 0"><b>${esc(t.proposer)}</b> 提议:</p>
    <div style="display:flex;gap:12px;justify-content:center;margin:10px 0;font-size:.85em">
      <div style="padding:8px 12px;background:rgba(46,204,113,.1);border-radius:8px"><strong style="color:var(--green)">给你:</strong><br>${offerParts.join(', ') || '无'}</div>
      <div style="padding:8px 12px;background:rgba(231,76,60,.1);border-radius:8px"><strong style="color:var(--red)">换:</strong><br>${reqParts.join(', ') || '无'}</div>
    </div>
    <div class="act-btns" style="margin-top:10px">
      <button class="btn btn-green" onclick="send({action:'accept_trade'})">接受</button>
      <button class="btn btn-red" onclick="send({action:'reject_trade'})">拒绝</button>
    </div>
  </div>`;
  if (prompt) prompt.innerHTML = `${esc(t.proposer)}<br>想和你交易`;
  return;
}
// 发起者等待中
if (s.trade && s.trade.proposer === myName && !s.trade.ended) {
  el.innerHTML = `<div class="act"><p style="text-align:center;color:var(--muted)">等待 ${esc(s.trade.target)} 回应交易...</p>
    <div style="text-align:center;margin-top:8px"><button class="btn btn-sm btn-outline" onclick="send({action:'cancel_trade'})">取消交易</button></div></div>`;
  if (prompt) prompt.textContent = '等待对方回应...';
  return;
}
```

- [ ] **步骤 7：Commit**

```bash
git add games/monopoly.py server.py static/monopoly.html
git commit -m "feat: 大富翁添加交易系统和音效"
```

---

## NOT in scope

- 交易历史记录（属于平台增强）
- 自定义音效文件上传（使用 Web Audio 合成即可）
- 交易税/手续费（增加复杂度，暂不需要）
