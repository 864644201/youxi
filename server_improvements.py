"""
游戏服务器 - 改进的错误处理和验证
"""
import logging
from enum import Enum
from typing import Optional, Dict, Any

# ============ 日志配置 ============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============ 自定义异常 ============

class GameError(Exception):
    """游戏错误基类"""
    def __init__(self, code: str, message: str, details: Dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict:
        return {
            "type": "error",
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(GameError):
    """验证错误"""
    def __init__(self, message: str, field: str = None):
        super().__init__("VALIDATION_ERROR", message, {"field": field})


class GameStateError(GameError):
    """游戏状态错误"""
    def __init__(self, message: str):
        super().__init__("STATE_ERROR", message)


class AuthenticationError(GameError):
    """认证错误"""
    def __init__(self, message: str = "认证失败"):
        super().__init__("AUTH_ERROR", message)


class PermissionError(GameError):
    """权限错误"""
    def __init__(self, message: str = "权限不足"):
        super().__init__("PERMISSION_ERROR", message)


# ============ 验证器 ============

class Validators:
    """输入验证器"""

    @staticmethod
    def validate_player_name(name: str) -> bool:
        """验证玩家名称"""
        if not isinstance(name, str):
            raise ValidationError("玩家名称必须是字符串", "name")
        if not name or len(name) > 20:
            raise ValidationError("玩家名称长度必须在1-20之间", "name")
        if not all(c.isalnum() or c in '_-' or '一' <= c <= '鿿' for c in name):
            raise ValidationError("玩家名称只能包含字母、数字、下划线、中文", "name")
        return True

    @staticmethod
    def validate_amount(amount: Any, min_val: int = 0, max_val: int = 999999) -> bool:
        """验证金额"""
        if not isinstance(amount, int):
            raise ValidationError("金额必须是整数", "amount")
        if amount < min_val or amount > max_val:
            raise ValidationError(f"金额必须在{min_val}-{max_val}之间", "amount")
        return True

    @staticmethod
    def validate_room_id(room_id: str) -> bool:
        """验证房间ID"""
        if not isinstance(room_id, str):
            raise ValidationError("房间ID必须是字符串", "room_id")
        if not room_id or len(room_id) < 6:
            raise ValidationError("房间ID无效", "room_id")
        return True

    @staticmethod
    def validate_message(message: str) -> bool:
        """验证聊天消息"""
        if not isinstance(message, str):
            raise ValidationError("消息必须是字符串", "message")
        if not message or len(message) > 200:
            raise ValidationError("消息长度必须在1-200之间", "message")
        return True


# ============ 错误响应格式 ============

class ErrorResponse:
    """统一的错误响应"""

    @staticmethod
    def from_error(error: GameError) -> Dict:
        """从异常生成错误响应"""
        return {
            "type": "error",
            "code": error.code,
            "message": error.message,
            "details": error.details,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def validation_error(message: str, field: str = None) -> Dict:
        """验证错误响应"""
        return ErrorResponse.from_error(ValidationError(message, field))

    @staticmethod
    def state_error(message: str) -> Dict:
        """状态错误响应"""
        return ErrorResponse.from_error(GameStateError(message))

    @staticmethod
    def auth_error(message: str = "认证失败") -> Dict:
        """认证错误响应"""
        return ErrorResponse.from_error(AuthenticationError(message))

    @staticmethod
    def permission_error(message: str = "权限不足") -> Dict:
        """权限错误响应"""
        return ErrorResponse.from_error(PermissionError(message))


# ============ 操作日志 ============

class OperationLogger:
    """操作日志记录"""

    @staticmethod
    def log_action(
        room_id: str,
        player_name: str,
        action: str,
        result: str = "success",
        details: Dict = None
    ):
        """记录玩家操作"""
        log_data = {
            "room_id": room_id,
            "player": player_name,
            "action": action,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }

        if result == "success":
            logger.info(f"Action: {action} by {player_name} in {room_id}", extra=log_data)
        else:
            logger.warning(f"Action failed: {action} by {player_name} in {room_id}", extra=log_data)

    @staticmethod
    def log_error(
        room_id: str,
        player_name: str,
        action: str,
        error: Exception
    ):
        """记录错误"""
        logger.error(
            f"Error in {action} by {player_name} in {room_id}: {str(error)}",
            extra={
                "room_id": room_id,
                "player": player_name,
                "action": action,
                "error": str(error),
                "error_type": type(error).__name__
            }
        )


# ============ 权限检查 ============

class PermissionChecker:
    """权限检查器"""

    @staticmethod
    def check_player_in_room(room, player_name: str) -> bool:
        """检查玩家是否在房间中"""
        if not any(p["name"] == player_name for p in room.players):
            raise PermissionError("玩家不在房间中")
        return True

    @staticmethod
    def check_is_host(room, player_name: str) -> bool:
        """检查是否是房主"""
        if room.host_name != player_name:
            raise PermissionError("只有房主可以执行此操作")
        return True

    @staticmethod
    def check_is_current_player(room, player_name: str) -> bool:
        """检查是否是当前玩家"""
        if not hasattr(room, 'current_player') or room.current_player != player_name:
            raise PermissionError("不是你的操作")
        return True

    @staticmethod
    def check_player_alive(room, player_name: str) -> bool:
        """检查玩家是否还活着"""
        player = next((p for p in room.players if p["name"] == player_name), None)
        if not player or not player.get("alive", True):
            raise PermissionError("玩家已破产或已离开游戏")
        return True

    @staticmethod
    def check_sufficient_cash(room, player_name: str, amount: int) -> bool:
        """检查玩家是否有足够的现金"""
        cash = room.player_cash.get(player_name, 0)
        if cash < amount:
            raise ValidationError(f"现金不足，需要${amount}，但只有${cash}", "amount")
        return True


# ============ 使用示例 ============

"""
在 WebSocket 处理器中使用：

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ws_id = str(uuid.uuid4())
    await websocket.accept()

    try:
        async for message in websocket.iter_text():
            try:
                msg = json.loads(message)
                action = msg.get("action")

                # 验证输入
                if action == "bid_auction":
                    Validators.validate_amount(msg.get("amount", 0))

                # 检查权限
                conn = connections.get(ws_id)
                room = rooms.get(conn["room"])
                PermissionChecker.check_player_in_room(room, conn["name"])

                # 执行操作
                result = room.bid_auction(conn["name"], msg.get("amount"))

                if result.get("ok"):
                    await broadcast_room(conn["room"])
                    OperationLogger.log_action(
                        conn["room"],
                        conn["name"],
                        "bid_auction",
                        "success",
                        {"amount": msg.get("amount")}
                    )
                else:
                    error_msg = result.get("error", "操作失败")
                    await websocket.send_json({
                        "type": "error",
                        "code": "OPERATION_FAILED",
                        "message": error_msg
                    })
                    OperationLogger.log_action(
                        conn["room"],
                        conn["name"],
                        "bid_auction",
                        "failed",
                        {"error": error_msg}
                    )

            except ValidationError as e:
                await websocket.send_json(ErrorResponse.from_error(e))
                OperationLogger.log_error(conn["room"], conn["name"], action, e)
            except PermissionError as e:
                await websocket.send_json(ErrorResponse.from_error(e))
                OperationLogger.log_error(conn["room"], conn["name"], action, e)
            except GameError as e:
                await websocket.send_json(ErrorResponse.from_error(e))
                OperationLogger.log_error(conn["room"], conn["name"], action, e)
            except Exception as e:
                logger.exception(f"Unexpected error in {action}")
                await websocket.send_json({
                    "type": "error",
                    "code": "INTERNAL_ERROR",
                    "message": "发生内部错误"
                })

    except WebSocketDisconnect:
        # 处理断开连接
        pass
    except Exception as e:
        logger.exception("WebSocket error")
"""
