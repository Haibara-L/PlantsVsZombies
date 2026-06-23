__author__ = 'yuanyu'

"""Multiplayer game state — receives server state and renders with Pygame

The client runs the exact same update + draw order as single-player
level.py, so all animations are 100% identical.
"""

import pygame as pg
from .. import tool
from .. import constants as c
from ..component import plant as plant_module
from ..component import zombie as zombie_module
from ..component import menubar
from ..component.zombie_menu import ZombieMenuBar
from ..network.protocol import (
    ROLE_PLANTS, ROLE_ZOMBIES,
    S2C_STATE_SYNC, S2C_ACTION_RESULT, S2C_GAME_OVER,
)
from ..network.engine import getMapGridPos, isValidGrid


class MultiplayerLevel(tool.State):
    def __init__(self):
        tool.State.__init__(self)
        self.network_client = None
        self.role = None

    def startup(self, current_time, persist):
        self.game_info = persist
        self.persist = self.game_info
        self.game_info[c.CURRENT_TIME] = current_time

        self.network_client = persist.get('network_client')
        self.role = persist.get('role', ROLE_PLANTS)
        self.map_y_len = c.GRID_Y_LEN

        self._fade_in = True
        self._fade_start = current_time

        self._initial_state = None
        if self.network_client and self.network_client.latest_state:
            self._initial_state = self.network_client.latest_state

        self.setupBackground()
        self.setupGroups()

        self.menubar = None
        self.zombie_menu = None
        self.drag_plant = False
        self.hint_image = None
        self.hint_plant = False
        self.mouse_image = None
        self.plant_name = None
        self.select_plant = None

        if self.role == ROLE_PLANTS:
            self.menubar = menubar.MenuBar(list(range(8)), 150)
        else:
            self.zombie_menu = ZombieMenuBar()

        self.state = c.PLAY
        self.sun_value = 150
        self.brain_points = 50
        self.zombie_cooldowns = {}
        self.game_over = False
        self._disconnected = False
        self.winner = None
        self.error_message = ''
        self.error_timer = 0

    def setupBackground(self):
        img_index = 0
        self.background = tool.GFX[c.BACKGROUND_NAME][img_index]
        self.bg_rect = self.background.get_rect()
        self.level = pg.Surface((self.bg_rect.w, self.bg_rect.h)).convert()
        self.viewport = tool.SCREEN.get_rect(bottom=self.bg_rect.bottom)
        self.viewport.x += c.BACKGROUND_OFFSET_X

    def setupGroups(self):
        self.sun_group = pg.sprite.Group()
        self.head_group = pg.sprite.Group()
        self.plant_groups = [pg.sprite.Group() for _ in range(self.map_y_len)]
        self.zombie_groups = [pg.sprite.Group() for _ in range(self.map_y_len)]
        self.hypno_zombie_groups = [pg.sprite.Group() for _ in range(self.map_y_len)]
        self.bullet_groups = [pg.sprite.Group() for _ in range(self.map_y_len)]

        self.cars = []
        for i in range(self.map_y_len):
            self.cars.append(plant_module.Car(
                -25, 20 + i * c.GRID_Y_SIZE + c.MAP_OFFSET_Y + 23, i))

        self.plant_sprites = {}
        self.zombie_sprites = {}
        self.bullet_sprites = {}
        self.sun_sprites = {}

    # ==================================================================
    #  update
    # ==================================================================

    def update(self, surface, current_time, mouse_pos, mouse_click):
        self.current_time = self.game_info[c.CURRENT_TIME] = current_time

        # 检查 ESC 键 → 返回大厅
        events = self.game_info.get('_key_events', [])
        for event in events:
            if hasattr(event, 'type') and event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.next = c.LOBBY
                    self.done = True
                    return

        if self._disconnected:
            # 网络断开，直接返回主菜单
            self.next = c.MAIN_MENU
            self.done = True
            return

        if self._initial_state is not None:
            self._apply_state(self._initial_state)
            self._initial_state = None

        self._process_network()
        if self.state == c.PLAY and not self.game_over:
            self._handle_input(mouse_pos, mouse_click)
        self._update_ui()
        self._draw(surface)

    # ==================================================================
    #  network
    # ==================================================================

    def _process_network(self):
        if not self.network_client:
            return
        for msg_type, data in self.network_client.poll():
            if msg_type == 'disconnected' or msg_type == 'error':
                # 标记断开，不直接改 done（避免在遍历中闪退）
                self._disconnected = True
                return
            if msg_type in (S2C_STATE_SYNC, 'state_sync'):
                self._apply_state(data)
            elif msg_type in (S2C_ACTION_RESULT, 'action_result'):
                if not data.get('success', False):
                    self.error_message = data.get('error', 'Action failed')
                    self.error_timer = self.current_time
                if 'sun_value' in data and self.role == ROLE_PLANTS:
                    self.sun_value = data['sun_value']
                if 'brain_points' in data and self.role == ROLE_ZOMBIES:
                    self.brain_points = data['brain_points']
            elif msg_type in (S2C_GAME_OVER, 'game_over'):
                self.game_over = True
                self.winner = data.get('winner')

    def _apply_state(self, state_data):
        """Sync data from server into sprite objects."""
        # UI — 现在通过 _update_ui() 每帧更新，这里只做初始 sun_value 同步
        if 'sun_value' in state_data:
            self.sun_value = state_data['sun_value']
        zr = state_data.get('zombie_resources', {})
        if 'brain_points' in zr:
            self.brain_points = zr['brain_points']
        if 'cooldowns' in zr:
            self.zombie_cooldowns = zr['cooldowns']

        # plants
        sv = set()
        for p in state_data.get('plants', []):
            pid = p['id']; sv.add(pid)
            if pid not in self.plant_sprites:
                sp = self._make_plant(p)
                if sp: self.plant_sprites[pid] = sp
            sp = self.plant_sprites.get(pid)
            if not sp: continue
            lane = p['grid_y']
            _ensure_in_group(sp, self.plant_groups[lane], *self.plant_groups)
            sp.rect.centerx = p['pixel_x']
            sp.health = p['health']
            
            ns = p.get('state', c.IDLE)
            if ns != sp.state:
                if sp.name == c.CHOMPER:
                    # 大嘴花特殊处理：传空参数只播动画
                    if ns == c.ATTACK:
                        sp.setAttack(None, [])
                    elif ns == c.DIGEST:
                        sp.setDigest()
                    elif ns == c.IDLE:
                        sp.setIdle()
                else:
                    # 其他植物直接设状态，基类 Plant.setAttack/setIdle 无参
                    if ns == c.ATTACK:
                        sp.setAttack()
                    elif ns == c.IDLE:
                        sp.setIdle()
                sp.state = ns
        for pid in list(self.plant_sprites):
            if pid not in sv:
                self.plant_sprites.pop(pid).kill()

        # zombies
        sv = set()
        for z in state_data.get('zombies', []):
            zid = z['id']; sv.add(zid)
            if zid not in self.zombie_sprites:
                sp = self._make_zombie(z)
                if sp: self.zombie_sprites[zid] = sp
            sp = self.zombie_sprites.get(zid)
            if not sp: continue

            # ⚡ 服务端 to_state_dict 的 key 是 'lane'，不是 'grid_y'
            lane = z.get('lane', 0)
            _ensure_in_group(sp, self.zombie_groups[lane], *self.zombie_groups)

            # ⚡ 死亡/爆炸死亡 → 跳过物理拉扯，让倒地断头动画完整播放
            if sp.state == c.DIE:
                continue

            # 活着的僵尸同步坐标 & 血量
            sp.rect.centerx = z['pixel_x']
            sp.rect.bottom = z['pixel_y']
            sp.health = z['health']

            # 状态切换 — 省略所有 hasattr，Zombie 基类必有这些方法
            ns = z.get('state', c.WALK)
            if ns != sp.state:
                if ns == c.DIE:
                    if z.get('boom_die'):
                        sp.setBoomDie()      # 爆炸死亡 → boomdie_frames
                    else:
                        sp.setDie()          # 普通死亡 → die_frames
                elif ns == c.ATTACK:
                    sp.setAttack(_DummyPrey())
                elif ns == c.WALK:
                    sp.setWalk()
                sp.state = ns

            # 同步催眠状态（可能在 WALK 状态下改变，不触发 state change）
            sp.is_hypno = z.get('is_hypno', False)

        # 清理被服务端移除的僵尸
        for zid in list(self.zombie_sprites):
            if zid not in sv:
                self.zombie_sprites.pop(zid).kill()

        # bullets
        sv = set()
        for b in state_data.get('bullets', []):
            bid = b['id']; sv.add(bid)
            if bid not in self.bullet_sprites:
                sp = self._make_bullet(b)
                if sp: self.bullet_sprites[bid] = sp
            sp = self.bullet_sprites.get(bid)
            if not sp: continue
            lane = b['lane']
            _ensure_in_group(sp, self.bullet_groups[lane], *self.bullet_groups)

            # ⚡ X 坐标完全同步服务器 — 本地 x_vel=0，绝无左右振动
            sp.rect.centerx = b['pixel_x']

            # ⚡ Y 坐标精确校准对准豌豆嘴巴
            # 单机子弹 y ≈ plant.pixel_y - 70；服务端 pixel_y = plant.pixel_y - 12
            # 本行将 rect.bottom 上提 28 像素，补偿服务端偏移 + 子弹自身高度
            sp.rect.bottom = b['pixel_y'] - 28

            # ⚡ 服务器标记爆炸 → 触发本地破裂动画，让 PeaExplode 帧播完再死
            # 绝不能用 sp.kill() 硬删，否则玩家永远看不到爆裂特效
            if b.get('state') == 'explode' and sp.state != c.EXPLODE:
                sp.setExplode()

        # 清理已消失的子弹（setExplode 后 500ms 会自动 kill，这里兜底清理）
        for bid in list(self.bullet_sprites):
            if bid not in sv:
                self.bullet_sprites.pop(bid).kill()

        # suns
        sv = set()
        for s in state_data.get('suns', []):
            sid = s['id']; sv.add(sid)
            if sid not in self.sun_sprites:
                sp = plant_module.Sun(s['pixel_x'], 0,
                                      s['target_x'], s['target_y'],
                                      is_big=(s.get('sun_value', 25) == 25))
                self.sun_sprites[sid] = sp
                self.sun_group.add(sp)
                # ⚡ 首帧即冻结本地位移：让 dest 指向当前坐标，
                # 阻止 handleState() 擅自移动并与服务器拉扯
                sp.dest_x = sp.rect.centerx
                sp.dest_y = sp.rect.bottom
            sp = self.sun_sprites[sid]
            sp.rect.centerx = s['pixel_x']
            sp.rect.bottom = s['pixel_y']
            # ⚡ 每帧将 dest 钉死在服务器坐标上，
            # 确保 handleState() 判断 rect == dest → 跳过本地位移 → 零抖动
            sp.dest_x = sp.rect.centerx
            sp.dest_y = sp.rect.bottom
        for sid in list(self.sun_sprites):
            if sid not in sv:
                self.sun_sprites.pop(sid).kill()

        # cars
        cars_data = state_data.get('cars', [])
        for i, cd in enumerate(cars_data):
            if i < len(self.cars):
                alive = cd.get('alive', cd) if isinstance(cd, dict) else bool(cd)
                if not alive:
                    self.cars[i].dead = True

        # UI — 每帧通过 _update_ui() 更新，这里只做初始值同步
        if self.menubar:
            self.menubar.sun_value = self.sun_value
        if self.zombie_menu:
            self.zombie_menu.brain_points = self.brain_points

    def _update_ui(self):
        """用服务器下发的 sun_value / brain_points 更新本地 UI"""
        if self.menubar:
            self.menubar.sun_value = self.sun_value
            self.menubar.update(self.current_time)
        if self.zombie_menu:
            self.zombie_menu.brain_points = self.brain_points
            self.zombie_menu.update(self.current_time, self.zombie_cooldowns)

    # ---- sprite factories

    def _make_plant(self, p):
        import pygame
        # ⚡ 建立一个多人模式专用的“死胡同子弹组”，这个组不会被游戏循环 draw 和 update
        dummy_group = pygame.sprite.Group()

        pt = p['plant_type']; x = p['pixel_x']; y = p['pixel_y']; l = p['grid_y']
        m = {c.SUNFLOWER: lambda: plant_module.SunFlower(x, y, self.sun_group),
             # ⚡【核心修改】将以下所有射手类植物原本传入的 self.bullet_groups[l] 替换为 dummy_group
             c.PEASHOOTER: lambda: plant_module.PeaShooter(x, y, dummy_group),
             c.SNOWPEASHOOTER: lambda: plant_module.SnowPeaShooter(x, y, dummy_group),
             c.WALLNUT: lambda: plant_module.WallNut(x, y),
             c.CHERRYBOMB: lambda: plant_module.CherryBomb(x, y),
             # 三线射手要特殊处理，它原本接收整个大组，这里也让它塞进 dummy_group
             c.THREEPEASHOOTER: lambda: plant_module.ThreePeaShooter(x, y, [dummy_group]*5, l),
             c.REPEATERPEA: lambda: plant_module.RepeaterPea(x, y, dummy_group),
             c.CHOMPER: lambda: plant_module.Chomper(x, y),
             c.PUFFSHROOM: lambda: plant_module.PuffShroom(x, y, dummy_group),
             c.POTATOMINE: lambda: plant_module.PotatoMine(x, y),
             c.SQUASH: lambda: plant_module.Squash(x, y),
             c.SPIKEWEED: lambda: plant_module.Spikeweed(x, y),
             c.JALAPENO: lambda: plant_module.Jalapeno(x, y),
             c.SCAREDYSHROOM: lambda: plant_module.ScaredyShroom(x, y, dummy_group),
             c.SUNSHROOM: lambda: plant_module.SunShroom(x, y, self.sun_group),
             c.ICESHROOM: lambda: plant_module.IceShroom(x, y),
             c.HYPNOSHROOM: lambda: plant_module.HypnoShroom(x, y)}
        fn = m.get(pt)
        return fn() if fn else None

    def _make_zombie(self, z):
        zt = z['zombie_type']; x = z['pixel_x']; y = z['pixel_y']
        m = {c.NORMAL_ZOMBIE: lambda: zombie_module.NormalZombie(x, y, self.head_group),
             c.CONEHEAD_ZOMBIE: lambda: zombie_module.ConeHeadZombie(x, y, self.head_group),
             c.BUCKETHEAD_ZOMBIE: lambda: zombie_module.BucketHeadZombie(x, y, self.head_group),
             c.FLAG_ZOMBIE: lambda: zombie_module.FlagZombie(x, y, self.head_group),
             c.NEWSPAPER_ZOMBIE: lambda: zombie_module.NewspaperZombie(x, y, self.head_group)}
        fn = m.get(zt)
        sp = fn() if fn else None
        if sp and z.get('is_hypno'):
            sp.is_hypno = True
        return sp

    def _make_bullet(self, b):
        bt = b['bullet_type']; x = b['pixel_x']; y = b['pixel_y']
        m = {c.BULLET_PEA: lambda: plant_module.Bullet(x, y, y, c.BULLET_PEA, c.BULLET_DAMAGE_NORMAL, False),
             c.BULLET_PEA_ICE: lambda: plant_module.Bullet(x, y, y, c.BULLET_PEA_ICE, c.BULLET_DAMAGE_NORMAL, True),
             c.BULLET_MUSHROOM: lambda: plant_module.Bullet(x, y, y, c.BULLET_MUSHROOM, c.BULLET_DAMAGE_NORMAL, True)}
        fn = m.get(bt)
        sp = fn() if fn else None
        if sp:
            # ⚡ 彻底冻结本地位移：子弹变成顺从网络坐标的"提线木偶"
            # 防止 Bullet.update() 里的 self.rect.x += self.x_vel 与
            # _apply_state 的 rect.x = pixel_x 产生逐帧拉扯
            sp.x_vel = 0
            sp.y_vel = 0
        return sp

    # ==================================================================
    #  input
    # ==================================================================

    def _handle_input(self, mouse_pos, mouse_click):
        if self.role == ROLE_PLANTS:
            self._handle_plant_input(mouse_pos, mouse_click)
        else:
            self._handle_zombie_input(mouse_pos, mouse_click)

    def _handle_plant_input(self, mouse_pos, mouse_click):
        if self.menubar is None:
            return
        if not self.drag_plant and mouse_pos and mouse_click[0]:
            for sun in self.sun_group:
                if sun.checkCollision(mouse_pos[0], mouse_pos[1]):
                    if self.network_client:
                        for sid, s in self.sun_sprites.items():
                            if s == sun:
                                self.network_client.collect_sun(sid)
                                break
                    return
            result = self.menubar.checkCardClick(mouse_pos)
            if result:
                self._setupMouseImage(result[0], result[1])
        elif self.drag_plant:
            if mouse_click[1]:
                self._removeMouseImage()
            elif mouse_click[0]:
                if self.menubar.checkMenuBarClick(mouse_pos):
                    self._removeMouseImage()
                else:
                    self._addPlant()
            elif mouse_pos is None:
                self._setupHintImage()

    def _handle_zombie_input(self, mouse_pos, mouse_click):
        if self.zombie_menu is None:
            return
        if mouse_pos and mouse_click[0]:
            # 先检查是否点击了底部菜单栏中的卡片
            result = self.zombie_menu.checkCardClick(mouse_pos)
            if result:
                self.zombie_menu.select_card(result)
                return
            # 如果已经有选中的僵尸，点击空地 → 在该位置生成
            if self.zombie_menu.selected_zombie_type:
                x, y = mouse_pos
                map_x, map_y = self._getGridFromMouse(x, y)
                if self.network_client:
                    self.network_client.spawn_zombie(
                        self.zombie_menu.selected_zombie_type, map_y)
                self.zombie_menu.selected_zombie_type = None

    def _getGridFromMouse(self, x, y):
        return int((x - c.MAP_OFFSET_X) // c.GRID_X_SIZE), \
               int((y - c.MAP_OFFSET_Y) // c.GRID_Y_SIZE)

    def _setupMouseImage(self, plant_name, select_plant):
        frame_list = tool.GFX[plant_name]
        if plant_name in tool.PLANT_RECT:
            d = tool.PLANT_RECT[plant_name]
            x, y, w, h = d['x'], d['y'], d['width'], d['height']
        else:
            x, y, w, h = 0, 0, frame_list[0].get_rect().w, frame_list[0].get_rect().h
        color = c.WHITE if plant_name in (
            c.POTATOMINE, c.SQUASH, c.SPIKEWEED, c.JALAPENO,
            c.SCAREDYSHROOM, c.SUNSHROOM, c.ICESHROOM, c.HYPNOSHROOM) else c.BLACK
        self.mouse_image = tool.get_image(frame_list[0], x, y, w, h, color, 1)
        self.mouse_rect = self.mouse_image.get_rect()
        pg.mouse.set_visible(False)
        self.drag_plant = True
        self.plant_name = plant_name
        self.select_plant = select_plant

    def _removeMouseImage(self):
        pg.mouse.set_visible(True)
        self.drag_plant = False
        self.mouse_image = None
        self.hint_image = None
        self.hint_plant = False

    def _setupHintImage(self):
        if not self.mouse_image:
            return
        x, y = pg.mouse.get_pos()
        map_x, map_y = self._getGridFromMouse(x, y)
        if not isValidGrid(map_x, map_y):
            self.hint_plant = False
            return
        px, py = getMapGridPos(map_x, map_y)
        w, h = self.mouse_rect.w, self.mouse_rect.h
        img = pg.Surface([w, h])
        img.blit(self.mouse_image, (0, 0), (0, 0, w, h))
        img.set_colorkey(c.BLACK)
        img.set_alpha(128)
        self.hint_image = img
        self.hint_rect = img.get_rect()
        self.hint_rect.centerx = px
        self.hint_rect.bottom = py
        self.hint_plant = True

    def _addPlant(self):
        if self.network_client is None or self.plant_name is None:
            return
        x, y = pg.mouse.get_pos()
        if x is None:
            return
        map_x, map_y = self._getGridFromMouse(x, y)
        if not isValidGrid(map_x, map_y):
            return
        self.network_client.place_plant(self.plant_name, map_x, map_y)
        self._removeMouseImage()

    # ==================================================================
    #  draw
    # ==================================================================

    def _draw(self, surface):
        self.level.blit(self.background, self.viewport, self.viewport)
        surface.blit(self.level, (0, 0), self.viewport)

        if self._fade_in:
            elapsed = self.current_time - self._fade_start
            if elapsed < 500:
                alpha = max(0, 255 - int(elapsed / 500 * 255))
                overlay = pg.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
                overlay.set_alpha(alpha)
                overlay.fill(c.BLACK)
                surface.blit(overlay, (0, 0))
            else:
                self._fade_in = False

        if self.state != c.PLAY:
            return

        for i in range(self.map_y_len):
            self.bullet_groups[i].update(self.game_info)
            self.plant_groups[i].update(self.game_info)
            self.zombie_groups[i].update(self.game_info)
            self.hypno_zombie_groups[i].update(self.game_info)
        self.head_group.update(self.game_info)
        self.sun_group.update(self.game_info)
        for car in self.cars:
            car.update(self.game_info)

        self._checkBulletCollisions()
        self._checkZombieCollisions()
        self._checkPlants()
        self._checkCarCollisions()

        if self.menubar:
            self.menubar.draw(surface)
        elif self.zombie_menu:
            self.zombie_menu.draw(surface)

        for i in range(self.map_y_len):
            self.plant_groups[i].draw(surface)
            self.zombie_groups[i].draw(surface)
            self.hypno_zombie_groups[i].draw(surface)
            self.bullet_groups[i].draw(surface)
        for car in self.cars:
            if not car.dead:
                car.draw(surface)
        self.head_group.draw(surface)
        if self.role == ROLE_PLANTS:
            self.sun_group.draw(surface)
        if self.drag_plant:
            self._drawMouseShow(surface)

        if self.error_message and (self.current_time - self.error_timer) < 2000:
            f = pg.font.Font(None, 28)
            s = f.render(self.error_message, True, c.RED)
            surface.blit(s, s.get_rect(center=(c.SCREEN_WIDTH // 2, c.SCREEN_HEIGHT - 30)))

        if self.game_over:
            self._draw_game_over(surface)

        f = pg.font.Font(None, 20)
        t = 'Plants' if self.role == ROLE_PLANTS else 'Zombies'
        surface.blit(f.render(f'You: {t}', True, c.WHITE), (c.SCREEN_WIDTH - 120, 5))

    # ==================================================================
    #  client-side checks (drives ANIMATION only)
    # ==================================================================

    def _checkBulletCollisions(self):
        collided = pg.sprite.collide_circle_ratio(0.7)
        for i in range(self.map_y_len):
            for bullet in self.bullet_groups[i]:
                if bullet.state != c.FLY:
                    continue
                zombie = pg.sprite.spritecollideany(
                    bullet, self.zombie_groups[i], collided)
                if zombie and zombie.state != c.DIE:
                    zombie.setDamage(bullet.damage, bullet.ice)
                    bullet.setExplode()

    def _checkZombieCollisions(self):
        collided = pg.sprite.collide_circle_ratio(0.7)
        for i in range(self.map_y_len):
            for zombie in self.zombie_groups[i]:
                if zombie.state != c.WALK:
                    continue
                plant = pg.sprite.spritecollideany(
                    zombie, self.plant_groups[i], collided)
                if plant:
                    # ⚡【智能状态拦截】
                    if plant.name == c.CHOMPER:
                        # 只有当大嘴花处于 IDLE（准备吃人）状态时，才拦截僵尸的攻击，让大嘴花优先吞噬
                        # 如果大嘴花已经在 ATTACK（张嘴）或 DIGEST（咀嚼），僵尸可以正常咬它！
                        if plant.state == c.IDLE:
                            continue  # 跳过本地攻击，等待服务器判定谁把谁吃了
                        else:
                            zombie.setAttack(plant) # 大嘴花在忙，僵尸上去围殴它
                    elif plant.name != c.SPIKEWEED:
                        # 普通植物正常啃咬
                        zombie.setAttack(plant)
            for hypno in self.hypno_zombie_groups[i]:
                if hypno.health <= 0:
                    continue
                zlist = pg.sprite.spritecollide(
                    hypno, self.zombie_groups[i], False, collided)
                for z in zlist:
                    if z.state == c.DIE:
                        continue
                    if z.state == c.WALK:
                        z.setAttack(hypno, False)
                    if hypno.state == c.WALK:
                        hypno.setAttack(z, False)

    def _checkPlants(self):
        for i in range(self.map_y_len):
            for plant in self.plant_groups[i]:
                if plant.state == c.SLEEP:
                    continue
                self._checkPlant(plant, i)
                if plant.health <= 0:
                    self._killPlant(plant)

    def _killPlant(self, plant):
        x, y = plant.getPosition()
        _, map_y = self._getGridFromPixel(x, y)
        if (plant.name == c.CHERRYBOMB or plant.name == c.JALAPENO or
            plant.name == c.POTATOMINE or
            plant.name == c.REDWALLNUTBOWLING):
            self._boomZombies(plant.rect.centerx, map_y,
                              getattr(plant, 'explode_y_range', 1),
                              getattr(plant, 'explode_x_range', c.GRID_X_SIZE))
        plant.kill()

    def _boomZombies(self, x, map_y, y_range, x_range):
        for i in range(self.map_y_len):
            if abs(i - map_y) > y_range:
                continue
            for zombie in self.zombie_groups[i]:
                if abs(zombie.rect.centerx - x) <= x_range:
                    zombie.setBoomDie()
            for zombie in self.hypno_zombie_groups[i]:
                if abs(zombie.rect.centerx - x) <= x_range:
                    zombie.setBoomDie()

    def _getGridFromPixel(self, x, y):
        return self._getGridFromMouse(x, y)

    # def _checkPlant(self, plant, i):
    #     zlen = len(self.zombie_groups[i])
    #     if plant.name == c.THREEPEASHOOTER:
    #         if plant.state == c.IDLE:
    #             if zlen > 0 or \
    #                (i-1 >= 0 and len(self.zombie_groups[i-1]) > 0) or \
    #                (i+1 < self.map_y_len and len(self.zombie_groups[i+1]) > 0):
    #                 plant.setAttack()
    #         elif plant.state == c.ATTACK:
    #             if not (zlen > 0 or
    #                     (i-1 >= 0 and len(self.zombie_groups[i-1]) > 0) or
    #                     (i+1 < self.map_y_len and len(self.zombie_groups[i+1]) > 0)):
    #                 plant.setIdle()
    #     elif plant.name == c.CHOMPER:
    #         # if plant.state == c.IDLE:
    #         #     for z in self.zombie_groups[i]:
    #         #         # 确保僵尸没有死
    #         #         if plant.canAttack(z) and z.state != c.DIE:
    #         #             plant.setAttack(z, self.zombie_groups[i])
    #         #             break
    #         pass
    #     elif plant.name == c.POTATOMINE:
    #         for z in self.zombie_groups[i]:
    #             if plant.canAttack(z):
    #                 plant.setAttack()
    #                 break
    #     elif plant.name == c.SQUASH:
    #         for z in self.zombie_groups[i]:
    #             if plant.canAttack(z):
    #                 plant.setAttack(z, self.zombie_groups[i])
    #                 break
    #     elif plant.name == c.SPIKEWEED:
    #         can = any(plant.canAttack(z) for z in self.zombie_groups[i])
    #         if plant.state == c.IDLE and can:
    #             plant.setAttack(self.zombie_groups[i])
    #         elif plant.state == c.ATTACK and not can:
    #             plant.setIdle()
    #     elif plant.name == c.SCAREDYSHROOM:
    #         cry = False; can = False
    #         for z in self.zombie_groups[i]:
    #             if plant.needCry(z):
    #                 cry = True; break
    #             elif plant.canAttack(z):
    #                 can = True
    #         if cry:
    #             if plant.state != c.CRY: plant.setCry()
    #         elif can:
    #             if plant.state != c.ATTACK: plant.setAttack()
    #         elif plant.state != c.IDLE:
    #             plant.setIdle()
    #     elif plant.name in (c.WALLNUTBOWLING, c.REDWALLNUTBOWLING):
    #         pass
    #     else:
    #         can = (plant.state == c.IDLE and zlen > 0 and
    #                any(plant.canAttack(z) for z in self.zombie_groups[i]))
    #         if plant.state == c.IDLE and can:
    #             plant.setAttack()
    #         elif plant.state == c.ATTACK and not can:
    #             plant.setIdle()
    def _checkPlant(self, plant, i):
        zlen = len(self.zombie_groups[i])
        
        # ⚡ 射手类植物的触发判定全部归服务器管！
        # 客户端本地不要擅自调用 plant.setAttack() 导致本地产生重叠子弹。
        if plant.name == c.THREEPEASHOOTER:
            pass  # 三线射手也不要本地触发
        elif plant.name == c.CHOMPER:
            pass
        elif plant.name == c.POTATOMINE:
            for z in self.zombie_groups[i]:
                if plant.canAttack(z):
                    plant.setAttack()
                    break
        elif plant.name == c.SQUASH:
            for z in self.zombie_groups[i]:
                if plant.canAttack(z):
                    plant.setAttack(z, self.zombie_groups[i])
                    break
        elif plant.name == c.SPIKEWEED:
            can = any(plant.canAttack(z) for z in self.zombie_groups[i])
            if plant.state == c.IDLE and can:
                plant.setAttack(self.zombie_groups[i])
            elif plant.state == c.ATTACK and not can:
                plant.setIdle()
        elif plant.name == c.SCAREDYSHROOM:
            # 胆小菇的哭泣判定可以保留在本地控制状态，但攻击逻辑最好也交给服务端
            cry = False
            for z in self.zombie_groups[i]:
                if plant.needCry(z):
                    cry = True; break
            if cry:
                if plant.state != c.CRY: plant.setCry()
            elif plant.state == c.CRY:
                plant.setIdle()
        elif plant.name in (c.WALLNUTBOWLING, c.REDWALLNUTBOWLING):
            pass
        else:
            # 普通豌豆、双发等射手植物的 else 兜底逻辑直接 pass
            # 让它们静静等待 _apply_state 同步服务端的 ATTACK 状态
            pass

    def _checkCarCollisions(self):
        collided = pg.sprite.collide_circle_ratio(0.8)
        for car in list(self.cars):
            zombies = pg.sprite.spritecollide(
                car, self.zombie_groups[car.map_y], False, collided)
            for z in zombies:
                if z and z.state != c.DIE:
                    car.setWalk()
                    z.setDie()
            if car.dead:
                self.cars.remove(car)

    # ==================================================================
    #  misc draw helpers
    # ==================================================================

    def _drawMouseShow(self, surface):
        if self.hint_plant and self.hint_image:
            surface.blit(self.hint_image, self.hint_rect)
        x, y = pg.mouse.get_pos()
        self.mouse_rect.centerx = x
        self.mouse_rect.centery = y
        surface.blit(self.mouse_image, self.mouse_rect)

    def _draw_game_over(self, surface):
        overlay = pg.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
        overlay.set_alpha(180); overlay.fill(c.BLACK)
        surface.blit(overlay, (0, 0))
        f = pg.font.Font(None, 48)
        if self.winner == 'plants' and self.role == ROLE_PLANTS:
            t = 'You Win!'
        elif self.winner == 'zombies' and self.role == ROLE_ZOMBIES:
            t = 'You Win!'
        elif self.winner:
            t = 'You Lose!'
        else:
            t = 'Game Over'
        s = f.render(t, True, c.GOLD)
        surface.blit(s, s.get_rect(center=(c.SCREEN_WIDTH // 2, c.SCREEN_HEIGHT // 2)))
        sf = pg.font.Font(None, 24)
        tip = sf.render('Press ESC to return to menu', True, c.WHITE)
        surface.blit(tip, tip.get_rect(
            center=(c.SCREEN_WIDTH // 2, c.SCREEN_HEIGHT // 2 + 50)))


def _ensure_in_group(sprite, target, *all_groups):
    if sprite in target:
        return
    for g in all_groups:
        if sprite in g:
            g.remove(sprite)
    target.add(sprite)


class _DummyPrey:
    __slots__ = ()
    health = 9999
    state = c.IDLE
    alive = True
    def setDamage(self, _d=0, _z=None): pass
    def kill(self): pass