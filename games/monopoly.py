"""大富翁游戏逻辑 - 商业版 Monopoly 完整实现"""
import random
import secrets
import time
from .base import BaseGameRoom


COLOR_GROUPS = {
    "brown": {"name": "棕色", "color": "#8B4513"},
    "lightblue": {"name": "浅蓝", "color": "#87CEEB"},
    "pink": {"name": "粉色", "color": "#FF69B4"},
    "orange": {"name": "橙色", "color": "#FFA500"},
    "red": {"name": "红色", "color": "#FF0000"},
    "yellow": {"name": "黄色", "color": "#FFD700"},
    "green": {"name": "绿色", "color": "#228B22"},
    "darkblue": {"name": "深蓝", "color": "#00008B"},
}

BOARD_SPACES = [
    {"index": 0, "type": "go", "name": "起点", "emoji": "▶"},
    {"index": 1, "type": "property", "name": "地中海大道", "group": "brown", "price": 60, "rent": [2, 10, 30, 90, 160, 250], "house_cost": 50, "mortgage": 30},
    {"index": 2, "type": "community_chest", "name": "公益金", "emoji": "📦"},
    {"index": 3, "type": "property", "name": "巴尔的摩大道", "group": "brown", "price": 60, "rent": [4, 20, 60, 180, 320, 450], "house_cost": 50, "mortgage": 30},
    {"index": 4, "type": "tax", "name": "所得税", "amount": 200, "emoji": "💰"},
    {"index": 5, "type": "railroad", "name": "阅读铁路", "price": 200, "emoji": "🚂", "mortgage": 100},
    {"index": 6, "type": "property", "name": "东方大道", "group": "lightblue", "price": 100, "rent": [6, 30, 90, 270, 400, 550], "house_cost": 50, "mortgage": 50},
    {"index": 7, "type": "chance", "name": "机会", "emoji": "❓"},
    {"index": 8, "type": "property", "name": "佛蒙特大道", "group": "lightblue", "price": 100, "rent": [6, 30, 90, 270, 400, 550], "house_cost": 50, "mortgage": 50},
    {"index": 9, "type": "property", "name": "康涅狄格大道", "group": "lightblue", "price": 120, "rent": [8, 40, 100, 300, 450, 600], "house_cost": 50, "mortgage": 60},
    {"index": 10, "type": "jail", "name": "监狱", "emoji": "🔒"},
    {"index": 11, "type": "property", "name": "圣查尔斯广场", "group": "pink", "price": 140, "rent": [10, 50, 150, 450, 625, 750], "house_cost": 100, "mortgage": 70},
    {"index": 12, "type": "utility", "name": "电力公司", "price": 150, "emoji": "💡", "mortgage": 75},
    {"index": 13, "type": "property", "name": "弗吉尼亚大道", "group": "pink", "price": 140, "rent": [10, 50, 150, 450, 625, 750], "house_cost": 100, "mortgage": 70},
    {"index": 14, "type": "property", "name": "州际大道", "group": "pink", "price": 160, "rent": [12, 60, 180, 500, 700, 900], "house_cost": 100, "mortgage": 80},
    {"index": 15, "type": "railroad", "name": "宾夕法尼亚铁路", "price": 200, "emoji": "🚂", "mortgage": 100},
    {"index": 16, "type": "property", "name": "圣詹姆斯广场", "group": "orange", "price": 180, "rent": [14, 70, 200, 550, 750, 950], "house_cost": 100, "mortgage": 90},
    {"index": 17, "type": "community_chest", "name": "公益金", "emoji": "📦"},
    {"index": 18, "type": "property", "name": "田纳西大道", "group": "orange", "price": 180, "rent": [14, 70, 200, 550, 750, 950], "house_cost": 100, "mortgage": 90},
    {"index": 19, "type": "property", "name": "纽约大道", "group": "orange", "price": 200, "rent": [16, 80, 220, 600, 800, 1000], "house_cost": 100, "mortgage": 100},
    {"index": 20, "type": "free_parking", "name": "免费停车", "emoji": "🅿️"},
    {"index": 21, "type": "property", "name": "肯塔基大道", "group": "red", "price": 220, "rent": [18, 90, 250, 700, 875, 1050], "house_cost": 150, "mortgage": 110},
    {"index": 22, "type": "chance", "name": "机会", "emoji": "❓"},
    {"index": 23, "type": "property", "name": "印第安纳大道", "group": "red", "price": 220, "rent": [18, 90, 250, 700, 875, 1050], "house_cost": 150, "mortgage": 110},
    {"index": 24, "type": "property", "name": "伊利诺伊大道", "group": "red", "price": 240, "rent": [20, 100, 300, 750, 925, 1100], "house_cost": 150, "mortgage": 120},
    {"index": 25, "type": "railroad", "name": "B&O铁路", "price": 200, "emoji": "🚂", "mortgage": 100},
    {"index": 26, "type": "property", "name": "大西洋大道", "group": "yellow", "price": 260, "rent": [22, 110, 330, 800, 975, 1150], "house_cost": 150, "mortgage": 130},
    {"index": 27, "type": "property", "name": "文特诺大道", "group": "yellow", "price": 260, "rent": [22, 110, 330, 800, 975, 1150], "house_cost": 150, "mortgage": 130},
    {"index": 28, "type": "utility", "name": "自来水公司", "price": 150, "emoji": "🚰", "mortgage": 75},
    {"index": 29, "type": "property", "name": "马文花园", "group": "yellow", "price": 280, "rent": [24, 120, 360, 850, 1025, 1200], "house_cost": 150, "mortgage": 140},
    {"index": 30, "type": "go_to_jail", "name": "进监狱", "emoji": "🚔"},
    {"index": 31, "type": "property", "name": "太平洋大道", "group": "green", "price": 300, "rent": [26, 130, 390, 900, 1100, 1275], "house_cost": 200, "mortgage": 150},
    {"index": 32, "type": "property", "name": "北卡罗来纳大道", "group": "green", "price": 300, "rent": [26, 130, 390, 900, 1100, 1275], "house_cost": 200, "mortgage": 150},
    {"index": 33, "type": "community_chest", "name": "公益金", "emoji": "📦"},
    {"index": 34, "type": "property", "name": "宾夕法尼亚大道", "group": "green", "price": 320, "rent": [28, 150, 450, 1000, 1200, 1400], "house_cost": 200, "mortgage": 160},
    {"index": 35, "type": "railroad", "name": "短途铁路", "price": 200, "emoji": "🚂", "mortgage": 100},
    {"index": 36, "type": "chance", "name": "机会", "emoji": "❓"},
    {"index": 37, "type": "property", "name": "公园广场", "group": "darkblue", "price": 350, "rent": [35, 175, 500, 1100, 1300, 1500], "house_cost": 200, "mortgage": 175},
    {"index": 38, "type": "tax", "name": "奢侈税", "amount": 100, "emoji": "💎"},
    {"index": 39, "type": "property", "name": "海滨大道", "group": "darkblue", "price": 400, "rent": [50, 200, 600, 1400, 1700, 2000], "house_cost": 200, "mortgage": 200},
]

CHANCE_CARDS = [
    {"text": "前进到起点，收取 $200", "action": "move_to", "target": 0, "icon": "🎯"},
    {"text": "前进到伊利诺伊大道", "action": "move_to", "target": 24, "icon": "🚶"},
    {"text": "前进到圣查尔斯广场", "action": "move_to", "target": 11, "icon": "🚶"},
    {"text": "前进到最近的铁路，支付双倍租金", "action": "nearest_railroad", "icon": "🚂"},
    {"text": "银行付给你 $50 股息", "action": "receive", "amount": 50, "icon": "💵"},
    {"text": "你被选为董事会主席，每位玩家付你 $50", "action": "collect_from_all", "amount": 50, "icon": "👔"},
    {"text": "房屋维修：每栋房屋 $25，每栋酒店 $100", "action": "repair", "per_house": 25, "per_hotel": 100, "icon": "🔧"},
    {"text": "后退3格", "action": "move_back", "steps": 3, "icon": "⬅️"},
    {"text": "去监狱！直接去监狱，不经过起点", "action": "go_to_jail", "icon": "🚔"},
    {"text": "你中了彩票！获得 $150", "action": "receive", "amount": 150, "icon": "🎰"},
    {"text": "前进到海滨大道", "action": "move_to", "target": 39, "icon": "🚶"},
    {"text": "每位玩家过生日，每人付你 $10", "action": "collect_from_all", "amount": 10, "icon": "🎂"},
    {"text": "道路维修：每栋房屋 $40，每栋酒店 $115", "action": "repair", "per_house": 40, "per_hotel": 115, "icon": "🔧"},
    {"text": "银行错误！获得 $200", "action": "receive", "amount": 200, "icon": "🏦"},
    {"text": "付 $15 罚款", "action": "pay", "amount": 15, "icon": "💸"},
]

COMMUNITY_CARDS = [
    {"text": "前进到起点，收取 $200", "action": "move_to", "target": 0, "icon": "🎯"},
    {"text": "银行错误！获得 $200", "action": "receive", "amount": 200, "icon": "🏦"},
    {"text": "医疗费用，支付 $50", "action": "pay", "amount": 50, "icon": "🏥"},
    {"text": "出售股票，获得 $50", "action": "receive", "amount": 50, "icon": "📈"},
    {"text": "去监狱！直接去监狱，不经过起点", "action": "go_to_jail", "icon": "🚔"},
    {"text": "假期基金到期，获得 $100", "action": "receive", "amount": 100, "icon": "🏖"},
    {"text": "所得税退款，获得 $20", "action": "receive", "amount": 20, "icon": "💰"},
    {"text": "生日快乐！获得 $100", "action": "receive", "amount": 100, "icon": "🎂"},
    {"text": "人寿保险到期，获得 $100", "action": "receive", "amount": 100, "icon": "📋"},
    {"text": "支付医院费用 $100", "action": "pay", "amount": 100, "icon": "🏥"},
    {"text": "支付学校费用 $50", "action": "pay", "amount": 50, "icon": "🏫"},
    {"text": "咨询费，获得 $25", "action": "receive", "amount": 25, "icon": "💼"},
    {"text": "你继承了 $100", "action": "receive", "amount": 100, "icon": "📜"},
    {"text": "房屋维修：每栋房屋 $40，每栋酒店 $115", "action": "repair", "per_house": 40, "per_hotel": 115, "icon": "🔧"},
    {"text": "你赢得比赛二等奖，获得 $10", "action": "receive", "amount": 10, "icon": "🏆"},
]


class MonopolyRoom(BaseGameRoom):
    game_type = "monopoly"
    game_name = "大富翁"

    def __init__(self, room_id: str, host_name: str, settings: dict = None):
        super().__init__(room_id, host_name, settings)
        self.phase = "waiting"
        s = settings or {}
        self.initial_cash = s.get("initial_cash", 1500)
        self.go_salary = s.get("go_salary", 200)
        self.properties: dict[int, str | None] = {}
        self.houses: dict[int, int] = {}
        self.mortgaged: dict[int, bool] = {}
        self.player_positions: dict[str, int] = {}
        self.player_cash: dict[str, int] = {}
        self.player_in_jail: dict[str, bool] = {}
        self.player_jail_turns: dict[str, int] = {}
        self.player_get_out_cards: dict[str, int] = {}
        self.current_player_index = 0
        self.dice1 = 0
        self.dice2 = 0
        self.doubles_count = 0
        self.pending_action: dict | None = None
        self._chance_deck = list(range(len(CHANCE_CARDS)))
        self._community_deck = list(range(len(COMMUNITY_CARDS)))
        random.shuffle(self._chance_deck)
        random.shuffle(self._community_deck)
        # 拍卖
        self.auction: dict | None = None
        # 事件日志 [{text, icon, time, type}]
        self.events: list[dict] = []
        # 回合阶段: roll -> post_roll -> build -> end
        self.turn_phase = "roll"
        # 交易系统
        self.trade: dict | None = None  # 当前活跃交易
        # 上一次移动经过起点
        self.last_passed_go = False

    def _add_event(self, text: str, icon: str = "", event_type: str = "info"):
        t = time.strftime("%H:%M:%S")
        self.events.append({"text": text, "icon": icon, "type": event_type, "time": t})
        if len(self.events) > 100:
            self.events = self.events[-100:]

    def add_player(self, name: str, max_players: int = 8) -> bool:
        if any(p["name"] == name for p in self.players):
            return False
        if len(self.players) >= max_players:
            return False
        reconnect_token = secrets.token_hex(6)
        self.players.append({"name": name, "reconnect_token": reconnect_token})
        return True

    def start_round(self) -> bool:
        if not self.can_start():
            return False
        if self.phase == "finished":
            self.properties = {}
            self.houses = {}
            self.mortgaged = {}
            self.player_positions = {}
            self.player_cash = {}
            self.player_in_jail = {}
            self.player_jail_turns = {}
            self.player_get_out_cards = {}
            self.current_player_index = 0
            self.doubles_count = 0
            self.pending_action = None
            self.auction = None
            self.events = []
            self.turn_phase = "roll"
            self._chance_deck = list(range(len(CHANCE_CARDS)))
            self._community_deck = list(range(len(COMMUNITY_CARDS)))
            random.shuffle(self._chance_deck)
            random.shuffle(self._community_deck)
            self.players = [p for p in self.players if p.get("alive", True)]

        self.round_number += 1
        self.phase = "playing"
        for p in self.players:
            name = p["name"]
            self.player_positions[name] = 0
            self.player_cash[name] = self.initial_cash
            self.player_in_jail[name] = False
            self.player_jail_turns[name] = 0
            self.player_get_out_cards[name] = 0
            p["alive"] = True
        self.current_player_index = 0
        self.turn_phase = "roll"
        self._add_event("游戏开始！每人 $%d 起步" % self.initial_cash, "🎉", "system")
        return True

    @property
    def current_player(self) -> dict | None:
        alive = [p for p in self.players if p.get("alive", True)]
        if not alive:
            return None
        self.current_player_index = self.current_player_index % len(alive)
        return alive[self.current_player_index]

    def _get_space(self, idx: int) -> dict:
        return BOARD_SPACES[idx]

    def _get_owner(self, space_index: int) -> str | None:
        return self.properties.get(space_index)

    def _is_mortgaged(self, space_index: int) -> bool:
        return self.mortgaged.get(space_index, False)

    def _count_owned_in_group(self, name: str, group: str) -> int:
        return sum(1 for sp in BOARD_SPACES if sp.get("group") == group and self.properties.get(sp["index"]) == name)

    def _count_group_size(self, group: str) -> int:
        return sum(1 for sp in BOARD_SPACES if sp.get("group") == group)

    def _has_monopoly(self, name: str, group: str) -> bool:
        return self._count_owned_in_group(name, group) == self._count_group_size(group)

    def _count_railroads(self, name: str) -> int:
        return sum(1 for sp in BOARD_SPACES if sp["type"] == "railroad" and self.properties.get(sp["index"]) == name and not self._is_mortgaged(sp["index"]))

    def _count_utilities(self, name: str) -> int:
        return sum(1 for sp in BOARD_SPACES if sp["type"] == "utility" and self.properties.get(sp["index"]) == name and not self._is_mortgaged(sp["index"]))

    def _get_player_properties(self, name: str) -> list[dict]:
        result = []
        for sp in BOARD_SPACES:
            if self.properties.get(sp["index"]) == name:
                result.append({
                    "index": sp["index"], "name": sp["name"],
                    "group": sp.get("group"), "type": sp["type"],
                    "houses": self.houses.get(sp["index"], 0),
                    "mortgaged": self._is_mortgaged(sp["index"]),
                    "price": sp.get("price", 0),
                    "mortgage_value": sp.get("mortgage", 0),
                    "house_cost": sp.get("house_cost", 0),
                    "group_color": COLOR_GROUPS.get(sp.get("group"), {}).get("color", "#888"),
                })
        return result

    def _draw_chance(self) -> dict:
        if not self._chance_deck:
            self._chance_deck = list(range(len(CHANCE_CARDS)))
            random.shuffle(self._chance_deck)
        return CHANCE_CARDS[self._chance_deck.pop(0)]

    def _draw_community(self) -> dict:
        if not self._community_deck:
            self._community_deck = list(range(len(COMMUNITY_CARDS)))
            random.shuffle(self._community_deck)
        return COMMUNITY_CARDS[self._community_deck.pop(0)]

    def roll_dice(self, name: str) -> dict:
        cp = self.current_player
        if not cp or cp["name"] != name:
            return {"ok": False, "error": "不是你的回合"}
        if self.pending_action:
            return {"ok": False, "error": "请先处理当前操作"}
        if self.turn_phase not in ("roll",):
            return {"ok": False, "error": "当前不能掷骰子"}

        in_jail = self.player_in_jail.get(name, False)
        self.dice1 = random.randint(1, 6)
        self.dice2 = random.randint(1, 6)
        total = self.dice1 + self.dice2
        is_doubles = self.dice1 == self.dice2
        self.last_passed_go = False

        result = {"ok": True, "dice": [self.dice1, self.dice2], "total": total, "doubles": is_doubles, "steps": []}

        if in_jail:
            if is_doubles:
                self.player_in_jail[name] = False
                self.player_jail_turns[name] = 0
                result["jail_released"] = True
                self._add_event(f"{name} 掷出双骰出狱！🎲🎲", "🔓", "action")
            else:
                self.player_jail_turns[name] = self.player_jail_turns.get(name, 0) + 1
                if self.player_jail_turns[name] >= 3:
                    self.player_cash[name] = max(0, self.player_cash[name] - 50)
                    self.player_in_jail[name] = False
                    self.player_jail_turns[name] = 0
                    result["jail_paid"] = True
                    result["jail_fee"] = 50
                    self._add_event(f"{name} 第三次出狱，自动支付 $50", "🔓", "action")
                else:
                    result["jail_stay"] = True
                    result["jail_turn"] = self.player_jail_turns[name]
                    self._add_event(f"{name} 在监狱中掷骰子，没有出狱 ({self.player_jail_turns[name]}/3)", "🔒", "action")
                    self.turn_phase = "end"
                    self._next_turn()
                    return result

        # 步进式移动
        old_pos = self.player_positions.get(name, 0)
        path = []
        for step in range(1, total + 1):
            pos = (old_pos + step) % 40
            path.append(pos)
            if pos == 0 and step > 0:
                self.player_cash[name] += self.go_salary
                self.last_passed_go = True
                result["passed_go"] = True
                result["salary"] = self.go_salary
                self._add_event(f"{name} 经过起点，收取 $%d" % self.go_salary, "💰", "money")

        new_pos = path[-1] if path else old_pos
        self.player_positions[name] = new_pos
        result["position"] = new_pos
        result["path"] = path
        result["space"] = BOARD_SPACES[new_pos]

        land_result = self._handle_land(name, new_pos)
        result.update(land_result)

        # 双骰处理
        if is_doubles and not in_jail:
            self.doubles_count += 1
            if self.doubles_count >= 3:
                self._go_to_jail(name)
                result["triple_doubles_jail"] = True
                self.doubles_count = 0
                self._add_event(f"{name} 连续三个双骰，进监狱！🚔", "🚔", "action")
                self.turn_phase = "end"
                self._next_turn()
            elif not land_result.get("needs_action"):
                result["roll_again"] = True
                self.turn_phase = "roll"
        else:
            self.doubles_count = 0
            if not land_result.get("needs_action"):
                self.turn_phase = "end"
                self._next_turn()

        return result

    def _handle_land(self, name: str, pos: int) -> dict:
        space = BOARD_SPACES[pos]
        result = {}

        if space["type"] in ("property", "railroad", "utility"):
            owner = self._get_owner(pos)
            if owner is None:
                result["needs_action"] = True
                self.pending_action = {"type": "buy_property", "player": name, "space": pos, "price": space["price"]}
                result["can_buy"] = True
                result["price"] = space["price"]
                self._add_event(f"{name} 到达 {space['name']}（未拥有，可购买 $%d）" % space["price"], "🏠", "land")
            elif owner != name:
                if self._is_mortgaged(pos):
                    result["mortgaged_no_rent"] = True
                    self._add_event(f"{name} 到达 {space['name']}（已抵押，免租金）", "🏠", "land")
                else:
                    rent = self._calculate_rent(pos, name)
                    self.player_cash[name] -= rent
                    self.player_cash[owner] += rent
                    result["rent_paid"] = rent
                    result["rent_to"] = owner
                    self._add_event(f"{name} 支付租金 ${rent} 给 {owner}", "💸", "money")
                    self._check_bankruptcy(name, owner)
            else:
                self._add_event(f"{name} 到达自己的 {space['name']}", "🏠", "land")

        elif space["type"] == "chance":
            card = self._draw_chance()
            result["card"] = {"type": "chance", "text": card["text"], "icon": card.get("icon", "❓")}
            self._add_event(f"{name} 抽到机会卡: {card['text']}", card.get("icon", "❓"), "card")
            card_result = self._apply_card(name, card)
            result.update(card_result)

        elif space["type"] == "community_chest":
            card = self._draw_community()
            result["card"] = {"type": "community_chest", "text": card["text"], "icon": card.get("icon", "📦")}
            self._add_event(f"{name} 抽到公益金: {card['text']}", card.get("icon", "📦"), "card")
            card_result = self._apply_card(name, card)
            result.update(card_result)

        elif space["type"] == "tax":
            amount = space["amount"]
            self.player_cash[name] -= amount
            result["tax_paid"] = amount
            self._add_event(f"{name} 支付{space['name']} ${amount}", "💰", "money")
            self._check_bankruptcy(name, None)

        elif space["type"] == "go_to_jail":
            self._go_to_jail(name)
            result["went_to_jail"] = True
            self._add_event(f"{name} 被送进监狱！🚔", "🚔", "action")

        elif space["type"] == "go":
            self._add_event(f"{name} 停在起点", "▶️", "land")

        elif space["type"] == "jail":
            self._add_event(f"{name} 只是路过监狱（探监）", "🔒", "land")

        elif space["type"] == "free_parking":
            self._add_event(f"{name} 免费停车", "🅿️", "land")

        return result

    def _apply_card(self, name: str, card: dict) -> dict:
        result = {}
        action = card["action"]

        if action == "move_to":
            old_pos = self.player_positions[name]
            target = card["target"]
            # 构建路径
            path = []
            pos = old_pos
            while pos != target:
                pos = (pos + 1) % 40
                path.append(pos)
                if pos == 0 and target != 0:
                    self.player_cash[name] += self.go_salary
                    result["passed_go"] = True
            if target == 0:
                self.player_cash[name] += self.go_salary
                result["passed_go"] = True
            self.player_positions[name] = target
            result["path"] = path
            land_result = self._handle_land(name, target)
            result.update(land_result)

        elif action == "move_back":
            steps = card.get("steps", 3)
            old_pos = self.player_positions[name]
            path = [(old_pos - s) % 40 for s in range(1, steps + 1)]
            new_pos = path[-1] if path else old_pos
            self.player_positions[name] = new_pos
            result["path"] = path
            land_result = self._handle_land(name, new_pos)
            result.update(land_result)

        elif action == "receive":
            self.player_cash[name] += card["amount"]
            result["received"] = card["amount"]

        elif action == "pay":
            self.player_cash[name] -= card["amount"]
            result["paid"] = card["amount"]
            self._check_bankruptcy(name, None)

        elif action == "go_to_jail":
            self._go_to_jail(name)
            result["went_to_jail"] = True

        elif action == "collect_from_all":
            alive = [p for p in self.players if p.get("alive", True) and p["name"] != name]
            total = 0
            for p in alive:
                pay = min(card["amount"], self.player_cash[p["name"]])
                self.player_cash[p["name"]] -= pay
                self.player_cash[name] += pay
                total += pay
            result["collected"] = total

        elif action == "repair":
            per_house = card.get("per_house", 0)
            per_hotel = card.get("per_hotel", 0)
            cost = 0
            for sp in BOARD_SPACES:
                if self.properties.get(sp["index"]) == name:
                    h = self.houses.get(sp["index"], 0)
                    cost += per_hotel if h == 5 else h * per_house
            self.player_cash[name] -= cost
            result["repair_cost"] = cost
            self._check_bankruptcy(name, None)

        elif action == "nearest_railroad":
            pos = self.player_positions[name]
            rr_positions = [sp["index"] for sp in BOARD_SPACES if sp["type"] == "railroad"]
            nearest = min(rr_positions, key=lambda r: (r - pos) % 40)
            # 构建路径
            path = []
            p = pos
            while p != nearest:
                p = (p + 1) % 40
                path.append(p)
            self.player_positions[name] = nearest
            result["path"] = path
            owner = self._get_owner(nearest)
            if owner and owner != name and not self._is_mortgaged(nearest):
                count = self._count_railroads(owner)
                rent = 25 * (2 ** (count - 1)) * 2
                self.player_cash[name] -= rent
                self.player_cash[owner] += rent
                result["rent_paid"] = rent
                result["rent_to"] = owner
                self._check_bankruptcy(name, owner)

        return result

    def _go_to_jail(self, name: str):
        self.player_positions[name] = 10
        self.player_in_jail[name] = True
        self.player_jail_turns[name] = 0
        self.doubles_count = 0

    def _calculate_rent(self, pos: int, tenant: str = None) -> int:
        space = BOARD_SPACES[pos]
        owner = self._get_owner(pos)
        if not owner:
            return 0
        if self._is_mortgaged(pos):
            return 0

        if space["type"] == "railroad":
            count = self._count_railroads(owner)
            return 25 * (2 ** (count - 1))

        if space["type"] == "utility":
            count = self._count_utilities(owner)
            return (self.dice1 + self.dice2) * (4 if count == 1 else 10)

        # property
        houses = self.houses.get(pos, 0)
        if houses > 0:
            return space["rent"][houses]
        if self._has_monopoly(owner, space["group"]):
            return space["rent"][0] * 2
        return space["rent"][0]

    def _check_bankruptcy(self, name: str, creditor: str | None):
        cash = self.player_cash.get(name, 0)
        if cash >= 0:
            return

        # 破产：尝试卖房/抵押来偿还
        can_raise = 0
        for sp in BOARD_SPACES:
            if self.properties.get(sp["index"]) == name:
                h = self.houses.get(sp["index"], 0)
                if h > 0:
                    can_raise += h * (sp.get("house_cost", 0) // 2)
                if not self._is_mortgaged(sp["index"]):
                    can_raise += sp.get("mortgage", 0)
        if can_raise + cash >= 0:
            # 还能自救，不破产（前端会看到负数要求操作）
            return

        # 真的破产了
        self._add_event(f"{name} 破产了！💸💸", "💀", "bankruptcy")
        self.player_cash[name] = 0
        for sp in BOARD_SPACES:
            idx = sp["index"]
            if self.properties.get(idx) == name:
                self.houses[idx] = 0
                self.mortgaged[idx] = False
                if creditor:
                    self.properties[idx] = creditor
                    self._add_event(f"{sp['name']} 转移给 {creditor}", "🏠", "transfer")
                else:
                    self.properties[idx] = None
        for p in self.players:
            if p["name"] == name:
                p["alive"] = False
        if name in self.player_positions:
            del self.player_positions[name]

        # 检查游戏结束
        alive = [p for p in self.players if p.get("alive", True)]
        if len(alive) == 1:
            self._add_event(f"🏆 {alive[0]['name']} 获胜！恭喜！", "🏆", "victory")
            self.phase = "finished"

    def _next_turn(self):
        alive = [p for p in self.players if p.get("alive", True)]
        if len(alive) <= 1:
            if alive:
                self._add_event(f"🏆 {alive[0]['name']} 获胜！恭喜！", "🏆", "victory")
            self.phase = "finished"
            self.pending_action = None
            return
        self.current_player_index = (self.current_player_index + 1) % len(alive)
        self.doubles_count = 0
        self.pending_action = None
        self.turn_phase = "roll"
        self.trade = None
        cp = self.current_player
        if cp:
            self._add_event(f"轮到 {cp['name']} 了", "🎲", "turn")

    # ---- 玩家操作 ----

    def buy_property(self, name: str) -> dict:
        if not self.pending_action or self.pending_action["type"] != "buy_property":
            return {"ok": False, "error": "没有待购买的地产"}
        if self.pending_action["player"] != name:
            return {"ok": False, "error": "不是你的操作"}
        pos = self.pending_action["space"]
        price = self.pending_action["price"]
        if self.player_cash.get(name, 0) < price:
            return {"ok": False, "error": "现金不足"}
        self.player_cash[name] -= price
        self.properties[pos] = name
        self.houses[pos] = 0
        self.mortgaged[pos] = False
        sp = BOARD_SPACES[pos]
        self._add_event(f"{name} 购买了 {sp['name']}，花费 ${price}", "🏠", "buy")
        self.pending_action = None
        if self.doubles_count > 0:
            self.turn_phase = "roll"
        else:
            self._next_turn()
        return {"ok": True, "position": pos, "price": price}

    def skip_buy(self, name: str) -> dict:
        if not self.pending_action or self.pending_action["type"] != "buy_property":
            return {"ok": False, "error": "没有待处理的操作"}
        if self.pending_action["player"] != name:
            return {"ok": False, "error": "不是你的操作"}
        pos = self.pending_action["space"]
        sp = BOARD_SPACES[pos]
        price = self.pending_action["price"]
        self._add_event(f"{name} 放弃购买 {sp['name']}，进入拍卖", "🔨", "auction")
        # 开始拍卖
        self.auction = {
            "space": pos,
            "price": 0,
            "highest_bidder": None,
            "bids": {},
            "players": [p["name"] for p in self.players if p.get("alive", True) and p["name"] != name],
            "ended": False,
            "from_doubles": self.doubles_count > 0,
        }
        self.pending_action = {"type": "auction", "space": pos}
        return {"ok": True, "auction_started": True, "space": pos}

    def bid_auction(self, name: str, amount: int) -> dict:
        if not self.auction or self.auction.get("ended"):
            return {"ok": False, "error": "没有进行中的拍卖"}
        if name not in self.auction["players"]:
            return {"ok": False, "error": "你不能参与此拍卖"}
        if amount <= self.auction["price"]:
            return {"ok": False, "error": "出价必须高于当前最高价"}
        if self.player_cash.get(name, 0) < amount:
            return {"ok": False, "error": "现金不足"}
        self.auction["price"] = amount
        self.auction["highest_bidder"] = name
        self.auction["bids"][name] = amount
        self._add_event(f"{name} 出价 ${amount}", "🔨", "auction")
        return {"ok": True, "bid": amount}

    def pass_auction(self, name: str) -> dict:
        if not self.auction or self.auction.get("ended"):
            return {"ok": False, "error": "没有进行中的拍卖"}
        if name in self.auction["players"]:
            self.auction["players"].remove(name)
        # 检查是否只剩一个出价者
        active_bidders = [p for p in self.auction["players"] if p != self.auction.get("highest_bidder")]
        if len(active_bidders) == 0 or len(self.auction["players"]) <= 1:
            return self._end_auction()
        return {"ok": True, "passed": True}

    def _end_auction(self) -> dict:
        self.auction["ended"] = True
        winner = self.auction.get("highest_bidder")
        price = self.auction.get("price", 0)
        pos = self.auction["space"]
        from_doubles = self.auction.get("from_doubles", False)
        sp = BOARD_SPACES[pos]
        if winner and price > 0:
            self.player_cash[winner] -= price
            self.properties[pos] = winner
            self.houses[pos] = 0
            self.mortgaged[pos] = False
            self._add_event(f"{winner} 以 ${price} 拍得 {sp['name']}！", "🔨", "auction")
        else:
            self._add_event(f"{sp['name']} 流拍", "🔨", "auction")
        self.auction = None
        self.pending_action = None
        if from_doubles:
            self.turn_phase = "roll"
        else:
            self._next_turn()
        return {"ok": True, "auction_ended": True, "winner": winner, "price": price}

    def buy_house(self, name: str, position: int) -> dict:
        if self.properties.get(position) != name:
            return {"ok": False, "error": "这不是你的地产"}
        space = BOARD_SPACES[position]
        if space["type"] != "property":
            return {"ok": False, "error": "不能在这建房子"}
        if self._is_mortgaged(position):
            return {"ok": False, "error": "已抵押的地产不能建房"}
        if not self._has_monopoly(name, space["group"]):
            return {"ok": False, "error": "需要拥有同色全部地产"}
        current = self.houses.get(position, 0)
        if current >= 5:
            return {"ok": False, "error": "已满级（酒店）"}
        # 均衡建设
        group_houses = []
        for sp in BOARD_SPACES:
            if sp.get("group") == space["group"] and self.properties.get(sp["index"]) == name:
                group_houses.append(self.houses.get(sp["index"], 0))
        min_h = min(group_houses)
        if self.houses.get(position, 0) > min_h:
            return {"ok": False, "error": "需要均衡建设"}
        cost = space["house_cost"]
        if self.player_cash.get(name, 0) < cost:
            return {"ok": False, "error": "现金不足"}
        self.player_cash[name] -= cost
        self.houses[position] = current + 1
        level = "酒店" if current + 1 == 5 else f"{current + 1}栋房"
        self._add_event(f"{name} 在 {space['name']} 建了{level}（花费 ${cost}）", "🏗️", "build")
        return {"ok": True, "position": position, "houses": current + 1}

    def sell_house(self, name: str, position: int) -> dict:
        if self.properties.get(position) != name:
            return {"ok": False, "error": "这不是你的地产"}
        current = self.houses.get(position, 0)
        if current <= 0:
            return {"ok": False, "error": "没有房子可卖"}
        space = BOARD_SPACES[position]
        group_houses = []
        for sp in BOARD_SPACES:
            if sp.get("group") == space["group"] and self.properties.get(sp["index"]) == name:
                group_houses.append(self.houses.get(sp["index"], 0))
        max_h = max(group_houses)
        if self.houses.get(position, 0) < max_h:
            return {"ok": False, "error": "需要均衡拆除"}
        refund = space["house_cost"] // 2
        self.houses[position] = current - 1
        self.player_cash[name] += refund
        self._add_event(f"{name} 拆除了 {space['name']} 的房子，收回 ${refund}", "🏚️", "build")
        return {"ok": True, "position": position, "houses": current - 1, "refund": refund}

    def mortgage_property(self, name: str, position: int) -> dict:
        if self.properties.get(position) != name:
            return {"ok": False, "error": "这不是你的地产"}
        if self._is_mortgaged(position):
            return {"ok": False, "error": "已经抵押了"}
        if self.houses.get(position, 0) > 0:
            return {"ok": False, "error": "请先拆除所有房子"}
        space = BOARD_SPACES[position]
        value = space.get("mortgage", space.get("price", 0) // 2)
        self.mortgaged[position] = True
        self.player_cash[name] += value
        self._add_event(f"{name} 抵押了 {space['name']}，获得 ${value}", "📋", "mortgage")
        return {"ok": True, "position": position, "value": value}

    def unmortgage_property(self, name: str, position: int) -> dict:
        if self.properties.get(position) != name:
            return {"ok": False, "error": "这不是你的地产"}
        if not self._is_mortgaged(position):
            return {"ok": False, "error": "没有被抵押"}
        space = BOARD_SPACES[position]
        mortgage_val = space.get("mortgage", space.get("price", 0) // 2)
        cost = int(mortgage_val * 1.1)
        if self.player_cash.get(name, 0) < cost:
            return {"ok": False, "error": f"需要 ${cost}（含10%利息）才能赎回"}
        self.player_cash[name] -= cost
        self.mortgaged[position] = False
        self._add_event(f"{name} 赎回了 {space['name']}（花费 ${cost}）", "📋", "mortgage")
        return {"ok": True, "position": position, "cost": cost}

    def pay_jail_fine(self, name: str) -> dict:
        if not self.player_in_jail.get(name):
            return {"ok": False, "error": "你不在监狱"}
        if self.player_cash.get(name, 0) < 50:
            return {"ok": False, "error": "现金不足"}
        self.player_cash[name] -= 50
        self.player_in_jail[name] = False
        self.player_jail_turns[name] = 0
        self._add_event(f"{name} 支付 $50 出狱", "🔓", "action")
        return {"ok": True, "paid": 50}

    def use_jail_card(self, name: str) -> dict:
        if not self.player_in_jail.get(name):
            return {"ok": False, "error": "你不在监狱"}
        if self.player_get_out_cards.get(name, 0) <= 0:
            return {"ok": False, "error": "没有出狱卡"}
        self.player_get_out_cards[name] -= 1
        self.player_in_jail[name] = False
        self.player_jail_turns[name] = 0
        self._add_event(f"{name} 使用出狱卡出狱", "🔓", "action")
        return {"ok": True, "used_card": True}

    # ---- 状态 ----

    def get_state(self, viewer: str = None) -> dict:
        alive = [p for p in self.players if p.get("alive", True)]
        current_name = None
        if alive:
            idx = self.current_player_index % len(alive)
            current_name = alive[idx]["name"]

        players_info = []
        for p in self.players:
            name = p["name"]
            props = self._get_player_properties(name)
            total_asset = self.player_cash.get(name, 0)
            for pr in props:
                if not pr["mortgaged"]:
                    total_asset += pr["price"]
                total_asset += pr["houses"] * (pr["house_cost"] // 2)
            players_info.append({
                "name": name,
                "alive": p.get("alive", True),
                "cash": self.player_cash.get(name, 0),
                "total_asset": total_asset,
                "position": self.player_positions.get(name, 0),
                "in_jail": self.player_in_jail.get(name, False),
                "jail_turns": self.player_jail_turns.get(name, 0),
                "properties": props,
                "is_current": name == current_name,
                "get_out_cards": self.player_get_out_cards.get(name, 0),
            })

        board_state = []
        for sp in BOARD_SPACES:
            bs = {"index": sp["index"], "type": sp["type"], "name": sp["name"]}
            owner = self.properties.get(sp["index"])
            if owner:
                bs["owner"] = owner
                bs["houses"] = self.houses.get(sp["index"], 0)
                bs["mortgaged"] = self._is_mortgaged(sp["index"])
            if sp.get("group"):
                bs["group"] = sp["group"]
                bs["group_color"] = COLOR_GROUPS.get(sp["group"], {}).get("color", "#888")
            if sp.get("price"):
                bs["price"] = sp["price"]
            board_state.append(bs)

        positions_map = {}
        for name, pos in self.player_positions.items():
            if pos not in positions_map:
                positions_map[pos] = []
            positions_map[pos].append(name)

        return {
            "game_type": self.game_type,
            "room_id": self.room_id,
            "round": self.round_number,
            "phase": self.phase,
            "host": self.host_name,
            "players": players_info,
            "board": board_state,
            "current_player": current_name,
            "dice": [self.dice1, self.dice2],
            "pending_action": self.pending_action,
            "auction": self.auction,
            "viewer": viewer,
            "positions": positions_map,
            "events": self.events[-30:],
            "turn_phase": self.turn_phase,
            "chat": self.chat[-20:],
            "trade": self.trade if self.trade and not self.trade.get("ended") else None,
        }

    def admin_get_full_state(self) -> dict:
        state = self.get_state()
        state["properties_raw"] = {str(k): v for k, v in self.properties.items()}
        state["houses_raw"] = {str(k): v for k, v in self.houses.items()}
        state["mortgaged_raw"] = {str(k): v for k, v in self.mortgaged.items()}
        return state

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

        # 校验现金非负
        if offer_cash < 0 or req_cash < 0:
            return {"ok": False, "error": "现金不能为负数"}
        # 校验非空交易
        if offer_cash == 0 and not offer_props and req_cash == 0 and not req_props:
            return {"ok": False, "error": "请至少设置一项交易内容"}

        # 验证 proposer 拥有 offer 的地产
        for idx in offer_props:
            if not (0 <= idx < len(BOARD_SPACES)):
                return {"ok": False, "error": "无效的地产索引"}
            if self.properties.get(idx) != proposer:
                return {"ok": False, "error": f"你不拥有 {BOARD_SPACES[idx]['name']}"}
            if self.houses.get(idx, 0) > 0:
                return {"ok": False, "error": f"请先拆除 {BOARD_SPACES[idx]['name']} 的房子"}

        # 验证 target 拥有 request 的地产
        for idx in req_props:
            if not (0 <= idx < len(BOARD_SPACES)):
                return {"ok": False, "error": "无效的地产索引"}
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

    def admin_set_chips(self, target_name: str, chips: int) -> bool:
        if target_name in self.player_cash:
            self.player_cash[target_name] = max(0, chips)
            return True
        return False
