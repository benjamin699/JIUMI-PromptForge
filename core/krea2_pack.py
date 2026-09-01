# -*- coding: utf-8 -*-
"""
JIUMI Krea2 Prompt Builder — LLM 驱动的 Krea2 12 字段提示词构建器

输入：一段中文 / 英文的创意描述（raw_input）
处理：
  1. 调用 OpenAI 兼容的 Chat Completions API
     （可指向 OpenAI / DeepSeek / Qwen / 本地 llama.cpp / Ollama(openai 兼容) 等）
  2. 让 LLM 把描述结构化成一个 JSON 对象（Krea2 12 字段：subject / composition / micro_density / lens / materials / lighting / style / environment / quality / atmosphere / extras / negative_prompt）
  3. 把同一份结构拼回一段通顺的 Krea2 自然语言提示词（给普通人读）

双输出（对应你的设计）：
  - structured_json (机器 / ComfyUI 下游节点用)：Python dict 对象，下游可直接 data['subject'] 取值
  - natural_text    (普通人读)：通顺段落；LLM 罢工或解析格式坏了，至少还有字

容错（关键，已在 process 内 try/except 兜住，节点绝不崩溃）：
  - 网络 / 鉴权异常   → 返回 (fallback_dict, "⚠️ LLM 调用失败：..." 原文)
  - JSON 解析失败     → 返回 (fallback_dict 含 raw, 原始 LLM 文本)  ← 解析坏了 Text 仍有字
"""

import json
import os
import re
import urllib.request
import urllib.error


# ===================== Krea2 12 字段 =====================
# 与 jiumi_promptforge 插件 PromptForgeImage 输出的结构化 JSON 完全对齐：
# subject / composition / micro_density / lens / materials / lighting / style /
# environment / quality / atmosphere / extras / negative_prompt
KREA2_DIMS = ["subject", "composition", "micro_density", "lens", "materials",
              "lighting", "style", "environment", "quality", "atmosphere",
              "extras", "negative_prompt"]
# 模型未给出 negative_prompt 时的兜底负面词（与插件 NEG 默认一致）
DEFAULT_NEG = "low quality, blurry, watermark, text, deformed"

# 默认系统提示词：要求 LLM 只吐一个 JSON 对象，12 字段全部用英文短语
SYSTEM_PROMPT = """你是一名专业的 Krea2 图像提示词工程师。Krea2 是一种用英文写成的“巨物感 / 电影级”图像提示词格式。
用户会给你一段创意描述（可能是中文或英文）。请把它拆解并重写为下面的 12 字段结构，全部用英文短语。

必须只输出一个 JSON 对象，不要任何解释文字、不要 markdown 代码块、不要 ```json 围栏。
JSON 的字段固定为以下十二个（缺一不可）：
- "subject"：主体是什么、外观、材质、姿态（例 "a colossal brass mechanical titan with glowing core"）
- "composition"：构图 / 尺度关系 / 画面占位 / 比例冲突（例 "occupying 80% of the canvas, rising within a snowfield, a tiny figure dwarfed at the base"）
- "micro_density"：微观密度 / 表面细节 / 纹理颗粒（例 "hyper-detailed riveted armor panels, hydraulic pistons, coiled cable bundles"）
- "lens"：镜头 / 构图角度 / 焦段（例 "low angle wide shot, 14mm lens"）
- "materials"：材质与高细节渲染（例 "weathered titanium alloy, oxidized steel, carbon-fiber plating"）
- "lighting"：光影 / 打光（例 "volumetric rim light, cold-warm contrast, hard neon reflections"）
- "style"：艺术风格 / 渲染风格（例 "cinematic sci-fi concept art, Octane render"）
- "environment"：环境 / 场景背景（例 "a neon-lit cyberpunk metropolis at night"）
- "quality"：画质增益词（例 "8k resolution, masterpiece, extreme detail"）
- "atmosphere"：整体氛围 / 情绪（例 "oppressive, awe-inspiring, cinematic"）
- "extras"：额外叙事 / 安静的人尺度细节（例 "a tiny maintenance worker stands at the terrace edge, utterly dwarfed"）
- "negative_prompt"：负面词，要避开的东西（例 "low quality, blurry, watermark, text, deformed, extra limbs"）

规则：
1. 十二个字段全部用英文短语，不要用中文。
2. 如果用户给的信息不足，请基于描述合理补全，不要留空；缺失字段用空字符串 "" 代替，不要用 null。
3. 只输出 JSON，不要输出其它任何字符。

示例输出：
{"subject":"a colossal brass mechanical titan with glowing core","composition":"occupying 80% of the canvas, rising within a snowfield, a tiny figure stands dwarfed at the base","micro_density":"hyper-detailed riveted armor panels, hydraulic piston segments, coiled cable bundles","lens":"low angle wide shot, 14mm lens","materials":"weathered titanium alloy, oxidized steel, brushed metal and carbon-fiber plating","lighting":"volumetric rim light, cold-warm contrast between deep shadows and warm rim","style":"cinematic sci-fi concept art, Octane render","environment":"a frozen neon-lit battlefield under falling snow","quality":"8k resolution, masterpiece, extreme detail","atmosphere":"oppressive, awe-inspiring, cinematic","extras":"a tiny maintenance worker stands at the terrace edge, utterly dwarfed","negative_prompt":"low quality, blurry, watermark, text, deformed, extra limbs"}"""


# ===================== LLM 调用（OpenAI 兼容） =====================
def call_llm(raw_input, base_url, api_key, model, temperature, system_prompt, timeout):
    """调用 OpenAI 兼容的 /chat/completions，返回模型回复的文本内容。任何异常都向上抛。"""
    base_url = (base_url or "").rstrip("/").strip()
    if not base_url:
        raise ValueError("base_url 为空，请填写 OpenAI 兼容的 API 地址（如 https://api.openai.com/v1）")

    url = base_url + "/chat/completions"
    # 兼容用户填了多个模型的情况（如"GLM-4.7-Flash、GLM-4.6V-Flash"），只取第一个
    if model:
        model = re.split(r"[、,]", model)[0].strip()
    model = model or "GLM-4.7-Flash"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": raw_input},
        ],
        "temperature": float(temperature),
        "max_tokens": 2048,
        # 注：部分本地服务（llama.cpp / Ollama）不支持 response_format，故默认不带，
        # 仅靠系统提示词约束输出为 JSON。若你的服务商支持，可自行在 payload 加：
        # "response_format": {"type": "json_object"}
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key and api_key.strip():
        req.add_header("Authorization", "Bearer " + api_key.strip())

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:600]
        raise RuntimeError(f"HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误: {e.reason}")

    obj = json.loads(body)
    return obj["choices"][0]["message"]["content"]


# ===================== JSON 解析（带容错） =====================
def parse_to_json(text):
    """从 LLM 文本里抠出 JSON 对象并补齐 12 字段。解析不到就抛异常（由调用方兜底）。"""
    if not text or not text.strip():
        raise ValueError("LLM 返回为空")

    s = text.strip()

    # 去掉 ```json ... ``` 或 ``` ... ``` 围栏
    if "```" in s:
        parts = s.split("```")
        if len(parts) >= 2:
            s = parts[1]
            # 去掉可能的语言标识行（json / JSON）
            stripped = s.lstrip()
            if stripped[:4].lower() == "json":
                s = stripped[4:]
        s = s.strip()

    # 截取第一个 { 到最后一个 } 之间的内容（容忍前后有闲杂文字）
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("未在回复中找到 JSON 对象")
    s = s[start:end + 1]

    obj = json.loads(s)
    if not isinstance(obj, dict):
        raise ValueError("JSON 顶层不是对象")

    # 补齐 / 清洗 12 字段
    for k in KREA2_DIMS:
        if k not in obj or obj[k] is None:
            obj[k] = ""
        else:
            obj[k] = str(obj[k]).strip()
    # negative_prompt 兜底（模型没给就用插件默认负面词）
    if not obj.get("negative_prompt"):
        obj["negative_prompt"] = DEFAULT_NEG
    return obj


# ===================== JSON → 自然语言段落 =====================
def json_to_paragraph(data):
    """把 12 字段结构拼回一段通顺的 Krea2 风格英文提示词（仅正文字段，逗号连接 + 句号结尾；negative_prompt 不进正文）。"""
    parts = []
    for k in KREA2_DIMS:
        if k == "negative_prompt":
            continue
        v = (data.get(k) or "").strip()
        if v:
            parts.append(v)
    if not parts:
        return "(结构为空，请检查 LLM 返回)"
    return ", ".join(parts) + "."


# ===================== ComfyUI 节点 =====================
class Krea2PromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_input": ("STRING", {"multiline": True, "default": "", "placeholder": "在这里填写你的创意描述（中文 / 英文均可）"}),
                "base_url": ("STRING", {"multiline": False, "default": "https://open.bigmodel.cn/api/paas/v4/", "placeholder": "OpenAI 兼容 API 地址，如 https://open.bigmodel.cn/api/paas/v4/ 或本地 http://127.0.0.1:8080/v1"}),
                "api_key": ("STRING", {"multiline": False, "default": "", "placeholder": "API Key；本地服务可留空；也可通过 ZHIPU_API_KEY / OPENAI_API_KEY 环境变量注入"}),
                "model": ("STRING", {"multiline": False, "default": "GLM-4.7-Flash", "placeholder": "如 GLM-4.7-Flash；若填多个用顿号/逗号分隔，会自动取第一个"}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.01}),
                "timeout": ("INT", {"default": 60, "min": 5, "max": 600, "step": 5}),
                "system_prompt": ("STRING", {"multiline": True, "default": SYSTEM_PROMPT}),
            },
        }

    # 三输出：
    #   structured_json (机器/下游节点用)：Python dict 对象，下游直接 data['subject'] 取值
    #   natural_text    (普通人读)：通顺英文段落
    #   json_string     (通用)：同一份结构的 JSON 字符串，可接任意文本/剪贴板/日志
    RETURN_TYPES = ("JSON", "STRING", "STRING")
    RETURN_NAMES = ("structured_json", "natural_text", "json_string")
    FUNCTION = "build"
    CATEGORY = "JIUMI PromptForge/图片提示词"

    def build(self, raw_input, base_url, api_key, model, temperature, timeout, system_prompt):
        raw_input = (raw_input or "").strip()
        if not raw_input:
            empty = {k: "" for k in KREA2_DIMS}
            return (empty, "(空输入) 请在 raw_input 中填写创意描述。", json.dumps(empty, ensure_ascii=False, indent=2))

        # api_key 支持环境变量回退（避免把 key 写进工作流 JSON）
        key = (api_key or "").strip()
        if not key:
            key = os.environ.get("ZHIPU_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""

        # 1) 调用 LLM（整体容错：网络 / 鉴权 / 任何异常都不让节点崩）
        try:
            llm_text = call_llm(raw_input, base_url, key, model, temperature, system_prompt, timeout)
        except Exception as e:
            fallback = {k: "" for k in KREA2_DIMS}
            fallback["error"] = f"LLM 调用失败: {type(e).__name__}: {e}"
            return (fallback, f"⚠️ LLM 调用失败：{e}\n\n原始输入：\n{raw_input}", json.dumps(fallback, ensure_ascii=False, indent=2))

        # 2) 解析为 JSON（失败也容错：返回兜底 dict + 原始文本）
        try:
            data = parse_to_json(llm_text)
        except Exception as e:
            fallback = {k: "" for k in KREA2_DIMS}
            fallback["error"] = f"JSON 解析失败: {type(e).__name__}: {e}"
            fallback["raw"] = llm_text
            # ← 关键：解析坏了，至少 Text 里还有 LLM 的原始字，知道它没罢工
            return (fallback, llm_text, json.dumps(fallback, ensure_ascii=False, indent=2))

        # 3) 拼回自然语言段落
        text = json_to_paragraph(data)
        return (data, text, json.dumps(data, ensure_ascii=False, indent=2))


# 供 __init__.py 合并注册
KREA2_CLASS_MAPPINGS = {
    "Krea2PromptBuilder": Krea2PromptBuilder,
}
KREA2_DISPLAY_NAME_MAPPINGS = {
    "Krea2PromptBuilder": "krea2 提示词构建器 LLM",
}
