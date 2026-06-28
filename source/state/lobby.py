__author__ = 'yuanyu'

"""Lobby / room selection screen with MainMenu.png background."""

import pygame as pg
from .. import tool
from .. import constants as c
import os

FONT_SIZE = 22
FONT_SIZE_LARGE = 36


class Lobby(tool.State):
    """Lobby state — connect to server + select room"""

    def __init__(self):
        tool.State.__init__(self)
        self.font = None
        self.font_large = None
        self._editing_host = ''
        self._editing_port = ''
        self._editing_room = ''
        self.input_active = None
        self._ready_sent = False
        self.opponent_ready = False
        self.role = None
        self.room_id = None
        self.players_in_room = 0
        self.state_text = ''
        self.connected = False
        self.waiting_opponent = False
        self.error_text = ''
        self.game_started = False
        self._fade_in = True
        self._fade_start = 0
        self.buttons = []
        self._bg_image = None

    def startup(self, current_time, persist):
        self.next = c.MULTIPLAYER_LEVEL
        self.persist = persist
        self.game_info = persist
        self.network_client = persist.get('network_client', None)
        self.game_started = False
        self._fade_in = True
        self._fade_start = current_time
        self.server_host = persist.get('server_host', c.DEFAULT_SERVER_HOST)
        self.server_port = persist.get('server_port', c.DEFAULT_SERVER_PORT)
        self._editing_host = str(self.server_host)
        self._editing_port = str(self.server_port)
        self._editing_room = ''
        self.input_active = None
        self._ready_sent = False
        self.opponent_ready = False
        self.role = None
        self.room_id = None
        self.players_in_room = 0
        self.state_text = ''
        self.connected = False
        self.waiting_opponent = False
        self.error_text = ''
        self._init_fonts()
        self._load_background()
        self._init_buttons()

    def _init_fonts(self):
        self.font = tool.get_font(FONT_SIZE)
        self.font_large = tool.get_font(FONT_SIZE_LARGE)

    def _load_background(self):
        try:
            raw = pg.image.load(os.path.join(tool._PROJECT_ROOT, 'resources', 'graphics', 'Screen', 'MainMenu.png'))
            self._bg_image = pg.transform.smoothscale(
                raw, (c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
        except Exception:
            self._bg_image = None

    # ==================================================================
    #  布局 — MainMenu.png 做背景，横贯屏幕的黑色半透明遮罩
    #  输入框和按钮居中放置
    # ==================================================================

    _MASK_Y = 130         # 遮罩顶部 y
    _MASK_H = 370          # 遮罩高度

    _BTN_Y = 500           # 按钮行 y
    _BTN_H = 44
    _BTN_W = 150

    _connecting = False    # 防止重复点击 Connect

    def _init_buttons(self):
        mid = 400
        b_w = self._BTN_W
        b_h = self._BTN_H
        b_y = self._BTN_Y
        gap = 20

        self.buttons = [
            # --- 已连接 + 已分配角色 ---
            {'rect': pg.Rect(mid - b_w - gap // 2, b_y, b_w, b_h),
             'text': 'Ready!', 'action': 'ready',
             'visible': lambda: self.connected and self.role is not None},
            {'rect': pg.Rect(mid + gap // 2, b_y, b_w, b_h),
             'text': 'Disconnect', 'action': 'disconnect',
             'visible': lambda: self.connected and self.role is not None},

            # --- 已连接但还没加入房间 ---
            {'rect': pg.Rect(mid - b_w - gap // 2, b_y, b_w, b_h),
             'text': 'Quick Match', 'action': 'quick_join',
             'visible': lambda: self.connected and self.role is None},
            {'rect': pg.Rect(mid + gap // 2, b_y, b_w, b_h),
             'text': 'Join Room', 'action': 'join',
             'visible': lambda: self.connected and self.role is None},

            # --- 未连接（仅占位，无 action） ---
            {'rect': pg.Rect(mid - b_w - gap // 2, b_y, b_w, b_h),
             'text': 'Quick Match', 'action': None,
             'visible': lambda: not self.connected},
            {'rect': pg.Rect(mid + gap // 2, b_y, b_w, b_h),
             'text': 'Join Room', 'action': None,
             'visible': lambda: not self.connected},

            # --- 通用 ---
            {'rect': pg.Rect(mid - 50, b_y + b_h + 14, 100, 36),
             'text': 'Back', 'action': 'back',
             'visible': lambda: True},
        ]

    # ==================================================================
    #  update
    # ==================================================================

    def update(self, surface, current_time, mouse_pos, mouse_click):
        self.current_time = self.game_info[c.CURRENT_TIME] = current_time

        self._handle_keyboard()

        if self.network_client:
            try:
                for msg_type, data in self.network_client.poll():
                    self._handle_network(msg_type, data)
            except Exception:
                pass

        if self.game_started:
            self.persist['network_client'] = self.network_client
            self.persist['role'] = self.network_client.role
            self.persist['server_host'] = self.server_host
            self.persist['server_port'] = self.server_port
            self.done = True
            return

        if mouse_pos and mouse_click[0]:
            self._handle_click(mouse_pos)

        self._draw(surface)

    # ==================================================================
    #  keyboard
    # ==================================================================

    def _handle_keyboard(self):
        events = self.game_info.get('_key_events', [])
        for event in events:
            if not hasattr(event, 'type') or event.type != pg.KEYDOWN:
                continue

            if event.key == pg.K_RETURN:
                if not self.connected:
                    self._do_connect()
                self.input_active = None
                return
            elif event.key == pg.K_ESCAPE:
                self.input_active = None
                return

            if event.key == pg.K_BACKSPACE:
                if self.input_active == 'host':
                    self._editing_host = self._editing_host[:-1]
                elif self.input_active == 'port':
                    self._editing_port = self._editing_port[:-1]
                elif self.input_active == 'room':
                    self._editing_room = self._editing_room[:-1]
                continue

            if event.key == pg.K_v and (event.mod & pg.KMOD_CTRL):
                continue

            if not self.input_active:
                continue

            # 尝试 event.unicode；对于数字行键（无 unicode），回退到 key name
            ch = event.unicode
            if not ch:
                key_name = pg.key.name(event.key)
                if key_name and len(key_name) == 1 and key_name.isprintable():
                    ch = key_name

            if not ch or not ch.isprintable():
                continue

            self._insert_char(ch)

    def _insert_char(self, ch):
        """在当前激活的输入框中插入一个字符"""
        if self.input_active == 'host':
            if (ch.isdigit() or ch == '.') and len(self._editing_host) < 25:
                self._editing_host += ch
        elif self.input_active == 'port':
            if ch.isdigit() and len(self._editing_port) < 6:
                self._editing_port += ch
        elif self.input_active == 'room':
            if len(self._editing_room) < 20:
                self._editing_room += ch

    # ==================================================================
    #  mouse click
    # ==================================================================

    def _handle_click(self, mouse_pos):
        x, y = mouse_pos
        clicked = False

        iy = self._MASK_Y + 70

        if not self.connected:
            # 未连接：Host / Port / Room ID + Connect
            if pg.Rect(200, iy, 280, 36).collidepoint(x, y):
                self.input_active = 'host'
                return
            if pg.Rect(520, iy, 100, 36).collidepoint(x, y):
                self.input_active = 'port'
                return
            if pg.Rect(200, iy + 60, 280, 36).collidepoint(x, y):
                self.input_active = 'room'
                return
            if pg.Rect(300, iy + 130, 200, 40).collidepoint(x, y):
                self._do_connect()
                return

        elif self.role is None:
            # 已连接但还没加入房间：Room ID 输入框
            if pg.Rect(200, iy + 30, 280, 36).collidepoint(x, y):
                self.input_active = 'room'
                return

        for btn in self.buttons:
            if not btn['visible']():
                continue
            if btn['rect'].collidepoint(x, y):
                action = btn['action']
                if action is None:
                    # 灰掉的按钮（未连接时的 Quick Match / Join Room）
                    return
                clicked = True

                if action == 'join':
                    if self.network_client and self.connected:
                        room = self._editing_room.strip()
                        self.network_client.send('join_room', {'room_id': room})
                        self.state_text = f'Joining room: {room}...'
                        self.error_text = ''
                    return
                elif action == 'quick_join':
                    if self.network_client and self.connected:
                        self.network_client.send('join_room', {'room_id': ''})
                        self.state_text = 'Quick Match — searching...'
                        self.error_text = ''
                    return
                elif action == 'ready':
                    if self.network_client and self.connected and self.players_in_room >= 2:
                        self.network_client.send('ready', {})
                        self._ready_sent = True
                        self.state_text = 'Waiting for opponent to ready...'
                    return
                elif action == 'back':
                    self._disconnect_and_exit()
                    return
                elif action == 'disconnect':
                    self._disconnect_and_exit()
                    return

        if not clicked:
            self.input_active = None

    def _disconnect_and_exit(self):
        if self.network_client:
            try:
                self.network_client.disconnect()
            except Exception:
                pass
            self.network_client = None
        self.connected = False
        self._connecting = False
        self.next = c.MAIN_MENU
        self.done = True

    def _do_connect(self):
        if self._connecting:
            return
        self._connecting = True
        if self.network_client:
            try:
                self.network_client.disconnect()
            except Exception:
                pass
            self.network_client = None

        host = self._editing_host.strip() or str(self.server_host)
        try:
            port = int(self._editing_port.strip() or str(self.server_port))
        except ValueError:
            port = c.DEFAULT_SERVER_PORT

        self.server_host, self.server_port = host, port
        from ..network.client import NetworkClient
        try:
            self.network_client = NetworkClient(host, port)
            self.network_client.connect()
            # ★ 立即设为已连接，不等后台线程的 'connected' 消息
            self.connected = True
            self.role = None
            self.state_text = f'Connecting to {host}:{port}...'
            self.error_text = ''
        except Exception as e:
            self._connecting = False
            self.state_text = f'Connection failed: {e}'
            self.error_text = self.state_text

    # ==================================================================
    #  draw
    # ==================================================================

    def _draw(self, surface):
        # 1. 背景
        if self._bg_image:
            surface.blit(self._bg_image, (0, 0))
        else:
            surface.fill((30, 60, 30))

        # 2. 横贯全屏的半透明遮罩
        mask = pg.Surface((c.SCREEN_WIDTH, self._MASK_H), pg.SRCALPHA)
        mask.fill((0, 0, 0, 160))
        surface.blit(mask, (0, self._MASK_Y))

        mid = c.SCREEN_WIDTH // 2

        # 3. 标题
        title = self.font_large.render('PvP Multiplayer', True, c.GOLD)
        surface.blit(title, title.get_rect(center=(mid, self._MASK_Y + 28)))

        if not self.connected:
            # ===== 未连接：Host/Port/Room 输入 + Connect 按钮 =====
            iy = self._MASK_Y + 70

            self._draw_input(surface, 200, iy, 280, 36,
                             'Host:', self._editing_host,
                             self.input_active == 'host')
            self._draw_input(surface, 520, iy, 100, 36,
                             'Port:', self._editing_port,
                             self.input_active == 'port')
            self._draw_input(surface, 200, iy + 60, 280, 36,
                             'Room ID:', self._editing_room,
                             self.input_active == 'room')

            # Connect
            br = pg.Rect(mid - 100, iy + 130, 200, 40)
            hover = br.collidepoint(pg.mouse.get_pos())
            pg.draw.rect(surface, (60, 130, 30) if hover else (40, 90, 20),
                         br, border_radius=6)
            pg.draw.rect(surface, c.WHITE, br, 2, border_radius=6)
            ts = self.font.render('Connect', True, c.WHITE)
            surface.blit(ts, ts.get_rect(center=br.center))

            if self.state_text:
                color = c.RED if self.error_text else c.GOLD
                s = self.font.render(self.state_text, True, color)
                surface.blit(s, s.get_rect(center=(mid, iy + 200)))

        elif self.role is None:
            # ===== 已连接但还没加入房间：Room ID + Quick Match / Join Room =====
            iy = self._MASK_Y + 70

            self._draw_input(surface, 200, iy + 30, 280, 36,
                             'Room ID:', self._editing_room,
                             self.input_active == 'room')

            if self.state_text:
                color = c.RED if self.error_text else c.GOLD
                s = self.font.render(self.state_text, True, color)
                surface.blit(s, s.get_rect(center=(mid, iy + 120)))
        else:
            # ===== 已连接 + 已分配角色 =====
            iy = self._MASK_Y + 70
            info = f'Room: {self.room_id or "..."} — Role: {self.role or "..."}'
            surface.blit(self.font.render(info, True, c.WHITE),
                         self.font.render(info, True, c.WHITE).get_rect(center=(mid, iy + 40)))

            if self.state_text:
                color = c.RED if self.error_text else c.GOLD
                s = self.font.render(self.state_text, True, color)
                surface.blit(s, s.get_rect(center=(mid, iy + 120)))

        # 4. 可见按钮
        for btn in self.buttons:
            if btn['visible']():
                self._draw_button(surface, btn)

    def _draw_input(self, surface, x, y, w, h, label, value, active):
        """单个输入框"""
        ls = self.font.render(label, True, c.GOLD)
        surface.blit(ls, (x, y - 18))

        # 背景
        box = pg.Surface((w, h), pg.SRCALPHA)
        box.fill((0, 0, 0, 120))
        pg.draw.rect(box, c.GOLD if active else (120, 120, 120),
                     (0, 0, w, h), 2, border_radius=4)
        surface.blit(box, (x, y))

        # 文字 + 光标
        cursor = '|' if active and (self.current_time // 400) % 2 == 0 else ''
        ts = self.font.render(value + cursor, True, c.WHITE)
        ty = y + (h - ts.get_height()) // 2
        surface.blit(ts, (x + 8, ty))

    def _draw_button(self, surface, btn):
        r = btn['rect']
        hover = r.collidepoint(pg.mouse.get_pos())
        color = (80, 160, 40) if hover else (50, 110, 30)
        pg.draw.rect(surface, color, r, border_radius=8)
        pg.draw.rect(surface, c.WHITE, r, 2, border_radius=8)
        ts = self.font.render(btn['text'], True, c.WHITE)
        surface.blit(ts, ts.get_rect(center=r.center))

    # ==================================================================
    #  network
    # ==================================================================

    def _handle_network(self, msg_type, data):
        if msg_type == 'connected':
            # 后台确认连接成功，清除 connecting 标记
            self.connected = True
            self._connecting = False
            self._ready_sent = False
            self.opponent_ready = False
            self.role = None
            self.state_text = 'Connected!'
            self.error_text = ''
        elif msg_type == 'disconnected':
            self.connected = False
            self._connecting = False
            self.waiting_opponent = False
            self._ready_sent = False
            self.opponent_ready = False
            self.role = None
            self.state_text = 'Disconnected'
            # 非主动退出 → 自动返回主菜单
            self.next = c.MAIN_MENU
            self.done = True
        elif msg_type == 'role_assigned':
            self.role = data.get('role')
            self.room_id = data.get('room_id')
            rn = 'Plants' if self.role == 'plants' else 'Zombies'
            self.state_text = f'Role: {rn} — Waiting for opponent...'
            self.waiting_opponent = True
            self.error_text = ''
            # 如果玩家重连到已有对手的房间里，立即检查
            self._check_players()
        elif msg_type == 'room_info':
            self.players_in_room = data.get('players', 0)
            if self.players_in_room >= 2:
                self.players_in_room = 2
            self._check_players()
        elif msg_type == 'opponent_ready':
            self.opponent_ready = True
            if not self._ready_sent:
                self.state_text = 'Opponent is ready! Click Ready.'
        elif msg_type == 'game_start':
            self.game_started = True
        elif msg_type == 'error':
            self.error_text = data.get('message', 'Error')
            self.state_text = self.error_text

    def _check_players(self):
        """当房间满人、且尚未发送过 ready 时提示玩家"""
        if self.players_in_room >= 2 and not self._ready_sent:
            self.state_text = 'Opponent joined! Click Ready.'
