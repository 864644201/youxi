"""牛牛游戏 WebSocket 服务器"""
import json
import uuid
import socket
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from game import GameRoom

app = FastAPI()

rooms: dict[str, GameRoom] = {}           # room_id -> GameRoom
connections: dict[str, dict] = {}         # ws_id -> {"ws": WebSocket, "room": str, "name": str}
player_rooms: dict[str, set] = {}         # room_id -> {ws_id, ...}


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
    """向房间内所有玩家广播游戏状态"""
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


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


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
                room_id = _generate_room_id()
                room = GameRoom(room_id, name)
                room.add_player(name)
                rooms[room_id] = room
                player_rooms[room_id] = {ws_id}
                connections[ws_id] = {"ws": ws, "room": room_id, "name": name}
                await ws.send_json({"type": "room_created", "room_id": room_id, "name": name})
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
                if not room.add_player(name):
                    await ws.send_json({"type": "error", "message": "昵称重复或房间已满(最多20人)"})
                    continue
                if room_id not in player_rooms:
                    player_rooms[room_id] = set()
                player_rooms[room_id].add(ws_id)
                connections[ws_id] = {"ws": ws, "room": room_id, "name": name}
                await ws.send_json({"type": "room_joined", "room_id": room_id, "name": name})
                await broadcast_room(room_id)

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

            elif action == "confirm_cards":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if not room:
                    continue
                all_confirmed = room.confirm_cards(conn["name"])
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

            elif action == "get_state":
                conn = connections.get(ws_id)
                if not conn:
                    continue
                room = rooms.get(conn["room"])
                if room:
                    state = room.get_state(viewer=conn["name"])
                    await ws.send_json({"type": "game_state", "data": state})

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
        rid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if rid not in rooms:
            return rid


# 挂载静态文件（在路由之后）
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


if __name__ == "__main__":
    import uvicorn
    host = _get_local_ip()
    port = 8000
    print(f"\n{'='*40}")
    print(f"  牛牛游戏服务器已启动!")
    print(f"  本机访问: http://localhost:{port}")
    print(f"  局域网访问: http://{host}:{port}")
    print(f"  把上面的地址发给朋友!")
    print(f"{'='*40}\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
