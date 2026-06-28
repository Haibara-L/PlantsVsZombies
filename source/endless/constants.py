"""游戏常量和数据表"""

# ========================= 窗口设置 =========================
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700
FPS = 60
TITLE = "植物大战僵尸 - 无尽模式"

# ========================= 网格设置 =========================
ROWS = 5
COLS = 9
GRID_OFFSET_X = 180  # 网格起始X坐标
GRID_OFFSET_Y = 100  # 网格起始Y坐标
CELL_WIDTH = 90      # 每格宽度
CELL_HEIGHT = 100    # 每格高度
PLANT_LOAD_SIZE = 80     # 精灵字典中植物的统一画布尺寸(按比例缩放居中)
PLANT_DISPLAY_SIZE = 62  # 种植后实际显示的植物尺寸(调小，避免占满整格)

# ========================= 植物类型 =========================
PT_SUNFLOWER = 0
PT_PEASHOOTER = 1
PT_WALLNUT = 2
PT_TORCHWOOD = 3
PT_SNOWPEA = 4
PT_CHERRYBOMB = 5
PT_CHOMPER = 6
PT_GATLINGPEA = 7
PT_POTATOMINE = 8
PT_SPIKEWEED = 9
PT_JALAPENO = 10
PT_ICESHROOM = 11
PT_KERNELPULT = 12
PT_DOOMSHROOM = 13
PT_MELONPULT = 14
PT_COUNT = 15

# ========================= 僵尸类型 =========================
ZT_BASIC = 0
ZT_FLAG = 1
ZT_CONE = 2
ZT_BUCKET = 3
ZT_NEWSPAPER = 4
ZT_POLEVAULT = 5
ZT_FOOTBALL = 6
ZT_COUNT = 7

# ========================= 子弹类型 =========================
PROJ_PEA = 0
PROJ_SNOWPEA = 1
PROJ_KERNEL = 2
PROJ_BUTTER = 3
PROJ_MELON = 4
PROJ_FIREPEA = 5
PROJ_STAR = 6          # 星星: 命中即秒杀
PROJ_EXPLOSIONPEA = 7  # 爆炸豌豆: 命中后3x3范围樱桃炸弹伤害

# ========================= 游戏状态 =========================
ST_PLAYING = 0
ST_BUFF_SELECT = 1
ST_GAMEOVER = 2
ST_WAVE_INTRO = 3
ST_MENU = 4

# ========================= 颜色定义 =========================
COLOR_BG = (34, 139, 34)           # 草地绿
COLOR_GRID = (100, 150, 100)       # 网格线
COLOR_GRID_DARK = (80, 120, 80)    # 深网格
COLOR_UI_BG = (40, 40, 40)         # UI背景
COLOR_UI_TEXT = (255, 255, 255)    # UI文字
COLOR_SUN = (255, 220, 50)         # 阳光黄
COLOR_HEALTH_GREEN = (50, 200, 50) # 健康绿
COLOR_HEALTH_YELLOW = (255, 200, 0) # 警告黄
COLOR_HEALTH_RED = (255, 50, 50)   # 危险红
COLOR_ZOMBIE = (150, 180, 150)     # 僵尸绿
COLOR_ZOMBIE_DARK = (100, 130, 100)
COLOR_ICE = (100, 200, 255)        # 冰冻蓝
COLOR_FIRE = (255, 100, 50)        # 火焰红

# ========================= 植物信息表 =========================
PLANT_INFO = {
    PT_SUNFLOWER: {
        'name': '向日葵', 'cost': 50, 'hp': 150, 'cooldown': 18.0,
        'damage': 0, 'desc': '产生阳光', 'color': (255, 200, 50)
    },
    PT_PEASHOOTER: {
        'name': '豌豆射手', 'cost': 100, 'hp': 150, 'cooldown': 1.2,
        'damage': 25, 'desc': '发射豌豆', 'color': (100, 200, 100)
    },
    PT_WALLNUT: {
        'name': '坚果', 'cost': 50, 'hp': 3000, 'cooldown': 0,
        'damage': 0, 'desc': '高血量挡僵尸', 'color': (180, 140, 80)
    },
    PT_TORCHWOOD: {
        'name': '火炬树桩', 'cost': 175, 'hp': 300, 'cooldown': 0,
        'damage': 0, 'desc': '点燃经过的豌豆', 'color': (200, 100, 50)
    },
    PT_SNOWPEA: {
        'name': '寒冰豌豆', 'cost': 175, 'hp': 150, 'cooldown': 1.2,
        'damage': 25, 'desc': '减速僵尸', 'color': (100, 200, 255)
    },
    PT_CHERRYBOMB: {
        'name': '樱桃炸弹', 'cost': 150, 'hp': 150, 'cooldown': 0,
        'damage': 1800, 'desc': '3x3范围爆炸', 'color': (255, 50, 50)
    },
    PT_CHOMPER: {
        'name': '食人花', 'cost': 150, 'hp': 300, 'cooldown': 30.0,
        'damage': 1800, 'desc': '一口吃掉僵尸', 'color': (150, 50, 150)
    },
    PT_GATLINGPEA: {
        'name': '机枪射手', 'cost': 450, 'hp': 150, 'cooldown': 1.2,
        'damage': 25, 'desc': '四连发豌豆', 'color': (80, 180, 80)
    },
    PT_POTATOMINE: {
        'name': '土豆地雷', 'cost': 25, 'hp': 150, 'cooldown': 0,
        'damage': 1800, 'desc': '12秒后激活爆炸', 'color': (180, 140, 100)
    },
    PT_SPIKEWEED: {
        'name': '地刺', 'cost': 100, 'hp': 9999, 'cooldown': 0.6,
        'damage': 20, 'desc': '伤害走过的僵尸', 'color': (120, 120, 120)
    },
    PT_JALAPENO: {
        'name': '火爆辣椒', 'cost': 125, 'hp': 150, 'cooldown': 0,
        'damage': 1800, 'desc': '一整行爆炸', 'color': (255, 80, 50)
    },
    PT_ICESHROOM: {
        'name': '冰冻蘑菇', 'cost': 75, 'hp': 150, 'cooldown': 0,
        'damage': 0, 'desc': '全屏冰冻5秒', 'color': (150, 220, 255)
    },
    PT_KERNELPULT: {
        'name': '玉米投手', 'cost': 100, 'hp': 150, 'cooldown': 2.5,
        'damage': 45, 'desc': '投掷玉米/黄油', 'color': (255, 220, 100)
    },
    PT_DOOMSHROOM: {
        'name': '毁灭菇', 'cost': 125, 'hp': 150, 'cooldown': 0,
        'damage': 1800, 'desc': '5x5范围毁灭', 'color': (100, 50, 150)
    },
    PT_MELONPULT: {
        'name': '西瓜投手', 'cost': 300, 'hp': 150, 'cooldown': 2.5,
        'damage': 80, 'desc': '投掷西瓜溅射', 'color': (100, 200, 100)
    },
}

# ========================= 僵尸信息表 =========================
ZOMBIE_INFO = {
    ZT_BASIC: {
        'name': '普通僵尸', 'hp': 180, 'speed': 0.18, 'damage': 80
    },
    ZT_FLAG: {
        'name': '带队僵尸', 'hp': 180, 'speed': 0.18, 'damage': 80
    },
    ZT_CONE: {
        'name': '路障僵尸', 'hp': 450, 'speed': 0.18, 'damage': 80
    },
    ZT_BUCKET: {
        'name': '铁桶僵尸', 'hp': 900, 'speed': 0.18, 'damage': 80
    },
    ZT_NEWSPAPER: {
        'name': '看报僵尸', 'hp': 280, 'speed': 0.18, 'damage': 80
    },
    ZT_POLEVAULT: {
        'name': '撑杆跳僵尸', 'hp': 400, 'speed': 0.36, 'damage': 80
    },
    ZT_FOOTBALL: {
        'name': '橄榄球僵尸', 'hp': 1100, 'speed': 0.36, 'damage': 80
    },
}

# ========================= 快捷键映射 =========================
PLANT_HOTKEYS = {
    '1': PT_SUNFLOWER,
    '2': PT_PEASHOOTER,
    '3': PT_WALLNUT,
    '4': PT_TORCHWOOD,
    '5': PT_SNOWPEA,
    '6': PT_CHERRYBOMB,
    '7': PT_CHOMPER,
    '8': PT_GATLINGPEA,
    '9': PT_POTATOMINE,
    '0': PT_SPIKEWEED,
    'q': PT_JALAPENO,
    'w': PT_ICESHROOM,
    'e': PT_KERNELPULT,
    'r': PT_DOOMSHROOM,
    't': PT_MELONPULT,
}

# ========================= 天赋(增益)信息 =========================
# id 0/1/2 为可叠加的数值增益; id 3/4/5 为一次性特殊天赋
# 游戏每波结束后从可用天赋池中随机抽 3 个供玩家选择
TALENT_INFO = {
    0: {
        'name': '豌豆精通',
        'title': '豌豆类攻击 +10%',
        'desc': '影响: 豌豆射手、寒冰豌豆、机枪射手的子弹伤害',
        'color': (100, 255, 100),
        'repeatable': True,
    },
    1: {
        'name': '光合作用',
        'title': '向日葵产量 +10%',
        'desc': '影响: 向日葵产出的阳光数量',
        'color': (255, 220, 50),
        'repeatable': True,
    },
    2: {
        'name': '投掷强化',
        'title': '投手类伤害 +10%',
        'desc': '影响: 玉米投手、西瓜投手的投掷伤害',
        'color': (255, 200, 100),
        'repeatable': True,
    },
    3: {
        'name': '豌豆百变',
        'title': '豌豆射手发射特殊子弹',
        'desc': '豌豆射手: 70%豌豆 / 10%黄油 / 10%星星(秒杀) / 10%爆炸豌豆(3x3)',
        'color': (180, 120, 255),
        'repeatable': False,
    },
    4: {
        'name': '双倍阳光',
        'title': '向日葵 50% 概率双倍产出',
        'desc': '向日葵有 50% 概率一次产出两颗阳光',
        'color': (255, 240, 150),
        'repeatable': False,
    },
    5: {
        'name': '连环投掷',
        'title': '投手类植物 50% 概率连击',
        'desc': '玉米投手、西瓜投手有 50% 概率连续攻击两次',
        'color': (255, 160, 100),
        'repeatable': False,
    },
}

# 特殊子弹的固定参数
BUTTER_DAMAGE_MULT_SRC = True   # 黄油伤害取西瓜投手基础伤害(80)
EXPLOSION_PEA_DAMAGE = 1800     # 爆炸豌豆范围伤害 = 樱桃炸弹
