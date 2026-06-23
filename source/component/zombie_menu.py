__author__ = 'yuanyu'

"""Zombie player UI — bottom card bar with real zombie images and cooldown overlay."""

import pygame as pg
from .. import tool
from .. import constants as c

# --- card data ----------------------------------------------------------------

ZOMBIE_CARD_COST = {
    c.NORMAL_ZOMBIE:     25,
    c.FLAG_ZOMBIE:       50,
    c.CONEHEAD_ZOMBIE:   75,
    c.BUCKETHEAD_ZOMBIE: 125,
    c.NEWSPAPER_ZOMBIE:  100,
}
ZOMBIE_CARD_COOLDOWN = {
    c.NORMAL_ZOMBIE:     7500,
    c.FLAG_ZOMBIE:       15000,
    c.CONEHEAD_ZOMBIE:   20000,
    c.BUCKETHEAD_ZOMBIE: 30000,
    c.NEWSPAPER_ZOMBIE:  25000,
}
ZOMBIE_CARD_ORDER = [
    c.NORMAL_ZOMBIE, c.FLAG_ZOMBIE, c.CONEHEAD_ZOMBIE,
    c.BUCKETHEAD_ZOMBIE, c.NEWSPAPER_ZOMBIE,
]

# Map each zombie type to the card image key loaded from resources/graphics/Cards/
ZOMBIE_CARD_GFX_KEY = {
    c.NORMAL_ZOMBIE:     'card_zombie',
    c.FLAG_ZOMBIE:       'card_flagzombie',
    c.CONEHEAD_ZOMBIE:   'card_coneheadzombie',
    c.BUCKETHEAD_ZOMBIE: 'card_bucketheadzombie',
    c.NEWSPAPER_ZOMBIE:  'card_newspapaerzombie',  # 文件名原版拼写如此
}


class ZombieCard:
    """A single zombie card — shows a mini zombie sprite with cooldown overlay."""

    def __init__(self, x, y, zombie_type, scale=0.30):
        # 原图 ~160×230，scale 0.30 → ~48×69 ≈ 植物卡片 ~50×70
        self.zombie_type = zombie_type
        self.brain_cost = ZOMBIE_CARD_COST.get(zombie_type, 50)
        self.frozen_time = ZOMBIE_CARD_COOLDOWN.get(zombie_type, 7500)
        self.frozen_timer = -self.frozen_time
        self.refresh_timer = 0
        self.select = True

        gfx_key = ZOMBIE_CARD_GFX_KEY.get(zombie_type, 'card_zombie')
        raw = tool.GFX[gfx_key]
        if isinstance(raw, list):
            raw = raw[0]
        # 步骤一模一样：先 loadFrame 拿到原图，再 get_rect 算大小，最后 smoothscale
        w, h = raw.get_rect().w, raw.get_rect().h
        new_w, new_h = int(w * scale), int(h * scale)
        self.orig_image = pg.transform.smoothscale(raw, (new_w, new_h))
        self.image = self.orig_image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def setFrozenTime(self, current_time):
        self.frozen_timer = current_time

    def canClick(self, brain_points, current_time):
        return (self.brain_cost <= brain_points and
                (current_time - self.frozen_timer) >= self.frozen_time and
                self.select)

    def checkMouseClick(self, mouse_pos):
        x, y = mouse_pos
        return (x >= self.rect.x and x <= self.rect.right and
                y >= self.rect.y and y <= self.rect.bottom)

    def createShowImage(self, brain_points, current_time):
        time = current_time - self.frozen_timer
        if time < self.frozen_time:                     # on cooldown
            img = pg.Surface([self.rect.w, self.rect.h], pg.SRCALPHA)
            frozen = self.orig_image.copy()
            frozen.set_alpha(128)
            h = int((self.frozen_time - time) / self.frozen_time * self.rect.h)
            img.blit(frozen, (0, 0), (0, 0, self.rect.w, h))
            img.blit(self.orig_image, (0, h),
                     (0, h, self.rect.w, self.rect.h - h))
            return img
        elif self.brain_cost > brain_points:             # not enough brains
            img = self.orig_image.copy()
            img.set_alpha(192)
            return img
        return self.orig_image

    def update(self, brain_points, current_time):
        if (current_time - self.refresh_timer) >= 250:
            self.image = self.createShowImage(brain_points, current_time)
            self.refresh_timer = current_time

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class ZombieMenuBar:
    """Zombie player bar — same layout as plant MenuBar."""

    def __init__(self):
        self._loadBackground()
        self.rect = self.image.get_rect()
        self.rect.x = 10
        self.rect.y = 0
        self.brain_points = 50
        self.current_time = 0
        self.selected_zombie_type = None
        self.card_offset_x = 32
        self.card_list = []
        self._setupCards()

    def _loadBackground(self):
        """加载 ChooseBackGroundforzombie.png 并缩放至植物菜单栏相同大小"""
        try:
            raw = tool.GFX.get('ChooseBackGroundforzombie')
            if raw is None:
                # 尝试直接从文件加载
                raw = pg.image.load(
                    'resources/graphics/Screen/ChooseBackGroundforzombie.png')
            # 保持宽高比缩放到和 ChooserBackground 一样的大小 (522×87)
            self.image = pg.transform.smoothscale(raw, (522, 87))
        except Exception:
            self.image = pg.Surface([522, 87], pg.SRCALPHA)
            self.image.fill((50, 0, 0, 180))      # dark red translucent

    def _setupCards(self):
        x = self.card_offset_x
        y = 8
        for ztype in ZOMBIE_CARD_ORDER:
            x += 55
            self.card_list.append(ZombieCard(x, y, ztype, scale=0.28))

    def update(self, current_time, server_cooldowns=None):
        self.current_time = current_time
        for card in self.card_list:
            card.update(self.brain_points, self.current_time)
        if server_cooldowns:
            for ztype, cd in server_cooldowns.items():
                for card in self.card_list:
                    if card.zombie_type == ztype:
                        remaining = cd.get('frozen_time', 0)
                        if remaining > 0:
                            total = cd.get('total_frozen_time', 7500)
                            card.frozen_timer = current_time - (total - remaining)

    def checkCardClick(self, mouse_pos):
        for card in self.card_list:
            if card.checkMouseClick(mouse_pos):
                if card.canClick(self.brain_points, self.current_time):
                    return card
                break
        return None

    def select_card(self, card):
        self.selected_zombie_type = card.zombie_type

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        self._drawBrainValue(surface)
        for card in self.card_list:
            card.draw(surface)
        if self.selected_zombie_type:
            f = pg.font.Font(None, 18)
            t = f.render(f'Selected: {self.selected_zombie_type} — click lane',
                         True, c.GOLD)
            surface.blit(t, (self.rect.x + 5, self.rect.bottom + 5))

    def _drawBrainValue(self, surface):
        """用金色数字显示脑点数"""
        f = pg.font.Font(None, 22)
        txt = f.render(str(self.brain_points), True, c.BLACK)
        surface.blit(txt, (22, self.rect.bottom - 21))

    def setCardFrozenTime(self, zombie_type):
        for card in self.card_list:
            if card.zombie_type == zombie_type:
                card.setFrozenTime(self.current_time)
                break

    def canClickAny(self, brain_points, current_time):
        """至少有一张卡片可点击时返回 True"""
        for card in self.card_list:
            if card.canClick(brain_points, current_time):
                return True
        return False
