# -*- coding: utf-8 -*-
"""
JIUMI 提示词工作台 — 风格包注册表与统一调度器

把 4 个风格包（巨构 / 武侠 / 普通 / 千禧年）与 2 种架构（image / h3）统一封装。
所有 builder 均为纯 Python（来自插件 vendor 的 core 文件），零 ComfyUI 依赖。

每个风格包声明 FIELDS（供 GUI 渲染下拉），build() 负责把中文下拉值解析成英文提示词。
"""

import random
import json
import re

from . import mega_pack, wuxia_pack, y2k_pack

RAND = "🎲 随机"

# 中文画质 / 氛围尾缀（让中文提示词也成串、成段，而不仅是字段对照）
ZH_TAIL = {
    "mega": "，电影级巨物感，超精细，高细节，8K 分辨率，史诗尺度，极致写实，大师级作品，氛围磅礴，电影布光",
    "normal": "，高细节，8K，电影感，大师级作品，色彩饱满，构图稳健，质感细腻",
    "wuxia": "，水墨电影质感，意境悠远，留白得当，东方古典美学，空灵禅意，笔意淋漓",
    "y2k": "，千禧年科技乐观主义，高饱和，锃亮质感，梦幻气泡感，复古未来主义，闪亮通透",
}


def _zh_no(v):
    """过滤掉『无（…）』『随机』类占位值。"""
    if not v:
        return True
    s = str(v)
    if s.startswith("无（") or s in (RAND, "🎲 随机", "无", "⚪ 无（标准框）"):
        return True
    return False


# ===================== 随机键解析 =====================
def _rand_key(d, key):
    """下拉选随机 / 空 → 抽一个实际键（排除 'rand' 哨兵）。"""
    if key in (None, "", RAND, "rand"):
        choices = [k for k in d.keys() if k != "rand"]
        return random.choice(choices)
    return key


def _dict_options(d):
    """mega_pack 的 dict 结构：{key: {'label': ...}} → [(中文label, key)]。"""
    return [(v.get("label", k), k) for k, v in d.items()]


def _mega_options(d):
    """mega_pack.MEGA 的条目只有 'name'（中文名）没有 'label' 键，
    用 _dict_options 会 fallback 成英文 key（robot / karstMega …），下拉就变英文。
    这里按 label → name → key 顺序取中文名。"""
    return [((v.get("label") or v.get("name") or k), k) for k, v in d.items()]


def _is_rand_item(it):
    return str(it[0]).strip() in (RAND, "随机", "rand", "🎲随机", "🎲 随机")


def _with_random_first(enum_list):
    """统一下拉排序：🎲 随机 第一；词库自带『无（…）』排第二；其余保持原顺序。
    用户要求：随机第一，有"无"的其次，没有就随机第一。没有随机的自动补一个。"""
    items = list(enum_list)
    if not any(_is_rand_item(it) for it in items):
        items = [(RAND, "")] + items
    rands = [it for it in items if _is_rand_item(it)]
    nones = [it for it in items if str(it[0]).startswith("无")]
    rest = [it for it in items if not _is_rand_item(it) and not str(it[0]).startswith("无")]
    return rands + nones + rest


def _enum_options(enum_list):
    """wuxia/y2k 的 enum 结构：[(中文, 英文)] → [(中文, 中文)]（值即中文标签）。
    统一补/排『🎲 随机』到第一项。"""
    return [(it[0], it[0]) for it in _with_random_first(enum_list)]


def _h3_cam_options(prefix):
    """H3 运镜下拉。H3_CAM_ALL 自带中文 label；按 mega_ / norm_ 前缀分流，
    因为 buildH3 内部按 is_mega 取 mega/normal 文案，类型给错会拿到字符串 'None'。"""
    out = []
    for k, v in mega_pack.H3_CAM_ALL.items():
        if k == "auto" or k.startswith(prefix):
            out.append((v.get("label", k), k))
    return out


# ===================== 各包字段声明（GUI 渲染用） =====================
MEGA_FIELDS = [
    {"key": "pk", "label": "巨构主体", "options": _mega_options(mega_pack.MEGA)},
    {"key": "styleKey", "label": "风格", "options": _dict_options(mega_pack.STYLES)},
    {"key": "varKey", "label": "视角变体", "options": _dict_options(mega_pack.MVAR)},
    {"key": "lightKey", "label": "光影", "options": _dict_options(mega_pack.LIGHTS)},
    {"key": "envKey", "label": "环境", "options": _dict_options(mega_pack.ENVS)},
    {"key": "lensKey", "label": "镜头", "options": _dict_options(mega_pack.LENSES)},
    {"key": "morphKey", "label": "形态", "options": _dict_options(mega_pack.MEGA_MORPH)},
    {"key": "theme", "label": "题材（联动风格）", "options": _dict_options(mega_pack.THEME_POOL)},
    {"key": "mix_mode", "label": "风格混合",
     "options": [(k, v) for k, v in mega_pack.MIX_L2K.items()]},
    {"key": "cam", "label": "运镜（视频）", "options": _h3_cam_options("mega"), "video": True},
    {"key": "shots", "label": "分镜数（视频）", "kind": "int", "video": True,
     "min": 1, "max": 5, "default": 1},
    {"key": "seed", "label": "随机种子", "kind": "int"},
]

NORMAL_FIELDS = [
    {"key": "styleKey", "label": "风格", "options": _dict_options(mega_pack.STYLES)},
    {"key": "catKey", "label": "类别", "options": _dict_options(mega_pack.CATS)},
    {"key": "lensKey", "label": "镜头", "options": _dict_options(mega_pack.LENSES)},
    {"key": "lightKey", "label": "光影", "options": _dict_options(mega_pack.LIGHTS)},
    {"key": "envKey", "label": "环境", "options": _dict_options(mega_pack.ENVS)},
    {"key": "viewKey", "label": "宏大视角", "options": _dict_options(mega_pack.NORMAL_VIEW)},
    {"key": "theme", "label": "题材（联动风格）", "options": _dict_options(mega_pack.THEME_POOL)},
    {"key": "mix_mode", "label": "风格混合",
     "options": [(k, v) for k, v in mega_pack.MIX_L2K.items()]},
    {"key": "cam", "label": "运镜（视频）", "options": _h3_cam_options("norm"), "video": True},
    {"key": "shots", "label": "分镜数（视频）", "kind": "int", "video": True,
     "min": 1, "max": 5, "default": 1},
    {"key": "seed", "label": "随机种子", "kind": "int"},
]

WUXIA_FIELDS = [
    {"key": "wuxia_type", "label": "武侠类型", "options": _enum_options(wuxia_pack.WUXIA_TYPES)},
    {"key": "subject", "label": "主体", "options": _enum_options(wuxia_pack.SUBJECTS)},
    {"key": "shot_type", "label": "镜头", "options": _enum_options(wuxia_pack.SHOTS)},
    {"key": "composition", "label": "构图", "options": _enum_options(wuxia_pack.COMPOSITION)},
    {"key": "lighting", "label": "光影", "options": _enum_options(wuxia_pack.LIGHTING)},
    {"key": "color_tone", "label": "色调", "options": _enum_options(wuxia_pack.COLOR_TONES)},
    {"key": "atmosphere", "label": "氛围", "options": _enum_options(wuxia_pack.ATMOSPHERES)},
    {"key": "action", "label": "动作", "options": _enum_options(wuxia_pack.ACTIONS)},
    {"key": "weapon", "label": "武器", "options": _enum_options(wuxia_pack.WEAPONS)},
    {"key": "object", "label": "道具", "options": _enum_options(wuxia_pack.OBJECTS)},
    {"key": "element", "label": "点缀", "options": _enum_options(wuxia_pack.ELEMENTS)},
    {"key": "summon", "label": "召唤", "options": _enum_options(wuxia_pack.SUMMON)},
    {"key": "camera_motion", "label": "运镜（视频）", "options": _enum_options(wuxia_pack.CAMERA_MOTION), "video": True},
    {"key": "character_motion", "label": "角色动态（视频）", "options": _enum_options(wuxia_pack.CHARACTER_MOTION), "video": True},
    {"key": "weather_motion", "label": "天气动态（视频）", "options": _enum_options(wuxia_pack.WEATHER_MOTION), "video": True},
    {"key": "foliage_motion", "label": "草木动态（视频）", "options": _enum_options(wuxia_pack.FOLIAGE_MOTION), "video": True},
    {"key": "scene_motion", "label": "场景动态（视频）", "options": _enum_options(wuxia_pack.SCENE_MOTION), "video": True},
    {"key": "motion_strength", "label": "动态强度（视频）", "kind": "int", "video": True,
     "min": 0, "max": 10, "default": 7},
]

Y2K_FIELDS = [
    {"key": k, "label": zh, "options": _enum_options(enum), "video": v}
    for (k, zh, enum, v) in y2k_pack.FIELDS
] + [
    {"key": "motion_strength", "label": "动态强度(视频)", "kind": "int", "video": True,
     "min": 0, "max": 10, "default": 7},
]

# 默认种子
_SEED = {"seed": 0, "motion_strength": 7}


def _h3_video_args(params):
    """解析视频专用参数：分镜数 shots(1-5)、运镜 cam。"""
    try:
        shots = int(params.get("shots", 1) or 1)
    except (TypeError, ValueError):
        shots = 1
    shots = max(1, min(5, shots))
    cam = params.get("cam", "auto") or "auto"
    if cam not in mega_pack.H3_CAM_ALL:
        cam = "auto"
    return shots, cam


def _h3_zh_suffix(shots, cam):
    """视频模式下给中文串补的分镜/运镜说明。"""
    cam_zh = mega_pack.H3_CAM_ALL.get(cam, {}).get("label", "自动循环")
    return f"；分镜 {shots} 个，{cam_zh}"


def _resolve_mega_pk(params, envKey, rng):
    """6a 联动：巨构主体为随机时，若环境属地域（广西/南方/北方），
    只从该地域巨构池抽取，避免「选广西却出未来都市」。"""
    raw = params.get("pk", "rand")
    if raw in (None, "", "rand", RAND):
        pool = mega_pack.ENV_MEGA_POOL.get(envKey)
        if pool:
            return rng.rnd(pool)
    return _rand_key(mega_pack.MEGA, raw)


# ===================== 巨构规范补全（对齐用户案例文档） =====================
# 画框溢出：巨构须从顶部 + 至少一侧溢出，只能看到冰山一角
FRAME_OVERFLOW = [
    ("从画面顶部与右侧溢出画框", "cropped by the top edge and the right edge of the frame"),
    ("从画面顶部与左侧溢出画框", "cropped by the top edge and the left edge of the frame"),
    ("从画面顶部与左右两侧同时溢出", "cropped by the top edge and both side edges of the frame"),
    ("从画面底部与右侧溢出画框", "cropped by the bottom edge and the right edge of the frame"),
    ("横向绵延并从左、右边缘与上缘溢出", "running off the left and right edges as well as the upper edge"),
    ("顶部被截断、下部向画外无限延伸", "cropped by the top edge, its lower body plunging out of frame"),
]

# 跨区域环境反馈：巨构须对环境造成至少两种影响（把"物体"变成"地标"）
ENV_IMPACT = [
    ("遮蔽整条地平线", "its mass occludes the entire horizon line across the frame"),
    ("穿透多层云海", "piercing through multiple stratified cloud layers"),
    ("投下跨越山谷的公里级阴影", "casting a kilometers-long shadow across the valley below"),
    ("迫使风沙绕流改向", "deflecting prevailing wind and sand currents around its flanks"),
    ("把云层压成低矮云台", "pressing the cloud deck down into a compressed shelf"),
    ("掀起公里级雾浪", "generating kilometer-scale fog waves rolling off its surface"),
    ("令背后的星光被扭曲", "visibly distorting the starfield behind its silhouette"),
    ("海浪持续撞击基座", "ocean swells detonating against its wave-carved base"),
    ("把河流截成巨大水库", "damming a river into a vast reservoir at its foot"),
    ("造出独立的局部小气候", "creating a permanent microclimate zone around itself"),
    ("让可见天空只剩一线", "reducing the visible sky to a thin sliver"),
    ("使远处山体显得矮小", "making distant mountain ranges appear diminutive beside it"),
]


def _pick_pairs(pool, rng, n):
    """从 (中文, 英文) 池里用 rng 不重复抽 n 条，保证同种子可复现。"""
    items = list(pool)
    out = []
    for _ in range(min(n, len(items))):
        c = rng.rnd(items)
        out.append(c)
        items.remove(c)
    return out


def _append_mega_spec(positive, zh_head, rng):
    """补两条规范要素：画框溢出 + 至少两种跨区域环境反馈。
    英文追加进 prompt，中文追加进中文串（中文不经过英译，避免残留）。"""
    overflow = _pick_pairs(FRAME_OVERFLOW, rng, 1)
    impacts = _pick_pairs(ENV_IMPACT, rng, 2)
    if overflow:
        positive = (positive.rstrip('. ') + '. ' + overflow[0][1]
                    + ', revealing only a terrifying fraction of its true scale.')
    if impacts:
        positive = (positive.rstrip('. ') + '. The structure '
                    + ' and '.join(e for _z, e in impacts) + '.')
    extra = ""
    if overflow:
        extra += f"；边缘溢出：{overflow[0][0]}"
    if impacts:
        extra += f"；环境影响：{'、'.join(z for z, _ in impacts)}"
    return positive, zh_head + extra


def _append_theme_zh(zh_head, theme_inject):
    """把生效的题材中文名写进中文串（被隔离/为无则不写），让联动结果可见。"""
    if not theme_inject or theme_inject == "none":
        return zh_head
    label = mega_pack.THEME_POOL.get(theme_inject, {}).get("label", "")
    if not label or label.startswith("无") or _is_rand_item((label, "")):
        return zh_head
    return zh_head + f"；题材：{label}"


def _theme_args(params):
    """6b：题材 + 风格混合模式，供 mega_pack._affinity 使用。"""
    thk = params.get("theme", "rand")
    if thk in (None, "", "rand", RAND):
        pool = [k for k in mega_pack.THEME_POOL.keys() if k not in ("rand", "none")]
        thk = random.choice(pool) if pool else "none"
    elif thk == "none" or str(thk).startswith("无"):
        thk = "none"
    mix = params.get("mix_mode", "隔离")
    if mix not in ("隔离", "碰撞"):
        mix = "隔离"
    return thk, mix


def _int_param(params, key, default, lo, hi):
    """安全读整数参数并夹在 [lo, hi]。"""
    try:
        v = int(params.get(key, default))
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


# ===================== 各包 build 实现（返回 (英文, 中文)） =====================
def build_mega(params, arch):
    rng = mega_pack.RNG(int(params.get("seed", 0) or 0))
    styleKey = _rand_key(mega_pack.STYLES, params.get("styleKey", "rand"))
    envKey = _rand_key(mega_pack.ENVS, params.get("envKey", "rand"))
    # 6a 联动：环境 = 广西/南方/北方 且主体为随机时，只从该地域巨构池抽
    pk = _resolve_mega_pk(params, envKey, rng)
    lensKey = _rand_key(mega_pack.LENSES, params.get("lensKey", "rand"))
    varKey = _rand_key(mega_pack.MVAR, params.get("varKey", "rand"))
    lightKey = _rand_key(mega_pack.LIGHTS, params.get("lightKey", "rand"))
    morphKey = _rand_key(mega_pack.MEGA_MORPH, params.get("morphKey", "honeycomb"))
    # 6b 联动：风格 × 题材亲和层（冲突→隔离或碰撞桥接）
    thk, mix_mode = _theme_args(params)
    theme_inject, warns, bridge = mega_pack._affinity(styleKey, thk, mix_mode, "")
    positive, fields = mega_pack.buildMega(
        pk, lensKey, varKey, lightKey, envKey, styleKey, rng, morphKey=morphKey,
        theme=theme_inject, bridge=bridge
    )
    name = mega_pack.MEGA.get(pk, {}).get("name", pk)
    subject_zh = name if "巨构" in name else (name + "巨构")
    style_zh = mega_pack.STYLES.get(styleKey, {}).get("label", styleKey)
    lens_zh = mega_pack.LENSES.get(lensKey, {}).get("label", lensKey)
    light_zh = mega_pack.LIGHTS.get(lightKey, {}).get("label", lightKey)
    env_zh = mega_pack.ENVS.get(envKey, {}).get("label", envKey) if envKey in mega_pack.ENVS else ""
    morph_zh = mega_pack.MEGA_MORPH.get(morphKey, {}).get("name", morphKey)
    var_zh = mega_pack.MVAR.get(varKey, {}).get("label", varKey)
    zh_head = (f"一座{subject_zh}，{style_zh}风格，{lens_zh}，{light_zh}，{env_zh}环境，"
               f"{morph_zh}形态，{var_zh}视角；材质：{fields.get('materials','')}；"
               f"氛围与细节：{fields.get('atmosphere','')}")
    zh_head = _append_theme_zh(zh_head, theme_inject)
    # ②④ 规范要素：边缘溢出画框 + 至少两种跨区域环境反馈（巨构须把环境变成地标）
    positive, zh_head = _append_mega_spec(positive, zh_head, rng)
    if arch == "h3":
        shots, cam = _h3_video_args(params)
        h3 = mega_pack.buildH3("mega", styleKey, envKey, positive, shots=shots, camKey=cam)
        text = h3 if isinstance(h3, str) else h3[0]
        return text, purify_zh(zh_head + _h3_zh_suffix(shots, cam) + ZH_TAIL["mega"]), warns
    return positive, purify_zh(zh_head + ZH_TAIL["mega"]), warns


def build_normal(params, arch):
    rng = mega_pack.RNG(int(params.get("seed", 0) or 0))
    styleKey = _rand_key(mega_pack.STYLES, params.get("styleKey", "rand"))
    catKey = _rand_key(mega_pack.CATS, params.get("catKey", "rand"))
    lensKey = _rand_key(mega_pack.LENSES, params.get("lensKey", "rand"))
    lightKey = _rand_key(mega_pack.LIGHTS, params.get("lightKey", "rand"))
    envKey = _rand_key(mega_pack.ENVS, params.get("envKey", "rand"))
    viewKey = _rand_key(mega_pack.NORMAL_VIEW, params.get("viewKey", "none"))
    # 6b 联动：风格 × 题材亲和层（冲突→隔离或碰撞桥接）
    thk, mix_mode = _theme_args(params)
    theme_inject, warns, bridge = mega_pack._affinity(styleKey, thk, mix_mode, "")
    positive, fields = mega_pack.buildNormal(
        styleKey, catKey, lensKey, lightKey, envKey, rng, viewKey=viewKey,
        theme=theme_inject, bridge=bridge
    )
    style_zh = mega_pack.STYLES.get(styleKey, {}).get("label", styleKey)
    cat_zh = mega_pack.CATS.get(catKey, {}).get("label", catKey)
    lens_zh = mega_pack.LENSES.get(lensKey, {}).get("label", lensKey)
    light_zh = mega_pack.LIGHTS.get(lightKey, {}).get("label", lightKey)
    env_zh = mega_pack.ENVS.get(envKey, {}).get("label", envKey) if envKey in mega_pack.ENVS else ""
    view_zh = mega_pack.NORMAL_VIEW.get(viewKey, {}).get("label", "") if (viewKey and viewKey not in ("none", "rand")) else ""
    zh_head = (f"{cat_zh}，{style_zh}风格，{lens_zh}镜头，{light_zh}，{env_zh}环境"
               f"{('，' + view_zh) if view_zh else ''}；材质与氛围：{fields.get('atmosphere','')}")
    zh_head = _append_theme_zh(zh_head, theme_inject)
    if arch == "h3":
        shots, cam = _h3_video_args(params)
        h3 = mega_pack.buildH3(catKey, styleKey, envKey, positive, shots=shots, camKey=cam)
        text = h3 if isinstance(h3, str) else h3[0]
        return text, purify_zh(zh_head + _h3_zh_suffix(shots, cam) + ZH_TAIL["normal"]), warns
    return positive, purify_zh(zh_head + ZH_TAIL["normal"]), warns


def build_wuxia(params, arch):
    d = {
        "wuxia_type": params.get("wuxia_type", "文人武侠"),
        "subject": params.get("subject", "无（纯风景）"),
        "shot_type": params.get("shot_type", "远景建立镜头"),
        "composition": params.get("composition", "居中构图"),
        "lighting": params.get("lighting", "柔和漫射光"),
        "color_tone": params.get("color_tone", "大地苍青色调"),
        "atmosphere": params.get("atmosphere", "禅意宁静"),
        "action": params.get("action", "静坐调息"),
        "weapon": params.get("weapon", "长剑 jian"),
        "object": params.get("object", "无（不加道具）"),
        "element": params.get("element", "无（不加点缀）"),
        "summon": params.get("summon", "无（无召唤）"),
    }
    ms = _int_param(params, "motion_strength", 7, 0, 10)
    cam_m = params.get("camera_motion", RAND) or RAND
    ch_m = params.get("character_motion", RAND) or RAND
    we_m = params.get("weather_motion", RAND) or RAND
    fo_m = params.get("foliage_motion", RAND) or RAND
    sc_m = params.get("scene_motion", RAND) or RAND
    if arch == "h3":
        text = wuxia_pack._build_h3_prompt(
            d["wuxia_type"], d["shot_type"], d["composition"], d["lighting"],
            d["color_tone"], d["atmosphere"], d["action"], d["weapon"], None,
            ms, d["subject"], None, d["object"], None, d["element"], None,
            cam_m, ch_m, we_m, fo_m, sc_m, d["summon"], None,
        )
    else:
        text = wuxia_pack._build_img_prompt(
            d["wuxia_type"], d["shot_type"], d["composition"], d["lighting"],
            d["color_tone"], d["atmosphere"], d["action"], d["weapon"], None,
            d["subject"], None, d["object"], None, d["element"], None, d["summon"], None,
        )
    # 中文段落：滤掉「无（…）」占位，串成自然句
    order = [d["wuxia_type"], d["subject"], d["shot_type"], d["composition"],
             d["lighting"], d["color_tone"], d["atmosphere"], d["action"],
             d["weapon"], d["object"], d["element"], d["summon"]]
    parts = [v for v in order if not _zh_no(v)]
    tail = ""
    if arch == "h3":
        vids = [v for v in (cam_m, ch_m, we_m, fo_m, sc_m) if not _zh_no(v)]
        tail = "（视频 H3）"
        if vids:
            tail += "，运镜与动态：" + "、".join(vids)
        tail += f"，动态强度 {ms}"
    zh = purify_zh("，".join(parts) + tail + ZH_TAIL["wuxia"])
    return text, zh, []


def build_y2k(params, arch):
    text, js = y2k_pack.build(params, arch)
    # 用 y2k 词库自带的 (中文, 英文) 配对做英文→中文替换，保证有值即有中文
    zh = en_to_zh(text, Y2K_EN2ZH)
    if arch == "h3":
        ms = _int_param(params, "motion_strength", 7, 0, 10)
        zh = zh.rstrip("；。， ") + "，动态强度 %d%s" % (ms, ZH_TAIL["y2k"])
    else:
        zh = zh + ZH_TAIL["y2k"]
    return text, purify_zh(zh), []


# 千禧年英文→中文映射（取自 y2k_pack.FIELDS 的 (中文, 英文) 配对）
Y2K_EN2ZH = {}
for (_k, _zh_label, _enum, _v) in y2k_pack.FIELDS:
    for (_czh, _cen) in _enum:
        if _cen and _czh and _cen not in ("🎲 随机", "随机"):
            Y2K_EN2ZH[_cen] = _czh


def en_to_zh(text, mapping):
    """把英文提示词里的已知词条替换为中文（长词优先）。"""
    out = text
    for en in sorted(mapping.keys(), key=len, reverse=True):
        if not en:
            continue
        out = out.replace(en, mapping[en])
    return out


# ===================== 中文净化（A 方案：中文提示词 100% 中文） =====================
# 领域词条词典：覆盖 mega 的材质/环境/光影/风格/质量词库与 y2k 固定尾缀。
# 未命中的英文片段由 purify_zh 剔除，保证中文串纯中文可读（英文 prompt 不受影响）。
ZH_DICT = {
    # —— 材质与表面 ——
    "weathered titanium alloy": "风化钛合金", "titanium alloy": "钛合金",
    "oxidized steel": "氧化钢", "brushed metal silver": "拉丝银",
    "brushed metal": "拉丝金属", "brushed steel": "拉丝钢",
    "carbon-fiber plating": "碳纤维覆板", "carbon fiber": "碳纤维",
    "carbon composite": "碳复合材", "glass curtain walls": "玻璃幕墙",
    "luminescent signage": "自发光招牌", "ancient bark": "古木树皮",
    "living wood": "活体木", "bioluminescent moss": "生物荧光苔藓",
    "bioluminescent": "生物荧光", "woven rope": "编织绳缆",
    "pitted taihu limestone": "多孔太湖石", "pitted limestone": "多孔石灰岩",
    "limestone": "石灰岩", "stalactite": "钟乳石", "travertine": "石灰华",
    "clinging moss": "攀附苔藓", "moss": "苔藓", "rammed-earth paddy walls": "夯水田埂",
    "rammed-earth": "夯土", "flooded loess": "浸水黄土", "loess": "黄土",
    "rice straw": "稻草", "fieldstone": "田石", "white-washed walls": "白粉墙",
    "dark clay tiles": "青瓦", "grey brick": "青砖", "carved stone": "雕石",
    "carved wood": "木雕", "weathered timber": "风化木构", "weathered cedar": "风化雪松",
    "grey tile": "灰瓦", "lacquered wood": "髹漆木", "stone piers": "石墩",
    "bronze drums": "铜鼓", "indigo-dyed cloth": "靛蓝染布", "indigo": "靛蓝",
    "karst stone": "喀斯特岩", "battleship grey steel": "战舰灰钢",
    "glowing thrusters": "炽亮推进器", "riveted armor panels": "铆接装甲板",
    "hydraulic piston segments": "液压活塞节", "coiled cable bundles": "盘绕线缆束",
    "polished mirror metal": "抛光镜面金属", "mirror metal": "镜面金属",
    "reflective mercury surface": "水银反光面", "mercury surface": "水银表面",
    "liquid chrome": "液态铬", "polished": "抛光", "reflective": "反光",
    "iridescent holographic": "虹彩全息", "iridescent": "虹彩", "holographic": "全息",
    "rainbow oil-slick color shift": "彩虹油膜流变", "pearlescent": "珠光",
    "frosted translucent plastic": "磨砂半透塑料", "jelly-like acrylic": "果冻质感亚克力",
    "see-through frosted shell": "通透磨砂外壳", "glossy wet-look finish": "湿润高光质感",
    "high-shine vinyl": "高亮乙烯基", "patent leather sheen": "漆皮光泽",
    "lip-gloss surface": "唇釉质感", "rhinestone encrusted": "满镶水钻",
    "rhinestone": "水钻", "bedazzled": "满钻镶嵌",
    "Swarovski crystal sparkle": "施华洛世奇水晶闪耀", "Swarovski": "施华洛世奇",
    "clear acrylic": "透明亚克力", "transparent gel texture": "透明凝胶质感",
    "candy-colored see-through plastic": "糖果色透明塑料", "candy-colored": "糖果色",
    "pearl sheen": "珍珠光泽", "satin iridescent": "缎面虹彩",
    "opalescent glow": "乳白辉光", "rose gold metallic gradient": "玫瑰金渐变",
    "rose gold": "玫瑰金", "chrome": "铬", "bronze": "青铜", "copper": "紫铜",
    "marble": "大理石", "granite": "花岗岩", "obsidian": "黑曜石", "crystal": "水晶",
    "jade": "玉石", "porcelain": "陶瓷", "lacquer": "漆", "bamboo": "竹",
    "rattan": "藤", "silk": "丝绸", "velvet": "丝绒", "leather": "皮革",
    "concrete": "混凝土", "rusted": "锈蚀", "rust": "铁锈", "corroded": "腐蚀",
    "patina": "铜绿包浆", "weathered": "风化",

    # —— 光影 ——
    "specular highlight": "镜面高光", "sharp highlight points": "锐利高光点",
    "glossy sheen": "润泽光泽", "lens flare": "镜头光晕", "light burst": "光芒迸射",
    "sunstar": "星芒", "soft studio lighting": "柔和棚拍光", "clean highlights": "洁净高光",
    "product-shot gloss": "产品级光泽", "neon glow": "霓虹辉光",
    "cyberpunk color grading": "赛博朋克调色", "electric rim light": "电光轮廓",
    "chrome reflection": "铬面反射", "reflective environment": "环境反射",
    "mirror surface bounce": "镜面反弹光", "volumetric lighting": "体积光",
    "volumetric": "体积感", "god rays": "神明光束", "golden hour": "黄金时刻",
    "rembrandt": "伦勃朗光", "dappled": "斑驳光影", "tyndall": "丁达尔效应",
    "candlelight": "烛火", "candle": "烛光", "bicolor": "双色光", "hard light": "硬光",
    "overcast": "阴天漫射", "moonlight": "月光", "backlight": "逆光", "rim light": "轮廓光",
    "cold-warm contrast": "冷暖对比", "deep structural shadows": "结构深阴影",
    "warm rim light on the upper edges": "上缘暖色轮廓光", "warm rim light": "暖色轮廓光",
    "upper edges": "上缘", "neon": "霓虹", "glowing": "发光", "glow": "辉光",
    "shimmer": "微光闪烁", "sparkle": "闪烁",

    # —— 环境 / 氛围 ——
    "cloud sea": "云海", "clouds": "云层", "mountains": "群山", "mountain": "山峦",
    "cyber": "赛博", "forest": "森林", "palace": "宫殿", "ruins": "废墟",
    "void": "虚空", "ocean": "海洋", "desert": "沙漠", "snow": "雪原", "rain": "雨幕",
    "galaxy": "星系", "lava": "熔岩", "aurora": "极光", "misty": "雾气氤氲",
    "mist": "薄雾", "fog": "浓雾", "haze": "霾", "dust": "尘埃", "drifting": "飘动",
    "swirling": "旋绕", "towering": "高耸", "endless": "无尽", "vast": "广袤",
    "cavern": "洞窟", "cliff": "悬崖", "valley": "山谷", "river": "河流", "lake": "湖面",
    "starfield": "星野", "stars": "星辰", "nebula": "星云", "cosmic": "宇宙",
    "floating": "悬浮", "distant": "远处", "silhouette": "剪影",

    # —— 风格 / 画质 ——
    "photorealistic photograph": "写实摄影", "photorealistic": "写实摄影",
    "8k resolution": "8K 分辨率", "8k": "8K", "4k": "4K", "ultra-sharp": "极致锐利", "high detail": "高细节",
    "hyper-detailed materials of": "超精细", "hyper-detailed": "超精细",
    "extreme detail": "极致细节", "ultra detailed": "极致细节", "highly detailed": "高度精细",
    "shot on 50mm": "50mm 焦段", "natural lighting": "自然光照",
    "masterpiece": "大师级作品", "ink wash": "水墨", "sumi-e": "水墨画",
    "monochrome with subtle color": "淡彩单色", "monochrome": "单色",
    "brush texture": "笔触肌理", "elegant negative space": "雅致留白", "negative space": "留白",
    "cel-shaded": "赛璐璐", "anime style": "动漫风格", "anime": "动漫",
    "vibrant colors": "鲜明色彩", "clean linework": "干净线稿", "flat shading": "平涂",
    "digital painting": "数字绘画", "thick brushstrokes": "厚涂笔触", "rich texture": "丰富肌理",
    "artstation trending": "ArtStation 热门", "octane render": "Octane 渲染",
    "ray tracing": "光线追踪", "physically based rendering": "基于物理的渲染",
    "neon-lit": "霓虹照明", "high contrast": "高对比", "rain-slick streets": "湿滑街面",
    "holographic signage": "全息招牌", "blade runner mood": "银翼杀手氛围",
    "futuristic": "未来感", "high-tech": "高科技",
    "sleek brushed-metal surfaces": "流线拉丝金属面", "subtle glowing energy lines": "微光能量线",
    "crisp detailing": "利落细节", "epic scale": "史诗尺度",
    "traditional Chinese gongbi painting": "中国传统工笔画", "gongbi": "工笔",
    "fine brushwork": "精细笔法", "elegant line": "优雅线条",
    "soft mineral pigments": "柔和矿物颜料", "mineral pigments": "矿物颜料",
    "classical composition": "古典构图", "classical realism": "古典写实",
    "pixel art illustration": "像素插画", "pixel art": "像素艺术", "retro 16-bit": "复古 16 位",
    "limited palette": "有限色板", "crisp pixels": "清晰像素",
    "game sprite aesthetic": "游戏精灵美学", "cinematic film still": "电影剧照",
    "35mm film": "35mm 胶片", "anamorphic flare": "变形宽银幕光晕", "film grain": "胶片颗粒",
    "teal and orange grading": "青橙调色", "shallow depth": "浅景深", "oil painting": "油画",
    "visible brushstrokes": "可见笔触", "impasto": "厚涂堆色", "chiaroscuro": "明暗对照法",
    "museum quality": "博物馆级品质", "low-poly 3D render": "低多边形 3D 渲染",
    "low-poly": "低多边形", "faceted geometry": "多面几何", "minimalist": "极简",
    "clean pastel palette": "柔和粉彩", "isometric": "等距视角", "vaporwave": "蒸汽波",
    "pink and cyan gradients": "粉青渐变", "grids": "网格",
    "retro 80s aesthetic": "复古 80 年代美学", "glitch": "故障艺术",
    "science-fiction concept illustration": "科幻概念插画", "3D octane render": "3D Octane 渲染",
    "cinematic": "电影感",

    # —— 构图 / 镜头 ——
    "sharp focus": "锐利对焦", "depth of field": "景深", "bokeh": "散景",
    "wide shot": "远景", "close-up": "特写", "low angle": "低角度", "high angle": "高角度",
    "aerial view": "俯瞰视角", "dutch angle": "荷兰角", "ultra wide": "超广角",
    "fisheye": "鱼眼", "telephoto": "长焦",

    # —— Y2K 固定尾缀与词条 ——
    "early 2000s Y2K aesthetic": "千禧年初美学", "early 2000s": "千禧年初",
    "Y2K aesthetic": "千禧年美学", "vintage CGI render": "复古 CGI 渲染",
    "vintage CGI": "复古 CGI", "iridescent and glossy surfaces": "虹彩光泽表面",
    "retro-futurism": "复古未来主义", "retro futurism": "复古未来主义",
    "techno-optimism": "科技乐观主义", "techno utopia": "科技乌托邦",
    "bright saturated candy colors": "高饱和糖果色", "saturated candy colors": "饱和糖果色",
    "cinematic y2k video": "千禧年电影感视频", "smooth motion": "流畅运动",
    "early-2000s computer graphics animation": "千禧年初电脑动画",
    "computer graphics animation": "电脑图形动画",
    "glossy futuristic optimism": "光泽未来乐观主义", "glossy": "光泽",
    "bubblegum pink": "泡泡糖粉", "hot pink": "艳粉", "fuchsia": "紫红",
    "electric blue": "电光蓝", "Bondi blue": "邦迪蓝", "aqua cyan": "水青",
    "acid lime green": "酸性青柠绿", "electric yellow": "电光黄",
    "lavender violet": "薰衣草紫", "holo violet": "全息紫", "holographic cyan": "全息青",
    "iridescent teal": "虹彩蓝绿", "champagne gold": "香槟金",
    "pristine icy white": "洁净冰白", "frosted white": "磨砂白", "deep purple": "深紫",
    "midnight glam": "午夜华丽", "butterfly motifs": "蝴蝶纹样",
    "fluttering chrome butterfly wings": "振翅的铬质蝶翼", "pixel heart": "像素爱心",
    "floating sparkles": "漂浮闪光", "star-shaped sparkles": "星形闪光",
    "glitter particles": "闪粉微粒", "inflated bubble forms": "充气气泡造型",
    "blobject": "气泡软体", "rounded toy-like shapes": "圆润玩具感造型",
    "low-poly 3D": "低多边形 3D", "visible faceting": "可见切面",
    "early-2000s CGI roughness": "千禧年初 CGI 粗粝感", "circuit board traces": "电路板走线",
    "matrix digital rain": "矩阵数字雨", "binary code": "二进制码",
    "wireframe grid": "线框网格", "CD-ROM iridescent disc": "CD 光碟虹彩盘面",
    "rainbow reflective surface": "彩虹反射面",
    "glossy hyper-saturated flowers": "高饱和光泽花朵", "celestial bloom": "星辉绽放",
    "planet": "行星", "orbital path": "轨道轨迹", "chrome smiley": "铬质笑脸",
    "y2k smiley face": "千禧年笑脸", "glossy emoji": "光泽表情",
    "space buns": "太空丸子头", "glossy lips": "水光唇", "tiny sunglasses": "迷你墨镜",
    "silver makeup": "银色妆容", "pastel iridescent finish": "粉彩虹彩饰面",
    "flip phone": "翻盖手机", "chrome body": "铬质机身", "glowing tiny screen": "微光小屏",
    "bubble buttons": "气泡按键", "cute rounded robot mascot": "圆润机器萌宠",
    "simple low-poly form": "简约低多边形造型", "rhinestone choker": "水钻项圈",
    "y2k makeup": "千禧年妆容", "candy shell revealing circuitry": "糖果外壳透出电路",
    "Tamagotchi digital pet": "拓麻歌子电子宠", "translucent colored shell": "半透明彩壳",
    "tiny pixel screen": "迷你像素屏", "glossy white puffy suit": "光泽白色蓬松宇航服",
    "chrome helmet visor": "铬质头盔面罩", "floating in pastel space": "悬浮于粉彩太空",
    "glossy 3D render": "光泽 3D 渲染", "abstract 3D chrome lettering": "抽象 3D 铬质字母",
    "liquid mercury bevel": "水银斜面", "music player interface": "音乐播放器界面",
    "translucent buttons": "半透明按键", "neon highlights": "霓虹高光",
    "glass UI": "玻璃质感界面", "polished silver and aqua glow": "抛光银与水光",

    # —— 运镜 / 动态 ——
    "the camera pushes in toward the subject": "镜头向主体推进",
    "the camera pulls out": "镜头拉远", "the subject slowly rotates": "主体缓慢旋转",
    "showing all glossy angles": "展现各角度光泽",
    "the camera arcs around the subject": "镜头环绕主体", "in a slow circle": "缓慢绕行",
    "the subject gently floats upward": "主体缓缓上浮", "bubbles rising": "气泡上升",
    "the camera holds still": "镜头静止", "butterfly wings flutter": "蝶翼振颤",
    "chrome dust drifting": "铬尘飘散", "sparkles float and twinkle": "闪光漂浮闪烁",
    "liquid chrome ripples and flows": "液态铬流动泛波",
    "translucent bubbles rise and pop": "半透明气泡升起破裂", "gel texture wobble": "凝胶质感晃动",
    "iridescent color shifts through the spectrum": "虹彩在光谱间流转",
    "holographic shimmer": "全息微闪",

    # —— 通用残留句式 ——
    "of the frame": "画面", "occupying only": "仅占", "a glossy y2k object": "一件光泽千禧年物件",
    "a tiny": "一个微小的", "materials of": "", "Hyper-detailed": "超精细",
    # 品牌/技术名音译或意译，避免中文串残留英文
    "ArtStation": "知名艺术平台", "artstation": "知名艺术平台",
    "Octane": "高速渲染器", "octane": "高速渲染器",
    "CGI": "电脑图形", "cgi": "电脑图形",
    "iMac G3": "苹果 G3 电脑", "Tamagotchi": "电子宠物机",
}

# 允许保留的英文（仅数字规格类，中文圈通用且无更好译法）
_KEEP_EN = {"Y2K", "8K", "4K", "3D", "16-bit", "50mm", "35mm"}

# 前面紧邻字母/数字的不算独立英文片段（保护 "8K" 的 K、"14mm" 的 mm）；
# 独立出现的单字母（如 "a"）则会被剔除。
_EN_TOKEN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9\-']*(?:\s+[A-Za-z0-9\-']+)*")


def _strip_en(s, keep=_KEEP_EN):
    """删除中文串里的英文片段，白名单保留。"""
    def repl(m):
        w = m.group(0).strip()
        return w if w in keep else ""
    return _EN_TOKEN.sub(repl, s)


def _tidy_zh(s):
    """清理权重标记、残留标点与空白，让中文串通顺。"""
    s = re.sub(r":\s*\d+(?:\.\d+)?", "", s)      # 权重标记 :1.1 / :1
    s = s.replace(".", "")                        # 英文句点在中文串无意义
    s = re.sub(r"[()]", "", s)                    # 半角括号
    s = re.sub(r"\s*,\s*", "，", s)               # 英文逗号 → 中文逗号
    s = re.sub(r"[（(]\s*[）)]", "", s)            # 空的全角括号
    s = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", s)  # 中文之间的空格
    s = re.sub(r"[：:]\s*(?=[，；。、]|$)", "", s)  # 空冒号
    s = re.sub(r"[，、；]{2,}", "，", s)           # 连续标点
    s = re.sub(r"，\s*。", "。", s)
    s = re.sub(r"[，；、]\s*$", "", s)
    s = re.sub(r"^[，；。、\s]+", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def purify_zh(s):
    """含英文的中文提示词 → 纯中文：词典替换 → 剔除残留英文 → 整理标点。"""
    if not s:
        return s
    return _tidy_zh(_strip_en(en_to_zh(s, ZH_DICT)))


# ===================== 公共调度 =====================
# 顺序即顶部按钮顺序：普通 > 巨构 > 武侠 > 千禧年（用户指定）
PACKS = {
    "normal": {
        "name": "普通",
        "desc": "通用出图 · 可选宏大视角框感",
        "architectures": ["image", "h3"],
        "fields": NORMAL_FIELDS,
        "build": build_normal,
    },
    "mega": {
        "name": "巨构",
        "desc": "巨物感 / 电影级六维 · colossal megastructure",
        "architectures": ["image", "h3"],
        "fields": MEGA_FIELDS,
        "build": build_mega,
    },
    "wuxia": {
        "name": "武侠",
        "desc": "胡金铨武侠 · 国风水墨电影感",
        "architectures": ["image", "h3"],
        "fields": WUXIA_FIELDS,
        "build": build_wuxia,
    },
    "y2k": {
        "name": "千禧年",
        "desc": "Y2K / 千禧年 · 铬 / 虹彩 / 水钻 / 科技乐观",
        "architectures": ["image", "h3"],
        "fields": Y2K_FIELDS,
        "build": build_y2k,
    },
}


def list_packs():
    return PACKS


def build(style, arch, params=None):
    """统一入口。返回 (english_prompt_text, json_string, chinese_prompt_text)。"""
    pack = PACKS.get(style)
    if not pack:
        raise ValueError("未知风格包: %s" % style)
    if arch not in pack["architectures"]:
        arch = pack["architectures"][0]
    p = dict(_SEED)
    p.update(params or {})
    text, zh, warns = pack["build"](p, arch)
    data = {
        "style": style,
        "architecture": arch,
        "positive_prompt": text,
        "params": {k: v for k, v in p.items() if k not in ("seed",)},
    }
    if warns:
        data["warnings"] = warns
    return text, json.dumps(data, ensure_ascii=False, indent=2), zh


# ===================== 随机哨兵预解析（纯新增，不改动上方任何函数） =====================
_RAND_SENTINELS = {"", None, "rand", "RAND", "随机", RAND, "🎲随机", "🎲 随机", "🎲 自动"}


def resolve_randoms(style, params):
    """把下拉里的『随机』哨兵解析成具体值，供调用方在 build() 前统一处理。

    为什么需要：wuxia / y2k 的下拉值是中文标签，生成英文时由 _resolve / _pick
    把『🎲 随机』解析成实际项；但中文段落 parts 用的是**原始占位值**，会被
    _zh_no() 当占位符滤掉，导致中文只剩风格尾巴（如武侠只剩 33 字）。
    在入口预解析后，中英文即完全一致。

    约定：只替换哨兵值，用户显式选定的值一律不改动；int 类字段不处理。
    不改动上方任何既有函数，桌面端与移动端可共用同一份逻辑。
    """
    pack = PACKS.get(style)
    if not pack or not params:
        return params
    for f in pack.get("fields", []):
        key = f.get("key")
        if f.get("kind") == "int" or key not in params:
            continue
        if params[key] not in _RAND_SENTINELS:
            continue
        cands = [v for (_l, v) in (f.get("options") or [])
                 if v not in _RAND_SENTINELS and v not in ("", None)]
        if cands:
            params[key] = random.choice(cands)
    return params
