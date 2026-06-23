__author__ = 'yuanyu'

import pygame as pg
from .. import tool
from .. import constants as c

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
            raw = pg.image.load('resources/graphics/Screen/multiplayer.png')
        frame_rect = [0, 0, 166, 70]
        self.multi_image = tool.get_image(raw, *frame_rect, c.BLACK, 1.7)
        self.multi_rect = self.multi_image.get_rect()
        self.multi_rect.x = 432
        self.multi_rect.y = 215
        self.multi_clicked = False
        self.multi_timer = 0
        self.multi_start = 0
        self.multi_fade = False

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

    def update(self, surface, current_time, mouse_pos, mouse_click):
        self.current_time = self.game_info[c.CURRENT_TIME] = current_time

        if not self.option_clicked and not self.multi_clicked:
            # 点击判定：先检测多人按钮，再检测冒险按钮
            if mouse_pos and mouse_click[0]:
                if self.checkMultiplayerClick(mouse_pos):
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

        surface.blit(self.bg_image, self.bg_rect)
        surface.blit(self.option_image, self.option_rect)

        # 多人游戏按钮 — 使用 multiplayer.png，始终显示不淡出
        surface.blit(self.multi_image, self.multi_rect)