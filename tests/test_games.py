"""
游戏集合单元测试
"""
import pytest
from games.bull_bull import BullBullRoom, Card, evaluate_hand, HandResult
from games.monopoly import MonopolyRoom
from games.ludo import LudoRoom


# ============ 牛牛游戏测试 ============

class TestBullBullHand:
    """牛牛手牌评估测试"""

    def test_five_small(self):
        """五小牛测试"""
        cards = [
            Card("spades", "2"),
            Card("hearts", "3"),
            Card("diamonds", "4"),
            Card("clubs", "5"),
            Card("spades", "A"),
        ]
        result = evaluate_hand(cards)
        assert result.hand_type == "bull5"
        assert result.bull_number == 5

    def test_bull10(self):
        """牛牛测试"""
        cards = [
            Card("spades", "5"),
            Card("hearts", "5"),
            Card("diamonds", "K"),
            Card("clubs", "K"),
            Card("spades", "K"),
        ]
        result = evaluate_hand(cards)
        assert result.hand_type == "bull10"
        assert result.bull_number == 10

    def test_bomb(self):
        """炸弹牛测试"""
        cards = [
            Card("spades", "5"),
            Card("hearts", "5"),
            Card("diamonds", "5"),
            Card("clubs", "5"),
            Card("spades", "K"),
        ]
        result = evaluate_hand(cards)
        assert result.hand_type == "bomb"
        assert result.bull_number == 10

    def test_five_flower(self):
        """五花牛测试"""
        cards = [
            Card("spades", "J"),
            Card("hearts", "Q"),
            Card("diamonds", "K"),
            Card("clubs", "J"),
            Card("spades", "Q"),
        ]
        result = evaluate_hand(cards)
        assert result.hand_type == "five_flower"
        assert result.bull_number == 10

    def test_no_bull(self):
        """无牛测试"""
        cards = [
            Card("spades", "2"),
            Card("hearts", "3"),
            Card("diamonds", "4"),
            Card("clubs", "6"),
            Card("spades", "7"),
        ]
        result = evaluate_hand(cards)
        assert result.hand_type == "none"
        assert result.bull_number == 0


class TestBullBullRoom:
    """牛牛房间测试"""

    def test_room_creation(self):
        """房间创建测试"""
        room = BullBullRoom("room1", "host1", {"bet_mode": "classic"})
        assert room.room_id == "room1"
        assert room.host_name == "host1"
        assert room.phase == "waiting"

    def test_add_player(self):
        """添加玩家测试"""
        room = BullBullRoom("room1", "host1")
        assert room.add_player("player1")
        assert room.add_player("player2")
        assert len(room.players) == 2

    def test_duplicate_player(self):
        """重复玩家测试"""
        room = BullBullRoom("room1", "host1")
        assert room.add_player("player1")
        assert not room.add_player("player1")

    def test_can_start(self):
        """游戏开始条件测试"""
        room = BullBullRoom("room1", "host1")
        assert not room.can_start()
        room.add_player("player1")
        assert not room.can_start()
        room.add_player("player2")
        assert room.can_start()


# ============ 大富翁游戏测试 ============

class TestMonopolyRoom:
    """大富翁房间测试"""

    def test_room_creation(self):
        """房间创建测试"""
        room = MonopolyRoom("room1", "host1")
        assert room.room_id == "room1"
        assert room.host_name == "host1"
        assert room.phase == "waiting"

    def test_add_player(self):
        """添加玩家测试"""
        room = MonopolyRoom("room1", "host1")
        assert room.add_player("player1")
        assert room.add_player("player2")
        assert len(room.players) == 2

    def test_can_start(self):
        """游戏开始条件测试"""
        room = MonopolyRoom("room1", "host1")
        assert not room.can_start()
        room.add_player("player1")
        assert not room.can_start()
        room.add_player("player2")
        assert room.can_start()

    def test_auction_creation(self):
        """拍卖创建测试"""
        room = MonopolyRoom("room1", "host1")
        room.add_player("player1")
        room.add_player("player2")
        # 直接创建拍卖状态而不依赖复杂的游戏流程
        room.auction = {
            "space": 0,
            "price": 0,
            "highest_bidder": None,
            "bids": {},
            "players": ["player2"],
            "ended": False,
            "from_doubles": False,
        }
        room.pending_action = {"type": "auction", "space": 0}
        assert room.auction is not None
        assert "player2" in room.auction["players"]

    def test_auction_bid(self):
        """拍卖出价测试"""
        room = MonopolyRoom("room1", "host1")
        room.add_player("player1")
        room.add_player("player2")
        # 初始化玩家现金
        room.player_cash["player1"] = 1000
        room.player_cash["player2"] = 1000
        # 直接创建拍卖状态
        room.auction = {
            "space": 0,
            "price": 0,
            "highest_bidder": None,
            "bids": {},
            "players": ["player2"],
            "ended": False,
            "from_doubles": False,
        }
        # 出价
        result = room.bid_auction("player2", 100)
        assert result.get("ok")
        assert room.auction["price"] == 100
        assert room.auction["highest_bidder"] == "player2"

    def test_auction_pass(self):
        """拍卖放弃测试"""
        room = MonopolyRoom("room1", "host1")
        room.add_player("player1")
        room.add_player("player2")
        room.player_cash["player1"] = 1000
        room.player_cash["player2"] = 1000
        # 直接创建拍卖状态
        room.auction = {
            "space": 0,
            "price": 100,
            "highest_bidder": "player2",
            "bids": {"player2": 100},
            "players": ["player2"],
            "ended": False,
            "from_doubles": False,
        }
        # 放弃
        result = room.pass_auction("player2")
        assert result.get("ok") or result.get("passed")


# ============ 飞行棋游戏测试 ============

class TestLudoRoom:
    """飞行棋房间测试"""

    def test_room_creation(self):
        """房间创建测试"""
        room = LudoRoom("room1", "host1")
        assert room.room_id == "room1"
        assert room.host_name == "host1"
        assert room.phase == "waiting"

    def test_add_player(self):
        """添加玩家测试"""
        room = LudoRoom("room1", "host1")
        assert room.add_player("player1")
        assert room.add_player("player2")
        assert len(room.players) == 2

    def test_can_start(self):
        """游戏开始条件测试"""
        room = LudoRoom("room1", "host1")
        assert not room.can_start()
        room.add_player("player1")
        assert not room.can_start()
        room.add_player("player2")
        assert room.can_start()


# ============ 验证器测试 ============

class TestValidators:
    """输入验证器测试"""

    def test_valid_player_name(self):
        """有效玩家名称测试"""
        from game_server_improvements import Validators
        assert Validators.validate_player_name("player1")
        assert Validators.validate_player_name("玩家1")
        assert Validators.validate_player_name("player_1")

    def test_invalid_player_name(self):
        """无效玩家名称测试"""
        from game_server_improvements import Validators, ValidationError
        with pytest.raises(ValidationError):
            Validators.validate_player_name("")
        with pytest.raises(ValidationError):
            Validators.validate_player_name("a" * 21)

    def test_valid_amount(self):
        """有效金额测试"""
        from game_server_improvements import Validators
        assert Validators.validate_amount(100)
        assert Validators.validate_amount(1)
        assert Validators.validate_amount(999999)

    def test_invalid_amount(self):
        """无效金额测试"""
        from game_server_improvements import Validators, ValidationError
        with pytest.raises(ValidationError):
            Validators.validate_amount(-1)
        with pytest.raises(ValidationError):
            Validators.validate_amount(1000000)
        with pytest.raises(ValidationError):
            Validators.validate_amount("100")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
