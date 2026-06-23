__author__ = 'yuanyu'

"""无头游戏引擎 — 纯 Python 游戏逻辑模拟，不依赖 Pygame

在服务器端运行，复刻单机版所有核心玩法。
使用 dataclass 代替 pygame.sprite.Sprite，
使用手动距离计算代替 pygame 碰撞检测。
"""

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

# 安全导入常量（constants.py 不依赖 pygame）
from .. import constants as c


# ========== 实体 ID 生成 ==========

def _new_id():
    return str(uuid.uuid4())[:8]


# ========== 服务端实体 dataclass ==========

@dataclass
class Entity:
    """所有实体的基类"""
    id: str = field(default_factory=_new_id)
    pixel_x: float = 0.0
    pixel_y: float = 0.0
    health: int = 0
    state: str = c.IDLE
    alive: bool = True


@dataclass
class PlantEntity(Entity):
    """植物实体（服务端模拟）"""
    plant_type: str = ''
    grid_x: int = 0
    grid_y: int = 0
    health: int = c.PLANT_HEALTH
    state: str = c.IDLE
    can_sleep: bool = False
    is_sleeping: bool = False

    # 攻击计时
    shoot_timer: float = 0.0
    shoot_interval: float = 2000.0
    attack_timer: float = 0.0
    attack_interval: float = 2000.0
    digest_timer: float = 0.0
    digest_interval: float = 15000.0
    sun_timer: float = 0.0
    animate_timer: float = 0.0
    hit_timer: float = 0.0

    # 特殊状态
    is_cracked1: bool = False
    is_cracked2: bool = False
    is_init: bool = True       # PotatoMine 初始化
    is_big: bool = False       # SunShroom 长大
    is_aiming: bool = False    # Squash 瞄准
    is_squashing: bool = False # Squash 压扁
    start_boom: bool = False   # CherryBomb 爆炸
    start_freeze: bool = False # IceShroom 冰冻
    start_explode: bool = False # Jalapeno 燃烧

    # 特殊目标
    attack_zombie_id: Optional[str] = None  # Chomper/Squash 攻击目标
    digest_zombie_id: Optional[str] = None  # Chomper 消化目标
    kill_zombie_id: Optional[str] = None    # HypnoShroom 被吃时记录的僵尸

    def to_state_dict(self):
        """转为客户端渲染用的 PlantState dict"""
        return {
            'id': self.id,
            'plant_type': self.plant_type,
            'grid_x': self.grid_x,
            'grid_y': self.grid_y,
            'health': self.health,
            'state': self.state,
            'pixel_x': self.pixel_x,
            'pixel_y': self.pixel_y,
        }


@dataclass
class ZombieEntity(Entity):
    """僵尸实体（服务端模拟）"""
    zombie_type: str = ''
    lane: int = 0
    health: int = c.NORMAL_HEALTH
    max_health: int = c.NORMAL_HEALTH
    state: str = c.WALK
    speed: float = 1.0
    damage: int = 1

    # 计时器
    walk_timer: float = 0.0
    attack_timer: float = 0.0
    animate_timer: float = 0.0
    hit_timer: float = 0.0
    freeze_timer: float = 0.0

    # 状态
    is_hypno: bool = False
    los_head: bool = False
    has_helmet: bool = False
    ice_slow_ratio: float = 1.0
    ice_slow_timer: float = 0.0
    dead: bool = False

    # 攻击目标
    prey_id: Optional[str] = None
    prey_is_plant: bool = True

    # Newspaper zombie speed boost after losing paper
    lost_helmet_speed_boost: bool = False

    def to_state_dict(self):
        """Build zombie state dict for client rendering."""
        return {
            'id': self.id,
            'zombie_type': self.zombie_type,
            'pixel_x': self.pixel_x,
            'pixel_y': self.pixel_y,
            'lane': self.lane,
            'health': self.health,
            'state': self.state,
            'is_hypno': self.is_hypno,
            'has_helmet': self.has_helmet,
            'speed': self.speed,
            'boom_die': getattr(self, '_boom_die', False),
        }


@dataclass
class BulletEntity(Entity):
    """子弹实体（服务端模拟）"""
    bullet_type: str = ''
    lane: int = 0
    dest_y: float = 0.0
    x_vel: float = 4.0
    y_vel: float = 0.0
    damage: int = c.BULLET_DAMAGE_NORMAL
    ice: bool = False
    state: str = c.FLY
    explode_timer: float = 0.0

    def to_state_dict(self):
        return {
            'id': self.id,
            'bullet_type': self.bullet_type,
            'pixel_x': self.pixel_x,
            'pixel_y': self.pixel_y,
            'lane': self.lane,
            'state': self.state,
        }


@dataclass
class SunEntity(Entity):
    """阳光实体（服务端模拟）"""
    target_x: float = 0.0
    target_y: float = 0.0
    sun_value: int = c.SUN_VALUE
    move_speed: float = 1.0
    state: str = 'falling'
    die_timer: float = 0.0
    spawn_time: float = 0.0

    def to_state_dict(self):
        return {
            'id': self.id,
            'pixel_x': self.pixel_x,
            'pixel_y': self.pixel_y,
            'target_x': self.target_x,
            'target_y': self.target_y,
            'sun_value': self.sun_value,
            'state': self.state,
        }


@dataclass
class CarEntity(Entity):
    """Car entity (server-side)."""
    lane: int = 0
    state: str = c.IDLE
    dead: bool = False

    def to_state_dict(self):
        return {'alive': self.alive, 'state': self.state,
                'triggered': getattr(self, '_triggered', False)}


# ========== Zombie player resources ==========

ZOMBIE_CARD_CONFIG = {
    c.NORMAL_ZOMBIE:    {'brain_cost': 25,  'cooldown': 7500},
    c.FLAG_ZOMBIE:      {'brain_cost': 50,  'cooldown': 15000},
    c.CONEHEAD_ZOMBIE:  {'brain_cost': 75,  'cooldown': 20000},
    c.BUCKETHEAD_ZOMBIE:{'brain_cost': 125, 'cooldown': 30000},
    c.NEWSPAPER_ZOMBIE: {'brain_cost': 100, 'cooldown': 25000},
}

ZOMBIE_HEALTH_MAP = {
    c.NORMAL_ZOMBIE:    c.NORMAL_HEALTH,
    c.FLAG_ZOMBIE:      c.FLAG_HEALTH,
    c.CONEHEAD_ZOMBIE:  c.CONEHEAD_HEALTH,
    c.BUCKETHEAD_ZOMBIE: c.BUCKETHEAD_HEALTH,
    c.NEWSPAPER_ZOMBIE: c.NEWSPAPER_HEALTH,
}


# ========== 坐标工具函数 ==========

def getMapIndex(pixel_x, pixel_y):
    """像素坐标 → 网格坐标"""
    x = pixel_x - c.MAP_OFFSET_X
    y = pixel_y - c.MAP_OFFSET_Y
    return (int(x // c.GRID_X_SIZE), int(y // c.GRID_Y_SIZE))


def getMapGridPos(map_x, map_y):
    """网格坐标 → 像素中心坐标"""
    return (map_x * c.GRID_X_SIZE + c.GRID_X_SIZE // 2 + c.MAP_OFFSET_X,
            map_y * c.GRID_Y_SIZE + c.GRID_Y_SIZE // 5 * 3 + c.MAP_OFFSET_Y)


def isValidGrid(map_x, map_y):
    """检查网格坐标是否有效"""
    return 0 <= map_x < c.GRID_X_LEN and 0 <= map_y < c.GRID_Y_LEN


# ========== 碰撞检测（替代 pygame spritecollide） ==========

def _circle_distance(e1, e2):
    """两个实体中心点的欧几里得距离"""
    return math.sqrt((e1.pixel_x - e2.pixel_x) ** 2 + (e1.pixel_y - e2.pixel_y) ** 2)


def _rects_overlap(e1, e2, ratio=0.7):
    """简化的碰撞检测：使用实体位置和估算的矩形大小判断是否重叠"""
    w1, h1 = c.GRID_X_SIZE * ratio, c.GRID_Y_SIZE * ratio
    w2, h2 = c.GRID_X_SIZE * ratio, c.GRID_Y_SIZE * ratio
    return abs(e1.pixel_x - e2.pixel_x) < (w1 + w2) / 2 and \
           abs(e1.pixel_y - e2.pixel_y) < (h1 + h2) / 2


def _bullet_hit_zombie(bullet, zombie):
    """子弹是否命中僵尸"""
    return abs(bullet.pixel_x - zombie.pixel_x) < 40 and \
           abs(bullet.pixel_y - zombie.pixel_y) < 50


def _zombie_hit_plant(zombie, plant, ratio=0.7):
    """僵尸是否碰到植物"""
    w = c.GRID_X_SIZE * ratio
    h = c.GRID_Y_SIZE * ratio
    return abs(zombie.pixel_x - plant.pixel_x) < w and \
           abs(zombie.pixel_y - plant.pixel_y) < h


def _car_hit_zombie(car, zombie):
    """Is the car close enough to a zombie?"""
    return abs(car.pixel_x - zombie.pixel_x) < 100 and \
           abs(car.pixel_y - zombie.pixel_y) < 100


# ========== 游戏模拟器 ==========

class GameState:
    """游戏状态容器"""

    def __init__(self):
        self.tick = 0
        self.game_time = 0.0
        self.sun_value = 150
        self.state = 'waiting'  # waiting | playing | finished

        # 实体列表
        self.plants: List[PlantEntity] = []
        self.zombies: List[ZombieEntity] = []
        self.bullets: List[BulletEntity] = []
        self.suns: List[SunEntity] = []
        self.cars: List[CarEntity] = []

        # Grid occupancy
        self.grid = [[c.MAP_EMPTY for _ in range(c.GRID_X_LEN)] for _ in range(c.GRID_Y_LEN)]

        # Plant player
        self.sun_timer = 0.0
        self.plant_cooldowns: Dict[str, float] = {}  # plant_type -> frozen_until

        # Zombie player
        self.brain_points = 50
        self.brain_timer = 0.0
        self.zombie_cooldowns: Dict[str, float] = {}  # zombie_type -> frozen_until

        # Match end
        self.winner: Optional[str] = None
        self.match_duration = 5 * 60 * 1000  # 5 minutes (milliseconds)

    def get_snapshot(self):
        """Build a state snapshot dict for clients."""
        from .protocol import CooldownInfo, ZombiePlayerResources

        cooldowns = {}
        now = self.game_time
        for ztype, frozen_until in self.zombie_cooldowns.items():
            cfg = ZOMBIE_CARD_CONFIG.get(ztype, {})
            total = cfg.get('cooldown', 7500)
            cooldowns[ztype] = {
                'current_time': now,
                'frozen_time': max(0, frozen_until - now),
                'total_frozen_time': total,
            }

        return {
            'tick': self.tick,
            'sun_value': self.sun_value,
            'plants': [p.to_state_dict() for p in self.plants if p.alive],
            'zombies': [z.to_state_dict() for z in self.zombies if z.alive],
            'bullets': [b.to_state_dict() for b in self.bullets if b.alive],
            'suns': [s.to_state_dict() for s in self.suns if s.alive],
            'cars': [c.alive for c in self.cars],
            'zombie_resources': {
                'brain_points': self.brain_points,
                'cooldowns': cooldowns,
            },
            'game_time': self.game_time,
        }


class Simulator:
    """权威游戏模拟器 — 每个 tick 推进游戏逻辑一步"""

    def __init__(self, is_day=True):
        self.state = GameState()
        self.is_day = is_day

        # Initialize cars (one per row) with correct pixel positions
        for lane in range(c.GRID_Y_LEN):
            _, y = getMapGridPos(0, lane)
            car = CarEntity(
                pixel_x=-25,
                pixel_y=y + 20,
                lane=lane,
                alive=True,
            )
            self.state.cars.append(car)

        # Initialize grid: mark columns 0-7 as empty (so the
        # rightmost column 8 is free for zombies to pass through).
        for y in range(c.GRID_Y_LEN):
            for x in range(c.GRID_X_LEN):
                self.state.grid[y][x] = c.MAP_EMPTY

    # ===== 植物操作 =====

    def place_plant(self, plant_type, grid_x, grid_y,
                    plant_sun_cost=0, plant_frozen_time=7500):
        """Place a plant. Returns (success, error_message)."""
        if not isValidGrid(grid_x, grid_y):
            return False, "Invalid grid position"

        if self.state.grid[grid_y][grid_x] == c.MAP_EXIST:
            return False, "Position already occupied"

        if self.state.sun_value < plant_sun_cost:
            return False, "Not enough sun"

        now = self.state.game_time
        frozen_until = self.state.plant_cooldowns.get(plant_type, 0)
        if now < frozen_until:
            return False, "On cooldown"

        pixel_x, pixel_y = getMapGridPos(grid_x, grid_y)
        plant = self._create_plant(plant_type, grid_x, grid_y, pixel_x, pixel_y)

        if plant is None:
            return False, f"Unknown plant type: {plant_type}"

        self.state.sun_value -= plant_sun_cost
        self.state.plant_cooldowns[plant_type] = now + plant_frozen_time
        self.state.grid[grid_y][grid_x] = c.MAP_EXIST
        self.state.plants.append(plant)

        return True, None

    def _create_plant(self, plant_type, grid_x, grid_y, pixel_x, pixel_y):
        """Create a plant entity — mirrors single-player Plant.__init__."""
        p = PlantEntity(
            plant_type=plant_type,
            grid_x=grid_x,
            grid_y=grid_y,
            pixel_x=pixel_x,
            pixel_y=pixel_y,
        )

        if plant_type == c.SUNFLOWER:
            p.health = c.PLANT_HEALTH
            p.sun_timer = self.state.game_time - (c.FLOWER_SUN_INTERVAL - 6000)
        elif plant_type == c.PEASHOOTER:
            p.health = c.PLANT_HEALTH
            p.shoot_interval = 2000.0
        elif plant_type == c.SNOWPEASHOOTER:
            p.health = c.PLANT_HEALTH
            p.shoot_interval = 2000.0
        elif plant_type == c.WALLNUT:
            p.health = c.WALLNUT_HEALTH
        elif plant_type == c.CHERRYBOMB:
            p.health = c.WALLNUT_HEALTH
            p.state = c.ATTACK
            # Timer for CherryBomb stages:
            # _update_cherry_bomb checks animate_timer==0 as "just created"
            # It will be set on the first tick through the update loop.
            p.animate_timer = 0
        elif plant_type == c.THREEPEASHOOTER:
            p.health = c.PLANT_HEALTH
            p.shoot_interval = 2000.0
        elif plant_type == c.REPEATERPEA:
            p.health = c.PLANT_HEALTH
            p.shoot_interval = 2000.0
        elif plant_type == c.CHOMPER:
            p.health = c.PLANT_HEALTH
            p.digest_interval = 15000.0
        elif plant_type == c.PUFFSHROOM:
            p.health = c.PLANT_HEALTH
            p.can_sleep = True
            p.shoot_interval = 3000.0
        elif plant_type == c.POTATOMINE:
            p.health = c.PLANT_HEALTH
            p.is_init = True
        elif plant_type == c.SQUASH:
            p.health = c.PLANT_HEALTH
        elif plant_type == c.SPIKEWEED:
            p.health = c.PLANT_HEALTH
            p.attack_interval = 2000.0
        elif plant_type == c.JALAPENO:
            p.health = c.PLANT_HEALTH
            p.state = c.ATTACK
            p.animate_timer = self.state.game_time
        elif plant_type == c.SCAREDYSHROOM:
            p.health = c.PLANT_HEALTH
            p.can_sleep = True
            p.shoot_interval = 2000.0
        elif plant_type == c.SUNSHROOM:
            p.health = c.PLANT_HEALTH
            p.can_sleep = True
            p.sun_timer = self.state.game_time - (c.FLOWER_SUN_INTERVAL - 6000)
        elif plant_type == c.ICESHROOM:
            p.health = c.PLANT_HEALTH
            p.can_sleep = True
        elif plant_type == c.HYPNOSHROOM:
            p.health = 1
            p.can_sleep = True
        else:
            return None

        # Night mushrooms sleep during day
        if p.can_sleep and self.is_day:
            p.is_sleeping = True
            p.state = c.SLEEP

        return p

    def collect_sun(self, sun_id):
        """Collect a sun. Returns (success, sun_value)."""
        for sun in self.state.suns:
            if sun.id == sun_id and sun.alive:
                sun.alive = False
                self.state.sun_value += sun.sun_value
                return True, sun.sun_value
        return False, 0

    # ===== 僵尸操作 =====

    def spawn_zombie(self, zombie_type, lane):
        """Spawn a zombie. Returns (success, error_message)."""
        if not 0 <= lane < c.GRID_Y_LEN:
            return False, "Invalid lane"

        cfg = ZOMBIE_CARD_CONFIG.get(zombie_type)
        if cfg is None:
            return False, f"Unknown zombie type: {zombie_type}"

        if self.state.brain_points < cfg['brain_cost']:
            return False, "Not enough brain points"

        now = self.state.game_time
        frozen_until = self.state.zombie_cooldowns.get(zombie_type, 0)
        if now < frozen_until:
            return False, "On cooldown"

        _, y = getMapGridPos(0, lane)
        health = ZOMBIE_HEALTH_MAP.get(zombie_type, c.NORMAL_HEALTH)
        zombie = ZombieEntity(
            zombie_type=zombie_type,
            lane=lane,
            pixel_x=c.ZOMBIE_START_X,
            pixel_y=y,
            health=health,
            max_health=health,
        )

        if zombie_type in (c.CONEHEAD_ZOMBIE, c.BUCKETHEAD_ZOMBIE, c.NEWSPAPER_ZOMBIE):
            zombie.has_helmet = True

        self.state.brain_points -= cfg['brain_cost']
        self.state.zombie_cooldowns[zombie_type] = now + cfg['cooldown']
        self.state.zombies.append(zombie)

        return True, None

    # ===== 主 Tick 循环 =====

    def tick(self, delta_ms):
        """Advance game logic — mirrors single-player Level.play() order."""
        dt = delta_ms
        self.state.tick += 1
        self.state.game_time += dt

        if self.state.state != 'playing':
            return

        self._update_suns(dt)
        self._update_plants(dt)
        self._update_zombies(dt)
        self._update_bullets(dt)
        self._update_cars(dt)
        self._update_brain_points(dt)
        # Single-player order: bullets -> zombies -> plants -> cars
        self._check_bullet_zombie_collisions()
        self._check_zombie_plant_collisions()
        self._check_plant_special_attacks()
        self._check_car_zombie_collisions()
        self._cleanup_dead()
        self._check_game_over()

    def _update_suns(self, dt):
        """Update sun entities — natural production + movement."""
        now = self.state.game_time

        # Natural sun production (daytime)
        if self.is_day:
            if now - self.state.sun_timer > c.PRODUCE_SUN_INTERVAL:
                self.state.sun_timer = now
                map_x = random.randint(0, c.GRID_X_LEN - 1)
                map_y = random.randint(0, c.GRID_Y_LEN - 1)
                x, y = getMapGridPos(map_x, map_y)
                sun = SunEntity(
                    pixel_x=x,
                    pixel_y=0,
                    target_x=x,
                    target_y=y,
                    sun_value=c.SUN_VALUE,
                    spawn_time=now,
                )
                self.state.suns.append(sun)

        # Update existing suns — drift toward target, then expire
        for sun in self.state.suns:
            if not sun.alive:
                continue
            # Move to target
            if sun.pixel_x != sun.target_x:
                sun.pixel_x += sun.move_speed if sun.pixel_x < sun.target_x else -sun.move_speed
                if abs(sun.pixel_x - sun.target_x) < sun.move_speed:
                    sun.pixel_x = sun.target_x
            if sun.pixel_y != sun.target_y:
                sun.pixel_y += sun.move_speed if sun.pixel_y < sun.target_y else -sun.move_speed
                if abs(sun.pixel_y - sun.target_y) < sun.move_speed:
                    sun.pixel_y = sun.target_y
            # Expire after sitting at target
            if sun.pixel_x == sun.target_x and sun.pixel_y == sun.target_y:
                if sun.die_timer == 0:
                    sun.die_timer = now
                elif now - sun.die_timer > c.SUN_LIVE_TIME:
                    sun.alive = False

    def _update_plants(self, dt):
        """Update all plants — ported from single-player level.py checkPlants()"""
        now = self.state.game_time

        for plant in self.state.plants:
            if not plant.alive:
                continue

            if plant.is_sleeping:
                continue

            # ---- tick timers for special plants ----
            if plant.plant_type == c.CHERRYBOMB:
                self._update_cherry_bomb(plant, now)
            elif plant.plant_type == c.POTATOMINE:
                self._update_potato_mine(plant, now)
            elif plant.plant_type == c.JALAPENO:
                self._update_jalapeno(plant, now)
            elif plant.plant_type == c.ICESHROOM:
                self._update_ice_shroom(plant, now)
            elif plant.plant_type == c.SQUASH:
                self._update_squash(plant, now)
            elif plant.plant_type == c.CHOMPER:
                self._update_chomper(plant, now)
            elif plant.plant_type == c.SUNFLOWER:
                self._update_sunflower(plant, now)
            elif plant.plant_type == c.SUNSHROOM:
                self._update_sunshroom(plant, now)
            elif plant.plant_type == c.WALLNUT:
                self._update_wallnut(plant)
            elif plant.plant_type == c.SPIKEWEED:
                self._update_spikeweed(plant, now)
            elif plant.plant_type == c.SCAREDYSHROOM:
                self._update_scaredyshroom(plant, now)
            else:
                self._update_shooter(plant, now)

    def _update_cherry_bomb(self, plant, now):
        """Cherry bomb: ~1.5s idle then 0.5s boom then explode + die.
        The explosion must be applied HERE because the plant will be
        cleaned up before _check_plant_special_attacks runs again."""
        if not plant.start_boom:
            if plant.animate_timer == 0:
                plant.animate_timer = now
            elif now - plant.animate_timer >= 1500:
                plant.start_boom = True
                plant.animate_timer = now
        else:
            if now - plant.animate_timer >= 500:
                # Boom! Explode now, then die.
                self._apply_explosion(plant)
                plant.health = 0
                plant.alive = False

    def _update_potato_mine(self, plant, now):
        """PotatoMine: arm for 15s, then wait for zombie to explode."""
        if plant.is_init:
            if plant.animate_timer == 0:
                plant.animate_timer = now
            elif now - plant.animate_timer > 15000:
                plant.is_init = False
        elif plant.state == c.ATTACK:
            if now - plant.attack_timer > 500:
                self._apply_explosion(plant)
                plant.health = 0
                plant.alive = False

    def _update_jalapeno(self, plant, now):
        """Jalapeno: play animation then explode entire row."""
        if plant.start_explode:
            if now - plant.animate_timer > 1200:
                self._apply_explosion(plant)
                plant.health = 0
                plant.alive = False
        else:
            plant.start_explode = True
            plant.animate_timer = now

    def _update_ice_shroom(self, plant, now):
        """Ice-shroom: freeze all zombies on screen."""
        if plant.start_freeze:
            if now - plant.animate_timer > 2000:
                plant.health = 0
        else:
            # First frame — trigger freeze immediately
            plant.start_freeze = True
            plant.animate_timer = now

    def _update_squash(self, plant, now):
        """Squash: aim 1s then squish zombie."""
        if plant.is_squashing:
            if now - plant.attack_timer > 1200:
                if plant.attack_zombie_id:
                    self._kill_zombie_by_id(plant.attack_zombie_id)
                plant.health = 0
                plant.alive = False
        elif plant.is_aiming:
            if now - plant.animate_timer > 1000:
                plant.is_squashing = True
                plant.attack_timer = now

    def _update_chomper(self, plant, now):
        """Chomper: attack first, then eat zombie then digest for 15s."""
        # 如果是攻击状态，给它 1 秒钟（1000毫秒）的时间让客户端把吞噬动画播完
        if plant.state == c.ATTACK:
            if now - plant.digest_timer > 1000: # 1秒后进入消化状态
                plant.state = c.DIGEST
                plant.digest_timer = now # 重新计时消化时间
                
        elif plant.state == c.DIGEST:
            if now - plant.digest_timer > plant.digest_interval:
                if plant.digest_zombie_id:
                    self._kill_zombie_by_id(plant.digest_zombie_id)
                plant.digest_zombie_id = None
                plant.state = c.IDLE

    def _update_sunflower(self, plant, now):
        """Sunflower: produce sun periodically."""
        if plant.sun_timer == 0:
            plant.sun_timer = now - (c.FLOWER_SUN_INTERVAL - 6000)
        elif now - plant.sun_timer > c.FLOWER_SUN_INTERVAL:
            plant.sun_timer = now
            sun = SunEntity(
                pixel_x=plant.pixel_x,
                pixel_y=plant.pixel_y,
                target_x=plant.pixel_x + c.GRID_X_SIZE // 2,
                target_y=plant.pixel_y + c.GRID_Y_SIZE // 4,
                sun_value=c.SUN_VALUE,
                spawn_time=now,
            )
            self.state.suns.append(sun)

    def _update_sunshroom(self, plant, now):
        """Sun-shroom: grows bigger then produces sun."""
        if not plant.is_big:
            if plant.animate_timer == 0:
                plant.animate_timer = now
            elif now - plant.animate_timer > 25000:
                plant.is_big = True
        if plant.sun_timer == 0:
            plant.sun_timer = now - (c.FLOWER_SUN_INTERVAL - 6000)
        elif now - plant.sun_timer > c.FLOWER_SUN_INTERVAL:
            plant.sun_timer = now
            value = c.SUN_VALUE if plant.is_big else 12
            sun = SunEntity(
                pixel_x=plant.pixel_x,
                pixel_y=plant.pixel_y,
                target_x=plant.pixel_x + c.GRID_X_SIZE // 2,
                target_y=plant.pixel_y + c.GRID_Y_SIZE // 4,
                sun_value=value,
                spawn_time=now,
            )
            self.state.suns.append(sun)

    def _update_wallnut(self, plant):
        """Wall-nut: visual crack states based on health."""
        if not plant.is_cracked1 and plant.health <= c.WALLNUT_CRACKED1_HEALTH:
            plant.is_cracked1 = True
        elif not plant.is_cracked2 and plant.health <= c.WALLNUT_CRACKED2_HEALTH:
            plant.is_cracked2 = True

    def _update_spikeweed(self, plant, now):
        """Spikeweed: damages zombies on it every 2s."""
        if plant.state == c.ATTACK:
            if now - plant.attack_timer > plant.attack_interval:
                plant.attack_timer = now
                for zombie in self.state.zombies:
                    if zombie.lane == plant.grid_y and zombie.alive:
                        if abs(zombie.pixel_x - plant.pixel_x) < c.GRID_X_SIZE:
                            zombie.health -= 1

    def _update_scaredyshroom(self, plant, now):
        """Scaredy-shroom: hide when zombie is close, shoot when far."""
        need_cry = False
        can_attack = False
        for zombie in self.state.zombies:
            if zombie.lane == plant.grid_y and zombie.alive and zombie.state != c.DIE:
                dist = zombie.pixel_x - plant.pixel_x
                if 0 <= dist < c.GRID_X_SIZE * 2:
                    need_cry = True
                    break
                elif dist < c.GRID_X_SIZE * 4:
                    can_attack = True
        if need_cry:
            plant.state = c.CRY
        elif can_attack:
            plant.state = c.ATTACK
        else:
            plant.state = c.IDLE

        if plant.state == c.ATTACK:
            if now - plant.shoot_timer > plant.shoot_interval:
                plant.shoot_timer = now
                bullet = BulletEntity(
                    bullet_type=c.BULLET_MUSHROOM,
                    lane=plant.grid_y,
                    pixel_x=plant.pixel_x + c.GRID_X_SIZE // 2,
                    pixel_y=plant.pixel_y + 40,
                    dest_y=plant.pixel_y + 40,
                    damage=c.BULLET_DAMAGE_NORMAL,
                    ice=True,
                )
                self.state.bullets.append(bullet)

    def _update_shooter(self, plant, now):
        """Shooter plants: auto-detect zombies ahead and fire."""
        has_target = False
        for zombie in self.state.zombies:
            if zombie.lane == plant.grid_y and zombie.alive and zombie.state != c.DIE:
                if zombie.pixel_x > plant.pixel_x:
                    has_target = True
                    break

        if has_target:
            if plant.state != c.ATTACK:
                plant.state = c.ATTACK
            if now - plant.shoot_timer > plant.shoot_interval:
                plant.shoot_timer = now
                self._plant_shoot(plant)
        else:
            if plant.state != c.IDLE:
                plant.state = c.IDLE

    def _plant_shoot(self, plant):
        """Create bullet entities for shooter plants."""
        ptype = plant.plant_type
        lane = plant.grid_y

        if ptype == c.PEASHOOTER:
            bullet = BulletEntity(
                bullet_type=c.BULLET_PEA,
                lane=lane,
                pixel_x=plant.pixel_x + c.GRID_X_SIZE // 2,
                # ⚡【已修改】减去 12 像素，让网络豌豆子弹对准嘴巴
                pixel_y=plant.pixel_y - 12,
                dest_y=plant.pixel_y - 12,
                damage=c.BULLET_DAMAGE_NORMAL,
                ice=False,
            )
            self.state.bullets.append(bullet)

        elif ptype == c.SNOWPEASHOOTER:
            bullet = BulletEntity(
                bullet_type=c.BULLET_PEA_ICE,
                lane=lane,
                pixel_x=plant.pixel_x + c.GRID_X_SIZE // 2,
                # ⚡【已修改】寒冰射手同样提升高度
                pixel_y=plant.pixel_y - 12,
                dest_y=plant.pixel_y - 12,
                damage=c.BULLET_DAMAGE_NORMAL,
                ice=True,
            )
            self.state.bullets.append(bullet)

        elif ptype == c.REPEATERPEA:
            for offset in (0, 40):
                bullet = BulletEntity(
                    bullet_type=c.BULLET_PEA,
                    lane=lane,
                    pixel_x=plant.pixel_x + c.GRID_X_SIZE // 2 + offset,
                    # ⚡【已修改】双发射手两颗子弹统一提升高度
                    pixel_y=plant.pixel_y - 12,
                    dest_y=plant.pixel_y - 12,
                    damage=c.BULLET_DAMAGE_NORMAL,
                    ice=False,
                )
                self.state.bullets.append(bullet)

        elif ptype == c.THREEPEASHOOTER:
            for i in range(3):
                tmp_lane = lane + (i - 1)
                if 0 <= tmp_lane < c.GRID_Y_LEN:
                    # ⚡【已修改】三线射手的初始位置和目标终点都需要顺应拔高
                    dest_y = plant.pixel_y + (i - 1) * c.GRID_Y_SIZE + 9 - 12
                    bullet = BulletEntity(
                        bullet_type=c.BULLET_PEA,
                        lane=tmp_lane,
                        pixel_x=plant.pixel_x + c.GRID_X_SIZE // 2,
                        pixel_y=plant.pixel_y - 12,
                        dest_y=dest_y,
                        damage=c.BULLET_DAMAGE_NORMAL,
                        ice=False,
                    )
                    self.state.bullets.append(bullet)

        elif ptype == c.PUFFSHROOM:
            bullet = BulletEntity(
                bullet_type=c.BULLET_MUSHROOM,
                lane=lane,
                pixel_x=plant.pixel_x + c.GRID_X_SIZE // 2,
                # 💡 小喷菇身材特殊，原本+10的设定高度应该是没问题的，这里保持原状
                pixel_y=plant.pixel_y + 10,
                dest_y=plant.pixel_y + 10,
                damage=c.BULLET_DAMAGE_NORMAL,
                ice=True,
            )
            self.state.bullets.append(bullet)

    def _update_zombies(self, dt):
        """Update all zombies — movement, attack damage, freeze/death."""
        now = self.state.game_time

        for zombie in self.state.zombies:
            if not zombie.alive:
                continue

            # Ice slow timer
            if zombie.ice_slow_ratio > 1:
                if now - zombie.ice_slow_timer > c.ICE_SLOW_TIME:
                    zombie.ice_slow_ratio = 1.0

            time_ratio = zombie.ice_slow_ratio

            if zombie.state == c.WALK:
                if now - zombie.walk_timer > c.ZOMBIE_WALK_INTERVAL * time_ratio:
                    zombie.walk_timer = now
                    if zombie.is_hypno:
                        zombie.pixel_x += zombie.speed
                    else:
                        zombie.pixel_x -= zombie.speed

            elif zombie.state == c.ATTACK:
                if zombie.prey_id:
                    prey = self._find_plant_by_id(zombie.prey_id) or \
                           self._find_zombie_by_id(zombie.prey_id)
                    if prey is None or not prey.alive or prey.health <= 0:
                        zombie.prey_id = None
                        zombie.state = c.WALK
                    elif now - zombie.attack_timer > c.ATTACK_INTERVAL * time_ratio:
                        zombie.attack_timer = now
                        prey.health -= zombie.damage

            elif zombie.state == c.FREEZE:
                if now - zombie.freeze_timer > c.FREEZE_TIME:
                    zombie.state = c.WALK

            elif zombie.state == c.DIE:
                pass

            # Lost head check
            if zombie.health <= c.LOSTHEAD_HEALTH and not zombie.los_head:
                zombie.los_head = True

            # Helmet drop
            if zombie.has_helmet and zombie.health <= c.NORMAL_HEALTH:
                zombie.has_helmet = False
                if zombie.zombie_type == c.NEWSPAPER_ZOMBIE:
                    zombie.speed = 2

            # Dead
            if zombie.health <= 0 and zombie.state != c.DIE:
                zombie.state = c.DIE
                zombie.alive = False

    def _update_bullets(self, dt):
        """Update all bullets — movement and explode timer."""
        for bullet in self.state.bullets:
            if not bullet.alive:
                continue

            if bullet.state == c.FLY:
                # Y-axis tracking
                if abs(bullet.pixel_y - bullet.dest_y) > 1:
                    if bullet.y_vel == 0:
                        bullet.y_vel = 4 if bullet.dest_y > bullet.pixel_y else -4
                    bullet.pixel_y += bullet.y_vel
                    if bullet.y_vel * (bullet.dest_y - bullet.pixel_y) < 0:
                        bullet.pixel_y = bullet.dest_y
                bullet.pixel_x += bullet.x_vel
                if bullet.pixel_x > c.SCREEN_WIDTH:
                    bullet.alive = False

            elif bullet.state == c.EXPLODE:
                if self.state.game_time - bullet.explode_timer > 500:
                    bullet.alive = False

    def _update_cars(self, dt):
        """Update cars — move right when walking, die off-screen."""
        for car in self.state.cars:
            if not car.alive:
                continue
            if car.state == c.WALK:
                car.pixel_x += 4
                if car.pixel_x > c.SCREEN_WIDTH + 100:
                    car.alive = False

    def _update_brain_points(self, dt):
        """Zombie player brain point regeneration."""
        now = self.state.game_time
        if now - self.state.brain_timer > 7000:
            self.state.brain_timer = now
            self.state.brain_points = min(300, self.state.brain_points + 25)

    # ===== Collision detection (called explicitly in tick) =====

    def _check_bullet_zombie_collisions(self):
        """Bullet vs zombie — damage and explode."""
        for bullet in self.state.bullets:
            if not bullet.alive or bullet.state != c.FLY:
                continue
            for zombie in self.state.zombies:
                if not zombie.alive or zombie.state == c.DIE:
                    continue
                if bullet.lane == zombie.lane:
                    if _bullet_hit_zombie(bullet, zombie):
                        zombie.health -= bullet.damage
                        if bullet.ice:
                            zombie.ice_slow_ratio = 2.0
                            zombie.ice_slow_timer = self.state.game_time
                        bullet.state = c.EXPLODE
                        bullet.explode_timer = self.state.game_time
                        break

    def _check_zombie_plant_collisions(self):
        """Zombie eats plant — only WALKING zombies can start attacking."""
        for zombie in self.state.zombies:
            if not zombie.alive or zombie.state != c.WALK:
                continue
            for plant in self.state.plants:
                if not plant.alive:
                    continue
                if zombie.lane == plant.grid_y:
                    if _zombie_hit_plant(zombie, plant):
                        if plant.plant_type == c.SPIKEWEED:
                            continue  # Spikeweed doesn't block zombies
                        zombie.state = c.ATTACK
                        zombie.prey_id = plant.id
                        zombie.prey_is_plant = True
                        zombie.attack_timer = self.state.game_time
                        break

        # Hypno zombie attacks normal zombie
        for hypno in self.state.zombies:
            if not hypno.alive or not hypno.is_hypno or hypno.state != c.WALK:
                continue
            for zombie in self.state.zombies:
                if not zombie.alive or zombie.is_hypno or zombie.state == c.DIE:
                    continue
                if hypno.lane == zombie.lane:
                    if _zombie_hit_plant(hypno, zombie, 0.7):
                        hypno.state = c.ATTACK
                        hypno.prey_id = zombie.id
                        hypno.prey_is_plant = False
                        zombie.state = c.ATTACK
                        zombie.prey_id = hypno.id
                        zombie.prey_is_plant = False
                        break

    def _check_car_zombie_collisions(self):
        """Car activates when zombie reaches left edge, then kills zombies it hits.
        Mirrors single-player checkCarCollisions()."""
        for car in self.state.cars:
            if not car.alive:
                continue
            for zombie in self.state.zombies:
                if not zombie.alive or zombie.state == c.DIE:
                    continue
                if car.lane == zombie.lane:
                    if _car_hit_zombie(car, zombie):
                        car.state = c.WALK
                        car._triggered = True
                        zombie.alive = False
                        zombie.state = c.DIE
            if car.state == c.WALK and car.pixel_x > c.SCREEN_WIDTH + 100:
                car.alive = False

    def _check_plant_special_attacks(self):
        """Melee / special plant attacks — matches single-player checkPlant()."""
        now = self.state.game_time

        for plant in self.state.plants:
            if not plant.alive or plant.is_sleeping:
                continue

            # Explosive plants whose health reached 0 — trigger explosion now
            if plant.health <= 0:
                self._apply_explosion(plant)
                plant.alive = False
                continue

            # Ice-shroom freeze
            if plant.plant_type == c.ICESHROOM and plant.start_freeze:
                for zombie in self.state.zombies:
                    if zombie.alive and zombie.pixel_x < c.SCREEN_WIDTH:
                        zombie.state = c.FREEZE
                        zombie.freeze_timer = now

            # Chomper
            # Chomper
            if plant.plant_type == c.CHOMPER:
                if plant.state == c.IDLE:
                    for zombie in self.state.zombies:
                        if zombie.lane == plant.grid_y and zombie.alive and zombie.state != c.DIE:
                            # ⚡【修改判定范围】
                            # 让大嘴花能吃到正前方 1.2 个格子内（约 100 像素）的僵尸
                            dist = zombie.pixel_x - plant.pixel_x
                            if 0 <= dist < (c.GRID_X_SIZE * 1.2): 
                                # ⚡【修改状态为 ATTACK，让客户端播放吞噬动画】
                                plant.state = c.ATTACK 
                                plant.digest_zombie_id = zombie.id
                                plant.digest_timer = now
                                zombie.alive = False
                                zombie.state = c.DIE
                                break

            # PotatoMine
            if plant.plant_type == c.POTATOMINE:
                if plant.is_init:
                    if plant.animate_timer == 0:
                        plant.animate_timer = now
                    elif now - plant.animate_timer > 15000:
                        plant.is_init = False
                elif plant.state == c.IDLE:
                    for zombie in self.state.zombies:
                        if zombie.lane == plant.grid_y and zombie.alive and zombie.state != c.DIE:
                            if zombie.pixel_x >= plant.pixel_x and \
                               zombie.pixel_x - plant.pixel_x < c.GRID_X_SIZE // 3 * 2:
                                plant.state = c.ATTACK
                                plant.attack_timer = now
                                break
                elif plant.state == c.ATTACK:
                    if now - plant.attack_timer > 500:
                        plant.health = 0
                        plant.alive = False
                continue

            # Squash
            if plant.plant_type == c.SQUASH:
                if not plant.is_aiming and not plant.is_squashing:
                    for zombie in self.state.zombies:
                        if zombie.lane == plant.grid_y and zombie.alive and zombie.state != c.DIE:
                            if plant.pixel_x <= zombie.pixel_x and \
                               zombie.pixel_x - plant.pixel_x < c.GRID_X_SIZE:
                                plant.is_aiming = True
                                plant.attack_zombie_id = zombie.id
                                plant.animate_timer = now
                                break
                elif plant.is_aiming and not plant.is_squashing:
                    if now - plant.animate_timer > 1000:
                        plant.is_squashing = True
                        plant.attack_timer = now
                elif plant.is_squashing:
                    if now - plant.attack_timer > 1200:
                        if plant.attack_zombie_id:
                            self._kill_zombie_by_id(plant.attack_zombie_id)
                        plant.health = 0
                        plant.alive = False
                continue

            # Hypno-shroom
            if plant.plant_type == c.HYPNOSHROOM and plant.health <= 0:
                if plant.kill_zombie_id:
                    zombie = self._find_zombie_by_id(plant.kill_zombie_id)
                    if zombie and zombie.alive:
                        zombie.is_hypno = True
                        zombie.state = c.WALK

    def _apply_explosion(self, plant):
        """Explosion damage — mirrors single-player boomZombies()."""
        ptype = plant.plant_type
        px, py = plant.grid_x, plant.grid_y

        if ptype == c.CHERRYBOMB:
            y_range, x_range = 1, c.GRID_X_SIZE
        elif ptype == c.JALAPENO:
            y_range, x_range = 0, 377
        elif ptype == c.POTATOMINE:
            y_range, x_range = 0, c.GRID_X_SIZE // 3 * 2
        else:
            return

        for zombie in self.state.zombies:
            if not zombie.alive:
                continue
            if abs(zombie.lane - py) <= y_range:
                if x_range >= 300:  # full-row
                    if zombie.pixel_x < c.SCREEN_WIDTH:
                        zombie.alive = False
                        zombie.state = c.DIE
                        # boomDie animation trigger for client
                        zombie._boom_die = True
                else:
                    if abs(zombie.pixel_x - plant.pixel_x) <= x_range:
                        zombie.alive = False
                        zombie.state = c.DIE

    # ===== 辅助方法 =====

    def _find_plant_by_id(self, entity_id):
        for p in self.state.plants:
            if p.id == entity_id:
                return p
        return None

    def _find_zombie_by_id(self, entity_id):
        for z in self.state.zombies:
            if z.id == entity_id:
                return z
        return None

    def _kill_zombie_by_id(self, entity_id):
        zombie = self._find_zombie_by_id(entity_id)
        if zombie:
            zombie.alive = False
            zombie.state = c.DIE

    def _cleanup_dead(self):
        """Remove dead entities."""
        # Only keep alive entities
        self.state.plants = [p for p in self.state.plants if p.alive]
        self.state.zombies = [z for z in self.state.zombies if z.alive]
        self.state.bullets = [b for b in self.state.bullets if b.alive]
        self.state.suns = [s for s in self.state.suns if s.alive]
        self.state.cars = [c for c in self.state.cars if c.alive]

        # Rebuild grid occupancy
        for y in range(c.GRID_Y_LEN):
            for x in range(c.GRID_X_LEN):
                self.state.grid[y][x] = c.MAP_EMPTY
        for plant in self.state.plants:
            if plant.alive:
                self.state.grid[plant.grid_y][plant.grid_x] = c.MAP_EXIST

    # ===== Win/lose conditions =====

    def _check_game_over(self):
        """Check win/lose conditions."""
        # Zombie victory: any zombie reaches the left edge
        for zombie in self.state.zombies:
            if zombie.alive and not zombie.is_hypno and zombie.pixel_x < 0:
                self.state.winner = 'zombies'
                self.state.state = 'finished'
                return

        # Plant victory: all zombies dead AND zombie player out of resources
        alive_zombies = any(z.alive for z in self.state.zombies)
        if not alive_zombies and self.state.brain_points <= 0:
            self.state.winner = 'plants'
            self.state.state = 'finished'
            return

        # Timeout (5 minutes)
        if self.state.game_time > self.state.match_duration:
            self.state.winner = 'plants'
            self.state.state = 'finished'
            return

    def start_game(self):
        """Start the game."""
        self.state.state = 'playing'
        self.state.game_time = 0.0
        self.state.sun_timer = 0.0
        self.state.brain_timer = 0.0
