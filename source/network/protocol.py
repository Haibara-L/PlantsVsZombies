__author__ = 'yuanyu'

"""通信协议定义 - 消息类型 dataclass + JSON 序列化/反序列化

客户端 → 服务器消息:
    join_room, ready, place_plant, spawn_zombie, collect_sun, ping

服务器 → 客户端消息:
    role_assigned, game_start, state_sync, state_delta,
    action_result, game_over, pong, error
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


# ========== 消息类型常量 ==========

# 客户端 → 服务器
C2S_JOIN_ROOM = 'join_room'
C2S_READY = 'ready'
C2S_PLACE_PLANT = 'place_plant'
C2S_SPAWN_ZOMBIE = 'spawn_zombie'
C2S_COLLECT_SUN = 'collect_sun'
C2S_PING = 'ping'

# 服务器 → 客户端
S2C_ROLE_ASSIGNED = 'role_assigned'
S2C_GAME_START = 'game_start'
S2C_STATE_SYNC = 'state_sync'
S2C_STATE_DELTA = 'state_delta'
S2C_ACTION_RESULT = 'action_result'
S2C_GAME_OVER = 'game_over'
S2C_PONG = 'pong'
S2C_ERROR = 'error'
S2C_OPPONENT_READY = 'opponent_ready'
S2C_OPPONENT_DISCONNECTED = 'opponent_disconnected'
S2C_ROOM_INFO = 'room_info'

# 角色
ROLE_PLANTS = 'plants'
ROLE_ZOMBIES = 'zombies'


# ========== 实体状态 dataclass ==========

@dataclass
class PlantState:
    """植物实体（服务端 → 客户端同步）"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    plant_type: str = ''
    grid_x: int = 0
    grid_y: int = 0
    health: int = 0
    state: str = 'idle'
    pixel_x: float = 0.0
    pixel_y: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class ZombieState:
    """僵尸实体（服务端 → 客户端同步）"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    zombie_type: str = ''
    pixel_x: float = 0.0
    pixel_y: float = 0.0
    lane: int = 0
    health: int = 0
    state: str = 'walk'
    is_hypno: bool = False
    has_helmet: bool = False
    speed: float = 0.0

    def to_dict(self):
        return asdict()


@dataclass
class BulletState:
    """子弹实体（服务端 → 客户端同步）"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    bullet_type: str = ''
    pixel_x: float = 0.0
    pixel_y: float = 0.0
    lane: int = 0
    state: str = 'fly'

    def to_dict(self):
        return asdict()


@dataclass
class SunState:
    """阳光实体（服务端 → 客户端同步）"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    pixel_x: float = 0.0
    pixel_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    sun_value: int = 25
    state: str = 'falling'

    def to_dict(self):
        return asdict()


@dataclass
class CooldownInfo:
    """冷却信息"""
    current_time: float = 0.0
    frozen_time: float = 0.0
    total_frozen_time: float = 0.0

    def to_dict(self):
        return asdict()


@dataclass
class ZombiePlayerResources:
    """僵尸玩家资源"""
    brain_points: int = 50
    cooldowns: Dict[str, CooldownInfo] = field(default_factory=dict)

    def to_dict(self):
        return {
            'brain_points': self.brain_points,
            'cooldowns': {k: v.to_dict() for k, v in self.cooldowns.items()}
        }


@dataclass
class GameStateSnapshot:
    """完整游戏状态快照"""
    tick: int = 0
    sun_value: int = 150
    plants: List[PlantState] = field(default_factory=list)
    zombies: List[ZombieState] = field(default_factory=list)
    bullets: List[BulletState] = field(default_factory=list)
    suns: List[SunState] = field(default_factory=list)
    cars: List[bool] = field(default_factory=list)  # 每行是否有车
    zombie_resources: ZombiePlayerResources = field(default_factory=ZombiePlayerResources)
    game_time: float = 0.0

    def to_dict(self):
        return {
            'tick': self.tick,
            'sun_value': self.sun_value,
            'plants': [p.to_dict() for p in self.plants],
            'zombies': [z.to_dict() for z in self.zombies],
            'bullets': [b.to_dict() for b in self.bullets],
            'suns': [s.to_dict() for s in self.suns],
            'cars': self.cars,
            'zombie_resources': self.zombie_resources.to_dict(),
            'game_time': self.game_time,
        }


# ========== 消息编码/解码 ==========

def encode_message(msg_type: str, data: dict) -> str:
    """将消息编码为 JSON 字符串"""
    msg = {'type': msg_type, 'data': data}
    return json.dumps(msg)


def decode_message(raw: str):
    """将 JSON 字符串解码为 (msg_type, data)"""
    msg = json.loads(raw)
    return msg.get('type'), msg.get('data', {})


# ========== 快捷消息构建函数 ==========

def build_action_place_plant(plant_type: str, grid_x: int, grid_y: int) -> str:
    return encode_message(C2S_PLACE_PLANT, {
        'plant_type': plant_type,
        'grid_x': grid_x,
        'grid_y': grid_y,
    })


def build_action_spawn_zombie(zombie_type: str, lane: int) -> str:
    return encode_message(C2S_SPAWN_ZOMBIE, {
        'zombie_type': zombie_type,
        'lane': lane,
    })


def build_action_collect_sun(sun_id: str) -> str:
    return encode_message(C2S_COLLECT_SUN, {'sun_id': sun_id})


def build_join_room(room_id: str) -> str:
    return encode_message(C2S_JOIN_ROOM, {'room_id': room_id})


def build_ready() -> str:
    return encode_message(C2S_READY, {})


def build_ping(client_time: float) -> str:
    return encode_message(C2S_PING, {'client_time': client_time})
