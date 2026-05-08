"""飞行棋游戏逻辑"""
import random
import time
from .base import BaseGameRoom

COLORS = ["blue", "yellow", "green", "red"]
COLOR_NAMES = {"blue": "蓝", "yellow": "黄", "green": "绿", "red": "红"}
COLOR_HEX = {"blue": "#3498db", "yellow": "#f0c040", "green": "#2ecc71", "red": "#e74c3c"}

START_POS = {"blue": 0, "yellow": 13, "green": 26, "red": 39}
SAFE_POSITIONS = {0, 8, 13, 21, 26, 34, 39, 47}
HOME_ENTRY = {"blue": 50, "yellow": 11, "green": 24, "red": 37}
HOME_START = {"blue": 52, "yellow": 59, "green": 66, "red": 73}
HOME_LEN = 6
FINISHED = -2
YARD = -1
OUTER_LEN = 52


def next_pos(color: str, current: int, steps: int) -> int | None:
    """计算棋子下一步位置。返回 None 表示超出（不能移动）"""
    start = START_POS[color]
    entry = HOME_ENTRY[color]
    home_s = HOME_START[color]

    if current == YARD:
        if steps == 6:
            return start
        return None

    if current >= home_s:
        offset = current - home_s
        new_offset = offset + steps
        if new_offset < HOME_LEN:
            return home_s + new_offset
        elif new_offset == HOME_LEN:
            return FINISHED
        else:
            return None

    dist_from_start = (current - start) % OUTER_LEN
    new_dist = dist_from_start + steps
    entry_dist = (entry - start) % OUTER_LEN

    if new_dist <= entry_dist:
        return (current + steps) % OUTER_LEN
    else:
        home_offset = new_dist - entry_dist - 1
        if home_offset < HOME_LEN:
            return home_s + home_offset
        elif home_offset == HOME_LEN:
            return FINISHED
        else:
            return None


class LudoRoom(BaseGameRoom):
    game_type = "ludo"
    game_name = "飞行棋"

    def __init__(self, room_id: str, host_name: str, settings: dict = None):
        super().__init__(room_id, host_name, settings)
        self.phase = "waiting"
        self.pieces: dict[str, list[int]] = {}
        self.player_colors: dict[str, str] = {}
        self.current_player_index = 0
        self.dice_value = 0
        self.doubles_streak = 0
        self.must_move = False
        self.events: list[dict] = []
        self.max_players_setting = 4

    def _add_event(self, text: str, icon: str = "", event_type: str = "info"):
        t = time.strftime("%H:%M:%S")
        self.events.append({"text": text, "icon": icon, "type": event_type, "time": t})
        if len(self.events) > 100:
            self.events = self.events[-100:]

    def start_round(self) -> bool:
        if not self.can_start():
            return False
        if self.phase == "finished":
            self.pieces = {}
            self.player_colors = {}
            self.events = []
            self.current_player_index = 0
            self.doubles_streak = 0
            self.must_move = False
            self.players = [p for p in self.players if p.get("alive", True)]
        self.round_number += 1
        self.phase = "playing"
        self.events = []

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
                self.dice_value = 0
            result["no_movable"] = True
            return result

        if len(movable) == 1:
            move_result = self.move_piece(name, movable[0])
            move_result.setdefault("dice", dice)
            return move_result

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
            capture = self._check_capture(color, new_pos)
            if capture:
                result["captured"] = capture
            self._add_event(
                f"{name} 移动飞机到位置 {new_pos}" +
                (f"，撞了 {capture['captured_player']} 的飞机！" if capture else ""),
                "✈️", "action"
            )

        if all(p == FINISHED for p in self.pieces[color]):
            self._add_event(f"🏆 {name} 所有飞机到达终点，获胜！", "🏆", "victory")
            self.phase = "finished"
            result["game_over"] = True
            result["winner"] = name
            return result

        self.must_move = False

        if dice == 6:
            self.dice_value = 0
            result["roll_again"] = True
        else:
            self._next_turn()

        return result

    def _check_capture(self, mover_color: str, pos: int) -> dict | None:
        if pos in SAFE_POSITIONS or pos >= HOME_START.get(mover_color, 999):
            return None
        if pos < 0:
            return None

        captures = []
        for color, pieces in self.pieces.items():
            if color == mover_color:
                continue
            for i, p in enumerate(pieces):
                if p == pos:
                    pieces[i] = YARD
                    pname = next((pl["name"] for pl in self.players
                                 if self.player_colors.get(pl["name"]) == color), COLOR_NAMES[color])
                    self._add_event(f"💥 {COLOR_NAMES[mover_color]}方撞了{COLOR_NAMES[color]}方的飞机！", "💥", "action")
                    captures.append({"captured_player": pname, "captured_color": color, "captured_piece": i})
        if captures:
            captures[0]["all_captures"] = captures
            return captures[0]
        return None

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
            pieces = self.pieces.get(color, [YARD] * 4)
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
        return False
