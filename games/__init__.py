"""游戏模块"""
from .bull_bull import BullBullRoom
from .monopoly import MonopolyRoom
from .ludo import LudoRoom

GAME_TYPES = {
    "bull_bull": {"name": "牛牛", "class": BullBullRoom, "min_players": 2, "max_players": 20},
    "monopoly": {"name": "大富翁", "class": MonopolyRoom, "min_players": 2, "max_players": 8},
    "ludo": {"name": "飞行棋", "class": LudoRoom, "min_players": 2, "max_players": 4},
}


def create_room(game_type: str, room_id: str, host_name: str, settings: dict = None):
    """根据游戏类型创建房间"""
    info = GAME_TYPES.get(game_type)
    if not info:
        return None
    return info["class"](room_id, host_name, settings)
