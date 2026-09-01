#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_icons.py — 用 JIUMI 头像(icon-512.png) 生成 Android 各密度启动图标。

产出：
  res/mipmap-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_launcher.png          (legacy 方形, 品牌底)
  res/mipmap-{...}/ic_launcher_round.png                               (legacy 圆, 同方图)
  res/mipmap-{...}/ic_launcher_foreground.png                         (自适应前景, 透明, 头像置安全区66%)
  res/values/ic_launcher_background.xml                               (品牌底色)

用法：
  python generate_icons.py
依赖(virtualenv)：pillow
"""
import os
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "static", "icon-512.png")
RES = os.path.join(ROOT, "android", "app", "src", "main", "res")

# density -> (legacy_size, adaptive_canvas)
DENS = {
    "mdpi":   (48,  108),
    "hdpi":   (72,  162),
    "xhdpi":  (96,  216),
    "xxhdpi": (144, 324),
    "xxxhdpi":(192, 432),
}

FALLBACK_BG = (20, 21, 28)  # 深石板, 无采样时的品牌底


def dominant_dark_bg(img: Image.Image):
    """采样不透明像素的主色, 压暗到 ~22% 亮度作为品牌底。"""
    rgba = img.convert("RGBA")
    px = rgba.getdata()
    from collections import Counter
    cnt = Counter()
    for r, g, b, a in px:
        if a < 24:
            continue
        # 量化到 4bit/通道, 便于聚类
        key = (r // 16, g // 16, b // 16)
        cnt[key] += 1
    if not cnt:
        return FALLBACK_BG
    (r, g, b), _ = cnt.most_common(1)[0]
    r, g, b = r * 16 + 8, g * 16 + 8, b * 16 + 8
    # 压暗
    def dk(v):
        return max(8, int(v * 0.22))
    return (dk(r), dk(g), dk(b))


def contain_paste(canvas: Image.Image, art: Image.Image, fill: float):
    """把 art 等比缩放贴合到 canvas 的 fill 比例并居中贴回(保留透明)。"""
    cw, ch = canvas.size
    aw, ah = art.size
    scale = (min(cw, ch) * fill) / max(aw, ah)
    nw, nh = max(1, int(aw * scale)), max(1, int(ah * scale))
    art2 = art.resize((nw, nh), Image.LANCZOS)
    ox, oy = (cw - nw) // 2, (ch - nh) // 2
    if art2.mode != "RGBA":
        art2 = art2.convert("RGBA")
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(art2, (ox, oy))
    return canvas


def main():
    if not os.path.isfile(SRC):
        print("ERR: 找不到", SRC)
        sys.exit(1)
    art = Image.open(SRC).convert("RGBA")
    bg = dominant_dark_bg(art)
    print("品牌底 RGB =", bg)

    # 写背景色到 values
    val_path = os.path.join(RES, "values", "ic_launcher_background.xml")
    hexc = "#%02X%02X%02X" % bg
    with open(val_path, "w", encoding="utf-8") as f:
        f.write(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<resources>\n'
            '    <color name="ic_launcher_background">%s</color>\n'
            '</resources>\n' % hexc
        )
    print("写背景色:", val_path, hexc)

    for dens, (leg, adv) in DENS.items():
        d = os.path.join(RES, "mipmap-" + dens)
        # legacy 方形: 品牌底 + 头像贴合 92%
        leg_canvas = Image.new("RGBA", (leg, leg), bg + (255,))
        leg_img = contain_paste(leg_canvas, art, 0.92)
        leg_img.convert("RGBA").save(os.path.join(d, "ic_launcher.png"), "PNG")
        leg_img.convert("RGBA").save(os.path.join(d, "ic_launcher_round.png"), "PNG")
        # 自适应前景: 透明底 + 头像置安全区 66%
        fg_canvas = Image.new("RGBA", (adv, adv), (0, 0, 0, 0))
        fg_img = contain_paste(fg_canvas, art, 0.66)
        fg_img.save(os.path.join(d, "ic_launcher_foreground.png"), "PNG")
        print("  %-7s legacy=%dx%d  foreground=%dx%d" % (dens, leg, leg, adv, adv))

    print("ICONS_OK")


if __name__ == "__main__":
    main()
