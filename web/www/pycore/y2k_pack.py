# -*- coding: utf-8 -*-
"""
JIUMI Y2K / 千禧年 风格包 — 离线确定性提示词构建器

美学来源（直采自 Y2K aesthetic 研究，未做联想）：
  - chrome / liquid metal, iridescent / holographic, frosted translucent plastic,
    glossy wet-look, rhinestone / bedazzled, bubblegum pink, Bondi blue,
    blobject, low-poly, circuit board, butterfly motif, techno-optimism.
  - 子风格分支：Y2K Glam / Cybercore / McBling / Frutiger Aero / Blobject / Retro-futurism

约定（与插件一致）：
  - 输出提示词 100% 纯英文；中文仅为 UI 标签（中英对照用）。
  - 仅依赖 random / re，零 ComfyUI 依赖，可被 EXE 直接 import。
"""

import random
import json

# ===================== 子风格（决定整体调性基调） =====================
SUBSTYLES = [
    ("Y2K 粉铬 Glam", "Y2K glam, pink-chrome duality, bedazzled, hot pink and liquid mercury chrome"),
    ("暗铬网络 Cybercore", "cybercore, chrome and liquid mercury, cold blue and neon green, matrix digital rain, wrapped eyewear"),
    ("水钻奢华 McBling", "McBling maximalism, rhinestones, Swarovski crystals, velour, bubblegum pink, butterfly motif, blinged-out"),
    ("光泽自然 Frutiger Aero", "Frutiger Aero, glossy textures, water droplets, bubbles, vibrant green landscape under clear blue sky, skeuomorphic glass"),
    ("气泡软未来 Blobject", "bubbly blobject forms, inflated rounded shapes, toy-like futurism, friendly consumer-tech optimism"),
    ("复古未来 Retro-futurism", "retro-futurism, futuristic as imagined in the year 2000, vintage CGI, optimistic techno-utopia"),
]

# ===================== 主体 =====================
# 分两类：【场景】以空间环境为主体（用户偏好）；其余为经典 Y2K 物件/人物单体。
SUBJECTS = [
    ("无（自由描述）", ""),

    # ---------- 场景型：空间 / 环境为主体 ----------
    ("【场景】商场中庭", "a Y2K shopping mall atrium, glass dome ceiling, escalators crossing diagonally, "
                        "neon storefront signs, glossy marble floor reflecting chrome and saturated color"),
    ("【场景】网吧电脑房", "a Y2K internet cafe, rows of bulky CRT monitors glowing cold blue, worn keyboards, "
                          "instant noodle cups, abstract patterned carpet, hazy air"),
    ("【场景】霓虹街机厅", "a neon arcade hall, candy-colored arcade cabinets, glowing marquee signs, "
                          "checkered floor receding into colored haze, prize claw machine"),
    ("【场景】CD 唱片店", "a CD record store interior, shelves packed with jewel cases, listening stations with "
                         "headphones, poster-covered walls, warm retail spot lighting"),
    ("【场景】少女卧室", "a Y2K teenage bedroom, walls covered in magazine posters, inflatable chair, "
                        "string lights, bean bag, lava lamp glowing on a glossy surface"),
    ("【场景】水族馆蓝光房间", "an aquarium room bathed in blue, glowing fish tanks with tropical fish, "
                             "bubbles rising, cyan light washing over glossy wet surfaces"),
    ("【场景】太空舱内饰", "a retro-futurist spaceship cockpit interior, chrome control panels, "
                          "glowing aqua instrument dials, porthole window filled with starfield"),
    ("【场景】洗车房霓虹隧道", "a neon car wash tunnel, colored light arches overhead, soap foam and water mist, "
                              "chrome reflections sliding over wet glossy surfaces"),
    ("【场景】学校电脑机房", "a school computer lab, rows of beige PCs with chunky monitors, grid carpet, "
                            "fluorescent ceiling lights, molded plastic chairs"),
    ("【场景】溜冰场", "a Y2K roller rink, polished reflective floor, mirrored disco ball scattering colored "
                      "light, pastel rental skates lined along the barrier"),
    ("【场景】快餐店卡座", "a fast food booth interior, orange molded plastic seats, glossy acrylic tabletop, "
                          "neon menu boards glowing overhead, checkerboard floor"),
    ("【场景】电梯轿厢", "a Y2K elevator interior, brushed stainless steel panels, mirrored ceiling, "
                        "glowing floor-number display, chrome handrail"),
    ("【场景】泳池更衣室", "a swimming pool changing room, glossy tile walls, drifting steam haze, "
                          "green-tinted underwater light, chrome locker rows"),
    ("【场景】天台水塔", "a rooftop water tower at sunset, chrome cylindrical tank on steel legs, "
                        "city skyline silhouette, warm golden rim light"),
    ("【场景】美食广场", "a shopping mall food court, plastic trays, neon menu signs stacked overhead, "
                        "glossy tabletops, pastel molded chairs"),
    ("【场景】卡拉 OK 包厢", "a karaoke box room, mirrored walls, color-changing LED strips, velvet sofa, "
                            "glossy songbook and microphone on the table"),
    ("【场景】加油站便利店", "a gas station convenience store at night, harsh fluorescent lighting, "
                            "glowing drink coolers, neon price sign, tiled floor"),
    ("【场景】美发沙龙", "a Y2K hair salon, chrome swivel chairs, pink neon signage on mirrored stations, "
                        "glossy product bottles lined on glass shelves"),
    ("【场景】保龄球馆", "a bowling alley interior, polished lanes stretching into colored haze, "
                        "colorful ball return machines, neon carpeting, overhead scoring screens"),
    ("【场景】电话亭", "a chrome public telephone booth, translucent panels, coiled cord handset, "
                      "reflective surfaces glowing at night"),

    # ---------- 物件 / 人物型：经典 Y2K 单体 ----------
    ("时尚人像·太空丸子头", "a fashion portrait of a model with space buns, glossy lips, tiny sunglasses, silver makeup"),
    ("透明塑料手提包", "a clear plastic handbag, see-through frosted shell, pastel iridescent finish"),
    ("翻盖手机", "a futuristic flip phone, chrome body, glowing tiny screen, bubble buttons"),
    ("机器萌宠", "a cute rounded robot mascot, baby blue accents, sparkles, simple low-poly form"),
    ("蝴蝶发夹少女", "a girl with a butterfly hairclip, rhinestone choker, glossy lips, y2k makeup"),
    ("iMac G3 全景", "a translucent Bondi-blue iMac G3, see-through candy shell revealing circuitry"),
    ("电子宠物机", "a Tamagotchi digital pet, translucent colored shell, tiny pixel screen"),
    ("太空人", "an astronaut in glossy white puffy suit, chrome helmet visor, floating in pastel space"),
    ("像素爱心", "a pixel heart, glossy 3D render, bubblegum pink, floating sparkles"),
    ("铬字母 Logo", "abstract 3D chrome lettering, liquid mercury bevel, lens flare"),
    ("音乐播放器界面", "a music player interface, translucent buttons, neon highlights, glass UI"),
    ("飞船 Logo", "a spaceship logo rendered in polished silver and aqua glow"),
    ("数码相机", "a chunky Y2K digital camera, silver plastic body, chunky lens, tiny LCD screen, wrist strap"),
    ("MP3 播放器", "a glossy white MP3 player, click wheel, chrome back, earbuds coiled around it"),
    ("光盘堆叠", "a stack of CD-ROM discs, iridescent rainbow reflective surfaces, scattered holo shine"),
    ("游戏手柄", "a translucent purple game controller, glossy plastic shell, colorful buttons, coiled cable"),
    ("果冻凉鞋", "a pair of jelly sandals, translucent candy-colored PVC, glossy shine, pastel sparkle"),
    ("水晶球", "a glossy crystal ball on a chrome stand, refracted rainbow light, floating glitter inside"),
]

# ===================== 材质 / 表面处理 =====================
MATERIALS = [
    ("液态铬 / 镜面金属", "liquid chrome, polished mirror metal, reflective mercury surface"),
    ("虹彩 / 全息", "iridescent holographic, rainbow oil-slick color shift, pearlescent"),
    ("磨砂半透明", "frosted translucent plastic, jelly-like acrylic, see-through frosted shell"),
    ("光泽湿感", "glossy wet-look finish, high-shine vinyl, patent leather sheen, lip-gloss surface"),
    ("水钻 / 满钻", "rhinestone encrusted, bedazzled, Swarovski crystal sparkle"),
    ("透明亚克力", "clear acrylic, transparent gel texture, candy-colored see-through plastic"),
    ("珍珠光泽", "pearl sheen, satin iridescent, soft opalescent glow"),
    ("金属银 / 玫瑰金", "brushed metal silver, rose gold metallic gradient"),
]

# ===================== 配色 =====================
COLORS = [
    ("泡泡糖粉", "bubblegum pink, hot pink, fuchsia"),
    ("电光蓝 / Bondi", "electric blue, Bondi blue, aqua cyan"),
    ("酸性绿 / 柠檬黄", "acid lime green, electric yellow"),
    ("薰衣草紫", "lavender violet, holo violet"),
    ("全息青", "holographic cyan, iridescent teal"),
    ("香槟金", "champagne gold, rose gold"),
    ("冰白", "pristine icy white, frosted white"),
    ("深紫", "deep purple, midnight glam"),
]

# ===================== 母题 / 装饰元素 =====================
MOTIFS = [
    ("无（不加母题）", ""),
    ("蝴蝶", "butterfly motifs, fluttering chrome butterfly wings"),
    ("像素爱心", "pixel heart, glossy 3D heart, floating sparkles"),
    ("星星 / 闪光", "star-shaped sparkles, glitter particles, lens flare bursts"),
    ("气泡 Blobject", "inflated bubble forms, blobject, rounded toy-like shapes"),
    ("低多边形", "low-poly 3D, visible faceting, early-2000s CGI roughness"),
    ("电路板 / 矩阵码", "circuit board traces, matrix digital rain, binary code, wireframe grid"),
    ("CD 纹", "CD-ROM iridescent disc, rainbow reflective surface"),
    ("花朵", "glossy hyper-saturated flowers, celestial bloom"),
    ("星球 / 星云", "planet, nebula, starfield, orbital path, cosmic futurism"),
    ("笑脸", "chrome smiley, y2k smiley face, glossy emoji"),
]

LIGHTING = [
    ("高光镜面", "specular highlight, sharp highlight points, glossy sheen"),
    ("镜头光晕", "lens flare, light burst, sunstar"),
    ("棚拍光泽", "soft studio lighting, clean highlights, product-shot gloss"),
    ("霓虹辉光", "neon glow, cyberpunk color grading, electric rim light"),
    ("铬反射", "chrome reflection, reflective environment, mirror surface bounce"),
]

ATMOSPHERE = [
    ("科技乐观", "techno-optimism, bright optimistic future, playful consumer-tech utopia"),
    ("复古未来", "retro-futurism, futuristic as imagined in 2000, vintage digital dream"),
    ("千禧狂热", "millennium fever, chrome and plastic flood, excited turn-of-century energy"),
    ("光泽最大化", "maximalist gloss, shiny excess, McBling glamour"),
    ("冷铬网络", "cold chrome cyberspace, digital frontier, matrix-green underworld"),
]

CAMERA_MOTION = [
    ("🎲 随机", ""),
    ("推近 Push In", "the camera pushes in toward the subject"),
    ("旋转展示 Rotate", "the subject slowly rotates, showing all glossy angles"),
    ("环绕 Arc", "the camera arcs around the subject in a slow circle"),
    ("上浮 Float Up", "the subject gently floats upward, bubbles rising"),
    ("静止 Static", "the camera holds still"),
]

MOTION = [
    ("🎲 随机", ""),
    ("蝴蝶振翅", "butterfly wings flutter, chrome dust drifting"),
    ("闪光漂浮", "rhinestone sparkles float and twinkle across the frame"),
    ("铬流动", "liquid chrome ripples and flows across the surface"),
    ("气泡上升", "translucent bubbles rise and pop, gel texture wobble"),
    ("全息变换", "iridescent color shifts through the spectrum, holographic shimmer"),
]

RANDOM_LABEL = "🎲 随机"


def _pick(enum_list, val):
    if val in (None, "", RANDOM_LABEL):
        return ""
    for item in enum_list:
        if item[0] == val:
            return item[1]
    return ""


def _resolve_rand(enum_list, val):
    if val in (None, "", RANDOM_LABEL):
        choices = [it[0] for it in enum_list if it[0] != RANDOM_LABEL and it[1] != ""]
        return random.choice(choices)
    return val


# ===================== GUI 字段声明（中英对照用） =====================
# (key, 中文名, enum, is_video_only)
FIELDS = [
    ("substyle", "子风格", SUBSTYLES, False),
    ("subject", "主体", SUBJECTS, False),
    ("material", "材质", MATERIALS, False),
    ("color", "配色", COLORS, False),
    ("motif", "母题", MOTIFS, False),
    ("lighting", "光影", LIGHTING, False),
    ("atmosphere", "氛围", ATMOSPHERE, False),
    ("motion", "动态（视频）", MOTION, True),
    ("camera_motion", "运镜（视频）", CAMERA_MOTION, True),
]

DEFAULTS = {
    "substyle": "Y2K 粉铬 Glam",
    "subject": "时尚人像·太空丸子头",
    "material": "液态铬 / 镜面金属",
    "color": "泡泡糖粉",
    "motif": "蝴蝶",
    "lighting": "高光镜面",
    "atmosphere": "科技乐观",
    "motion": "🎲 随机",
    "camera_motion": "🎲 随机",
}


def build(params, architecture="image"):
    """params: dict（含中文下拉值）；architecture: 'image' | 'h3'。
    返回 (english_prompt_text, json_string)。"""
    p = dict(DEFAULTS)
    p.update(params or {})

    substyle = _pick(SUBSTYLES, p.get("substyle"))
    subject = _pick(SUBJECTS, _resolve_rand(SUBJECTS, p.get("subject"))) if p.get("subject") else ""
    material = _pick(MATERIALS, p.get("material"))
    color = _pick(COLORS, p.get("color"))
    motif = _pick(MOTIFS, p.get("motif"))
    lighting = _pick(LIGHTING, p.get("lighting"))
    atmosphere = _pick(ATMOSPHERE, p.get("atmosphere"))

    parts = []
    if subject:
        parts.append(subject)
    else:
        parts.append("a glossy y2k object")
    parts += [material, color, motif, atmosphere, lighting, substyle]
    parts += [
        "early 2000s Y2K aesthetic",
        "vintage CGI render",
        "iridescent and glossy surfaces",
        "retro-futurism, techno-optimism",
        "bright saturated candy colors",
        "hyper-detailed, 8k, masterpiece",
    ]
    positive = ", ".join(x for x in parts if x).rstrip(", ")

    if architecture == "h3":
        motion = _pick(MOTION, _resolve_rand(MOTION, p.get("motion")))
        cam = _pick(CAMERA_MOTION, _resolve_rand(CAMERA_MOTION, p.get("camera_motion")))
        strength = int(p.get("motion_strength", 7) or 7)
        bits = [x for x in [motion, cam] if x]
        dyn = ("; ".join(bits) + ".") if bits else ""
        positive = (
            f"{positive}. "
            f"{dyn} "
            f"cinematic y2k video, smooth motion, --motion_strength {strength}/10, "
            f"early-2000s computer graphics animation, glossy futuristic optimism"
        ).strip()

    data = {
        "positive_prompt": positive,
        "style": "y2k",
        "architecture": architecture,
        "negative_prompt": "low quality, blurry, watermark, text, deformed, matte, dull, oversaturated, modern clothing",
    }
    return positive, json.dumps(data, ensure_ascii=False, indent=2)
