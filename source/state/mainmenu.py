__author__ = 'yuanyu'

import pygame as pg
from .. import tool
from .. import constants as c
import os

class Menu(tool.State):
    def __init__(self):
        tool.State.__init__(self)

    def startup(self, current_time, persist):
        self.next = c.LEVEL
        self.persist = persist
        self.game_info = persist

        self.setupBackground()
        self.setupOption()
        self.setupMultiplayerOption()
        self.setupEndlessOption()

    def setupBackground(self):
        frame_rect = [80, 0, 800, 600]
        self.bg_image = tool.get_image(tool.GFX[c.MAIN_MENU_IMAGE], *frame_rect)
        self.bg_rect = self.bg_image.get_rect()
        self.bg_rect.x = 0
        self.bg_rect.y = 0

    def setupOption(self):
        self.option_frames = []
        frame_names = [c.OPTION_ADVENTURE + '_0', c.OPTION_ADVENTURE + '_1']
        frame_rect = [0, 0, 166, 70]

        for name in frame_names:
            self.option_frames.append(tool.get_image(tool.GFX[name], *frame_rect, c.BLACK, 1.7))

        self.option_frame_index = 0
        self.option_image = self.option_frames[self.option_frame_index]
        self.option_rect = self.option_image.get_rect()
        self.option_rect.x = 435
        self.option_rect.y = 75

        self.option_start = 0
        self.option_timer = 0
        self.option_clicked = False

    def setupMultiplayerOption(self):
        """使用 multiplayer.png，仿照冒险模式按钮布局。
        原图 166×70，scale=1.7 → 282×119。
        放在冒险模式按钮正下方。
        """
        if 'multiplayer' in tool.GFX:
            raw = tool.GFX['multiplayer']
        else:
            raw = pg.image.load(os.path.join(tool._PROJECT_ROOT, 'resources', 'graphics', 'Screen', 'multiplayer.png'))
        frame_rect = [0, 0, 166, 70]
        self.multi_image = tool.get_image(raw, *frame_rect, c.BLACK, 1.7)
        self.multi_rect = self.multi_image.get_rect()
        self.multi_rect.x = 432
        self.multi_rect.y = 215
        self.multi_clicked = False
        self.multi_timer = 0
        self.multi_start = 0
        self.multi_fade = False

    def setupEndlessOption(self):
        """无尽模式按钮 —— 使用外部按钮图 endless_button.png，
        按比例缩放到与冒险/多人按钮相同的目标框，并居中放置。
        """
        target_w, target_h = 282, 119  # 与冒险/多人按钮同尺寸

        img = None
        try:
            img = pg.image.load(os.path.join(tool._PROJECT_ROOT, 'resources', 'graphics', 'Screen', 'endless_button.png')).convert_alpha()
        except Exception:
            img = None

        if img is None:
            # 兜底：等比拉伸一个占位
            img = pg.Surface((target_w, target_h), pg.SRCALPHA)

        iw, ih = img.get_size()
        scale = min(target_w / iw, target_h / ih)
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
        scaled = pg.transform.smoothscale(img, (nw, nh))

        # 居中放到目标框大小的透明画布上
        surf = pg.Surface((target_w, target_h), pg.SRCALPHA)
        surf.blit(scaled, ((target_w - nw) // 2, (target_h - nh) // 2))

        self.endless_image = surf
        self.endless_rect = surf.get_rect()
        self.endless_rect.x = 432
        self.endless_rect.y = 355
        self.endless_clicked = False

    @staticmethod
    def _cn_font(size):
        """优先使用系统中文字体，失败则回退到默认字体"""
        for path in ("C:/Windows/Fonts/simhei.ttf",
                     "C:/Windows/Fonts/msyh.ttc"):
            try:
                return pg.font.Font(path, size)
            except Exception:
                continue
        return pg.font.SysFont("simhei,microsoftyahei,arial", size)

    def checkOptionClick(self, mouse_pos):
        x, y = mouse_pos
        if(x >= self.option_rect.x and x <= self.option_rect.right and
           y >= self.option_rect.y and y <= self.option_rect.bottom):
            self.option_clicked = True
            self.option_timer = self.option_start = self.current_time
        return False

    def checkMultiplayerClick(self, mouse_pos):
        x, y = mouse_pos
        if self.multi_rect.collidepoint(x, y):
            self.multi_clicked = True
            self.multi_timer = self.multi_start = self.current_time
            self.next = c.LOBBY
            return True
        return False

    def checkEndlessClick(self, mouse_pos):
        x, y = mouse_pos
        if self.endless_rect.collidepoint(x, y):
            self.endless_clicked = True
            self.next = c.ENDLESS
            return True
        return False

    def update(self, surface, current_time, mouse_pos, mouse_click):
        self.current_time = self.game_info[c.CURRENT_TIME] = current_time

        if not (self.option_clicked or self.multi_clicked or self.endless_clicked):
            # 点击判定：先检测无尽/多人按钮，再检测冒险按钮
            if mouse_pos and mouse_click[0]:
                if self.checkEndlessClick(mouse_pos):
                    pass
                elif self.checkMultiplayerClick(mouse_pos):
                    pass
                else:
                    self.checkOptionClick(mouse_pos)
        else:
            if self.option_clicked:
                if(self.current_time - self.option_timer) > 200:
                    self.option_frame_index += 1
                    if self.option_frame_index >= 2:
                        self.option_frame_index = 0
                    self.option_timer = self.current_time
                    self.option_image = self.option_frames[self.option_frame_index]
                if(self.current_time - self.option_start) > 1300:
                    self.done = True
            elif self.multi_clicked:
                # 直接跳转，不做淡出动画
                self.done = True
            elif self.endless_clicked:
                # 直接进入无尽模式
                self.done = True

        surface.blit(self.bg_image, self.bg_rect)
        surface.blit(self.option_image, self.option_rect)

        # 多人游戏按钮 — 使用 multiplayer.png，始终显示不淡出
        surface.blit(self.multi_image, self.multi_rect)

        # 无尽模式按钮 — 程序化绘制，始终显示
        surface.blit(self.endless_image, self.endless_rect)