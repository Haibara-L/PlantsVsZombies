"""程序化生成游戏精灵图片"""
import pygame
import math
from .constants import *

def create_gradient_surface(width, height, color1, color2, vertical=True):
    """创建渐变表面"""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(height if vertical else width):
        ratio = i / (height if vertical else width)
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        if vertical:
            pygame.draw.line(surf, (r, g, b, 255), (0, i), (width, i))
        else:
            pygame.draw.line(surf, (r, g, b, 255), (i, 0), (i, height))
    return surf

def draw_sunflower(size=80):
    """绘制向日葵"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 茎
    pygame.draw.rect(surf, (80, 150, 80), (cx - 4, cy + 10, 8, size // 2 - 10))

    # 花瓣
    petal_color = (255, 200, 50)
    for i in range(12):
        angle = i * 30 * math.pi / 180
        px = cx + int(20 * math.cos(angle))
        py = cy + int(20 * math.sin(angle))
        pygame.draw.ellipse(surf, petal_color, (px - 10, py - 6, 20, 12))

    # 花心
    pygame.draw.circle(surf, (139, 69, 19), (cx, cy), 15)
    pygame.draw.circle(surf, (160, 82, 45), (cx, cy), 12)

    # 笑脸
    pygame.draw.circle(surf, (0, 0, 0), (cx - 5, cy - 3), 3)
    pygame.draw.circle(surf, (0, 0, 0), (cx + 5, cy - 3), 3)
    pygame.draw.arc(surf, (0, 0, 0), (cx - 6, cy - 4, 12, 10), 3.14, 6.28, 2)

    return surf

def draw_peashooter(size=80):
    """绘制豌豆射手"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 茎
    pygame.draw.rect(surf, (60, 140, 60), (cx - 5, cy + 5, 10, size // 2 - 5))

    # 叶子
    pygame.draw.ellipse(surf, (80, 180, 80), (cx - 25, cy, 20, 12))
    pygame.draw.ellipse(surf, (80, 180, 80), (cx + 5, cy + 5, 20, 12))

    # 头部
    pygame.draw.circle(surf, (100, 200, 100), (cx, cy - 5), 22)
    pygame.draw.circle(surf, (120, 220, 120), (cx, cy - 5), 18)

    # 炮管
    pygame.draw.rect(surf, (80, 180, 80), (cx + 10, cy - 12, 20, 14))
    pygame.draw.circle(surf, (60, 140, 60), (cx + 30, cy - 5), 7)

    # 眼睛
    pygame.draw.circle(surf, (255, 255, 255), (cx - 5, cy - 10), 6)
    pygame.draw.circle(surf, (0, 0, 0), (cx - 3, cy - 10), 3)

    return surf

def draw_wallnut(size=80):
    """绘制坚果"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 身体
    pygame.draw.ellipse(surf, (180, 140, 80), (cx - 28, cy - 30, 56, 65))
    pygame.draw.ellipse(surf, (200, 160, 100), (cx - 24, cy - 26, 48, 57))

    # 裂纹纹理
    pygame.draw.line(surf, (139, 90, 43), (cx - 10, cy - 15), (cx - 5, cy + 10), 2)
    pygame.draw.line(surf, (139, 90, 43), (cx + 8, cy - 20), (cx + 12, cy + 5), 2)

    # 眼睛
    pygame.draw.circle(surf, (255, 255, 255), (cx - 10, cy - 10), 7)
    pygame.draw.circle(surf, (255, 255, 255), (cx + 10, cy - 10), 7)
    pygame.draw.circle(surf, (0, 0, 0), (cx - 8, cy - 10), 4)
    pygame.draw.circle(surf, (0, 0, 0), (cx + 12, cy - 10), 4)

    # 嘴巴
    pygame.draw.arc(surf, (139, 90, 43), (cx - 8, cy + 2, 16, 12), 3.14, 6.28, 2)

    return surf

def draw_torchwood(size=80):
    """绘制火炬树桩"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 树桩
    pygame.draw.rect(surf, (139, 90, 43), (cx - 20, cy - 10, 40, 45))
    pygame.draw.rect(surf, (160, 110, 60), (cx - 16, cy - 6, 32, 37))

    # 年轮
    pygame.draw.ellipse(surf, (139, 90, 43), (cx - 18, cy - 12, 36, 10))
    pygame.draw.ellipse(surf, (180, 140, 80), (cx - 14, cy - 10, 28, 7))

    # 火焰
    for i in range(3):
        offset = i * 8 - 8
        pygame.draw.ellipse(surf, (255, 200, 50), (cx + offset - 6, cy - 35, 12, 20))
        pygame.draw.ellipse(surf, (255, 100, 50), (cx + offset - 4, cy - 30, 8, 15))

    return surf

def draw_snowpea(size=80):
    """绘制寒冰豌豆"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 茎
    pygame.draw.rect(surf, (60, 140, 180), (cx - 5, cy + 5, 10, size // 2 - 5))

    # 头部
    pygame.draw.circle(surf, (100, 200, 255), (cx, cy - 5), 22)
    pygame.draw.circle(surf, (150, 220, 255), (cx, cy - 5), 18)

    # 炮管
    pygame.draw.rect(surf, (80, 180, 230), (cx + 10, cy - 12, 20, 14))
    pygame.draw.circle(surf, (60, 140, 200), (cx + 30, cy - 5), 7)

    # 冰晶效果
    for i in range(3):
        angle = i * 120 * math.pi / 180
        px = cx + int(15 * math.cos(angle))
        py = cy - 5 + int(15 * math.sin(angle))
        pygame.draw.circle(surf, (220, 240, 255), (px, py), 3)

    # 眼睛
    pygame.draw.circle(surf, (255, 255, 255), (cx - 5, cy - 10), 6)
    pygame.draw.circle(surf, (0, 0, 100), (cx - 3, cy - 10), 3)

    return surf

def draw_cherrybomb(size=80):
    """绘制樱桃炸弹"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 茎
    pygame.draw.line(surf, (80, 150, 80), (cx - 10, cy - 25), (cx, cy - 35), 3)
    pygame.draw.line(surf, (80, 150, 80), (cx + 10, cy - 25), (cx, cy - 35), 3)

    # 左樱桃
    pygame.draw.circle(surf, (255, 50, 50), (cx - 12, cy), 20)
    pygame.draw.circle(surf, (255, 100, 100), (cx - 15, cy - 5), 8)

    # 右樱桃
    pygame.draw.circle(surf, (255, 50, 50), (cx + 12, cy + 5), 20)
    pygame.draw.circle(surf, (255, 100, 100), (cx + 9, cy), 8)

    # 愤怒表情
    pygame.draw.circle(surf, (0, 0, 0), (cx - 15, cy - 3), 3)
    pygame.draw.circle(surf, (0, 0, 0), (cx + 9, cy + 2), 3)

    return surf

def draw_chomper(size=80):
    """绘制食人花"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 茎
    pygame.draw.rect(surf, (80, 150, 80), (cx - 6, cy + 10, 12, size // 2 - 10))

    # 大嘴
    pygame.draw.ellipse(surf, (150, 50, 150), (cx - 25, cy - 25, 50, 40))
    pygame.draw.ellipse(surf, (200, 80, 200), (cx - 20, cy - 20, 40, 30))

    # 牙齿
    for i in range(4):
        x = cx - 18 + i * 12
        pygame.draw.polygon(surf, (255, 255, 255),
                          [(x, cy - 10), (x + 6, cy - 10), (x + 3, cy - 2)])

    # 眼睛
    pygame.draw.circle(surf, (255, 255, 0), (cx - 10, cy - 20), 6)
    pygame.draw.circle(surf, (0, 0, 0), (cx - 10, cy - 20), 3)

    return surf

def draw_gatlingpea(size=80):
    """绘制机枪射手"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 茎
    pygame.draw.rect(surf, (60, 140, 60), (cx - 5, cy + 5, 10, size // 2 - 5))

    # 头部
    pygame.draw.circle(surf, (80, 180, 80), (cx, cy - 5), 22)

    # 四个炮管
    for i in range(4):
        y_offset = -15 + i * 8
        pygame.draw.rect(surf, (60, 140, 60), (cx + 10, cy + y_offset, 25, 6))
        pygame.draw.circle(surf, (50, 120, 50), (cx + 35, cy + y_offset + 3), 3)

    # 眼睛
    pygame.draw.circle(surf, (255, 255, 255), (cx - 5, cy - 10), 6)
    pygame.draw.circle(surf, (0, 0, 0), (cx - 3, cy - 10), 3)

    return surf

def draw_potatomine(size=80):
    """绘制土豆地雷"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2 + 10

    # 土豆身体
    pygame.draw.ellipse(surf, (180, 140, 100), (cx - 25, cy - 15, 50, 35))
    pygame.draw.ellipse(surf, (200, 160, 120), (cx - 20, cy - 12, 40, 28))

    # 天线
    pygame.draw.line(surf, (139, 90, 43), (cx, cy - 15), (cx, cy - 30), 3)
    pygame.draw.circle(surf, (255, 50, 50), (cx, cy - 32), 5)

    # 眼睛(闭合表示未激活)
    pygame.draw.line(surf, (0, 0, 0), (cx - 10, cy - 5), (cx - 5, cy - 5), 2)
    pygame.draw.line(surf, (0, 0, 0), (cx + 5, cy - 5), (cx + 10, cy - 5), 2)

    return surf

def draw_spikeweed(size=80):
    """绘制地刺"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2 + 15

    # 底座
    pygame.draw.ellipse(surf, (100, 100, 100), (cx - 30, cy - 5, 60, 20))

    # 尖刺
    for i in range(6):
        x = cx - 25 + i * 10
        pygame.draw.polygon(surf, (150, 150, 150),
                          [(x, cy - 5), (x + 5, cy - 25), (x + 10, cy - 5)])

    return surf

def draw_jalapeno(size=80):
    """绘制火爆辣椒"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 辣椒身体
    pygame.draw.ellipse(surf, (255, 80, 50), (cx - 15, cy - 25, 30, 55))
    pygame.draw.ellipse(surf, (255, 120, 80), (cx - 10, cy - 20, 20, 45))

    # 茎
    pygame.draw.rect(surf, (80, 150, 80), (cx - 3, cy - 32, 6, 10))

    # 火焰效果
    for i in range(3):
        y = cy - 15 + i * 12
        pygame.draw.ellipse(surf, (255, 200, 50, 128), (cx - 20, y, 10, 8))
        pygame.draw.ellipse(surf, (255, 200, 50, 128), (cx + 10, y + 3, 10, 8))

    # 愤怒表情
    pygame.draw.circle(surf, (0, 0, 0), (cx - 5, cy - 10), 3)
    pygame.draw.circle(surf, (0, 0, 0), (cx + 5, cy - 10), 3)
    pygame.draw.line(surf, (0, 0, 0), (cx - 8, cy - 15), (cx - 3, cy - 12), 2)
    pygame.draw.line(surf, (0, 0, 0), (cx + 8, cy - 15), (cx + 3, cy - 12), 2)

    return surf

def draw_iceshroom(size=80):
    """绘制冰冻蘑菇"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 蘑菇柄
    pygame.draw.rect(surf, (200, 200, 220), (cx - 8, cy, 16, 25))

    # 蘑菇帽
    pygame.draw.ellipse(surf, (150, 220, 255), (cx - 25, cy - 20, 50, 35))
    pygame.draw.ellipse(surf, (180, 240, 255), (cx - 20, cy - 15, 40, 25))

    # 冰晶
    for i in range(4):
        angle = i * 90 * math.pi / 180
        px = cx + int(15 * math.cos(angle))
        py = cy - 5 + int(12 * math.sin(angle))
        pygame.draw.circle(surf, (220, 240, 255), (px, py), 3)

    return surf

def draw_kernelpult(size=80):
    """绘制玉米投手"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 茎
    pygame.draw.rect(surf, (80, 150, 80), (cx - 5, cy + 10, 10, size // 2 - 10))

    # 叶子
    pygame.draw.ellipse(surf, (100, 180, 100), (cx - 25, cy + 5, 20, 12))

    # 玉米头部
    pygame.draw.ellipse(surf, (255, 220, 100), (cx - 18, cy - 25, 36, 40))
    pygame.draw.ellipse(surf, (255, 240, 150), (cx - 14, cy - 20, 28, 32))

    # 玉米粒
    for row in range(3):
        for col in range(3):
            x = cx - 8 + col * 8
            y = cy - 15 + row * 8
            pygame.draw.circle(surf, (200, 180, 50), (x, y), 3)

    return surf

def draw_doomshroom(size=80):
    """绘制毁灭菇"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 蘑菇柄
    pygame.draw.rect(surf, (120, 100, 150), (cx - 10, cy, 20, 25))

    # 蘑菇帽
    pygame.draw.ellipse(surf, (100, 50, 150), (cx - 28, cy - 25, 56, 40))
    pygame.draw.ellipse(surf, (140, 80, 180), (cx - 22, cy - 20, 44, 30))

    # 邪恶眼睛
    pygame.draw.circle(surf, (255, 50, 50), (cx - 10, cy - 10), 6)
    pygame.draw.circle(surf, (255, 50, 50), (cx + 10, cy - 10), 6)
    pygame.draw.circle(surf, (0, 0, 0), (cx - 10, cy - 10), 3)
    pygame.draw.circle(surf, (0, 0, 0), (cx + 10, cy - 10), 3)

    return surf

def draw_melonpult(size=80):
    """绘制西瓜投手"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 茎
    pygame.draw.rect(surf, (80, 150, 80), (cx - 6, cy + 10, 12, size // 2 - 10))

    # 叶子
    pygame.draw.ellipse(surf, (100, 200, 100), (cx - 28, cy + 5, 22, 14))
    pygame.draw.ellipse(surf, (100, 200, 100), (cx + 6, cy + 8, 22, 14))

    # 西瓜头部
    pygame.draw.circle(surf, (100, 200, 100), (cx, cy - 5), 25)
    pygame.draw.circle(surf, (120, 220, 120), (cx, cy - 5), 20)

    # 西瓜条纹
    for i in range(3):
        angle = (i * 60 - 60) * math.pi / 180
        x1 = cx + int(15 * math.cos(angle))
        y1 = cy - 5 + int(15 * math.sin(angle))
        x2 = cx + int(22 * math.cos(angle))
        y2 = cy - 5 + int(22 * math.sin(angle))
        pygame.draw.line(surf, (80, 150, 80), (x1, y1), (x2, y2), 2)

    # 眼睛
    pygame.draw.circle(surf, (255, 255, 255), (cx - 5, cy - 10), 6)
    pygame.draw.circle(surf, (0, 0, 0), (cx - 3, cy - 10), 3)

    return surf

def draw_zombie_basic(size=80):
    """绘制普通僵尸"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 身体
    pygame.draw.rect(surf, (100, 100, 100), (cx - 12, cy, 24, 35))

    # 手臂
    pygame.draw.rect(surf, (150, 180, 150), (cx - 25, cy + 5, 12, 25))
    pygame.draw.rect(surf, (150, 180, 150), (cx + 13, cy + 5, 12, 25))

    # 头部
    pygame.draw.circle(surf, (150, 180, 150), (cx, cy - 10), 18)

    # 眼睛
    pygame.draw.circle(surf, (255, 255, 255), (cx - 6, cy - 12), 5)
    pygame.draw.circle(surf, (255, 255, 255), (cx + 6, cy - 12), 5)
    pygame.draw.circle(surf, (200, 50, 50), (cx - 6, cy - 12), 2)
    pygame.draw.circle(surf, (200, 50, 50), (cx + 6, cy - 12), 2)

    # 嘴巴
    pygame.draw.arc(surf, (100, 50, 50), (cx - 8, cy - 5, 16, 10), 3.14, 6.28, 2)

    # 腿
    pygame.draw.rect(surf, (80, 80, 80), (cx - 10, cy + 35, 8, 20))
    pygame.draw.rect(surf, (80, 80, 80), (cx + 2, cy + 35, 8, 20))

    return surf

def draw_zombie_cone(size=80):
    """绘制路障僵尸"""
    surf = draw_zombie_basic(size)
    cx, cy = size // 2, size // 2

    # 路障
    pygame.draw.polygon(surf, (255, 140, 0),
                       [(cx - 12, cy - 25), (cx, cy - 40), (cx + 12, cy - 25)])
    pygame.draw.rect(surf, (255, 160, 50), (cx - 10, cy - 28, 20, 5))

    return surf

def draw_zombie_bucket(size=80):
    """绘制铁桶僵尸"""
    surf = draw_zombie_basic(size)
    cx, cy = size // 2, size // 2

    # 铁桶
    pygame.draw.rect(surf, (150, 150, 150), (cx - 15, cy - 35, 30, 25))
    pygame.draw.rect(surf, (180, 180, 180), (cx - 12, cy - 32, 24, 19))
    pygame.draw.line(surf, (100, 100, 100), (cx - 15, cy - 25), (cx + 15, cy - 25), 2)

    return surf

def draw_zombie_flag(size=80):
    """绘制带队僵尸"""
    surf = draw_zombie_basic(size)
    cx, cy = size // 2, size // 2

    # 旗帜杆
    pygame.draw.line(surf, (139, 69, 19), (cx + 15, cy - 30), (cx + 15, cy + 10), 3)

    # 旗帜
    pygame.draw.polygon(surf, (255, 50, 50),
                       [(cx + 15, cy - 30), (cx + 35, cy - 20), (cx + 15, cy - 10)])

    return surf

def draw_zombie_newspaper(size=80):
    """绘制看报僵尸"""
    surf = draw_zombie_basic(size)
    cx, cy = size // 2, size // 2

    # 报纸
    pygame.draw.rect(surf, (240, 240, 220), (cx - 20, cy + 5, 25, 30))
    pygame.draw.line(surf, (100, 100, 100), (cx - 18, cy + 10), (cx + 3, cy + 10), 1)
    pygame.draw.line(surf, (100, 100, 100), (cx - 18, cy + 15), (cx + 3, cy + 15), 1)
    pygame.draw.line(surf, (100, 100, 100), (cx - 18, cy + 20), (cx + 3, cy + 20), 1)

    return surf

def draw_zombie_polevault(size=80):
    """绘制撑杆跳僵尸"""
    surf = draw_zombie_basic(size)
    cx, cy = size // 2, size // 2

    # 撑杆
    pygame.draw.line(surf, (139, 69, 19), (cx + 20, cy - 20), (cx + 20, cy + 40), 4)

    return surf

def draw_zombie_football(size=80):
    """绘制橄榄球僵尸"""
    surf = draw_zombie_basic(size)
    cx, cy = size // 2, size // 2

    # 头盔
    pygame.draw.ellipse(surf, (150, 150, 150), (cx - 20, cy - 30, 40, 25))
    pygame.draw.rect(surf, (100, 100, 100), (cx - 18, cy - 20, 36, 5))

    # 护肩
    pygame.draw.rect(surf, (120, 120, 120), (cx - 20, cy, 40, 8))

    return surf

def draw_sun(size=40):
    """绘制阳光"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 光芒
    for i in range(8):
        angle = i * 45 * math.pi / 180
        x1 = cx + int(12 * math.cos(angle))
        y1 = cy + int(12 * math.sin(angle))
        x2 = cx + int(18 * math.cos(angle))
        y2 = cy + int(18 * math.sin(angle))
        pygame.draw.line(surf, (255, 220, 50), (x1, y1), (x2, y2), 2)

    # 太阳本体
    pygame.draw.circle(surf, (255, 220, 50), (cx, cy), 12)
    pygame.draw.circle(surf, (255, 240, 100), (cx, cy), 8)

    # 笑脸
    pygame.draw.circle(surf, (200, 150, 0), (cx - 3, cy - 2), 2)
    pygame.draw.circle(surf, (200, 150, 0), (cx + 3, cy - 2), 2)
    pygame.draw.arc(surf, (200, 150, 0), (cx - 4, cy, 8, 6), 3.14, 6.28, 2)

    return surf

def draw_projectile_pea(size=20):
    """绘制豌豆子弹"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (100, 200, 100), (size // 2, size // 2), 8)
    pygame.draw.circle(surf, (150, 230, 150), (size // 2 - 2, size // 2 - 2), 4)
    return surf

def draw_projectile_snowpea(size=20):
    """绘制冰豌豆"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (100, 200, 255), (size // 2, size // 2), 8)
    pygame.draw.circle(surf, (180, 230, 255), (size // 2 - 2, size // 2 - 2), 4)
    return surf

def draw_projectile_firepea(size=20):
    """绘制火豌豆"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 100, 50), (size // 2, size // 2), 8)
    pygame.draw.circle(surf, (255, 200, 100), (size // 2 - 2, size // 2 - 2), 4)
    return surf

def draw_projectile_kernel(size=16):
    """绘制玉米粒"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (255, 220, 100), (4, 4, 8, 10))
    return surf

def draw_projectile_butter(size=24):
    """绘制黄油"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (255, 220, 100), (2, 6, 20, 12))
    pygame.draw.ellipse(surf, (255, 240, 150), (4, 8, 16, 8))
    return surf

def draw_projectile_melon(size=30):
    """绘制西瓜"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (100, 200, 100), (size // 2, size // 2), 12)
    pygame.draw.circle(surf, (120, 220, 120), (size // 2, size // 2), 9)
    # 条纹
    pygame.draw.line(surf, (80, 150, 80), (size // 2 - 8, size // 2 - 8),
                    (size // 2 + 8, size // 2 + 8), 2)
    return surf

def draw_projectile_star(size=24):
    """绘制星星子弹(命中秒杀)"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    r = size // 2 - 1
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = r if i % 2 == 0 else r * 0.45
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    pygame.draw.polygon(surf, (255, 230, 80), pts)
    pygame.draw.polygon(surf, (255, 255, 200), pts, 1)
    pygame.draw.circle(surf, (255, 255, 220), (cx, cy), 2)
    return surf

def draw_projectile_explosionpea(size=24):
    """绘制爆炸豌豆(命中后3x3樱桃炸弹伤害)"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    # 主体深色豌豆
    pygame.draw.circle(surf, (60, 120, 50), (cx, cy), size // 2 - 1)
    pygame.draw.circle(surf, (90, 170, 70), (cx - 2, cy - 2), size // 2 - 4)
    # 引线
    pygame.draw.line(surf, (80, 60, 40), (cx, cy - size // 2 + 1), (cx + 4, cy - size // 2 - 3), 2)
    # 火花
    pygame.draw.circle(surf, (255, 180, 60), (cx + 4, cy - size // 2 - 3), 2)
    pygame.draw.circle(surf, (255, 240, 120), (cx + 5, cy - size // 2 - 4), 1)
    return surf

def draw_explosion(size=90):
    """绘制爆炸效果"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 多层爆炸
    pygame.draw.circle(surf, (255, 100, 50, 180), (cx, cy), size // 2 - 5)
    pygame.draw.circle(surf, (255, 200, 50, 200), (cx, cy), size // 2 - 15)
    pygame.draw.circle(surf, (255, 255, 200, 220), (cx, cy), size // 2 - 25)

    return surf

def draw_shovel(size=40):
    """绘制铲子图标 - 更精致的铲子"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    # 铲子手柄 (木质棕色)
    pygame.draw.rect(surf, (139, 90, 43), (cx - 3, 2, 6, cy - 2))
    # 手柄高光
    pygame.draw.rect(surf, (180, 120, 60), (cx - 1, 3, 2, cy - 4))

    # 手柄顶部圆头
    pygame.draw.circle(surf, (160, 100, 50), (cx, 4), 5)

    # 铲头连接处
    pygame.draw.rect(surf, (120, 120, 120), (cx - 5, cy - 2, 10, 6))

    # 铲头 (金属灰色)
    pygame.draw.polygon(surf, (180, 180, 190),
                       [(cx - 12, cy + 4), (cx + 12, cy + 4),
                        (cx + 9, cy + 16), (cx - 9, cy + 16)])
    # 铲头高光
    pygame.draw.polygon(surf, (210, 210, 220),
                       [(cx - 8, cy + 5), (cx + 8, cy + 5),
                        (cx + 5, cy + 10), (cx - 5, cy + 10)])
    # 铲头边缘
    pygame.draw.line(surf, (100, 100, 110),
                    (cx - 12, cy + 4), (cx - 9, cy + 16), 1)
    pygame.draw.line(surf, (100, 100, 110),
                    (cx + 12, cy + 4), (cx + 9, cy + 16), 1)
    pygame.draw.line(surf, (100, 100, 110),
                    (cx - 9, cy + 16), (cx + 9, cy + 16), 1)

    return surf

def create_all_sprites():
    """创建所有精灵图片并返回字典"""
    sprites = {}

    # 植物精灵
    sprites['plants'] = {
        PT_SUNFLOWER: draw_sunflower(),
        PT_PEASHOOTER: draw_peashooter(),
        PT_WALLNUT: draw_wallnut(),
        PT_TORCHWOOD: draw_torchwood(),
        PT_SNOWPEA: draw_snowpea(),
        PT_CHERRYBOMB: draw_cherrybomb(),
        PT_CHOMPER: draw_chomper(),
        PT_GATLINGPEA: draw_gatlingpea(),
        PT_POTATOMINE: draw_potatomine(),
        PT_SPIKEWEED: draw_spikeweed(),
        PT_JALAPENO: draw_jalapeno(),
        PT_ICESHROOM: draw_iceshroom(),
        PT_KERNELPULT: draw_kernelpult(),
        PT_DOOMSHROOM: draw_doomshroom(),
        PT_MELONPULT: draw_melonpult(),
    }

    # 僵尸精灵
    sprites['zombies'] = {
        ZT_BASIC: draw_zombie_basic(),
        ZT_FLAG: draw_zombie_flag(),
        ZT_CONE: draw_zombie_cone(),
        ZT_BUCKET: draw_zombie_bucket(),
        ZT_NEWSPAPER: draw_zombie_newspaper(),
        ZT_POLEVAULT: draw_zombie_polevault(),
        ZT_FOOTBALL: draw_zombie_football(),
    }

    # 子弹精灵
    sprites['projectiles'] = {
        PROJ_PEA: draw_projectile_pea(),
        PROJ_SNOWPEA: draw_projectile_snowpea(),
        PROJ_FIREPEA: draw_projectile_firepea(),
        PROJ_KERNEL: draw_projectile_kernel(),
        PROJ_BUTTER: draw_projectile_butter(),
        PROJ_MELON: draw_projectile_melon(),
        PROJ_STAR: draw_projectile_star(),
        PROJ_EXPLOSIONPEA: draw_projectile_explosionpea(),
    }

    # 其他精灵
    sprites['sun'] = draw_sun()
    sprites['explosion'] = draw_explosion()
    sprites['shovel'] = draw_shovel()

    return sprites

def save_sprites_to_files(sprites, directory='assets'):
    """保存精灵到文件(可选)"""
    import os
    os.makedirs(directory, exist_ok=True)

    for plant_type, surf in sprites['plants'].items():
        pygame.image.save(surf, f'{directory}/plant_{plant_type}.png')

    for zombie_type, surf in sprites['zombies'].items():
        pygame.image.save(surf, f'{directory}/zombie_{zombie_type}.png')

    for proj_type, surf in sprites['projectiles'].items():
        pygame.image.save(surf, f'{directory}/proj_{proj_type}.png')

    pygame.image.save(sprites['sun'], f'{directory}/sun.png')
    pygame.image.save(sprites['explosion'], f'{directory}/explosion.png')
    pygame.image.save(sprites['shovel'], f'{directory}/shovel.png')

def _fit_to_box(img, box):
    """等比缩放图片并居中放到 box x box 的透明画布上(保持长宽比)"""
    w, h = img.get_size()
    if w == 0 or h == 0:
        return img
    scale = min(box / w, box / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    scaled = pygame.transform.smoothscale(img, (nw, nh))
    surf = pygame.Surface((box, box), pygame.SRCALPHA)
    surf.blit(scaled, ((box - nw) // 2, (box - nh) // 2))
    return surf

def load_sprites_from_files(directory='assets', target_size=80):
    """从文件加载精灵(如果存在)"""
    import os
    sprites = create_all_sprites()

    # 尝试加载植物(等比缩放居中,避免立绘被压扁)
    for plant_type in sprites['plants'].keys():
        path = os.path.join(directory, f'plant_{plant_type}.png')
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                sprites['plants'][plant_type] = _fit_to_box(img, target_size)
            except:
                pass

    # 尝试加载僵尸
    for zombie_type in sprites['zombies'].keys():
        path = os.path.join(directory, f'zombie_{zombie_type}.png')
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                sprites['zombies'][zombie_type] = _fit_to_box(img, target_size)
            except:
                pass

    # 尝试加载子弹
    proj_sizes = {PROJ_PEA: 20, PROJ_SNOWPEA: 20, PROJ_FIREPEA: 20,
                  PROJ_KERNEL: 16, PROJ_BUTTER: 24, PROJ_MELON: 30,
                  PROJ_STAR: 24, PROJ_EXPLOSIONPEA: 24}
    for proj_type in sprites['projectiles'].keys():
        path = os.path.join(directory, f'proj_{proj_type}.png')
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                size = proj_sizes.get(proj_type, 20)
                sprites['projectiles'][proj_type] = pygame.transform.scale(img, (size, size))
            except:
                pass

    # 尝试加载其他
    for name in ['sun', 'explosion', 'shovel']:
        path = os.path.join(directory, f'{name}.png')
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                if name == 'sun':
                    sprites[name] = pygame.transform.scale(img, (40, 40))
                elif name == 'explosion':
                    sprites[name] = pygame.transform.scale(img, (90, 90))
                else:
                    sprites[name] = pygame.transform.scale(img, (40, 40))
            except:
                pass

    return sprites
