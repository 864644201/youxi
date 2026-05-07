"""游戏房间基类"""
import secrets
from datetime import datetime


class BaseGameRoom:
    """所有游戏类型的公共基类"""

    game_type: str = "base"  # 子类覆盖
    game_name: str = "未知游戏"

    def __init__(self, room_id: str, host_name: str, settings: dict = None):
        self.room_id = room_id
        self.host_name = host_name
        self.admin_token = secrets.token_hex(8)
        self.players: list[dict] = []
        self.phase = "waiting"  # waiting -> playing -> finished
        self.round_number = 0
        self.chat: list[dict] = []
        self._disconnected: dict[str, dict] = {}

    def add_player(self, name: str, max_players: int = 20) -> bool:
        if any(p["name"] == name for p in self.players):
            return False
        if len(self.players) >= max_players:
            return False
        reconnect_token = secrets.token_hex(6)
        self.players.append({
            "name": name,
            "reconnect_token": reconnect_token,
        })
        return True

    def remove_player(self, name: str) -> dict | None:
        if self.phase == "playing":
            for p in self.players:
                if p["name"] == name:
                    self._disconnected[name] = {
                        "token": p["reconnect_token"],
                        "data": {k: v for k, v in p.items()},
                    }
                    return self._disconnected[name]
        self.players = [p for p in self.players if p["name"] != name]
        return None

    def try_reconnect(self, name: str, token: str) -> bool:
        info = self._disconnected.get(name)
        if not info or info["token"] != token:
            return False
        player_data = info["data"]
        player_data["reconnect_token"] = secrets.token_hex(6)
        existing = [p for p in self.players if p["name"] == name]
        if existing:
            existing[0].update(player_data)
        else:
            self.players.append(player_data)
        del self._disconnected[name]
        return True

    def can_start(self) -> bool:
        return self.phase in ("waiting", "finished") and len(self.players) >= 2

    def add_chat(self, name: str, message: str):
        self.chat.append({
            "name": name,
            "message": message[:200],
            "time": datetime.now().strftime("%H:%M"),
        })
        if len(self.chat) > 50:
            self.chat = self.chat[-50:]

    # 子类必须实现的方法
    def start_round(self) -> bool:
        raise NotImplementedError

    def get_state(self, viewer: str = None) -> dict:
        raise NotImplementedError

    def admin_get_full_state(self) -> dict:
        raise NotImplementedError

    def admin_set_chips(self, target_name: str, chips: int) -> bool:
        raise NotImplementedError

    def admin_kick(self, target_name: str) -> bool:
        if target_name == self.host_name:
            return False
        self.remove_player(target_name)
        return True
