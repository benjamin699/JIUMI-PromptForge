# -*- coding: utf-8 -*-
"""把 RTF（cp936 + \\uN 转义）提取为纯文本。供阅读案例文档用。"""
import re
import sys

SRC = r"C:\Users\jiumi\Desktop\巨构案例(1)\巨构 12.rtf"

CTRL_U = re.compile(r"\\u(-?\d+)\??")
CTRL_UC = re.compile(r"\\uc(\d+)")
CTRL_HEX = re.compile(r"\\'([0-9a-fA-F]{2})")
CTRL_WORD = re.compile(r"\\([a-zA-Z]+)(-?\d*) ?")
CTRL_SYM = re.compile(r"\\([^a-zA-Z])")


def rtf_to_text(raw: bytes) -> str:
    s = raw.decode("latin-1")
    out = []
    i, n = 0, len(s)
    uc = 1
    while i < n:
        c = s[i]
        if c != "\\":
            if c not in "{}":
                out.append(c)
            elif c == "\n":
                out.append("\n")
            i += 1
            continue

        m = CTRL_UC.match(s, i)
        if m:
            uc = int(m.group(1))
            i = m.end()
            continue

        m = CTRL_U.match(s, i)
        if m:
            code = int(m.group(1))
            if code < 0:
                code += 65536
            out.append(chr(code))
            i = m.end()
            # 跳过 uc 个 fallback 字节
            skip = uc
            while skip > 0 and i < n:
                if s[i] == "\\" and i + 3 < n and s[i + 1] == "'":
                    i += 4
                    skip -= 1
                elif s[i] in "{}":
                    i += 1
                elif s[i] == "\\":
                    break
                else:
                    i += 1
                    skip -= 1
            continue

        m = CTRL_HEX.match(s, i)
        if m:
            out.append(bytes([int(m.group(1), 16)]).decode("cp936", errors="replace"))
            i = m.end()
            continue

        m = CTRL_WORD.match(s, i)
        if m:
            word = m.group(1)
            if word in ("par", "line", "sect"):
                out.append("\n")
            i = m.end()
            continue

        m = CTRL_SYM.match(s, i)
        if m:
            out.append(m.group(1))
            i = m.end()
            continue

        i += 1

    txt = "".join(out)
    # 规整：去掉连续空行、行尾空白
    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


if __name__ == "__main__":
    with open(SRC, "rb") as f:
        raw = f.read()
    print(rtf_to_text(raw))
