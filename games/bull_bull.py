"""牛牛游戏逻辑"""
import random
import secrets
from itertools import combinations
from dataclasses import dataclass
from .base import BaseGameRoom

# 下注模式
BET_MODES = {
    "classic": "经典模式",
    "raise": "加注模式",
    "tournament": "锦标赛",
}

SUIT_SYMBOLS = {"spades": "♠", "hearts": "♥", "diamonds": "♦", "clubs": "♣"}
SUIT_COLORS = {"spades": "black", "hearts": "red", "diamonds": "red", "clubs": "black"}

RANK_NAMES = {
    "none": "无牛",
    "bull1": "牛一", "bull2": "牛二", "bull3": "牛三", "bull4": "牛四", "bull5": "牛五",
    "bull6": "牛六", "bull7": "牛七", "bull8": "牛八", "bull9": "牛九",
    "bull10": "牛牛",
    "bomb": "炸弹牛",
    "five_flower": "五花牛",
    "five_small": "五小牛",
}


@dataclass
class Card:
    suit: str
    rank: str

    @property
    def value(self) -> int:
        if self.rank in ("J", "Q", "K"):
            return 10
        if self.rank == "A":
            return 1
        return int(self.rank)

    @property
    def sort_key(self) -> int:
        order = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
                 "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13}
        return order[self.rank] * 4 + list(SUIT_SYMBOLS.keys()).index(self.suit)

    def to_dict(self) -> dict:
        return {
            "suit": self.suit,
            "rank": self.rank,
            "symbol": SUIT_SYMBOLS[self.suit],
            "color": SUIT_COLORS[self.suit],
            "value": self.value,
        }


@dataclass
class HandResult:
    hand_type: str
    bull_number: int
    type_score: int
    display: str

    def to_dict(self) -> dict:
        return {"type": self.hand_type, "bull": self.bull_number,
                "score": self.type_score, "display": self.display}


def _create_deck() -> list[Card]:
    suits = list(SUIT_SYMBOLS.keys())
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    return [Card(suit=s, rank=r) for s in suits for r in ranks]


def _hand_sort_key(card: Card) -> tuple:
    return (card.value, card.sort_key)


def evaluate_hand(cards: list[Card]) -> HandResult:
    """评估5张牌的牛牛牌型"""
    assert len(cards) == 5

    values = [c.value for c in cards]
    if all(v <= 5 for v in values) and sum(values) <= 10:
        return HandResult("five_small", 10, 10000, "五小牛")

    for v in set(values):
        if values.count(v) == 4:
            return HandResult("bomb", 10, 9000, "炸弹牛")

    if all(c.rank in ("J", "Q", "K") for c in cards):
        return HandResult("five_flower", 10, 8000, "五花牛")

    for combo in combinations(range(5), 3):
        if sum(values[i] for i in combo) % 10 == 0:
            remain = [i for i in range(5) if i not in combo]
            bull = (values[remain[0]] + values[remain[1]]) % 10
            if bull == 0:
                return HandResult("bull10", 10, 7000 + _tie_break(cards), "牛牛")
            return HandResult(f"bull{bull}", bull, 6000 + bull * 100 + _tie_break(cards),
                              RANK_NAMES[f"bull{bull}"])

    sorted_vals = sorted(values, reverse=True)
    return HandResult("none", 0, sorted_vals[0] * 100 + sorted_vals[1] * 10 + sorted_vals[2], "无牛")


def _tie_break(cards: list[Card]) -> int:
    sorted_cards = sorted(cards, key=_hand_sort_key, reverse=True)
    return sum(c.sort_key * (100 ** (4 - i)) for i, c in enumerate(sorted_cards))


class BullBullRoom(BaseGameRoom):
    game_type = "bull_bull"
    game_name = "牛牛"

    def __init__(self, room_id: str, host_name: str, settings: dict = None):
        super().__init__(room_id, host_name, settings)
        self.phase = "waiting"  # waiting -> dealing -> betting -> playing -> finished
        self.deck: list[Card] = []
        s = settings or {}
        self.bet_mode = s.get("bet_mode", "classic")
        self.initial_chips = s.get("initial_chips", 1000)
        self.base_bet = s.get("base_bet", 10)
        self.pot = 0
        self.current_bet = 0
        self.bet_timer = 0

    def add_player(self, name: str, max_players: int = 20) -> bool:
        if any(p["name"] == name for p in self.players):
            return False
        if len(self.players) >= max_players:
            return False
        reconnect_token = secrets.token_hex(6)
        self.players.append({
            "name": name, "hand": [], "confirmed": False, "result": None,
            "chips": self.initial_chips, "folded": False, "bet": 0, "luck": 0,
            "reconnect_token": reconnect_token,
        })
        return True

    def start_round(self) -> bool:
        if not self.can_start():
            return False
        self.round_number += 1
        self.pot = 0
        self.current_bet = 0
        self.deck = _create_deck()
        random.shuffle(self.deck)
        for p in self.players:
            p["hand"] = [self.deck.pop() for _ in range(5)]
            p["confirmed"] = False
            p["result"] = None
            p["folded"] = False
            p["bet"] = 0
            if self.bet_mode == "tournament" and p["chips"] <= 0:
                p["folded"] = True

        self._apply_luck()

        if self.bet_mode == "classic":
            for p in self.players:
                if p["chips"] > 0:
                    bet = min(self.base_bet, p["chips"])
                    p["chips"] -= bet
                    p["bet"] = bet
                    self.pot += bet
            self.phase = "playing"
        elif self.bet_mode == "tournament":
            for p in self.players:
                if p["chips"] > 0 and not p["folded"]:
                    bet = min(self.base_bet, p["chips"])
                    p["chips"] -= bet
                    p["bet"] = bet
                    self.pot += bet
            self.phase = "playing"
        elif self.bet_mode == "raise":
            self.current_bet = self.base_bet
            self.phase = "betting"
            self.bet_timer = 30
        return True

    def _apply_luck(self):
        for p in self.players:
            luck = p.get("luck", 0)
            if luck == 0 or not p["hand"] or p.get("folded"):
                continue
            swaps = min(abs(luck), 3)
            used = {(c.suit, c.rank) for c in p["hand"]}
            remaining = [c for c in self.deck if (c.suit, c.rank) not in used]
            for _ in range(swaps):
                if not remaining:
                    break
                if luck > 0:
                    weakest_idx = min(range(len(p["hand"])), key=lambda i: p["hand"][i].value)
                    best = max(remaining, key=lambda c: c.value)
                    remaining.remove(best)
                    p["hand"][weakest_idx] = best
                else:
                    strongest_idx = max(range(len(p["hand"])), key=lambda i: p["hand"][i].value)
                    worst = min(remaining, key=lambda c: c.value)
                    remaining.remove(worst)
                    p["hand"][strongest_idx] = worst
            used_after = {(c.suit, c.rank) for c in p["hand"]}
            self.deck = [c for c in self.deck if (c.suit, c.rank) not in used_after]

    def set_player_luck(self, host_name: str, target_name: str, luck: int) -> bool:
        if host_name != self.host_name:
            return False
        luck = max(-3, min(3, luck))
        for p in self.players:
            if p["name"] == target_name:
                p["luck"] = luck
                return True
        return False

    def admin_set_card(self, target_name: str, card_index: int, suit: str, rank: str) -> bool:
        for p in self.players:
            if p["name"] == target_name and p["hand"] and 0 <= card_index < 5:
                p["hand"][card_index] = Card(suit=suit, rank=rank)
                if p["confirmed"]:
                    p["result"] = evaluate_hand(p["hand"])
                return True
        return False

    def admin_set_chips(self, target_name: str, chips: int) -> bool:
        for p in self.players:
            if p["name"] == target_name:
                p["chips"] = max(0, chips)
                return True
        return False

    def admin_get_full_state(self) -> dict:
        players_info = []
        for p in self.players:
            info = {
                "name": p["name"], "confirmed": p["confirmed"],
                "chips": p["chips"], "folded": p["folded"], "bet": p["bet"],
                "luck": p.get("luck", 0),
                "hand": [c.to_dict() for c in p["hand"]] if p["hand"] else [],
                "result": p["result"].to_dict() if p["result"] else None,
            }
            players_info.append(info)

        results = []
        if self.phase == "finished":
            results = sorted(
                [{"name": p["name"], "result": p["result"].to_dict(), "chips": p["chips"]}
                 for p in self.players if p["result"]],
                key=lambda x: x["result"]["score"], reverse=True
            )

        return {
            "game_type": self.game_type,
            "room_id": self.room_id,
            "round": self.round_number,
            "phase": self.phase,
            "host": self.host_name,
            "players": players_info,
            "results": results,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "bet_mode": self.bet_mode,
            "bet_mode_name": BET_MODES.get(self.bet_mode, self.bet_mode),
            "base_bet": self.base_bet,
            "initial_chips": self.initial_chips,
        }

    def place_bet(self, name: str, action: str, amount: int = 0) -> dict:
        for p in self.players:
            if p["name"] != name or p["folded"] or p["confirmed"]:
                continue
            to_call = self.current_bet - p["bet"]
            if action == "fold":
                p["folded"] = True
                return {"ok": True, "action": "fold"}
            elif action == "call":
                pay = min(to_call, p["chips"])
                p["chips"] -= pay
                p["bet"] += pay
                self.pot += pay
                return {"ok": True, "action": "call", "amount": pay}
            elif action == "raise":
                raise_to = max(amount, self.current_bet + self.base_bet)
                pay = raise_to - p["bet"]
                pay = min(pay, p["chips"])
                p["chips"] -= pay
                p["bet"] += pay
                self.pot += pay
                self.current_bet = p["bet"]
                return {"ok": True, "action": "raise", "amount": p["bet"]}
        return {"ok": False}

    def check_betting_done(self) -> bool:
        active = [p for p in self.players if not p["folded"]]
        if len(active) <= 1:
            return True
        return all(p["bet"] == self.current_bet or p["chips"] == 0 for p in active)

    def finish_betting(self):
        active = [p for p in self.players if not p["folded"]]
        if len(active) == 1:
            winner = active[0]
            winner["chips"] += self.pot
            winner["result"] = HandResult("none", 0, 0, "对手弃牌")
            self.pot = 0
            self.phase = "finished"
            return True
        self.phase = "playing"
        return False

    def auto_fold_timeout(self):
        for p in self.players:
            if not p["folded"] and not p["confirmed"] and p["bet"] < self.current_bet:
                p["folded"] = True

    def confirm_cards(self, name: str) -> bool:
        for p in self.players:
            if p["name"] == name and not p["confirmed"] and not p["folded"]:
                p["confirmed"] = True
                p["result"] = evaluate_hand(p["hand"])
                break
        active = [p for p in self.players if not p["folded"]]
        if all(p["confirmed"] for p in active):
            self._settle_round()
            return True
        return False

    def _settle_round(self):
        self.phase = "finished"
        active = [p for p in self.players if not p["folded"] and p["result"]]
        if not active:
            return
        active.sort(key=lambda p: p["result"].type_score, reverse=True)
        winner = active[0]
        winner["chips"] += self.pot
        self.pot = 0

    def get_state(self, viewer: str = None) -> dict:
        is_host = viewer == self.host_name
        players_info = []
        for p in self.players:
            info = {
                "name": p["name"], "confirmed": p["confirmed"],
                "chips": p["chips"], "folded": p["folded"], "bet": p["bet"],
            }
            if is_host:
                info["luck"] = p.get("luck", 0)
            if self.phase in ("betting", "playing", "finished") and p["hand"]:
                if p["folded"]:
                    info["hand"] = [{"suit": "?", "rank": "?", "symbol": "?", "color": "gray"}] * 5
                elif p["confirmed"] or self.phase == "finished":
                    info["hand"] = [c.to_dict() for c in p["hand"]]
                    if p["result"]:
                        info["result"] = p["result"].to_dict()
                else:
                    info["hand"] = [{"suit": "?", "rank": "?", "symbol": "?", "color": "gray"}] * 5
            else:
                info["hand"] = []
            players_info.append(info)

        results = []
        if self.phase == "finished":
            results = sorted(
                [{"name": p["name"], "result": p["result"].to_dict(), "chips": p["chips"]}
                 for p in self.players if p["result"]],
                key=lambda x: x["result"]["score"], reverse=True
            )

        return {
            "game_type": self.game_type,
            "room_id": self.room_id,
            "round": self.round_number,
            "phase": self.phase,
            "host": self.host_name,
            "players": players_info,
            "results": results,
            "viewer": viewer,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "bet_mode": self.bet_mode,
            "bet_mode_name": BET_MODES.get(self.bet_mode, self.bet_mode),
            "base_bet": self.base_bet,
            "initial_chips": self.initial_chips,
            "bet_timer": self.bet_timer,
            "chat": self.chat[-20:],
        }
