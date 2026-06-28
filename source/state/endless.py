__author__ = 'qwh'

"""无尽模式状态 —— 作为一个独立子游戏接入宿主的开始界面。

设计要点：
  - pvzpython 的 Game 自带完整事件循环(1200x700)，与宿主(800x600)分辨率不同。
  - 进入本状态时把 display 切到 1200x700，跑完子游戏再切回 800x600，
    并刷新 tool.SCREEN / Control.screen，避免引用失效。
  - 子游戏 run(embedded=True) 会阻塞当前帧，直到玩家返回(B/ESC)或关窗(QUIT)：
      'back' → 返回宿主主菜单
      'quit' → 请求关闭整个程序(设置 tool._endless_quit_requested)
"""

import pygame as pg
from .. import tool
from .. import constants as c
from ..endless import game as endless_game


class Endless(tool.State):
    """无尽模式包装状态。"""

    def __init__(self):
        tool.State.__init__(self)
        self._ran = False
        self._result = 'back'

    def startup(self, current_time, persist):
        self.next = c.MAIN_MENU
        self.persist = persist
        self.game_info = persist
        self.current_time = current_time
        self._ran = False
        self._result = 'back'

    def update(self, surface, current_time, mouse_pos, mouse_click):
        self.current_time = current_time

        # 只在第一帧运行一次：resize → 创建子游戏 → 阻塞运行
        if not self._ran:
            self._ran = True
            screen = pg.display.set_mode(
                (endless_game.WINDOW_WIDTH, endless_game.WINDOW_HEIGHT))
            tool.SCREEN = screen
            try:
                game = endless_game.Game(screen)
                self._result = game.run(embedded=True)
            except Exception as e:
                print('[Endless] run error:', e)
                self._result = 'back'
            # 运行结束：恢复宿主分辨率
            screen = pg.display.set_mode(c.SCREEN_SIZE)
            tool.SCREEN = screen
            self.done = True
            if self._result == 'quit':
                tool._endless_quit_requested = True

    def cleanup(self):
        # 确保离开本状态时分辨率已是宿主尺寸
        if pg.display.get_surface() is None or \
           pg.display.get_surface().get_size() != c.SCREEN_SIZE:
            screen = pg.display.set_mode(c.SCREEN_SIZE)
            tool.SCREEN = screen
        self._ran = False
        return self.persist
