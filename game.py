"""牛牛游戏核心逻辑"""
import random
from itertools import combinations
from dataclasses import dataclass, field
from typing import Optional


# 花色 emoji
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
    hand_type: str   # "none" / "bull1" .. "bull10" / "bomb" / "five_flower" / "five_small"
    bull_number: int  # 0-10, 10=牛牛
    type_score: int   # 牌型权重，越大越强
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

    # 五小牛：5张牌都≤5且总点数≤10
    values = [c.value for c in cards]
    if all(v <= 5 for v in values) and sum(values) <= 10:
        return HandResult("five_small", 10, 10000, "五小牛")

    # 炸弹牛：4张同点数
    for v in set(values):
        if values.count(v) == 4:
            return HandResult("bomb", 10, 9000, "炸弹牛")

    # 五花牛：5张都是JQK
    if all(c.rank in ("J", "Q", "K") for c in cards):
        return HandResult("five_flower", 10, 8000, "五花牛")

    # 普通牛：找3张牌之和为10的倍数
    for combo in combinations(range(5), 3):
        if sum(values[i] for i in combo) % 10 == 0:
            remain = [i for i in range(5) if i not in combo]
            bull = (values[remain[0]] + values[remain[1]]) % 10
            if bull == 0:
                return HandResult("bull10", 10, 7000 + _tie_break(cards), "牛牛")
            return HandResult(f"bull{bull}", bull, 6000 + bull * 100 + _tie_break(cards),
                              RANK_NAMES[f"bull{bull}"])

    # 无牛
    sorted_vals = sorted(values, reverse=True)
    return HandResult("none", 0, sorted_vals[0] * 100 + sorted_vals[1] * 10 + sorted_vals[2], "无牛")


def _tie_break(cards: list[Card]) -> int:
    """同牌型时用最大牌比较"""
    sorted_cards = sorted(cards, key=_hand_sort_key, reverse=True)
    return sum(c.sort_key * (100 ** (4 - i)) for i, c in enumerate(sorted_cards))


class GameRoom:
    def __init__(self, room_id: str, host_name: str):
        self.room_id = room_id
        self.host_name = host_name
        self.players: list[dict] = []  # {"name": str, "hand": list[Card], "confirmed": bool, "result": HandResult}
        self.phase = "waiting"  # waiting -> dealing -> playing -> finished
        self.round_number = 0
        self.deck: list[Card] = []

    def add_player(self, name: str) -> bool:
        if any(p["name"] == name for p in self.players):
            return False
        if len(self.players) >= 20:
            return False
        self.players.append({"name": name, "hand": [], "confirmed": False, "result": None})
        return True

    def remove_player(self, name: str):
        self.players = [p for p in self.players if p["name"] != name]

    def can_start(self) -> bool:
        return self.phase == "waiting" and len(self.players) >= 2

    def start_round(self) -> bool:
        if not self.can_start():
            return False
        self.round_number += 1
        self.phase = "dealing"
        self.deck = _create_deck()
        random.shuffle(self.deck)
        for p in self.players:
            p["hand"] = [self.deck.pop() for _ in range(5)]
            p["confirmed"] = False
            p["result"] = None
        self.phase = "playing"
        return True

    def confirm_cards(self, name: str) -> bool:
        for p in self.players:
            if p["name"] == name and not p["confirmed"]:
                p["confirmed"] = True
                p["result"] = evaluate_hand(p["hand"])
                break
        if all(p["confirmed"] for p in self.players):
            self.phase = "finished"
            return True
        return False

    def get_state(self, viewer: str = None) -> dict:
        players_info = []
        for p in self.players:
            info = {"name": p["name"], "confirmed": p["confirmed"]}
            if self.phase in ("playing", "finished") and p["hand"]:
                if p["confirmed"] or self.phase == "finished":
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
                [{"name": p["name"], "result": p["result"].to_dict()} for p in self.players],
                key=lambda x: x["result"]["score"], reverse=True
            )

        return {
            "room_id": self.room_id,
            "round": self.round_number,
            "phase": self.phase,
            "host": self.host_name,
            "players": players_info,
            "results": results,
            "viewer": viewer,
        }
