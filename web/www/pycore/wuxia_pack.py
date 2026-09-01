# -*- coding: utf-8 -*-
"""
JiumiWuxiaVideoBuilder — 武侠图片 / 视频提示词生成节点

词汇来源（全部直采，未做联想）：
  - <Work-Fisher-MJ胡金铨风格提示词模板 .md>  → 胡金铨 9 参数 / 武侠类型 / 镜头 / 构图 / 光线 / 色调 / 氛围
  - <Seedence视频生成专业公开版.md>            → 九宫格分镜模板 / 违禁词替换 / 武器物理一致性
  - <Work-Fisher10秒视频提示词生成模板.md>     → 武器物理铁律 / 起承转合叙事 / 违禁词替换

约定：
  - 输入全部下拉枚举（值即英文提示词段），输出提示词 100% 纯英文，零翻译 / 零联网。
  - CATEGORY：图片节点 → JIUMI PromptForge/图片提示词，视频节点 → JIUMI PromptForge/视频提示词
  - 每个下拉末尾有「🎲 随机」项，选中则在生成时随机抽本枚举一个实际值；seed 可选，0 表示随机种子。
"""

import random
import re

# ==============================================================
# 胡金铨 恒定基底（文档 §2.1 + §2.2 + §十五，15 条核心参数）
# ==============================================================
HK_FILM_BASE = [
    "King Hu style",
    "1970s Technicolor film",
    "Kodak Ektachrome 1970s emulation",
    "2.35:1 Cinemascope widescreen",
    "35mm coarse grain film",
    "physical development effect simulation",
    "earth tones and pale cyan palette",
    "rustic cold stern solemn atmosphere",
    "side-backlighting, smoke scattering, strong light rays",
    "high contrast, enhanced chiaroscuro boundary",
    "foreground obstruction, minimalist composition, negative space",
    "natural motion of wind",
    "heavy yet restrained layering of earth tones and pale cyan",
    "Chinese aesthetic, Oriental beauty",
]

# ==============================================================
# 武侠类型（文档 §三，6 类）→ 用于 "King Hu [type] style"
# ==============================================================
WUXIA_TYPES = [
    ("文人武侠", "Literary Martial Arts"),
    ("奇幻武侠", "Fantasy Wuxia"),
    ("暗黑武侠", "Dark Wuxia"),
    ("史诗武侠", "Epic Wuxia"),
    ("浪漫武侠", "Romantic Wuxia"),
    ("武侠动作", "Wuxia Action"),
]

# ==============================================================
# 镜头类型（文档 §四，7 类）
# ==============================================================
SHOTS = [
    ("远景建立镜头", "Wide Establishing Shot"),
    ("中远景镜头", "Medium Wide Shot"),
    ("中景动作镜头", "Medium Action Shot"),
    ("中景肖像镜头", "Medium Portrait Shot"),
    ("微距特写镜头", "Macro Close-up, extreme detail"),
    ("极端特写镜头", "Extreme Close-up"),
    ("剪影镜头", "Wide Silhouette Shot, backlit against the horizon"),
]

# ==============================================================
# 构图方式（文档 §五，8 类）
# ==============================================================
COMPOSITION = [
    ("低角度剪影", "Low Angle Silhouette"),
    ("居中构图", "Centered Figure / Centered Detail Focus"),
    ("动态对角线", "Dynamic Diagonal"),
    ("对称月亮框架", "Symmetrical Moon Framing"),
    ("人物与广阔景色", "Figure Against Vast Landscape"),
    ("小人物巨龙对比", "Small Figure Against Giant Dragon"),
    ("前景遮挡构图", "Foreground Obstruction Composition"),
    ("极简留白构图", "Minimalist Composition with Negative Space"),
]

# ==============================================================
# 光线类型（文档 §六，8 类）
# ==============================================================
LIGHTING = [
    ("冷蓝顶光", "Cold Blue Overhead Light, oppressive and mysterious"),
    ("柔和漫射光", "Soft Diffused Overcast, tranquil and zen-like"),
    ("黄金时刻逆光", "Golden Hour Backlight, warm halo, transcendent glow"),
    ("冷月逆光", "Cold Moon Backlight, silver-blue rim light"),
    ("戏剧性火光", "Dramatic Chiaroscuro Fire Light, flickering shadows"),
    ("水下蓝光", "Underwater Blue Glow, diffused and ethereal"),
    ("红色灯笼光", "Red Lantern Glow, mysterious and oppressive"),
    ("侧逆光", "Side-backlighting with smoke scattering, strong light rays, high contrast, enhanced chiaroscuro boundary"),
]

# ==============================================================
# 色彩调性（文档 §七，6 类）
# ==============================================================
COLOR_TONES = [
    ("冷蓝色调", "Cold Blue / Steel Gray / Deep Black — oppressive, mysterious"),
    ("暖黄色调", "Warm Gold / Orange Red / Sky Blue — warmth, transcendence"),
    ("血红色调", "Blood Red / Flame Orange / Deep Black — intense, tragic"),
    ("青绿色调", "Emerald Green / Pink White / Lake Blue — ethereal, zen"),
    ("沙漠金色调", "Desert Gold / Dragon Yellow / Deep Shadow — vast, oppressive, fantasy"),
    ("大地苍青色调", "Earth Tones / Pale Cyan / Deep Shadow — restrained, heavy layering"),
]

# ==============================================================
# 氛围 / 场景（文档 §八，8 类）值即场景英文描述
# 纯风景模式时此场景词做主语，故写成"含具象景物"的完整句，避免一片空雾
# ==============================================================
ATMOSPHERES = [
    ("压抑神秘", "a sword graveyard shrouded in mist, countless broken blades stuck in the earth, shadows lengthening"),
    ("禅意宁静", "a serene courtyard garden at dawn, a lotus pond with pink blooms, a stone bridge and an old pine"),
    ("紧张期待", "a dark mountain pass, swirling fog, jagged pine trees and a weathered stone gate"),
    ("空灵奇幻", "an ethereal spirit realm, floating islands, drifting glow orbs and misty waterfalls"),
    ("黑暗神秘", "a shadowy temple hall, red lanterns flickering, carved beams and a long stone corridor"),
    ("浪漫唯美", "a classical Chinese garden, red walls, falling petals, a winding veranda and a lotus pond"),
    ("超脱悠远", "a cliff-edge peak overlooking rolling cloud seas at sunrise, a lone gnarled pine and distant monasteries"),
    ("古朴冷峻", "a desolate ancient path, stark rocks, twisted pines and a weathered stone tablet"),
    ("红墙宫苑", "a red lacquer palace courtyard, golden eaves, stone lions at the gate and a long veranda"),
    ("幽篁竹林", "a quiet bamboo grove, dappled sunlight through green stalks, a stone path winding in"),
    ("荷塘月色", "a lotus pond at night, koi beneath the water, duckweed on the surface and a moon bridge"),
    ("漓江山水", "towering karst peaks rising from a misty river, Guilin scenery, reeds along the bank"),
    ("戏台梨园", "an open opera stage with painted-face actors, red curtains, dragon reliefs on the beams and lantern light"),
    ("长城雄关", "the Great Wall snaking over distant mountain ridges, beacon towers and a vast northern horizon"),
    ("水乡古镇", "a riverside old town with stone alleys, tilted tiled roofs and a slow canal"),
    ("中国庭院", "a classical Chinese courtyard with lattice windows, rockery, a fish tank and a moon gate"),
    ("古寺禅院", "an ancient Buddhist temple with a golden roof, incense coils and a quiet courtyard"),
]

# ==============================================================
# 动作状态（文档示例 + 起承转合意象，7 类）
# ==============================================================
ACTIONS = [
    ("静坐调息", "standing in still meditation, hands at dantian, breathing with the wind"),
    ("拔剑出鞘", "drawing a curved jian, blade catching a glint of light"),
    ("展开对决", "facing an unseen opponent, sword raised in ready stance"),
    ("连斩三发", "executing a rapid three-slash combo, each strike a thin crescent of light"),
    ("轻掷飞剑", "throwing a flying sword that arcs like a silver comet"),
    ("翻身起势", "a fluid somersault into a low sweeping blade, dust scattering"),
    ("归心悟道", "sheathing the sword at the threshold as dawn breaks"),
    ("无（无动作）", ""),
]


# ===================== 视频专属动态枚举（H3/Minimax，区别于生图） =====================
# 人物动效 / 天气 / 植物 / 场景动 + 运镜镜头，视频节点专用，图片节点不引入
CAMERA_MOTION = [
    ("🎲 随机", ""),
    ("推近 Push In", "the camera pushes in toward the subject"),
    ("拉远 Pull Out", "the camera pulls out, revealing the wider scene"),
    ("左摇 Pan Left", "the camera pans left across the environment"),
    ("右摇 Pan Right", "the camera pans right across the environment"),
    ("左移 Truck Left", "the camera trucks left, following the lateral move"),
    ("右移 Truck Right", "the camera trucks right, following the lateral move"),
    ("仰拍 Tilt Up", "the camera tilts up toward the sky / towering height"),
    ("俯拍 Tilt Down", "the camera tilts down toward the ground / figures below"),
    ("环绕 Arc Shot", "the camera arcs around the subject in a slow circle"),
    ("跟拍 Tracking", "the camera tracks the moving subject, holding frame"),
    ("航拍 Aerial", "an aerial high-angle shot sweeps the landscape"),
    ("静止 Static", "the camera holds still, no movement"),
    ("手持微晃 Handheld", "a handheld camera with subtle natural shake"),
]
CHARACTER_MOTION = [
    ("🎲 随机", ""),
    ("缓步而行", "walking slowly with calm, measured steps"),
    ("衣袂翻飞", "robes and sleeves snapping in the wind"),
    ("御风而立", "standing poised against the wind, hair streaming"),
    ("腾跃起落", "leaping up and landing lightly on the feet"),
    ("拔剑出鞘", "drawing the blade from its scabbard in one fluid motion"),
    ("凝神调息", "standing still in meditation, breath steady with the wind"),
    ("回首远望", "turning the head to gaze into the distance"),
    ("挥剑生风", "swinging the sword so the blade cuts the air with a whistle"),
]
WEATHER_MOTION = [
    ("🎲 随机", ""),
    ("微风拂过", "a gentle breeze drifts through, stirring cloth and hair"),
    ("细雨斜织", "slanted fine rain weaves across the frame"),
    ("飞雪纷扬", "snowflakes drift and swirl through the air"),
    ("薄雾流动", "thin mist flows and shifts through the scene"),
    ("落叶随风", "fallen leaves tumble past on the wind"),
    ("晴空无风", "clear sky, still air, no weather movement"),
]
FOLIAGE_MOTION = [
    ("🎲 随机", ""),
    ("竹叶摇曳", "bamboo leaves sway and rustle in the wind"),
    ("落瓣飘零", "flower petals drift down and scatter on the breeze"),
    ("芦苇轻晃", "reeds sway gently along the water's edge"),
    ("荷塘涟漪", "ripples spread across the lotus pond surface"),
    ("松枝轻颤", "pine branches tremble faintly in the gust"),
    ("草叶起伏", "grass blades ripple in rolling waves"),
]
SCENE_MOTION = [
    ("🎲 随机", ""),
    ("烛火摇曳", "candle flames flicker and waver"),
    ("流水潺潺", "stream water flows and ripples over stones"),
    ("旗幡招展", "banners and flags snap and billow in the wind"),
    ("尘烟升起", "dust and smoke rise and curl upward"),
    ("波光粼粼", "water glints with shimmering light"),
    ("纸窗透暖", "warm light glows and shifts behind paper windows"),
]


# ==============================================================
# 主体 / 角色（文档示例人物 + 角色分析外貌清单）下拉，可选"纯风景"
# 每项 = (中文标签, 英文描述)；"无（纯风景）" 值为空串 → 不画人物
# ==============================================================
SUBJECTS = [
    ("无（纯风景）", ""),
    ("白衣女侠", "a valiant woman swordsman in white robes, poised for combat"),
    ("黑袍剑客", "a swordsman in black robes"),
    ("青袍文人", "a scholar in green robes"),
    ("青衣书生", "a young scholar in a plain cyan-blue robe, gentle and bookish, a scroll tucked in his belt"),
    ("银发剑仙", "a silver-haired sword immortal in pale blue robes"),
    ("红衣侠女", "a young woman warrior in silver-white light armor"),
    ("灰衣守护者", "a steadfast guardian in deep-gray windcoat"),
    ("蓑衣渔隐", "a recluse in a traditional opaque palm-leaf suoyi raincoat, sitting quietly by the riverbank"),
    ("僧人道人", "a Taoist monk in plain hemp robes"),
    ("蒙面刺客", "a masked assassin in dark tight attire"),
    ("将军 general", "a battle-scarred general in Chinese ceremonial armor, commanding presence"),
    ("战马 warhorse", "a warhorse in ornate barding, rearing by its rider"),
    ("戏曲伶人 opera actor", "a Chinese opera actor in painted-face makeup and brocade robe"),
    ("风水师 geomancer", "a Taoist geomancer in a flowing robe, holding a compass and a fengshui chart"),
    ("汉服仕女 hanfu lady", "a lady in elaborate hanfu, hairpin and dangling ornaments"),
    ("舞狮人 lion dancer", "a lion-dance performer in a vivid lion costume, leaping with the prop"),
    ("舞龙人 dragon dancer", "a dragon-dance performer guiding a coiling paper dragon with poles"),
]

# 物体 / 道具（文档角色分析武器清单以外的物件）下拉 + STRING 覆盖
# 值写成"演奏/持握姿态"完整句式：琴瑟类用端坐，笛箫伞灯类用站立手持
OBJECTS = [
    ("无（不加道具）", ""),
    ("古琴 guqin（端坐弹奏）", "seated cross-legged, cradling an ancient guqin, fingers on the strings"),
    ("酒葫芦 wine gourd", "with a wine gourd hanging at the belt"),
    ("油纸伞 paper umbrella（站立手持）", "standing and holding an oil-paper umbrella"),
    ("灯笼 lantern（站立手持）", "standing and holding a red paper lantern"),
    ("经卷 scripture（端坐展卷）", "seated and unrolling a scroll of scriptures"),
    ("玉箫 jade flute（站立横吹）", "standing and playing a jade flute horizontally"),
    ("残剑 broken sword", "a broken sword planted in the ground beside"),
    ("棋子 go pieces（对坐）", "seated at a board of go pieces"),
    ("信件 letter（站立手持）", "standing and holding a sealed letter"),
    ("琵琶 pipa（端坐抱弹）", "seated and cradling a pipa, fingers plucking the strings"),
    ("排笙 sheng（站立吹奏）", "standing and playing a pai-sheng mouth organ"),
    ("头上簪花 hair flower", "with a fresh flower pinned in the hair"),
    ("香炉 incense burner", "a bronze incense burner smoldering at the side"),
    ("二胡 erhu（站立拉奏）", "standing and drawing a bow across a two-string erhu"),
    ("中式扇子 folding fan", "holding a painted folding fan, half-open"),
    ("玉佩 jade pendant", "a jade pendant at the waist, softly glowing"),
    ("鱼竿 fishing rod", "holding a long vintage bamboo fishing rod, the line dropping straight into the still water"),
]
ELEMENTS = [
    ("无（不加点缀）", ""),
    ("白鹤 crane", "a white crane standing on one leg by the water, wings half-spread"),
    ("柳树 willow", "a weeping willow bending over the stream"),
    ("松树 pine", "an old upright pine with twisted branches"),
    ("柏松 cypress", "a solemn cypress towering nearby"),
    ("梅花 plum blossom", "a plum tree in sparse bloom, pink-white petals drifting"),
    ("竹子 bamboo", "a grove of green bamboo rustling in the wind"),
    ("水池 pool", "a still stone pool reflecting the sky"),
    ("鲤鱼 koi", "koi fish drifting beneath the clear water"),
    ("浮萍 duckweed", "duckweed scattered across the pond surface"),
    ("青苔 moss", "moss clinging to weathered stones"),
    ("红宫殿 red palace", "a red lacquer palace hall with golden eaves, Forbidden-City style"),
    ("石狮子 stone lion", "a carved stone lion guardian at the gate"),
    ("石拱门 stone arch", "a weathered stone archway framing the path"),
    ("龙浮雕 dragon relief", "a coiling dragon relief carved on the beam"),
    ("广西山水 karst", "towering karst peaks rising from a misty river, Guilin scenery"),
    ("青砖房 brick house", "a gray brick cottage with a tiled roof"),
    ("徽派建筑 hui-style", "a white-walled Anhui Hui-style dwelling with a dark tiled horse-head gable roof"),
    ("小船 skiff", "a slender skiff drifting on the river"),
    ("芦苇 reed", "reeds swaying along the bank"),
    ("芦苇花 reed flower", "fluffy reed flowers glowing in the backlight"),
    ("瀑布 waterfall", "a silver waterfall cascading down the cliff"),
    ("窗纸 window paper", "a lattice window with paper glowing warm from within"),
    ("小菊花 daisy", "small white and yellow daisies dotting the grass"),
    ("八卦 bagua", "a bagua trigram emblem carved or painted on the floor"),
    ("中式灯笼 lantern", "rows of red Chinese lanterns hanging under the eaves"),
    ("麒麟 qilin", "a mythical qilin statue standing guard at the step"),
    ("青花瓷 blue-white porcelain", "a blue-and-white porcelain vase on the side table"),
    ("瓷器 porcelain", "fine celadon porcelain wares displayed on a wooden shelf"),
    ("景泰蓝 cloisonne", "a cloisonne enamel censer gleaming with turquoise and gold"),
    ("玉 jade", "a jade carving resting on the stone sill"),
    ("绣品 embroidery", "a silk embroidery of cranes and clouds hung on the wall"),
    ("牡丹 peony", "a large cluster of lush peonies in full bloom, pink and crimson petals, prominently in the foreground"),
    ("宣纸 rice paper", "a scroll of xuan rice paper and a brush on the desk"),
    ("年画 newyear print", "a festive woodblock New Year picture pasted on the door"),
    ("舞狮 lion dance", "a colorful lion-dance troupe performing in the square"),
    ("舞龙 dragon dance", "a long coiling dragon dance winding through the street"),
    ("中国茶 tea", "a tea table with a porcelain set, steam rising from the cup"),
    ("田园 farmland", "terraced fields and vegetable beds, a rustic pastoral scene"),
    ("耕地 ploughing", "a farmer guiding an ox-drawn plough across the wet paddy"),
    ("种田 planting", "a figure bending to plant rice seedlings in the flooded field"),
]
WEAPONS = [
    ("无（不持武器）", "", ""),
    ("长剑 jian", "a straight double-edged jian", "blade"),
    ("弯刀 dao", "a curved single-edge dao saber", "blade"),
    ("长枪 qiang", "a long qiang spear", "pole"),
    ("战斧 axe", "a heavy battle axe", "pole"),
    ("双匕首 daggers", "twin butterfly daggers", "blade"),
    ("飞剑 flying sword", "a flying sword orbiting the wielder", "blade"),
    ("法杖 staff", "a glowing rune staff", "energy"),
    ("符咒 talisman", "paper talismans igniting with pentagrams", "energy"),
    ("能量剑 energy blade", "a humming energy blade", "energy"),
    ("拳掌 fist", "bare fists wreathed in qi", "fist"),
    ("护腕 gauntlet", "iron gauntlets", "fist"),
]

# 召唤物 / 伙伴（原 WEAPONS 里的「灵兽」移出，语义上不是手持武器）
# 值写成与人物同框的伴随描述，不套 wielding
SUMMON = [
    ("无（无召唤）", ""),
    ("灵兽 beast", "a summoned spirit beast companion at the side"),
    ("剑灵 sword spirit", "a translucent sword spirit hovering beside the wielder"),
    ("神鹤 crane spirit", "a divine crane spirit circling overhead"),
]

# 武器物理一致性铁律（文档 §5.2 / §6.2）
PHYSICS = {
    "blade": {
        "moves": "a clean slash, then a piercing thrust, then a spinning cleave",
        "impact": "cutting penetration, neat fractures, edge rebound",
    },
    "pole": {
        "moves": "a piercing lunge, then a sweeping strike, then a crushing smash",
        "impact": "penetration, knockback, blunt impact",
    },
    "energy": {
        "moves": "a released bolt, then a detonation, then an arcing discharge",
        "impact": "searing, explosion, energy shockwave",
    },
    "fist": {
        "moves": "a charging palm strike, then a block, then a throwing slam",
        "impact": "qi burst, ground shattering, shockwave",
    },
}

# ==============================================================
# 违禁词替换表（文档 §5.1 / §6.1，完整 8 组）
# ==============================================================
BANNED_WORDS = {
    "鲜血": "dark red traces / energy residual glow",
    "伤口": "crack / mark / imprint",
    "死亡": "stillness / slumber / unconsciousness",
    "尸体": "stillness / slumber / unconsciousness",
    "杀戮": "subdue / block / precise takedown",
    "暴力": "collision / strong impact",
    "殴打": "collision / strong impact",
    "恐怖": "tense / shocking",
    "血腥": "dark liquid / energy surge",
    "残忍": "sharp / decisive",
}


def _sanitize(text: str) -> str:
    if not text:
        return ""
    for bad, good in BANNED_WORDS.items():
        text = text.replace(bad, good)
    return text


# 下拉随机：选 RANDOM_LABEL 则在 forge 时随机抽本枚举一个实际项
RANDOM_LABEL = "🎲 随机"


def _with_random(enum_list):
    """返回『随机』选项放第一位的副本，供 INPUT_TYPES 下拉使用（默认也更醒目）。
    注意：ComfyUI 的 COMBO 只认字符串列表，不能把 (中文,英文) 元组直接塞进去，
    否则 UI 会把整个元组当 str 渲染，保存后也无法通过输入校验。"""
    out = [RANDOM_LABEL]
    # 部分枚举（CAMERA_MOTION 等动态枚举）自带 ('🎲 随机','') 项，必须去重，
    # 否则下拉里会出现两个「🎲 随机」。
    out += [it[0] for it in enum_list if it[0] != RANDOM_LABEL]
    return out


def _resolve(enum_list, val_ch):
    """若 val_ch 是随机哨兵，随机抽一个实际项（排除纯风景/无道具的空项与自身）；否则原样返回。"""
    if val_ch == RANDOM_LABEL:
        choices = [it[0] for it in enum_list if it[0] != RANDOM_LABEL and it[1] != ""]
        return random.choice(choices)
    return val_ch


def _pick(enum_list, val_ch):
    """enum_list 元素为 (中文, 英文) 或 (中文, 英文, 键)。返回英文。"""
    for item in enum_list:
        if item[0] == val_ch:
            return item[1]
    return ""


def _weapon(en_ch):
    for item in WEAPONS:
        if item[0] == en_ch:
            return item[1], item[2]
    return "a curved jian", "blade"


# 武器谓语分流：不同武器类别用不同英文谓语，避免 "wielding fists / beast" 等病句
# 纯风景（s_desc 为空）时一律不返回武器谓语
def _weapon_phrase(w_key, w_desc, s_desc):
    if not w_desc or not w_key or not s_desc:
        return ""
    if w_key == "fist":
        return "with " + w_desc
    if w_key == "energy":
        return "channeling " + w_desc
    return "wielding " + w_desc


# 明确手持的器物类道具：选了这些时，若武器仍是默认剑则不再叠加 wielding 武器，避免冲突
_HELD_OBJECTS = [
    "古琴", "guqin", "琵琶", "pipa", "玉箫", "jade flute", "排笙", "sheng",
    "油纸伞", "paper umbrella", "灯笼", "lantern", "信件", "letter",
    "中式扇子", "folding fan", "棋子", "go pieces", "经卷", "scripture",
    "鱼竿", "fishing rod",
]


def _weapon_suppressed_by_object(object_ch, object_desc, weapon_ch):
    """当道具已是明确手持物，且武器仍为用户未改的默认剑，则抑制武器谓语。"""
    o = (object_ch or "") + " " + (object_desc or "")
    if not any(h in o for h in _HELD_OBJECTS):
        return False
    # 用户显式选了非默认武器（如拳掌/法杖）时不抑制，尊重其意图
    if weapon_ch and weapon_ch not in ("长剑 jian", "无（不持武器）"):
        return False
    return True


def _subject(subject_ch, subject_desc):
    s = _pick(SUBJECTS, subject_ch) if subject_ch and subject_ch != "无（纯风景）" else ""
    if subject_desc and isinstance(subject_desc, str) and subject_desc.strip():
        s = subject_desc.strip()
    return s


# 纯风景构图改写：已知构图走高质量手写映射，未知构图走通用兜底（自动剥离 "Figure"）
# 龙在纯风景里视为景物而非人
_LANDSCAPE_COMPOSITION = {
    "Small Figure Against Giant Dragon": "Giant Dragon dominating the frame",
    "Figure Against Vast Landscape": "Vast Landscape with expansive negative space",
    "Centered Figure / Centered Detail Focus": "Centered Scenic Focus / Central Detail",
}
_FIGURE_RE = re.compile(r'\bFigure\b', re.IGNORECASE)


def _landscape_composition(comp):
    if comp in _LANDSCAPE_COMPOSITION:
        return _LANDSCAPE_COMPOSITION[comp]
    # 通用兜底：剥离 "Figure" 并清理残留空格/斜杠
    cleaned = _FIGURE_RE.sub('', comp)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' /')
    return cleaned if cleaned else comp


def _object(object_ch, object_desc):
    o = _pick(OBJECTS, object_ch) if object_ch and object_ch != "无（不加道具）" else ""
    if object_desc and isinstance(object_desc, str) and object_desc.strip():
        o = object_desc.strip()
    return o


def _element(element_ch, element_desc):
    e = _pick(ELEMENTS, element_ch) if element_ch and element_ch != "无（不加点缀）" else ""
    if element_desc and isinstance(element_desc, str) and element_desc.strip():
        e = element_desc.strip()
    return e


# 跨字段一致性联动：消除随机盲盒里的逻辑冲突（纯规则，不增模型）
def _harmonize(wuxia_type, subject, lighting, color_tone, atmosphere, weapon, object, element):
    e = element or ""
    o = object or ""
    # 1) 夜间发光元素（灯笼/窗纸）→ 强制夜景冷调，避免白天点灯
    if ("灯笼" in e or "lantern" in e or "窗纸" in e or "window paper" in e):
        lighting = "冷月逆光"
        color_tone = "冷蓝色调"
    # 2) 民俗表演元素（舞狮/舞龙/年画）→ 去掉战斗武器，表演者不扛枪
    if ("舞狮" in e or "lion dance" in e or "舞龙" in e or "dragon dance" in e
            or "年画" in e or "newyear print" in e):
        weapon = "拳掌 fist"
    # 2b) 舞狮/舞龙 → 主角强制为对应表演者，否则 krea2 会把独立人物吞掉只画表演
    if ("舞狮" in e or "lion dance" in e) and "舞狮人" not in (subject or ""):
        subject = "舞狮人 lion dancer"
    if ("舞龙" in e or "dragon dance" in e) and "舞龙人" not in (subject or ""):
        subject = "舞龙人 dragon dancer"
    # 3) 文房雅物（书卷/香炉/宣纸/绣品/乐器）→ 若在纯野外场景则改庭院，避免竹林摊书
    scholarly = ["经卷", "香炉", "宣纸", "绣品", "玉箫", "琵琶", "排笙"]
    wild = ["漓江山水", "长城雄关", "瀑布", "广西山水", "荷塘月色", "水乡古镇"]
    if any(s in o for s in scholarly) and atmosphere in wild:
        atmosphere = "中国庭院"
    return wuxia_type, subject, lighting, color_tone, atmosphere, weapon


def _build_img_prompt(wuxia_type, shot, composition, lighting, color_tone, atmosphere, action,
                      weapon_ch, weapon_desc, subject_ch, subject_desc, object_ch, object_desc, element_ch="", element_desc="",
                      summon_ch="", summon_desc=""):
    w_desc, w_key = _weapon(weapon_ch)
    if weapon_desc and weapon_desc.strip():
        w_desc = weapon_desc.strip()
    s_desc = _subject(subject_ch, subject_desc)
    o_desc = _object(object_ch, object_desc)
    e_desc = _element(element_ch, element_desc)
    sm_desc = _pick(SUMMON, summon_ch) if summon_ch and summon_ch != "无（无召唤）" else ""
    if summon_desc and summon_desc.strip():
        sm_desc = summon_desc.strip()

    # 主体做句首主语（纯风景时 s_desc 为空，则场景做主语）
    head = s_desc if s_desc else _pick(ATMOSPHERES, atmosphere)
    # 纯风景时把含 "Figure" 的构图改写为只留景/龙（避免模型画人）
    comp = _pick(COMPOSITION, composition)
    if not s_desc:
        comp = _landscape_composition(comp)
    parts = [
        _pick(SHOTS, shot),
        comp,
        _pick(LIGHTING, lighting),
        _pick(COLOR_TONES, color_tone),
        head,
    ]
    if s_desc:
        # 有人物时，场景词降级为环境补语；舞狮/舞龙等强表演元素降级为背景，保主角不被吞
        atm = _pick(ATMOSPHERES, atmosphere)
        if atm:
            parts.append("a scene of " + atm)
        parts.append(_pick(ACTIONS, action))
        if o_desc:
            parts.append(o_desc)
        # 武器谓语按类别分流（wielding/with/channeling），纯风景不拼；道具已是手持物时抑制默认剑
        if not _weapon_suppressed_by_object(object_ch, object_desc, weapon_ch):
            wp = _weapon_phrase(w_key, w_desc, s_desc)
            if wp:
                parts.append(wp)
        if sm_desc:
            parts.append("with " + sm_desc)
        if e_desc:
            if "lion dance" in e_desc or "dragon dance" in e_desc:
                # 把主角钉在前景句首，舞狮推到远处背景，避免 krea2 把主角吞掉
                parts.insert(0, "a clearly rendered " + s_desc + " in the foreground")
                parts.append("with a " + e_desc + " visible far in the background")
            else:
                parts.append("with " + e_desc)
    else:
        # 纯风景：场景词做主语（head 已是场景词），并强制与点缀元素同框（避免 krea2 只画其一）
        if e_desc:
            atm = _pick(ATMOSPHERES, atmosphere)
            if atm:
                # 把场景与点缀都写进同一句，强制 krea2 两者都渲染
                parts[-1] = "a scene of " + atm + ", with " + e_desc + " clearly visible in the frame"
            else:
                parts.append(e_desc)
        # 无点缀时 head 已是场景词，不再重复追加；纯风景不注入人物动作/武器/召唤
    parts += [
        "in the style of " + ", ".join(HK_FILM_BASE),
        "King Hu " + _pick(WUXIA_TYPES, wuxia_type) + " style",
    ]
    return _sanitize(", ".join(p for p in parts if p))


def _build_h3_prompt(wuxia_type, shot, composition, lighting, color_tone, atmosphere, action,
                     weapon_ch, weapon_desc, motion_strength, subject_ch, subject_desc, object_ch, object_desc, element_ch="", element_desc="",
                     camera_motion="", character_motion="", weather_motion="", foliage_motion="", scene_motion="",
                     summon_ch="", summon_desc=""):
    w_desc, w_key = _weapon(weapon_ch)
    if weapon_desc and weapon_desc.strip():
        w_desc = weapon_desc.strip()
    s_desc = _subject(subject_ch, subject_desc)
    o_desc = _object(object_ch, object_desc)
    e_desc = _element(element_ch, element_desc)
    sm_desc = _pick(SUMMON, summon_ch) if summon_ch and summon_ch != "无（无召唤）" else ""
    if summon_desc and summon_desc.strip():
        sm_desc = summon_desc.strip()
    phys = PHYSICS.get(w_key, PHYSICS["blade"])

    scene = _pick(ATMOSPHERES, atmosphere)
    dyn = _pick(LIGHTING, lighting)
    tone = _pick(COLOR_TONES, color_tone)
    act = _pick(ACTIONS, action)
    cam = _pick(CAMERA_MOTION, camera_motion)
    cmo = _pick(CHARACTER_MOTION, character_motion)
    wmo = _pick(WEATHER_MOTION, weather_motion)
    fmo = _pick(FOLIAGE_MOTION, foliage_motion)
    smo = _pick(SCENE_MOTION, scene_motion)
    # 纯风景时把含 "Figure" 的构图改写为只留景/龙（避免模型画人）
    comp = _landscape_composition(_pick(COMPOSITION, composition)) if not s_desc else _pick(COMPOSITION, composition)

    subject_noun = s_desc if s_desc else "the scene"
    subj_verb = ("The subject" if s_desc else "The scene")

    # 纯风景（无主体）走静态叙事，不注入任何人物起承转合动作
    if not s_desc:
        narrative = (
            f"The scene rests in {scene}, {dyn}, {tone} palette, "
            f"wind tugging the robes of no one, image freezing in lingering negative space."
        )
    else:
        # 起承转合 四段叙事（文档 §3.2）
        m = [x.strip() for x in phys["moves"].split(", ")]
        m = [x[5:] if x.lower().startswith("then ") else x for x in m]  # 去掉动作串自身的前缀 then
        narrative = (
            f"{subj_verb} begins in still poise within {scene}, {dyn}, {tone} palette. "
            f"{act}. "
            f"Then {m[0]}, qi and momentum building, rhythm accelerating. "
            f"Next {m[1]}, the core strike bursting with visual impact — {phys['impact']}. "
            f"Finally {m[2]}, {subject_noun} holds the finishing stance, "
            f"wind tugging the robe, image freezing in lingering negative space."
        )
    if o_desc:
        narrative += f" {o_desc} rests nearby, anchoring the frame."
    if e_desc:
        if s_desc:
            narrative += f" {e_desc} fills the surroundings."
        else:
            narrative += f" a scene of {scene}, with {e_desc} clearly visible in the frame."
    if sm_desc and s_desc:
        narrative += f" {sm_desc} stands with the subject."

    # 视频专属动态层（人物/天气/植物/场景动 + 运镜），区别于生图
    # 纯风景（无主体）不注入人物动态层 cmo，仅保留环境动（天气/植物/场景/运镜）
    _char_bits = [cmo] if s_desc else []
    motion_bits = [x for x in _char_bits + [wmo, fmo, smo, cam] if x]
    if motion_bits:
        narrative += " " + "; ".join(motion_bits) + "."

    return _sanitize(
        f"{narrative} "
        f"King Hu {_pick(WUXIA_TYPES, wuxia_type)} style, "
        f"{_pick(SHOTS, shot)}, {comp}, "
        f"cinematic wuxia, --ar 9:16, --style h3, "
        f"8k, masterpiece, ultra detailed, smooth motion, professional cinematography, "
        f"--motion_strength {motion_strength}/10"
    )


def _build_shot_grid(wuxia_type, shot, lighting, color_tone, atmosphere, action,
                     weapon_ch, weapon_desc, subject_ch, subject_desc, object_ch, object_desc, element_ch="", element_desc="",
                     camera_motion="", character_motion="", weather_motion="", foliage_motion="", scene_motion="",
                     summon_ch="", summon_desc=""):
    w_desc, w_key = _weapon(weapon_ch)
    if weapon_desc and weapon_desc.strip():
        w_desc = weapon_desc.strip()
    s_desc = _subject(subject_ch, subject_desc)
    o_desc = _object(object_ch, object_desc)
    e_desc = _element(element_ch, element_desc)
    sm_desc = _pick(SUMMON, summon_ch) if summon_ch and summon_ch != "无（无召唤）" else ""
    if summon_desc and summon_desc.strip():
        sm_desc = summon_desc.strip()
    scene = _pick(ATMOSPHERES, atmosphere)
    dyn = _pick(LIGHTING, lighting)
    tone = _pick(COLOR_TONES, color_tone)
    if s_desc:
        who = (s_desc + (" with " + w_desc if w_desc and not _weapon_suppressed_by_object(object_ch, object_desc, weapon_ch) else "") + (", " + o_desc if o_desc else "") + (", amid " + e_desc if e_desc else "") + (", with " + sm_desc if sm_desc else ""))
    else:
        # 纯风景：强制场景+点缀同框
        if e_desc:
            who = (tone + ", a scene of " + scene + ", with " + e_desc + " present in the frame, " + dyn)
        else:
            who = (tone + ", " + scene + ", " + dyn)
    cam = _pick(CAMERA_MOTION, camera_motion)
    cmo = _pick(CHARACTER_MOTION, character_motion)
    wmo = _pick(WEATHER_MOTION, weather_motion)
    fmo = _pick(FOLIAGE_MOTION, foliage_motion)
    smo = _pick(SCENE_MOTION, scene_motion)
    motion_bits = [x for x in [cmo, wmo, fmo, smo, cam] if x]
    base = f"{_pick(SHOTS, shot)}, {who}" + (", " + "; ".join(motion_bits) if motion_bits else "")

    # 九宫格标准模板（文档 §4.5）：3 行 × 3 列，铺垫 / 核心 / 收尾
    rows = [
        ("Row 1 — Setup (0-5s)",
         ["the hero stands firm, blade planted, measured breaths — establishing",
          "wind stirs the sleeves, medium shot, atmosphere laid",
          "a close look at the eyes, resolve forming — emotion"]),
        ("Row 2 — Core (5-10s)",
         ["drawing the weapon in one fluid motion, first explosive strike",
          "the core clash, air distortion and light streaks visible",
          "a leaping finishing strike, power fully released"]),
        ("Row 3 — Resolution (10-15s)",
         ["the strike settles, dust drifting down — falling action",
          "a beat of still emotion, breath released",
          "final freeze, subject in silhouette against pale cyan sky"]),
    ]

    out = [
        "Generate a 3x3 nine-grid vertical storyboard, clean symmetric layout, white background,",
        "9 panels divided by thin black lines, each panel 9:16 ratio, consistent King Hu style,",
        "each panel bottom-right a small white rounded label: X-1, X-2 ... X-9.",
        "No text, no subtitle, no timecode, no watermark.\n",
    ]
    n = 0
    for row_label, cells in rows:
        out.append(row_label + ":")
        for c in cells:
            n += 1
            out.append(f"  [{n}] {base}, {c}")
    return _sanitize("\n".join(out))


class JiumiWuxiaImageBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wuxia_type": (_with_random(WUXIA_TYPES), {"default": "文人武侠"}),
                "subject": (_with_random(SUBJECTS), {"default": "无（纯风景）"}),
                "shot_type": (_with_random(SHOTS), {"default": "远景建立镜头"}),
                "composition": (_with_random(COMPOSITION), {"default": "居中构图"}),
                "lighting": (_with_random(LIGHTING), {"default": "柔和漫射光"}),
                "color_tone": (_with_random(COLOR_TONES), {"default": "大地苍青色调"}),
                "atmosphere": (_with_random(ATMOSPHERES), {"default": "禅意宁静"}),
                "action": (_with_random(ACTIONS), {"default": "静坐调息"}),
                "weapon": (_with_random(WEAPONS), {"default": "长剑 jian"}),
                "object": (_with_random(OBJECTS), {"default": "无（不加道具）"}),
                "element": (_with_random(ELEMENTS), {"default": "无（不加点缀）"}),
                "summon": (_with_random(SUMMON), {"default": "无（无召唤）"}),
            },
            "optional": {
                "subject_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义主体描述，留空则用下拉"}),
                "weapon_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义武器描述，留空则用下拉"}),
                "object_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义物体描述，留空则用下拉"}),
                "element_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义景物点缀描述，留空则用下拉"}),
                "summon_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义召唤物描述，留空则用下拉"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 4294967294, "step": 1}),
            },
        }
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "prompt_json")
    FUNCTION = "forge"
    CATEGORY = "JIUMI PromptForge/图片提示词"

    def forge(self, wuxia_type, subject, shot_type, composition, lighting, color_tone, atmosphere, action, weapon, object, element, subject_desc=None, weapon_desc=None, object_desc=None, element_desc=None, summon=None, summon_desc=None, seed=0):
        wuxia_type = _resolve(WUXIA_TYPES, wuxia_type)
        subject = _resolve(SUBJECTS, subject)
        shot_type = _resolve(SHOTS, shot_type)
        composition = _resolve(COMPOSITION, composition)
        lighting = _resolve(LIGHTING, lighting)
        color_tone = _resolve(COLOR_TONES, color_tone)
        atmosphere = _resolve(ATMOSPHERES, atmosphere)
        action = _resolve(ACTIONS, action)
        weapon = _resolve(WEAPONS, weapon)
        object = _resolve(OBJECTS, object)
        element = _resolve(ELEMENTS, element)
        summon = _resolve(SUMMON, summon) if summon is not None else "无（无召唤）"
        wuxia_type, subject, lighting, color_tone, atmosphere, weapon = _harmonize(
            wuxia_type, subject, lighting, color_tone, atmosphere, weapon, object, element)
        # 纯风景（无主体）默认无人物动作，符合「无风无动作」诉求
        if not _subject(subject, subject_desc).strip():
            action = "无（无动作）"
        pos = _build_img_prompt(wuxia_type, shot_type, composition, lighting, color_tone, atmosphere, action, weapon, weapon_desc, subject, subject_desc, object, object_desc, element, element_desc, summon, summon_desc)
        neg = "low quality, blurry, watermark, text, deformed, extra limbs, oversaturated, modern clothing, 3D render, cartoon, plastic raincoat, modern fishing reel, lure, spinning rod, baseball cap, sunglasses"
        json_out = '{"positive_prompt": "%s", "negative_prompt": "%s", "seed": %d}' % (pos.replace('"', "'"), neg, seed)
        return (pos, neg, json_out)


class JiumiWuxiaVideoBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wuxia_type": (_with_random(WUXIA_TYPES), {"default": "武侠动作"}),
                "subject": (_with_random(SUBJECTS), {"default": "无（纯风景）"}),
                "shot_type": (_with_random(SHOTS), {"default": "远景建立镜头"}),
                "composition": (_with_random(COMPOSITION), {"default": "动态对角线"}),
                "lighting": (_with_random(LIGHTING), {"default": "侧逆光"}),
                "color_tone": (_with_random(COLOR_TONES), {"default": "大地苍青色调"}),
                "atmosphere": (_with_random(ATMOSPHERES), {"default": "紧张期待"}),
                "action": (_with_random(ACTIONS), {"default": "拔剑出鞘"}),
                "weapon": (_with_random(WEAPONS), {"default": "长剑 jian"}),
                "object": (_with_random(OBJECTS), {"default": "无（不加道具）"}),
                "element": (_with_random(ELEMENTS), {"default": "无（不加点缀）"}),
                "summon": (_with_random(SUMMON), {"default": "无（无召唤）"}),
            },
            "optional": {
                "subject_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义主体描述，留空则用下拉"}),
                "weapon_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义武器描述，留空则用下拉"}),
                "object_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义物体描述，留空则用下拉"}),
                "element_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义景物点缀描述，留空则用下拉"}),
                "summon_desc": ("STRING", {"default": "", "multiline": False, "placeholder": "自定义召唤物描述，留空则用下拉"}),
                "motion_strength": ("INT", {"default": 7, "min": 1, "max": 10, "step": 1}),
                "camera_motion": (_with_random(CAMERA_MOTION), {"default": "🎲 随机"}),
                "character_motion": (_with_random(CHARACTER_MOTION), {"default": "🎲 随机"}),
                "weather_motion": (_with_random(WEATHER_MOTION), {"default": "🎲 随机"}),
                "foliage_motion": (_with_random(FOLIAGE_MOTION), {"default": "🎲 随机"}),
                "scene_motion": (_with_random(SCENE_MOTION), {"default": "🎲 随机"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 4294967294, "step": 1}),
            },
        }
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("h3_prompt", "image_prompt", "shot_grid", "prompt_json")
    FUNCTION = "forge"
    CATEGORY = "JIUMI PromptForge/视频提示词"

    def forge(self, wuxia_type, subject, shot_type, composition, lighting, color_tone, atmosphere, action, weapon, object, element, subject_desc=None, weapon_desc=None, object_desc=None, element_desc=None, motion_strength=7, camera_motion="🎲 随机", character_motion="🎲 随机", weather_motion="🎲 随机", foliage_motion="🎲 随机", scene_motion="🎲 随机", summon=None, summon_desc=None, seed=0):
        wuxia_type = _resolve(WUXIA_TYPES, wuxia_type)
        subject = _resolve(SUBJECTS, subject)
        shot_type = _resolve(SHOTS, shot_type)
        composition = _resolve(COMPOSITION, composition)
        lighting = _resolve(LIGHTING, lighting)
        color_tone = _resolve(COLOR_TONES, color_tone)
        atmosphere = _resolve(ATMOSPHERES, atmosphere)
        action = _resolve(ACTIONS, action)
        weapon = _resolve(WEAPONS, weapon)
        object = _resolve(OBJECTS, object)
        element = _resolve(ELEMENTS, element)
        summon = _resolve(SUMMON, summon) if summon is not None else "无（无召唤）"
        camera_motion = _resolve(CAMERA_MOTION, camera_motion)
        character_motion = _resolve(CHARACTER_MOTION, character_motion)
        weather_motion = _resolve(WEATHER_MOTION, weather_motion)
        foliage_motion = _resolve(FOLIAGE_MOTION, foliage_motion)
        scene_motion = _resolve(SCENE_MOTION, scene_motion)
        wuxia_type, subject, lighting, color_tone, atmosphere, weapon = _harmonize(
            wuxia_type, subject, lighting, color_tone, atmosphere, weapon, object, element)
        # 纯风景（无主体）默认无人物动作，符合「无风无动作」诉求
        if not _subject(subject, subject_desc).strip():
            action = "无（无动作）"
        ms = motion_strength if motion_strength is not None else 7
        img = _build_img_prompt(wuxia_type, shot_type, composition, lighting, color_tone, atmosphere, action, weapon, weapon_desc, subject, subject_desc, object, object_desc, element, element_desc, summon, summon_desc)
        h3 = _build_h3_prompt(wuxia_type, shot_type, composition, lighting, color_tone, atmosphere, action, weapon, weapon_desc, ms, subject, subject_desc, object, object_desc, element, element_desc, camera_motion, character_motion, weather_motion, foliage_motion, scene_motion, summon, summon_desc)
        grid = _build_shot_grid(wuxia_type, shot_type, lighting, color_tone, atmosphere, action, weapon, weapon_desc, subject, subject_desc, object, object_desc, element, element_desc, camera_motion, character_motion, weather_motion, foliage_motion, scene_motion, summon, summon_desc)
        json_out = '{"h3_prompt": "%s", "image_prompt": "%s", "shot_grid": "%s", "seed": %d}' % (
            h3.replace('"', "'"), img.replace('"', "'"), grid.replace('"', "'"), seed)
        return (h3, img, grid, json_out)


# ===================== 注册（与现有范式一致，供 __init__.py 导入） =====================
WUXIA_CLASS_MAPPINGS = {
    "JiumiWuxiaImageBuilder": JiumiWuxiaImageBuilder,
    "JiumiWuxiaVideoBuilder": JiumiWuxiaVideoBuilder,
}
WUXIA_DISPLAY_NAME_MAPPINGS = {
    "JiumiWuxiaImageBuilder": "武侠图片提示词",
    "JiumiWuxiaVideoBuilder": "武侠视频提示词",
}
