"""游戏集合 WebSocket 服务器"""
import json
import uuid
import socket
import os
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from games import create_room, GAME_TYPES
from games.bull_bull import BullBullRoom, BET_MODES, evaluate_hand
from games.monopoly import MonopolyRoom
from games.ludo import LudoRoom

app = FastAPI()

rooms: dict[str, object] = {}              # room_id -> BaseGameRoom
connections: dict[str, dict] = {}          # ws_id -> {"ws": WebSocket, "room": str, "name": str}
player_rooms: dict[str, set] = {}          # room_id -> {ws_id, ...}

# ---- 安全：从环境变量读取管理员账号 ----
ADMIN_USERS = {
    os.environ.get("ADMIN_USER", "admin"): os.environ.get("ADMIN_PASS", "admin")
}
_login_attempts: dict[str, dict] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300

# 断线重连超时
RECONNECT_TIMEOUT = 60
_disconnect_timers: dict[str, dict] = {}


# ---- SQLite 持久化 ----
DB_PATH = Path(__file__).parent / "game_data.db"


def _init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS game_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id TEXT, game_type TEXT, round INTEGER, phase TEXT,
        winner TEXT, pot INTEGER,
        players TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT, room_id TEXT, target TEXT,
        detail TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS player_stats (
        name TEXT,
        room_id TEXT,
        game_type TEXT DEFAULT 'bull_bull',
        total_rounds INTEGER DEFAULT 0,
        total_wins INTEGER DEFAULT 0,
        total_chips_change INTEGER DEFAULT 0,
        last_seen TEXT DEFAULT (datetime('now','localtime')),
        PRIMARY KEY (name, room_id)
    )""")
    conn.commit()
    conn.close()


def _db_execute(query: str, params: tuple = ()):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")


def _db_fetch(query: str, params: tuple = (), fetchall: bool = True):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(query, params)
        result = c.fetchall() if fetchall else c.fetchone()
        conn.close()
        return result
    except Exception:
        return [] if fetchall else None


def log_admin_action(action: str, room_id: str = "", target: str = "", detail: dict = None):
    _db_execute(
        "INSERT INTO admin_logs (action, room_id, target, detail) VALUES (?, ?, ?, ?)",
        (action, room_id, target, json.dumps(detail or {}, ensure_ascii=False))
    )


def log_game_result(room, winner_name: str):
    game_type = getattr(room, 'game_type', 'unknown')
    players_data = json.dumps([{
        "name": p["name"], "chips": p.get("chips", 0),
        "result": p.get("result").display if p.get("result") else ""
    } for p in room.players], ensure_ascii=False)
    _db_execute(
        "INSERT INTO game_history (room_id, game_type, round, phase, winner, pot, players) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (room.room_id, game_type, room.round_number, room.phase, winner_name, getattr(room, 'pot', 0), players_data)
    )
    initial_chips = getattr(room, 'initial_chips', 0)
    for p in room.players:
        chips = p.get("chips", 0)
        _db_execute(
            """INSERT INTO player_stats (name, room_id, game_type, total_rounds, total_wins, total_chips_change, last_seen)
               VALUES (?, ?, ?, 1, 0, 0, datetime('now','localtime'))
               ON CONFLICT(name, room_id) DO UPDATE SET
               total_rounds = total_rounds + 1,
               total_chips_change = total_chips_change + (? - ?),
               last_seen = datetime('now','localtime')""",
            (p["name"], room.room_id, game_type, chips, initial_chips)
        )
        if p["name"] == winner_name:
            _db_execute(
                """UPDATE player_stats SET total_wins = total_wins + 1
                   WHERE name = ? AND room_id = ?""",
                (p["name"], room.room_id)
            )


_init_db()


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def broadcast_room(room_id: str):
    if room_id not in rooms or room_id not in player_rooms:
        return
    room = rooms[room_id]
    for ws_id in list(player_rooms[room_id]):
        if ws_id not in connections:
            continue
        conn = connections[ws_id]
        try:
            state = room.get_state(viewer=conn["name"])
            await conn["ws"].send_json({"type": "game_state", "data": state})
        except Exception:
            pass
    await broadcast_admin()


admin_connections: dict[str, dict] = {}


def get_rooms_overview() -> list[dict]:
    result = []
    for rid, room in rooms.items():
        game_type = getattr(room, 'game_type', 'unknown')
        game_info = GAME_TYPES.get(game_type, {})
        info = {
            "room_id": rid,
            "game_type": game_type,
            "game_name": game_info.get("name", game_type),
            "host": room.host_name,
            "phase": room.phase,
            "phase_name": {"waiting": "等待中", "betting": "下注中", "playing": "游戏中", "finished": "已结束"}.get(room.phase, room.phase),
            "round": room.round_number,
            "player_count": len(room.players),
            "players": [p["name"] for p in room.players],
            "pot": getattr(room, 'pot', 0),
        }
        # 牛牛特有信息
        if isinstance(room, BullBullRoom):
            info["bet_mode"] = BET_MODES.get(room.bet_mode, room.bet_mode)
            info["bet_mode_key"] = room.bet_mode
        result.append(info)
    return result


async def broadcast_admin():
    overview = get_rooms_overview()
    for aid, aconn in list(admin_connections.items()):
        try:
            await aconn["ws"].send_json({"type": "rooms_overview", "data": overview})
        except Exception:
            pass


# ---- 页面路由 ----

@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/bull-bull")
async def bull_bull_page():
    return FileResponse(Path(__file__).parent / "static" / "bull_bull.html")


@app.get("/monopoly")
async def monopoly_page():
    return FileResponse(Path(__file__).parent / "static" / "monopoly.html")


@app.get("/ludo")
async def ludo_page():
    return FileResponse(Path(__file__).parent / "static" / "ludo.html")


@app.get("/admin")
async def admin_page():
    return FileResponse(Path(__file__).parent / "static" / "admin.html")


@app.get("/api/rooms")
async def list_rooms():
    result = []
    for rid, room in rooms.items():
        if room.phase == "waiting":
            game_type = getattr(room, 'game_type', 'unknown')
            game_info = GAME_TYPES.get(game_type, {})
            max_players = game_info.get("max_players", 20)
            if len(room.players) < max_players:
                room_info = {
                    "room_id": rid,
                    "game_type": game_type,
                    "game_name": game_info.get("name", game_type),
                    "host": room.host_name,
                    "player_count": len(room.players),
                    "players": [p["name"] for p in room.players],
                    "max_players": max_players,
                }
                if isinstance(room, BullBullRoom):
                    room_info["bet_mode"] = BET_MODES.get(room.bet_mode, room.bet_mode)
                    room_info["bet_mode_key"] = room.bet_mode
                    room_info["initial_chips"] = room.initial_chips
                    room_info["base_bet"] = room.base_bet
                result.append(room_info)
    return {"rooms": result}


@app.get("/api/game-types")
async def game_types():
    return {"types": {k: {"name": v["name"], "min_players": v["min_players"], "max_players": v["max_players"]} for k, v in GAME_TYPES.items()}}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_id = str(uuid.uuid4())

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            action = msg.get("action")

            if action == "create_room":
                name = msg["name"].strip()
                if not name:
                    await ws.send_json({"type": "error", "message": "请输入昵称"})
                    continue
                game_type = msg.get("game_type", "bull_bull")
                if game_type not in GAME_TYPES:
                    await ws.send_json({"type": "error", "message": "未知游戏类型"})
                    continue
                room_id = _generate_room_id()
                settings = msg.get("settings", {})
                room = create_room(game_type, room_id, name, settings)
                if not room:
                    await ws.send_json({"type": "error", "message": "创建房间失败"})
                    continue
                game_max = GAME_TYPES[game_type]["max_players"]
                room.add_player(name, max_players=game_max)
                rooms[room_id] = room
                player_rooms[room_id] = {ws_id}
                connections[ws_id] = {"ws": ws, "room": room_id, "name": name}
                player = next((p for p in room.players if p["name"] == name), None)
                reconnect_token = player["reconnect_token"] if player else ""
                await ws.send_json({
                    "type": "room_created", "room_id": room_id, "name": name,
                    "game_type": game_type,
                    "reconnect_token": reconnect_token
                })
                await broadcast_room(room_id)

            elif action == "join_room":
                name = msg["name"].strip()
                room_id = msg["room_id"].strip().upper()
                if not name:
                    await ws.send_json({"type": "error", "message": "请输入昵称"})
                    continue
                if room_id not in rooms:
                    await ws.send_json({"type": "error", "message": "房间不存在"})
                    continue
                room = rooms[room_id]
                # 尝试断线重连
                reconnect_token_req = msg.get("reconnect_token", "")
                if reconnect_token_req and room.try_reconnect(name, reconnect_token_req):
                    if room_id not in player_rooms:
                        player_rooms[room_id] = set()
                    player_rooms[room_id].add(ws_id)
                    connections[ws_id] = {"ws": ws, "room": room_id, "name": name}
                    player = next((p for p in room.players if p["name"] == name), None)
                    new_token = player["reconnect_token"] if player else ""
                    await ws.send_json({
                        "type": "room_joined", "room_id": room_id, "name": name,
                        "game_type": getattr(room, 'game_type', 'unknown'),
                        "reconnected": True, "reconnect_token": new_token
                    })
                    await broadcast_room(room_id)
                    continue
                game_type = getattr(room, 'game_type', 'bull_bull')
                game_max = GAME_TYPES.get(game_type, {}).get("max_players", 20)
                if not room.add_player(name, max_players=game_max):
                    await ws.send_json({"type": "error", "message": f"昵称重复或房间已满(最多{game_max}人)"})
                    continue
                if room_id not in player_rooms:
                    player_rooms[room_id] = set()
                player_rooms[room_id].add(ws_id)
                connections[ws_id] = {"ws": ws, "room": room_id, "name": name}
                player = next((p for p in room.players if p["name"] == name), None)
                reconnect_token = player["reconnect_token"] if player else ""
                await ws.send_json({
                    "type": "room_joined", "room_id": room_id, "name": name,
                    "game_type": game_type,
                    "reconnect_token": reconnect_token
                })
                await broadcast_room(room_id)

            elif action == "reconnect":
                name = msg.get("name", "").strip()
                room_id = msg.get("room_id", "").strip().upper()
                token = msg.get("reconnect_token", "")
                if room_id in rooms:
                    room = rooms[room_id]
                    if room.try_reconnect(name, token):
                        if room_id not in player_rooms:
                            player_rooms[room_id] = set()
                        player_rooms[room_id].add(ws_id)
                        connections[ws_id] = {"ws": ws, "room": room_id, "name": name}
                        player = next((p for p in room.players if p["name"] == name), None)
                        new_token = player["reconnect_token"] if player else ""
                        await ws.send_json({
                            "type": "reconnected", "room_id": room_id, "name": name,
                            "game_type": getattr(room, 'game_type', 'unknown'),
                            "reconnect_token": new_token
                        })
                        await broadcast_room(room_id)
                        continue
                await ws.send_json({"type": "error", "message": "重连失败，房间可能已关闭"})

            elif action == "start_game":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room or conn["name"] != room.host_name:
                    await ws.send_json({"type": "error", "message": "只有房主能开始游戏"})
                    continue
                if not room.can_start():
                    await ws.send_json({"type": "error", "message": "至少需要2名玩家才能开始"})
                    continue
                room.start_round()
                await broadcast_room(conn["room"])

            elif action == "get_state":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if room:
                    state = room.get_state(viewer=conn["name"])
                    await ws.send_json({"type": "game_state", "data": state})

            elif action == "chat":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                message = msg.get("message", "").strip()
                if not message:
                    continue
                room.add_chat(conn["name"], message)
                await broadcast_room(conn["room"])

            elif action == "next_round":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room or conn["name"] != room.host_name:
                    await ws.send_json({"type": "error", "message": "只有房主能开始下一轮"})
                    continue
                room.start_round()
                await broadcast_room(conn["room"])

            # ---- 牛牛特有操作 ----

            elif action == "confirm_cards":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room or not isinstance(room, BullBullRoom):
                    continue
                all_confirmed = room.confirm_cards(conn["name"])
                if all_confirmed:
                    winner_name = next((p["name"] for p in room.players if p.get("result") and p["result"].type_score == max(
                        pp["result"].type_score for pp in room.players if pp.get("result")
                    )), "")
                    log_game_result(room, winner_name)
                await broadcast_room(conn["room"])

            elif action == "place_bet":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room or not isinstance(room, BullBullRoom):
                    continue
                bet_action = msg.get("bet_action", "call")
                amount = msg.get("amount", 0)
                result = room.place_bet(conn["name"], bet_action, amount)
                if result.get("ok"):
                    if room.check_betting_done():
                        room.finish_betting()
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": "下注失败"})

            elif action == "set_luck":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room or not isinstance(room, BullBullRoom):
                    continue
                target = msg.get("target", "")
                luck = msg.get("luck", 0)
                room.set_player_luck(conn["name"], target, luck)
                await broadcast_room(conn["room"])

            # ---- 大富翁特有操作 ----

            elif action == "roll_dice":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                if isinstance(room, (MonopolyRoom, LudoRoom)):
                    result = room.roll_dice(conn["name"])
                else:
                    result = {"ok": False, "error": "当前游戏不支持掷骰子"}
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "掷骰子失败")})

            elif action == "buy_property":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                result = room.buy_property(conn["name"])
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "购买失败")})

            elif action == "skip_buy":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                result = room.skip_buy(conn["name"])
                if result.get("ok"):
                    await broadcast_room(conn["room"])

            elif action == "buy_house":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                pos = msg.get("position", -1)
                result = room.buy_house(conn["name"], pos)
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "建房失败")})

            elif action == "sell_house":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                pos = msg.get("position", -1)
                result = room.sell_house(conn["name"], pos)
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "卖房失败")})

            elif action == "pay_jail_fine":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                result = room.pay_jail_fine(conn["name"])
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "付款失败")})

            elif action == "use_jail_card":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                result = room.use_jail_card(conn["name"])
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "使用出狱卡失败")})

            elif action == "bid_auction":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                amount = msg.get("amount", 0)
                result = room.bid_auction(conn["name"], amount)
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "出价失败")})

            elif action == "pass_auction":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                result = room.pass_auction(conn["name"])
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "操作失败")})

            elif action == "mortgage_property":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                pos = msg.get("position", -1)
                result = room.mortgage_property(conn["name"], pos)
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "抵押失败")})

            elif action == "unmortgage_property":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                pos = msg.get("position", -1)
                result = room.unmortgage_property(conn["name"], pos)
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "赎回失败")})

            # ---- 大富翁交易操作 ----

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

            # ---- 飞行棋特有操作 ----

            elif action == "move_piece":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                if not isinstance(room, LudoRoom):
                    await ws.send_json({"type": "error", "message": "当前游戏不支持移动棋子"})
                    continue
                piece_index = msg.get("piece_index", 0)
                result = room.move_piece(conn["name"], piece_index)
                if result.get("ok"):
                    await broadcast_room(conn["room"])
                else:
                    await ws.send_json({"type": "error", "message": result.get("error", "移动失败")})

    except WebSocketDisconnect:
        pass
    finally:
        if ws_id in connections:
            conn = connections[ws_id]
            room_id = conn["room"]
            name = conn["name"]
            if room_id in rooms:
                room = rooms[room_id]
                room.remove_player(name)
                if room_id in player_rooms:
                    player_rooms[room_id].discard(ws_id)
                if not room.players:
                    del rooms[room_id]
                    player_rooms.pop(room_id, None)
                else:
                    await broadcast_room(room_id)
            del connections[ws_id]


def _generate_room_id() -> str:
    import random, string
    while True:
        rid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if rid not in rooms:
            return rid


# ---- 登录安全检查 ----
def _check_login_blocked(ip: str) -> bool:
    info = _login_attempts.get(ip)
    if not info:
        return False
    if time.time() < info.get("lock_until", 0):
        return True
    if time.time() - info.get("first_attempt", 0) > LOCKOUT_SECONDS:
        del _login_attempts[ip]
        return False
    return False


def _record_login_attempt(ip: str, success: bool):
    if success:
        _login_attempts.pop(ip, None)
        return
    info = _login_attempts.get(ip, {"count": 0, "first_attempt": time.time()})
    info["count"] += 1
    if info["count"] >= MAX_LOGIN_ATTEMPTS:
        info["lock_until"] = time.time() + LOCKOUT_SECONDS
    _login_attempts[ip] = info


@app.websocket("/ws_admin")
async def admin_websocket(ws: WebSocket):
    await ws.accept()
    admin_ws_id = str(uuid.uuid4())
    logged_in = False
    client_ip = ws.client.host if ws.client else "unknown"

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            action = msg.get("action")

            if action == "login":
                if _check_login_blocked(client_ip):
                    await ws.send_json({"type": "error", "message": f"登录失败次数过多，请等待{LOCKOUT_SECONDS // 60}分钟后再试"})
                    continue
                username = msg.get("username", "").strip()
                password = msg.get("password", "").strip()
                if username in ADMIN_USERS and ADMIN_USERS[username] == password:
                    _record_login_attempt(client_ip, True)
                    logged_in = True
                    admin_connections[admin_ws_id] = {"ws": ws}
                    await ws.send_json({"type": "login_ok"})
                    await ws.send_json({"type": "rooms_overview", "data": get_rooms_overview()})
                else:
                    _record_login_attempt(client_ip, False)
                    remaining = MAX_LOGIN_ATTEMPTS - _login_attempts.get(client_ip, {}).get("count", 0)
                    await ws.send_json({"type": "error", "message": f"账号或密码错误（剩余{remaining}次尝试）"})

            if not logged_in:
                continue

            if action == "get_rooms":
                await ws.send_json({"type": "rooms_overview", "data": get_rooms_overview()})

            elif action == "get_room":
                rid = msg.get("room_id", "").strip().upper()
                if rid in rooms:
                    state = rooms[rid].admin_get_full_state()
                    await ws.send_json({"type": "room_detail", "data": state})
                else:
                    await ws.send_json({"type": "error", "message": "房间不存在"})

            elif action == "get_logs":
                limit = min(msg.get("limit", 50), 200)
                logs = _db_fetch(
                    "SELECT * FROM admin_logs ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
                log_list = [dict(r) for r in (logs or [])]
                await ws.send_json({"type": "admin_logs", "data": log_list})

            elif action == "get_stats":
                stats = _db_fetch("SELECT * FROM player_stats ORDER BY total_rounds DESC LIMIT 50")
                stat_list = [dict(r) for r in (stats or [])]
                history = _db_fetch("SELECT * FROM game_history ORDER BY id DESC LIMIT 30")
                hist_list = [dict(r) for r in (history or [])]
                await ws.send_json({"type": "game_stats", "data": {"players": stat_list, "history": hist_list}})

            elif action == "admin_set_chips":
                rid = msg.get("room_id", "").strip().upper()
                if rid not in rooms:
                    continue
                room = rooms[rid]
                target = msg.get("target", "")
                chips = msg.get("chips", 0)
                room.admin_set_chips(target, chips)
                log_admin_action("set_chips", rid, target, {"chips": chips})
                await broadcast_room(rid)

            elif action == "admin_kick":
                rid = msg.get("room_id", "").strip().upper()
                if rid not in rooms:
                    continue
                room = rooms[rid]
                target = msg.get("target", "")
                room.admin_kick(target)
                log_admin_action("kick", rid, target)
                await broadcast_room(rid)

            elif action == "admin_set_luck":
                rid = msg.get("room_id", "").strip().upper()
                if rid not in rooms:
                    continue
                room = rooms[rid]
                if not isinstance(room, BullBullRoom):
                    continue
                target = msg.get("target", "")
                luck = msg.get("luck", 0)
                room.set_player_luck(room.host_name, target, luck)
                log_admin_action("set_luck", rid, target, {"luck": luck})
                await broadcast_room(rid)

            elif action == "admin_set_card":
                rid = msg.get("room_id", "").strip().upper()
                if rid not in rooms:
                    continue
                room = rooms[rid]
                if not isinstance(room, BullBullRoom):
                    continue
                target = msg.get("target", "")
                idx = msg.get("card_index", 0)
                suit = msg.get("suit", "spades")
                rank = msg.get("rank", "A")
                room.admin_set_card(target, idx, suit, rank)
                log_admin_action("set_card", rid, target, {"index": idx, "suit": suit, "rank": rank})
                await broadcast_room(rid)

            elif action == "admin_next_round":
                rid = msg.get("room_id", "").strip().upper()
                if rid not in rooms:
                    continue
                room = rooms[rid]
                if room.can_start():
                    room.start_round()
                    log_admin_action("next_round", rid)
                    await broadcast_room(rid)

            elif action == "admin_force_finish":
                rid = msg.get("room_id", "").strip().upper()
                if rid not in rooms:
                    continue
                room = rooms[rid]
                if isinstance(room, BullBullRoom) and room.phase == "playing":
                    for p in room.players:
                        if not p.get("confirmed") and not p.get("folded"):
                            p["confirmed"] = True
                            p["result"] = evaluate_hand(p["hand"])
                    room._settle_round()
                    log_admin_action("force_finish", rid)
                    await broadcast_room(rid)

            elif action == "admin_delete_room":
                rid = msg.get("room_id", "").strip().upper()
                if rid in rooms:
                    log_admin_action("delete_room", rid)
                    del rooms[rid]
                    player_rooms.pop(rid, None)
                    await ws.send_json({"type": "rooms_overview", "data": get_rooms_overview()})

            elif action == "admin_clear_all":
                room_ids = list(rooms.keys())
                for rid in room_ids:
                    log_admin_action("delete_room", rid)
                rooms.clear()
                player_rooms.clear()
                await ws.send_json({"type": "rooms_overview", "data": get_rooms_overview()})

    except WebSocketDisconnect:
        pass
    finally:
        admin_connections.pop(admin_ws_id, None)


# 挂载静态文件
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


if __name__ == "__main__":
    import uvicorn
    host = _get_local_ip()
    port = 8000
    print(f"\n{'='*40}")
    print(f"  游戏集合服务器已启动!")
    print(f"  本机访问: http://localhost:{port}")
    print(f"  局域网访问: http://{host}:{port}")
    print(f"  把上面的地址发给朋友!")
    print(f"{'='*40}\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
