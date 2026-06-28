"""植物大战僵尸 - 无尽模式 Pygame主游戏逻辑

可作为独立脚本运行，也可被宿主项目嵌入：
  - 独立: game = Game(); game.run()
  - 嵌入: 传入宿主已创建的 display surface，run(embedded=True)，
          返回 'back'(返回宿主菜单) 或 'quit'(关闭窗口)。
"""
import pygame
import random
import math
from .constants import *
from .sprites import create_all_sprites, load_sprites_from_files

class Plant:
    """植物实体"""
    def __init__(self, plant_type, row, col):
        self.type = plant_type
        self.row = row
        self.col = col
        self.hp = PLANT_INFO[plant_type]['hp']
        self.max_hp = self.hp
        self.attack_timer = 0
        self.special_timer = 0
        self.active = False  # 土豆地雷激活状态
        self.used = False

        if plant_type == PT_POTATOMINE:
            self.special_timer = 12.0  # 土豆地雷12秒激活

class Zombie:
    """僵尸实体"""
    def __init__(self, zombie_type, row, wave):
        self.type = zombie_type
        self.row = row
        self.x = COLS + 0.5 + random.random() * 0.5
        info = ZOMBIE_INFO[zombie_type]
        hp_scale = 1.0 + (wave - 1) * 0.04  # 血量每波增长4%
        self.hp = int(info['hp'] * hp_scale)
        self.max_hp = self.hp
        self.speed = info['speed']
        self.eating = False
        self.slowed = False
        self.slow_timer = 0
        self.frozen = False
        self.frozen_timer = 0
        self.dead = False
        self.has_pole = (zombie_type == ZT_POLEVAULT)
        self.jumped = False
        self.paper_broken = False

class Projectile:
    """子弹实体"""
    def __init__(self, proj_type, row, x, damage):
        self.type = proj_type
        self.row = row
        self.x = x
        self.speed = 6.0
        self.damage = damage
        self.active = True
        self.from_snowpea = False  # 由寒冰豌豆经火炬树桩降级而来的普通豌豆, 不再被点燃

class Sun:
    """阳光实体"""
    def __init__(self, row, col, value=25, natural=True):
        self.row = row
        self.col = col
        self.x = float(col)
        self.y = -1.0 if natural else float(row)
        self.value = value
        self.timer = 12.0 if natural else 10.0
        self.falling = natural
        self.collected = False
        self.natural = natural
        # 动画目标
        self.target_x = GRID_OFFSET_X + col * CELL_WIDTH + CELL_WIDTH // 2
        self.target_y = GRID_OFFSET_Y + row * CELL_HEIGHT + CELL_HEIGHT // 2

class Explosion:
    """爆炸效果"""
    def __init__(self, row, col, radius, damage):
        self.row = row
        self.col = col
        self.radius = radius
        self.timer = 0.5
        self.damage = damage

class Game:
    """游戏主类"""
    def __init__(self, screen=None):
        # screen 传入表示由宿主嵌入运行(已创建 display)，不重复 init/set_mode
        self._embedded = screen is not None
        if not self._embedded:
            pygame.init()
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            pygame.display.set_caption(TITLE)
        else:
            self.screen = screen
        self.clock = pygame.time.Clock()

        # 字体 - 使用系统中文字体
        font_path = "C:/Windows/Fonts/simhei.ttf"
        self.font_large = pygame.font.Font(font_path, 48)
        self.font_medium = pygame.font.Font(font_path, 28)
        self.font_small = pygame.font.Font(font_path, 18)

        # 加载精灵(优先从文件加载)
        import os
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        self.sprites = load_sprites_from_files(assets_dir)
        # 种植后显示用的小尺寸植物精灵缓存(避免每帧缩放)
        self._plant_display_cache = {}

        # 草坪背景图: 复用宿主 PvZ 经典背景 (resources/graphics/Items/Background/Background_0.jpg)
        # 按"覆盖窗口"缩放铺满；加载失败则回退到程序化绘制
        self._bg_image = None
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        for rel in ('resources/graphics/Items/Background/Background_0.jpg',):
            p = os.path.join(root, rel)
            if os.path.exists(p):
                try:
                    img = pygame.image.load(p).convert()
                    iw, ih = img.get_size()
                    scale = max(WINDOW_WIDTH / iw, WINDOW_HEIGHT / ih)
                    nw, nh = int(iw * scale), int(ih * scale)
                    self._bg_image = pygame.transform.smoothscale(img, (nw, nh))
                    self._bg_offset = ((WINDOW_WIDTH - nw) // 2, (WINDOW_HEIGHT - nh) // 2)
                except Exception:
                    self._bg_image = None
                break

        # 游戏状态
        self.state = ST_MENU
        self.wave = 0
        self.sun = 350
        self.total_kills = 0
        self.game_time = 0
        self.sun_drop_timer = 6.0
        self.selected_plant = -1
        self.shovel_mode = False
        self.game_speed = 1  # 游戏倍速: 1, 2, 3
        self.speed_btn_rects = []  # 倍速按钮区域

        # 实体列表
        self.plants = []
        self.zombies = []
        self.projectiles = []
        self.suns = []
        self.explosions = []

        # 波次管理
        self.zombies_to_spawn = 0
        self.spawn_timer = 0
        self.wave_active = False
        self.wave_intro_timer = 0

        # 增益(天赋)
        self.pea_mult = 1.0
        self.sun_mult = 1.0
        self.pult_mult = 1.0
        self.buff_pea_level = 0
        self.buff_sun_level = 0
        self.buff_pult_level = 0
        # 特殊天赋(一次性, 命中后从天赋池移除)
        self.pea_variety = False   # 豌豆射手发射混合子弹
        self.sun_double = False    # 向日葵50%概率双倍阳光
        self.pult_double = False   # 投手类50%概率连击两次
        self.current_buff_choices = []  # 本波结束后随机抽出的3个天赋id

        # 冰冻效果
        self.global_frozen = False
        self.global_frozen_timer = 0

        # 鼠标
        self.mouse_pos = (0, 0)
        self.hover_cell = None

        # 卡片冷却
        self.card_cooldowns = [0.0] * PT_COUNT

        # 动画效果
        self.sun_animations = []  # 阳光收集动画

    def _get_display_plant(self, ptype):
        """获取种植显示尺寸(PLANT_DISPLAY_SIZE)的植物精灵, 带缓存"""
        cache = self._plant_display_cache
        if ptype not in cache:
            sprite = self.sprites['plants'].get(ptype)
            if sprite is None:
                cache[ptype] = None
            else:
                cache[ptype] = pygame.transform.smoothscale(
                    sprite, (PLANT_DISPLAY_SIZE, PLANT_DISPLAY_SIZE))
        return cache[ptype]

    def restart(self):
        """重新开始游戏"""
        self.state = ST_WAVE_INTRO
        self.wave = 0
        self.sun = 350
        self.total_kills = 0
        self.game_time = 0
        self.sun_drop_timer = 6.0
        self.selected_plant = -1
        self.shovel_mode = False
        self.plants.clear()
        self.zombies.clear()
        self.projectiles.clear()
        self.suns.clear()
        self.explosions.clear()
        self.zombies_to_spawn = 0
        self.spawn_timer = 0
        self.wave_active = False
        self.wave_intro_timer = 4.0
        self.pea_mult = 1.0
        self.sun_mult = 1.0
        self.pult_mult = 1.0
        self.buff_pea_level = 0
        self.buff_sun_level = 0
        self.buff_pult_level = 0
        self.pea_variety = False
        self.sun_double = False
        self.pult_double = False
        self.current_buff_choices = []
        self.global_frozen = False
        self.global_frozen_timer = 0
        self.card_cooldowns = [0.0] * PT_COUNT

    def start_next_wave(self):
        """开始下一波"""
        self.wave += 1
        self.wave_active = True
        base_count = 3 + self.wave  # 每波僵尸数量
        if base_count > 40:
            base_count = 40
        self.zombies_to_spawn = base_count
        self.spawn_timer = 3.0  # 准备时间

    def choose_zombie_type(self):
        """选择僵尸类型 - 更容易"""
        r = random.randint(0, 99)
        if self.wave <= 5:
            # 前5波基本都是普通和路障
            if r < 90: return ZT_BASIC
            return ZT_CONE
        elif self.wave <= 10:
            # 5-10波开始出现路障和铁桶
            if r < 60: return ZT_BASIC
            if r < 85: return ZT_CONE
            return ZT_BUCKET
        elif self.wave <= 15:
            # 10-15波开始出现特殊僵尸
            if r < 40: return ZT_BASIC
            if r < 60: return ZT_CONE
            if r < 75: return ZT_BUCKET
            if r < 90: return ZT_NEWSPAPER
            return ZT_POLEVAULT
        else:
            # 15波以后全种类
            if r < 25: return ZT_BASIC
            if r < 45: return ZT_CONE
            if r < 65: return ZT_BUCKET
            if r < 80: return ZT_NEWSPAPER
            if r < 90: return ZT_POLEVAULT
            return ZT_FOOTBALL

    def spawn_zombie(self):
        """生成一个僵尸"""
        row = random.randint(0, ROWS - 1)
        ztype = self.choose_zombie_type()
        if self.zombies_to_spawn == (3 + self.wave) // 2 and self.wave > 1:
            ztype = ZT_FLAG
        self.zombies.append(Zombie(ztype, row, self.wave))
        self.zombies_to_spawn -= 1
        base_interval = max(3.0, 8.0 - self.wave * 0.15)  # 僵尸出现间隔
        self.spawn_timer = base_interval + random.random() * 2.0

    def get_plant_at(self, row, col):
        """获取指定位置的植物"""
        for p in self.plants:
            if p.row == row and p.col == col and p.hp > 0 and not p.used:
                return p
        return None

    def has_zombie_in_row(self, row, from_x):
        """检查某行from_x右侧是否有僵尸"""
        for z in self.zombies:
            if not z.dead and z.row == row and z.x >= from_x - 0.5:
                return True
        return False

    def find_nearest_zombie_in_row(self, row, from_x):
        """找某行最近的僵尸"""
        nearest = None
        min_dist = 999
        for z in self.zombies:
            if not z.dead and z.row == row and z.x >= from_x:
                d = z.x - from_x
                if d < min_dist:
                    min_dist = d
                    nearest = z
        return nearest

    def fire_projectile(self, row, from_x, proj_type, damage):
        """发射子弹"""
        self.projectiles.append(Projectile(proj_type, row, from_x, damage))

    def _fire_peashooter(self, p):
        """豌豆射手开火: 启用'豌豆百变'天赋后发射混合子弹"""
        x = p.col + 0.5
        base_dmg = int(PLANT_INFO[PT_PEASHOOTER]['damage'] * self.pea_mult)
        if self.pea_variety:
            r = random.random()
            if r < 0.70:
                # 普通豌豆
                self.fire_projectile(p.row, x, PROJ_PEA, base_dmg)
            elif r < 0.80:
                # 黄油: 伤害=西瓜投手基础伤害, 单体+固定僵尸
                self.fire_projectile(p.row, x, PROJ_BUTTER,
                                     int(PLANT_INFO[PT_MELONPULT]['damage'] * self.pea_mult))
            elif r < 0.90:
                # 星星: 命中即秒杀(单体)
                self.fire_projectile(p.row, x, PROJ_STAR, 0)
            else:
                # 爆炸豌豆: 命中后3x3范围樱桃炸弹伤害
                self.fire_projectile(p.row, x, PROJ_EXPLOSIONPEA, EXPLOSION_PEA_DAMAGE)
        else:
            self.fire_projectile(p.row, x, PROJ_PEA, base_dmg)

    def trigger_cherry_bomb(self, row, col):
        """樱桃炸弹"""
        self.explosions.append(Explosion(row, col, 1, 1800))
        for z in self.zombies:
            if not z.dead and abs(z.row - row) <= 1 and abs(int(z.x) - col) <= 1:
                z.hp -= 1800
                if z.hp <= 0:
                    z.dead = True

    def trigger_jalapeno(self, row):
        """火爆辣椒"""
        self.explosions.append(Explosion(row, 4, 9, 1800))
        for z in self.zombies:
            if not z.dead and z.row == row:
                z.hp -= 1800
                if z.hp <= 0:
                    z.dead = True

    def trigger_ice_shroom(self):
        """冰冻蘑菇"""
        self.global_frozen = True
        self.global_frozen_timer = 5.0  # 冰冻持续5秒
        for z in self.zombies:
            if not z.dead:
                z.frozen = True
                z.frozen_timer = 5.0
                z.hp -= 50
                if z.hp <= 0:
                    z.dead = True

    def trigger_doom_shroom(self, row, col):
        """毁灭菇"""
        self.explosions.append(Explosion(row, col, 2, 1800))
        for z in self.zombies:
            if not z.dead and abs(z.row - row) <= 2 and abs(int(z.x) - col) <= 2:
                z.hp -= 1800
                if z.hp <= 0:
                    z.dead = True

    def trigger_potato_mine(self, row, col):
        """土豆地雷"""
        self.explosions.append(Explosion(row, col, 0, 1800))
        for z in self.zombies:
            if not z.dead and z.row == row and abs(z.x - col) < 0.8:
                z.hp -= 1800
                if z.hp <= 0:
                    z.dead = True

    def add_plant(self, plant_type, row, col):
        """种植植物"""
        cost = PLANT_INFO[plant_type]['cost']
        if self.sun < cost:
            return False
        if self.get_plant_at(row, col):
            return False

        self.sun -= cost
        self.card_cooldowns[plant_type] = 5.0  # 卡片冷却

        # 一次性植物立即触发
        if plant_type == PT_CHERRYBOMB:
            self.trigger_cherry_bomb(row, col)
            return True
        if plant_type == PT_JALAPENO:
            self.trigger_jalapeno(row)
            return True
        if plant_type == PT_ICESHROOM:
            self.trigger_ice_shroom()
            return True
        if plant_type == PT_DOOMSHROOM:
            self.trigger_doom_shroom(row, col)
            return True

        self.plants.append(Plant(plant_type, row, col))
        return True

    def collect_sun(self):
        """收集所有阳光"""
        for s in self.suns:
            if not s.collected and not s.falling:
                self.sun += s.value
                s.collected = True
                # 收集动画
                sx = GRID_OFFSET_X + s.col * CELL_WIDTH + CELL_WIDTH // 2
                sy = GRID_OFFSET_Y + s.row * CELL_HEIGHT + CELL_HEIGHT // 2
                self.sun_animations.append({
                    'x': sx, 'y': sy, 'tx': 80, 'ty': 20,
                    'timer': 0.5, 'value': s.value
                })

    def roll_buff_choices(self):
        """从天赋池中随机抽出3个供玩家选择(已获得的一次性天赋不再出现)"""
        pool = []
        for tid, info in TALENT_INFO.items():
            if info['repeatable'] or not self._talent_acquired(tid):
                pool.append(tid)
        # 0/1/2 永远可叠加, 因此池子至少有3个
        k = min(3, len(pool))
        self.current_buff_choices = random.sample(pool, k)

    def _talent_acquired(self, tid):
        """一次性天赋是否已被获得"""
        if tid == 3:
            return self.pea_variety
        if tid == 4:
            return self.sun_double
        if tid == 5:
            return self.pult_double
        return False

    def apply_buff(self, choice_idx):
        """应用天赋 choice_idx 为 current_buff_choices 中的下标(0/1/2)"""
        if not (0 <= choice_idx < len(self.current_buff_choices)):
            return
        tid = self.current_buff_choices[choice_idx]
        if tid == 0:
            self.pea_mult *= 1.1
            self.buff_pea_level += 1
        elif tid == 1:
            self.sun_mult *= 1.1
            self.buff_sun_level += 1
        elif tid == 2:
            self.pult_mult *= 1.1
            self.buff_pult_level += 1
        elif tid == 3:
            self.pea_variety = True
        elif tid == 4:
            self.sun_double = True
        elif tid == 5:
            self.pult_double = True
        self.current_buff_choices = []
        self.state = ST_WAVE_INTRO
        self.wave_intro_timer = 4.0  # 准备时间

    def update_sun(self, dt):
        """更新阳光"""
        self.sun_drop_timer -= dt
        if self.sun_drop_timer <= 0:
            self.sun_drop_timer = 6.0 + random.random() * 3.0  # 阳光掉落间隔
            row = random.randint(0, ROWS - 1)
            col = random.randint(0, COLS - 1)
            self.suns.append(Sun(row, col, 35, True))  # 自然掉落阳光

        for s in self.suns:
            if s.collected:
                continue
            if s.falling:
                s.y += dt * 2.0
                if s.y >= s.row:
                    s.y = s.row
                    s.falling = False
            s.timer -= dt
            if s.timer <= 0:
                s.collected = True

    def update_plants(self, dt):
        """更新植物"""
        for p in self.plants:
            if p.hp <= 0 or p.used:
                continue
            t = p.type
            info = PLANT_INFO[t]

            # 向日葵产阳光
            if t == PT_SUNFLOWER:
                p.attack_timer += dt
                if p.attack_timer >= info['cooldown']:
                    p.attack_timer = 0
                    value = int(35 * self.sun_mult)  # 向日葵产出阳光
                    # 双倍阳光天赋: 50%概率一次产出两颗
                    count = 2 if (self.sun_double and random.random() < 0.5) else 1
                    for i in range(count):
                        offset = (i - (count - 1) / 2) * 0.25
                        self.suns.append(Sun(p.row, p.col + offset, value, False))

            # 豌豆射手
            elif t == PT_PEASHOOTER:
                if self.has_zombie_in_row(p.row, p.col):
                    p.attack_timer += dt
                    if p.attack_timer >= info['cooldown']:
                        p.attack_timer = 0
                        self._fire_peashooter(p)

            # 寒冰豌豆
            elif t == PT_SNOWPEA:
                if self.has_zombie_in_row(p.row, p.col):
                    p.attack_timer += dt
                    if p.attack_timer >= info['cooldown']:
                        p.attack_timer = 0
                        dmg = int(info['damage'] * self.pea_mult)
                        self.fire_projectile(p.row, p.col + 0.5, PROJ_SNOWPEA, dmg)

            # 机枪射手
            elif t == PT_GATLINGPEA:
                if self.has_zombie_in_row(p.row, p.col):
                    p.attack_timer += dt
                    if p.attack_timer >= info['cooldown']:
                        p.attack_timer = 0
                        dmg = int(info['damage'] * self.pea_mult)
                        for i in range(4):
                            self.fire_projectile(p.row, p.col + 0.5 + i * 0.15, PROJ_PEA, dmg)

            # 玉米投手
            elif t == PT_KERNELPULT:
                if self.find_nearest_zombie_in_row(p.row, 0):
                    p.attack_timer += dt
                    if p.attack_timer >= info['cooldown']:
                        p.attack_timer = 0
                        # 连环投掷天赋: 50%概率连续投两次
                        shots = 2 if (self.pult_double and random.random() < 0.5) else 1
                        for i in range(shots):
                            bx = p.col + 0.5 + i * 0.3
                            if random.random() < 0.10:
                                # 黄油: 伤害=西瓜投手基础伤害, 单体+固定僵尸
                                bdmg = int(PLANT_INFO[PT_MELONPULT]['damage'] * self.pult_mult)
                                self.fire_projectile(p.row, bx, PROJ_BUTTER, bdmg)
                            else:
                                kdmg = int(info['damage'] * self.pult_mult)
                                self.fire_projectile(p.row, bx, PROJ_KERNEL, kdmg)

            # 西瓜投手
            elif t == PT_MELONPULT:
                if self.find_nearest_zombie_in_row(p.row, 0):
                    p.attack_timer += dt
                    if p.attack_timer >= info['cooldown']:
                        p.attack_timer = 0
                        dmg = int(info['damage'] * self.pult_mult)
                        # 连环投掷天赋: 50%概率连续投两次
                        shots = 2 if (self.pult_double and random.random() < 0.5) else 1
                        for i in range(shots):
                            self.fire_projectile(p.row, p.col + 0.5 + i * 0.3, PROJ_MELON, dmg)

            # 食人花
            elif t == PT_CHOMPER:
                if p.special_timer > 0:
                    p.special_timer -= dt
                else:
                    target = self.find_nearest_zombie_in_row(p.row, p.col)
                    if target and target.x - p.col < 1.5 and target.x >= p.col:
                        target.hp -= 1800
                        if target.hp <= 0:
                            target.dead = True
                        p.special_timer = 42.0

            # 地刺
            elif t == PT_SPIKEWEED:
                p.attack_timer += dt
                if p.attack_timer >= info['cooldown']:
                    p.attack_timer = 0
                    for z in self.zombies:
                        if not z.dead and z.row == p.row and abs(z.x - p.col) < 0.5:
                            z.hp -= info['damage']
                            if z.hp <= 0:
                                z.dead = True

            # 土豆地雷
            elif t == PT_POTATOMINE:
                if not p.active:
                    p.special_timer -= dt
                    if p.special_timer <= 0:
                        p.active = True
                else:
                    for z in self.zombies:
                        if not z.dead and z.row == p.row and abs(z.x - p.col) < 0.8:
                            self.trigger_potato_mine(p.row, p.col)
                            p.used = True
                            p.hp = 0
                            break

    def update_projectiles(self, dt):
        """更新子弹"""
        for p in self.projectiles:
            if not p.active:
                continue
            p.x += p.speed * dt

            if p.x > COLS + 1:
                p.active = False
                continue

            # 火炬树桩交互
            # 普通豌豆被点燃为火豌豆(伤害x2); 寒冰豌豆则融化为普通豌豆(失去减速)
            if p.type == PROJ_PEA and not p.from_snowpea:
                for pl in self.plants:
                    if pl.type == PT_TORCHWOOD and pl.hp > 0 and not pl.used:
                        if pl.row == p.row and abs(p.x - pl.col) < 0.3:
                            p.type = PROJ_FIREPEA
                            p.damage = int(p.damage * 2.0)
            elif p.type == PROJ_SNOWPEA:
                for pl in self.plants:
                    if pl.type == PT_TORCHWOOD and pl.hp > 0 and not pl.used:
                        if pl.row == p.row and abs(p.x - pl.col) < 0.3:
                            p.type = PROJ_PEA
                            p.from_snowpea = True
                            break

            # 碰撞检测
            for z in self.zombies:
                if z.dead or z.row != p.row:
                    continue
                if abs(p.x - z.x) < 0.5:
                    p.active = False

                    if p.type == PROJ_STAR:
                        # 星星: 命中即秒杀(单体)
                        z.hp = 0
                        z.dead = True
                    elif p.type == PROJ_EXPLOSIONPEA:
                        # 爆炸豌豆: 命中点3x3范围樱桃炸弹伤害
                        cz = int(z.x)
                        self.explosions.append(Explosion(z.row, cz, 1, p.damage))
                        for z2 in self.zombies:
                            if z2.dead:
                                continue
                            if abs(z2.row - z.row) <= 1 and abs(int(z2.x) - cz) <= 1:
                                z2.hp -= p.damage
                                if z2.hp <= 0:
                                    z2.dead = True
                    else:
                        z.hp -= p.damage
                        if p.type == PROJ_SNOWPEA:
                            z.slowed = True
                            z.slow_timer = 5.0
                        if p.type == PROJ_BUTTER:
                            z.frozen = True
                            z.frozen_timer = 3.0
                        if p.type == PROJ_MELON:
                            for z2 in self.zombies:
                                if z2.dead or z2 is z:
                                    continue
                                if abs(z2.row - z.row) <= 1 and abs(z2.x - z.x) < 1.5:
                                    z2.hp -= p.damage // 2
                                    if z2.hp <= 0:
                                        z2.dead = True
                        if z.hp <= 0:
                            z.dead = True
                    break

    def update_zombies(self, dt):
        """更新僵尸"""
        for z in self.zombies:
            if z.dead:
                continue

            if z.frozen:
                z.frozen_timer -= dt
                if z.frozen_timer <= 0:
                    z.frozen = False
                continue

            if z.slowed:
                z.slow_timer -= dt
                if z.slow_timer <= 0:
                    z.slowed = False

            # 看报僵尸加速(削弱)
            if z.type == ZT_NEWSPAPER and not z.paper_broken:
                if z.hp < z.max_hp * 0.5:
                    z.paper_broken = True
                    z.speed *= 1.5  # 加速减弱

            spd = z.speed
            if z.slowed:
                spd *= 0.5

            # 检查前方植物（跳过地刺，地刺不阻挡僵尸）
            check_col = int(z.x - 0.3)
            if 0 <= check_col < COLS:
                plant = self.get_plant_at(z.row, check_col)
                if plant and plant.type != PT_SPIKEWEED:
                    z.eating = True
                    plant.hp -= int(ZOMBIE_INFO[z.type]['damage'] * dt)
                    if plant.hp <= 0:
                        z.eating = False
                    continue

            z.eating = False

            # 撑杆跳（跳过地刺，地刺不能跳过）
            if z.type == ZT_POLEVAULT and z.has_pole and not z.jumped:
                next_col = int(z.x - 0.3)
                if 0 <= next_col < COLS:
                    plant = self.get_plant_at(z.row, next_col)
                    if plant and plant.type != PT_SPIKEWEED:
                        z.x = next_col - 0.5
                        z.jumped = True
                        z.has_pole = False
                        z.speed *= 0.5
                        continue

            z.x -= spd * dt
            if z.x < -1.0:
                self.state = ST_GAMEOVER

    def update_wave(self, dt):
        """更新波次"""
        if not self.wave_active:
            return
        if self.zombies_to_spawn <= 0:
            any_alive = any(not z.dead for z in self.zombies)
            if not any_alive:
                self.wave_active = False
                self.state = ST_BUFF_SELECT
                self.roll_buff_choices()
            return

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_zombie()

    def update(self, dt):
        """主更新"""
        # 应用倍速
        game_dt = dt * self.game_speed

        # 更新卡片冷却
        for i in range(PT_COUNT):
            if self.card_cooldowns[i] > 0:
                self.card_cooldowns[i] -= game_dt

        # 更新阳光动画
        self.sun_animations = [a for a in self.sun_animations if a['timer'] > 0]
        for a in self.sun_animations:
            a['timer'] -= game_dt
            ratio = 1.0 - a['timer'] / 0.5
            a['cx'] = a['x'] + (a['tx'] - a['x']) * ratio
            a['cy'] = a['y'] + (a['ty'] - a['y']) * ratio

        if self.state == ST_PLAYING:
            self.game_time += game_dt
            self.update_sun(game_dt)
            self.update_plants(game_dt)
            self.update_projectiles(game_dt)
            self.update_zombies(game_dt)
            self.update_wave(game_dt)

            # 更新爆炸
            self.explosions = [e for e in self.explosions if e.timer > 0]
            for e in self.explosions:
                e.timer -= game_dt

            # 全局冰冻
            if self.global_frozen:
                self.global_frozen_timer -= game_dt
                if self.global_frozen_timer <= 0:
                    self.global_frozen = False

            # 清理
            self.plants = [p for p in self.plants if p.hp > 0 and not p.used]
            dead_zombies = [z for z in self.zombies if z.dead]
            self.total_kills += len(dead_zombies)
            self.zombies = [z for z in self.zombies if not z.dead]
            self.projectiles = [p for p in self.projectiles if p.active]
            self.suns = [s for s in self.suns if not s.collected]

        elif self.state == ST_WAVE_INTRO:
            self.wave_intro_timer -= game_dt
            if self.wave_intro_timer <= 0:
                self.state = ST_PLAYING
                self.start_next_wave()

    def get_cell_from_mouse(self, mx, my):
        """从鼠标位置获取格子坐标"""
        col = (mx - GRID_OFFSET_X) // CELL_WIDTH
        row = (my - GRID_OFFSET_Y) // CELL_HEIGHT
        if 0 <= row < ROWS and 0 <= col < COLS:
            return (row, col)
        return None

    def draw_background(self):
        """绘制背景：优先用 PvZ 经典草坪图，否则回退到程序化天空+草地"""
        if self._bg_image is not None:
            self.screen.blit(self._bg_image, self._bg_offset)
            return

        # 以下为程序化回退方案
        # 天空渐变
        for y in range(GRID_OFFSET_Y):
            ratio = y / GRID_OFFSET_Y
            r = int(135 * (1 - ratio) + 100 * ratio)
            g = int(206 * (1 - ratio) + 180 * ratio)
            b = int(235 * (1 - ratio) + 140 * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        # 草地
        self.screen.fill(COLOR_BG, (0, GRID_OFFSET_Y, WINDOW_WIDTH, WINDOW_HEIGHT - GRID_OFFSET_Y))

        # 草地纹理
        for row in range(ROWS):
            for col in range(COLS):
                x = GRID_OFFSET_X + col * CELL_WIDTH
                y = GRID_OFFSET_Y + row * CELL_HEIGHT
                # 交替深浅绿
                color = (50, 160, 50) if (row + col) % 2 == 0 else (40, 140, 40)
                pygame.draw.rect(self.screen, color, (x, y, CELL_WIDTH, CELL_HEIGHT))

    def draw_grid(self):
        """绘制网格。背景换成真实草坪后，用半透明白线让格子清晰可辨。"""
        line_col = (255, 255, 255, 55)
        gx0, gy0 = GRID_OFFSET_X, GRID_OFFSET_Y
        gx1 = gx0 + COLS * CELL_WIDTH
        gy1 = gy0 + ROWS * CELL_HEIGHT
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for row in range(ROWS + 1):
            y = gy0 + row * CELL_HEIGHT
            pygame.draw.line(overlay, line_col, (gx0, y), (gx1, y), 1)
        for col in range(COLS + 1):
            x = gx0 + col * CELL_WIDTH
            pygame.draw.line(overlay, line_col, (x, gy0), (x, gy1), 1)
        self.screen.blit(overlay, (0, 0))

    def draw_plants(self):
        """绘制植物"""
        for p in self.plants:
            if p.hp <= 0 or p.used:
                continue
            sprite = self._get_display_plant(p.type)
            if sprite:
                x = GRID_OFFSET_X + p.col * CELL_WIDTH + (CELL_WIDTH - PLANT_DISPLAY_SIZE) // 2
                y = GRID_OFFSET_Y + p.row * CELL_HEIGHT + (CELL_HEIGHT - PLANT_DISPLAY_SIZE) // 2
                self.screen.blit(sprite, (x, y))

            # 血条（地刺不显示血条，因为它不会受损）
            if p.type != PT_SPIKEWEED:
                hp_ratio = p.hp / p.max_hp
                bar_x = GRID_OFFSET_X + p.col * CELL_WIDTH + 5
                bar_y = GRID_OFFSET_Y + p.row * CELL_HEIGHT + CELL_HEIGHT - 8
                bar_w = CELL_WIDTH - 10
                pygame.draw.rect(self.screen, (80, 80, 80), (bar_x, bar_y, bar_w, 5))
                if hp_ratio > 0.6:
                    color = COLOR_HEALTH_GREEN
                elif hp_ratio > 0.3:
                    color = COLOR_HEALTH_YELLOW
                else:
                    color = COLOR_HEALTH_RED
                pygame.draw.rect(self.screen, color, (bar_x, bar_y, int(bar_w * hp_ratio), 5))

            # 土豆地雷未激活标记
            if p.type == PT_POTATOMINE and not p.active:
                font = self.font_small
                text = font.render("zzz", True, (200, 200, 200))
                tx = GRID_OFFSET_X + p.col * CELL_WIDTH + CELL_WIDTH // 2 - 10
                ty = GRID_OFFSET_Y + p.row * CELL_HEIGHT + 5
                self.screen.blit(text, (tx, ty))

            # 食人花咀嚼中
            if p.type == PT_CHOMPER and p.special_timer > 0:
                font = self.font_small
                text = font.render(f"咀嚼{int(p.special_timer)}s", True, (200, 200, 200))
                tx = GRID_OFFSET_X + p.col * CELL_WIDTH + 5
                ty = GRID_OFFSET_Y + p.row * CELL_HEIGHT + 5
                self.screen.blit(text, (tx, ty))

    def draw_zombies(self):
        """绘制僵尸"""
        for z in self.zombies:
            if z.dead:
                continue
            col = int(z.x)
            if col < 0 or col >= COLS:
                continue
            x = GRID_OFFSET_X + int(z.x * CELL_WIDTH) + (CELL_WIDTH - 80) // 2
            y = GRID_OFFSET_Y + z.row * CELL_HEIGHT + (CELL_HEIGHT - 80) // 2

            sprite = self.sprites['zombies'].get(z.type)
            if sprite:
                if z.frozen:
                    # 冰冻效果 - 绘制蓝色覆盖
                    tinted = sprite.copy()
                    tinted.fill((100, 200, 255, 100), special_flags=pygame.BLEND_RGBA_ADD)
                    self.screen.blit(tinted, (x, y))
                else:
                    self.screen.blit(sprite, (x, y))

            # 血条
            hp_ratio = z.hp / z.max_hp
            bar_x = GRID_OFFSET_X + int(z.x * CELL_WIDTH) + 5
            bar_y = GRID_OFFSET_Y + z.row * CELL_HEIGHT + CELL_HEIGHT - 8
            bar_w = CELL_WIDTH - 10
            pygame.draw.rect(self.screen, (80, 80, 80), (bar_x, bar_y, bar_w, 5))
            if hp_ratio > 0.6:
                color = COLOR_HEALTH_RED
            elif hp_ratio > 0.3:
                color = COLOR_HEALTH_YELLOW
            else:
                color = (200, 50, 50)
            pygame.draw.rect(self.screen, color, (bar_x, bar_y, int(bar_w * hp_ratio), 5))

    def draw_projectiles(self):
        """绘制子弹"""
        for p in self.projectiles:
            if not p.active:
                continue
            col = int(p.x)
            if col < 0 or col >= COLS:
                continue
            x = GRID_OFFSET_X + int(p.x * CELL_WIDTH)
            y = GRID_OFFSET_Y + p.row * CELL_HEIGHT + CELL_HEIGHT // 2 - 10

            sprite = self.sprites['projectiles'].get(p.type)
            if sprite:
                self.screen.blit(sprite, (x, y))

    def draw_suns(self):
        """绘制阳光"""
        sun_sprite = self.sprites['sun']
        for s in self.suns:
            if s.collected:
                continue
            if s.falling:
                x = GRID_OFFSET_X + int(s.x * CELL_WIDTH) + CELL_WIDTH // 2 - 20
                y = GRID_OFFSET_Y + int(s.y * CELL_HEIGHT) + CELL_HEIGHT // 2 - 20
            else:
                x = GRID_OFFSET_X + s.col * CELL_WIDTH + CELL_WIDTH // 2 - 20
                y = GRID_OFFSET_Y + s.row * CELL_HEIGHT + CELL_HEIGHT // 2 - 20

            # 闪烁效果
            if s.timer < 3.0 and int(s.timer * 4) % 2 == 0:
                continue
            self.screen.blit(sun_sprite, (x, y))

    def draw_explosions(self):
        """绘制爆炸"""
        exp_sprite = self.sprites['explosion']
        for e in self.explosions:
            if e.timer <= 0:
                continue
            alpha = int(255 * (e.timer / 0.5))
            for dr in range(-e.radius, e.radius + 1):
                for dc in range(-e.radius, e.radius + 1):
                    r = e.row + dr
                    c = e.col + dc
                    if 0 <= r < ROWS and 0 <= c < COLS:
                        x = GRID_OFFSET_X + c * CELL_WIDTH + (CELL_WIDTH - 90) // 2
                        y = GRID_OFFSET_Y + r * CELL_HEIGHT + (CELL_HEIGHT - 90) // 2
                        temp = exp_sprite.copy()
                        temp.set_alpha(alpha)
                        self.screen.blit(temp, (x, y))

    def draw_card_bar(self):
        """绘制植物卡片栏"""
        # 背景
        pygame.draw.rect(self.screen, (60, 50, 40), (0, 0, WINDOW_WIDTH, 85))
        pygame.draw.rect(self.screen, (80, 70, 55), (0, 0, WINDOW_WIDTH, 82))

        # 阳光显示
        sun_icon = self.sprites['sun']
        self.screen.blit(sun_icon, (10, 10))
        font = self.font_large
        text = font.render(str(self.sun), True, COLOR_SUN)
        self.screen.blit(text, (55, 15))

        # 植物卡片
        card_x = 140
        for i in range(PT_COUNT):
            info = PLANT_INFO[i]
            can_afford = self.sun >= info['cost']
            on_cooldown = self.card_cooldowns[i] > 0
            is_selected = (self.selected_plant == i)

            # 卡片背景
            if is_selected:
                color = (255, 255, 200)
            elif can_afford and not on_cooldown:
                color = (180, 160, 120)
            else:
                color = (100, 90, 70)

            pygame.draw.rect(self.screen, color, (card_x, 5, 60, 72))
            pygame.draw.rect(self.screen, (50, 40, 30), (card_x, 5, 60, 72), 2)

            # 植物图标
            sprite = self.sprites['plants'].get(i)
            if sprite:
                small = pygame.transform.scale(sprite, (40, 40))
                self.screen.blit(small, (card_x + 10, 8))

            # 价格
            price_color = COLOR_SUN if can_afford else (150, 100, 100)
            text = self.font_small.render(f"${info['cost']}", True, price_color)
            self.screen.blit(text, (card_x + 15, 52))

            # 冷却覆盖
            if on_cooldown:
                overlay = pygame.Surface((60, 72), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 128))
                self.screen.blit(overlay, (card_x, 5))
                cd_text = self.font_small.render(f"{self.card_cooldowns[i]:.0f}", True, (255, 255, 255))
                self.screen.blit(cd_text, (card_x + 22, 30))

            # 快捷键
            if i < 9:
                hotkey = str(i + 1)
            elif i == 9:
                hotkey = '0'
            else:
                hotkey = "QWERT"[i - 10]
            key_text = self.font_small.render(hotkey, True, (200, 200, 200))
            self.screen.blit(key_text, (card_x + 2, 5))

            card_x += 65

        # 铲子按钮 (在卡片栏最后)
        mx, my = self.mouse_pos
        shovel_x = card_x + 10
        shovel_hovering = shovel_x <= mx <= shovel_x + 60 and 5 <= my <= 77
        shovel_active = self.shovel_mode

        # 背景
        if shovel_active:
            bg_color = (255, 220, 150)
        elif shovel_hovering:
            bg_color = (220, 200, 160)
        else:
            bg_color = (180, 160, 120)
        pygame.draw.rect(self.screen, bg_color, (shovel_x, 5, 60, 72))
        border_color = (255, 100, 100) if shovel_active else (50, 40, 30)
        pygame.draw.rect(self.screen, border_color, (shovel_x, 5, 60, 72), 3 if shovel_active else 2)

        # 铲子图标
        shovel_sprite = self.sprites['shovel']
        self.screen.blit(shovel_sprite, (shovel_x + 10, 8))

        # 快捷键标签
        key_text = self.font_small.render("X", True, (100, 100, 100))
        self.screen.blit(key_text, (shovel_x + 2, 5))

        # 文字标签
        label = self.font_small.render("铲子", True, (80, 80, 80))
        self.screen.blit(label, (shovel_x + 14, 52))

        # 激活时高亮边框闪烁
        if shovel_active:
            import time
            if int(time.time() * 3) % 2 == 0:
                pygame.draw.rect(self.screen, (255, 255, 200), (shovel_x - 2, 3, 64, 76), 2)

        # 倍速按钮移到单独方法

    def draw_speed_buttons(self):
        """绘制倍速按钮 (所有状态下都显示)"""
        mx, my = self.mouse_pos
        self.speed_btn_rects = []
        speed_start_x = WINDOW_WIDTH - 155
        speed_y = 88
        for idx, speed in enumerate([1, 2, 3]):
            btn_x = speed_start_x + idx * 48
            btn_hover = btn_x <= mx <= btn_x + 42 and speed_y <= my <= speed_y + 32
            is_active = (self.game_speed == speed)

            # 按钮背景
            if is_active:
                btn_bg = (255, 200, 100)
            elif btn_hover:
                btn_bg = (220, 190, 140)
            else:
                btn_bg = (160, 140, 110)

            pygame.draw.rect(self.screen, btn_bg, (btn_x, speed_y, 42, 32), border_radius=6)
            border_col = (255, 220, 100) if is_active else (80, 70, 60)
            border_w = 3 if is_active else 2
            pygame.draw.rect(self.screen, border_col, (btn_x, speed_y, 42, 32), border_w, border_radius=6)

            # 按钮文字
            txt_color = (50, 40, 30) if is_active else (220, 220, 220)
            speed_text = self.font_small.render(f"{speed}x", True, txt_color)
            text_rect = speed_text.get_rect(center=(btn_x + 21, speed_y + 16))
            self.screen.blit(speed_text, text_rect)

            # 存储按钮区域
            self.speed_btn_rects.append((btn_x, speed_y, 42, 32, speed))

        # 倍速标签
        label = self.font_small.render("速度", True, (180, 180, 160))
        self.screen.blit(label, (speed_start_x - 35, speed_y + 8))

    def draw_ui(self):
        """绘制UI"""
        self.draw_card_bar()

        # 底部信息栏
        info_y = GRID_OFFSET_Y + ROWS * CELL_HEIGHT + 10
        pygame.draw.rect(self.screen, (60, 50, 40), (0, info_y, WINDOW_WIDTH, WINDOW_HEIGHT - info_y))

        # 波次信息
        font = self.font_medium
        wave_text = font.render(f"波次: {self.wave}", True, (255, 100, 100))
        self.screen.blit(wave_text, (20, info_y + 10))

        if self.wave_active:
            alive = sum(1 for z in self.zombies if not z.dead)
            remain_text = font.render(f"剩余: {alive + self.zombies_to_spawn}", True, (255, 200, 100))
            self.screen.blit(remain_text, (20, info_y + 40))

        # 击杀数
        kill_text = font.render(f"击杀: {self.total_kills}", True, (200, 200, 200))
        self.screen.blit(kill_text, (180, info_y + 10))

        # 增益信息
        buff_text = self.font_small.render(
            f"豌豆 Lv.{self.buff_pea_level} x{self.pea_mult:.2f}  |  "
            f"向日葵 Lv.{self.buff_sun_level} x{self.sun_mult:.2f}  |  "
            f"投手 Lv.{self.buff_pult_level} x{self.pult_mult:.2f}",
            True, (180, 220, 255)
        )
        self.screen.blit(buff_text, (180, info_y + 45))

        # 特殊天赋
        specials = []
        if self.pea_variety:
            specials.append("豌豆百变")
        if self.sun_double:
            specials.append("双倍阳光")
        if self.pult_double:
            specials.append("连环投掷")
        special_text = self.font_small.render(
            "特殊天赋: " + ("  |  ".join(specials) if specials else "无"),
            True, (255, 200, 150)
        )
        self.screen.blit(special_text, (180, info_y + 65))

        # 当前选择提示
        if self.selected_plant >= 0:
            info = PLANT_INFO[self.selected_plant]
            sel_text = font.render(
                f">> {info['name']} (${info['cost']}) - 点击种植 | ESC取消 <<",
                True, (255, 255, 200)
            )
            self.screen.blit(sel_text, (350, info_y + 10))
        elif self.shovel_mode:
            sel_text = font.render(">> 铲子模式 - 点击移除植物 | ESC取消 <<", True, (255, 255, 200))
            self.screen.blit(sel_text, (350, info_y + 10))
        else:
            sel_text = font.render("空格=收集阳光 | 选择植物后点击种植", True, (180, 180, 180))
            self.screen.blit(sel_text, (350, info_y + 10))

        # 全局冰冻提示
        if self.global_frozen:
            ice_text = font.render(
                f"*** 全屏冰冻中! {self.global_frozen_timer:.1f}s ***",
                True, COLOR_ICE
            )
            self.screen.blit(ice_text, (WINDOW_WIDTH // 2 - 100, GRID_OFFSET_Y - 25))

    def draw_hover(self):
        """绘制鼠标悬停效果"""
        if self.state != ST_PLAYING:
            return
        if self.hover_cell is None:
            return
        row, col = self.hover_cell
        x = GRID_OFFSET_X + col * CELL_WIDTH
        y = GRID_OFFSET_Y + row * CELL_HEIGHT

        if self.selected_plant >= 0:
            # 显示植物预览
            can_place = not self.get_plant_at(row, col) and self.sun >= PLANT_INFO[self.selected_plant]['cost']
            color = (100, 255, 100, 80) if can_place else (255, 100, 100, 80)
            overlay = pygame.Surface((CELL_WIDTH, CELL_HEIGHT), pygame.SRCALPHA)
            overlay.fill(color)
            self.screen.blit(overlay, (x, y))

            if can_place:
                sprite = self._get_display_plant(self.selected_plant)
                if sprite:
                    sprite_copy = sprite.copy()
                    sprite_copy.set_alpha(128)
                    self.screen.blit(sprite_copy,
                                   (x + (CELL_WIDTH - PLANT_DISPLAY_SIZE) // 2,
                                    y + (CELL_HEIGHT - PLANT_DISPLAY_SIZE) // 2))
        elif self.shovel_mode:
            overlay = pygame.Surface((CELL_WIDTH, CELL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 200, 100, 80))
            self.screen.blit(overlay, (x, y))
        else:
            overlay = pygame.Surface((CELL_WIDTH, CELL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 30))
            self.screen.blit(overlay, (x, y))

    def draw_sun_animations(self):
        """绘制阳光收集动画"""
        sun_sprite = self.sprites['sun']
        for a in self.sun_animations:
            small = pygame.transform.scale(sun_sprite, (20, 20))
            small.set_alpha(int(255 * a['timer'] / 0.5))
            self.screen.blit(small, (int(a['cx']), int(a['cy'])))

    def draw_wave_intro(self):
        """绘制波次介绍"""
        self.screen.fill((20, 20, 40))

        font = self.font_large
        text = font.render(f"第 {self.wave + 1} 波 即将来袭!", True, (255, 100, 100))
        rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40))
        self.screen.blit(text, rect)

        text2 = self.font_medium.render("准备好你的植物!", True, (200, 200, 200))
        rect2 = text2.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
        self.screen.blit(text2, rect2)

        text3 = self.font_medium.render(f"倒计时: {self.wave_intro_timer:.0f}s", True, (255, 200, 100))
        rect3 = text3.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
        self.screen.blit(text3, rect3)

    def _buff_option_text(self, tid):
        """返回某天赋选项的 (标题, 描述, 颜色)"""
        info = TALENT_INFO[tid]
        if tid == 0:
            title = f"{info['title']}  (x{self.pea_mult:.2f} → x{self.pea_mult * 1.1:.2f})"
        elif tid == 1:
            title = f"{info['title']}  (x{self.sun_mult:.2f} → x{self.sun_mult * 1.1:.2f})"
        elif tid == 2:
            title = f"{info['title']}  (x{self.pult_mult:.2f} → x{self.pult_mult * 1.1:.2f})"
        else:
            title = info['title']
        return title, info['desc'], info['color']

    def draw_buff_select(self):
        """绘制增益选择(每波结束后从天赋池随机抽3个)"""
        self.screen.fill((20, 20, 40))

        font = self.font_large
        text = font.render(f"波次 {self.wave} 完成!", True, (180, 220, 255))
        rect = text.get_rect(center=(WINDOW_WIDTH // 2, 80))
        self.screen.blit(text, rect)

        sub = self.font_medium.render("从天赋池中选择一个增益:", True, (200, 200, 200))
        rect = sub.get_rect(center=(WINDOW_WIDTH // 2, 130))
        self.screen.blit(sub, rect)

        mx, my = self.mouse_pos
        for i, tid in enumerate(self.current_buff_choices):
            title, desc, color = self._buff_option_text(tid)
            name = TALENT_INFO[tid]['name']
            y = 200 + i * 120
            # 检测鼠标悬停
            hovering = 150 <= mx <= WINDOW_WIDTH - 150 and y <= my <= y + 90
            bg_color = (80, 80, 110) if hovering else (60, 60, 80)
            border_w = 4 if hovering else 3

            # 选项框
            pygame.draw.rect(self.screen, bg_color, (150, y, WINDOW_WIDTH - 300, 90))
            pygame.draw.rect(self.screen, color, (150, y, WINDOW_WIDTH - 300, 90), border_w)

            title_text = self.font_medium.render(f"[{i + 1}] {name} - {title}", True, color)
            self.screen.blit(title_text, (180, y + 15))

            desc_text = self.font_small.render(desc, True, (180, 180, 180))
            self.screen.blit(desc_text, (180, y + 50))

        # 底部提示
        hint = self.font_small.render("鼠标点击 或 按键盘 1/2/3 选择", True, (150, 150, 150))
        rect = hint.get_rect(center=(WINDOW_WIDTH // 2, 570))
        self.screen.blit(hint, rect)

    def draw_game_over(self):
        """绘制游戏结束"""
        self.screen.fill((40, 10, 10))

        font = self.font_large
        text = font.render("僵尸吃掉了你的脑子!", True, (255, 50, 50))
        rect = text.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(text, rect)

        stats = [
            f"你坚持了 {self.wave} 波!",
            f"总计击杀: {self.total_kills} 只僵尸",
            f"豌豆增益: Lv.{self.buff_pea_level} (x{self.pea_mult:.2f})",
            f"向日葵增益: Lv.{self.buff_sun_level} (x{self.sun_mult:.2f})",
            f"投手增益: Lv.{self.buff_pult_level} (x{self.pult_mult:.2f})",
            "特殊天赋: " + "  ".join(
                name for flag, name in [
                    (self.pea_variety, "豌豆百变"),
                    (self.sun_double, "双倍阳光"),
                    (self.pult_double, "连环投掷"),
                ] if flag) or "无",
        ]

        for i, s in enumerate(stats):
            text = self.font_medium.render(s, True, (200, 200, 200))
            rect = text.get_rect(center=(WINDOW_WIDTH // 2, 250 + i * 40))
            self.screen.blit(text, rect)

        restart_text = self.font_medium.render("按 R 重新开始  |  ESC 退出", True, (255, 255, 200))
        rect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, 500))
        self.screen.blit(restart_text, rect)

    def draw_menu(self):
        """绘制主菜单"""
        self.screen.fill((20, 40, 20))

        # 标题
        font = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 64)
        text = font.render("植物大战僵尸", True, (100, 255, 100))
        rect = text.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(text, rect)

        sub = self.font_large.render("无尽模式", True, (255, 200, 100))
        rect = sub.get_rect(center=(WINDOW_WIDTH // 2, 220))
        self.screen.blit(sub, rect)

        # 展示一些植物
        y_offset = 300
        for i in range(5):
            sprite = self.sprites['plants'].get(i)
            if sprite:
                self.screen.blit(sprite, (200 + i * 160, y_offset))
                name = PLANT_INFO[i]['name']
                text = self.font_small.render(name, True, (200, 200, 200))
                rect = text.get_rect(center=(200 + i * 160 + 40, y_offset + 90))
                self.screen.blit(text, rect)

        # 开始提示
        start_text = self.font_large.render("点击任意处开始游戏", True, (255, 255, 200))
        rect = start_text.get_rect(center=(WINDOW_WIDTH // 2, 500))
        self.screen.blit(start_text, rect)

        # 操作说明
        controls = [
            "鼠标点击选择/种植 | 数字键快捷选择 | 空格收集阳光",
            "X键铲子模式 | ESC取消选择"
        ]
        if self._embedded:
            controls.append("按 B 返回主菜单")
        for i, c in enumerate(controls):
            text = self.font_small.render(c, True, (150, 150, 150))
            rect = text.get_rect(center=(WINDOW_WIDTH // 2, 560 + i * 25))
            self.screen.blit(text, rect)

    def draw(self):
        """主绘制"""
        if self.state == ST_MENU:
            self.draw_menu()
        elif self.state == ST_WAVE_INTRO:
            self.draw_wave_intro()
        elif self.state == ST_BUFF_SELECT:
            self.draw_buff_select()
        elif self.state == ST_GAMEOVER:
            self.draw_game_over()
        else:
            self.draw_background()
            self.draw_grid()
            self.draw_hover()
            self.draw_plants()
            self.draw_zombies()
            self.draw_projectiles()
            self.draw_suns()
            self.draw_explosions()
            self.draw_sun_animations()
            self.draw_ui()

        # 倍速按钮 (所有状态都绘制)
        self.draw_speed_buttons()

        pygame.display.flip()

    def handle_click(self, pos):
        """处理鼠标点击"""
        mx, my = pos

        # 倍速按钮检测 (所有状态下都可用)
        for btn_x, btn_y, btn_w, btn_h, speed in self.speed_btn_rects:
            if btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h:
                self.game_speed = speed
                return

        if self.state == ST_MENU:
            self.restart()
            return

        if self.state == ST_BUFF_SELECT:
            # 选项位置: y = 200 + i*120, 高度90
            for i in range(len(self.current_buff_choices)):
                y = 200 + i * 120
                if 150 <= mx <= WINDOW_WIDTH - 150 and y <= my <= y + 90:
                    self.apply_buff(i)
                    return
            return

        if self.state == ST_WAVE_INTRO:
            # 点击跳过准备时间
            self.wave_intro_timer = 0
            return

        if self.state == ST_GAMEOVER:
            self.restart()
            return

        if self.state != ST_PLAYING:
            return

        # 检查是否点击了阳光
        for s in self.suns:
            if s.collected or s.falling:
                continue
            sx = GRID_OFFSET_X + s.col * CELL_WIDTH
            sy = GRID_OFFSET_Y + s.row * CELL_HEIGHT
            if sx <= mx < sx + CELL_WIDTH and sy <= my < sy + CELL_HEIGHT:
                self.sun += s.value
                s.collected = True
                self.sun_animations.append({
                    'x': sx + CELL_WIDTH // 2, 'y': sy + CELL_HEIGHT // 2,
                    'tx': 80, 'ty': 20, 'timer': 0.5, 'value': s.value
                })
                return

        # 检查是否点击了卡片
        card_x = 140
        for i in range(PT_COUNT):
            if card_x <= mx < card_x + 60 and 5 <= my < 77:
                if self.sun >= PLANT_INFO[i]['cost'] and self.card_cooldowns[i] <= 0:
                    if self.selected_plant == i:
                        self.selected_plant = -1
                    else:
                        self.selected_plant = i
                        self.shovel_mode = False
                return
            card_x += 65

        # 检查是否点击了铲子 (在卡片栏末尾)
        shovel_x = card_x + 10
        if shovel_x <= mx < shovel_x + 60 and 5 <= my < 77:
            self.shovel_mode = not self.shovel_mode
            self.selected_plant = -1
            return

        # 检查是否点击了格子
        cell = self.get_cell_from_mouse(mx, my)
        if cell:
            row, col = cell
            if self.shovel_mode:
                plant = self.get_plant_at(row, col)
                if plant:
                    plant.hp = 0
                    plant.used = True
                self.shovel_mode = False
            elif self.selected_plant >= 0:
                if self.add_plant(self.selected_plant, row, col):
                    self.selected_plant = -1

    def handle_key(self, key):
        """处理键盘输入"""
        # 倍速快捷键 (F1/F2/F3, 所有状态可用)
        if key == pygame.K_F1:
            self.game_speed = 1
            return True
        elif key == pygame.K_F2:
            self.game_speed = 2
            return True
        elif key == pygame.K_F3:
            self.game_speed = 3
            return True

        if self.state == ST_MENU:
            self.restart()
            return

        if self.state == ST_GAMEOVER:
            if key == pygame.K_r:
                self.restart()
            elif key == pygame.K_ESCAPE:
                return False
            return True

        if self.state == ST_BUFF_SELECT:
            if key == pygame.K_1:
                self.apply_buff(0)
            elif key == pygame.K_2:
                self.apply_buff(1)
            elif key == pygame.K_3:
                self.apply_buff(2)
            return True

        if self.state == ST_WAVE_INTRO:
            if key == pygame.K_SPACE or key == pygame.K_RETURN:
                self.wave_intro_timer = 0
            return True

        if self.state == ST_PLAYING:
            # 快捷键选植物
            key_name = pygame.key.name(key)
            if key_name in PLANT_HOTKEYS:
                pt = PLANT_HOTKEYS[key_name]
                if self.sun >= PLANT_INFO[pt]['cost'] and self.card_cooldowns[pt] <= 0:
                    self.selected_plant = pt
                    self.shovel_mode = False
                return True

            if key == pygame.K_x:
                self.shovel_mode = not self.shovel_mode
                self.selected_plant = -1
            elif key == pygame.K_SPACE:
                if self.selected_plant >= 0 or self.shovel_mode:
                    self.selected_plant = -1
                    self.shovel_mode = False
                else:
                    self.collect_sun()
            elif key == pygame.K_ESCAPE:
                self.selected_plant = -1
                self.shovel_mode = False

        return True

    def run(self, embedded=False):
        """主循环

        embedded=True 时为宿主嵌入模式：
          - 不调用 pygame.quit()（宿主仍需 pygame）
          - 窗口关闭(QUIT) → 返回 'quit'，宿主据此退出整个程序
          - 按 B 键(任意状态)或 ESC(在主菜单) → 返回 'back'，宿主返回主菜单
        embedded=False 时为独立运行，结束后 pygame.quit()，返回 None。
        """
        self._embedded = embedded
        self.return_code = 'back' if embedded else None
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            if dt > 0.1:
                dt = 0.1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.return_code = 'quit' if embedded else None
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_pos = event.pos
                    self.hover_cell = self.get_cell_from_mouse(*event.pos)
                elif event.type == pygame.KEYDOWN:
                    # 嵌入模式: B 键随时返回宿主菜单
                    if embedded and event.key == pygame.K_b:
                        self.return_code = 'back'
                        running = False
                        break
                    # 嵌入模式: 主菜单下 ESC 返回宿主菜单
                    if embedded and event.key == pygame.K_ESCAPE and self.state == ST_MENU:
                        self.return_code = 'back'
                        running = False
                        break
                    result = self.handle_key(event.key)
                    if result is False:
                        # 独立模式 handle_key 返回 False 表示退出
                        self.return_code = None
                        running = False

            self.update(dt)
            self.draw()

        if not embedded:
            pygame.quit()
        return self.return_code
