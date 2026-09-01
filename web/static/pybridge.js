/*
 * pybridge.js — 在浏览器/WebView 内嵌 Pyodide（Python WASM），
 * 把 core/ 词库原样挂载进 Python 运行时，前端经本模块调用 style_packs.build()。
 * 100% 复用已验证的 Python 提示词逻辑，无需翻译、质量零退步。
 */
(function () {
  "use strict";

  // core/ 包文件（复制进 web/pycore/，已剔除 krea2_pack）
  const CORE_FILES = [
    "__init__.py",
    "mega_pack.py",
    "wuxia_pack.py",
    "y2k_pack.py",
    "style_packs.py",
  ];

  let pyodide = null;
  let _ready = null; // Promise，加载完成后 resolve

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("无法加载 " + src));
      document.head.appendChild(s);
    });
  }

  async function init() {
    if (_ready) return _ready;
    _ready = (async () => {
      await loadScript("/pyodide/full/pyodide.js");
      pyodide = await loadPyodide({ indexURL: "/pyodide/full/" });

      // 把 core 包写入 Pyodide 虚拟文件系统
      for (const f of CORE_FILES) {
        const resp = await fetch("/pycore/" + f);
        if (!resp.ok) throw new Error("读取 /pycore/" + f + " 失败: " + resp.status);
        const buf = new Uint8Array(await resp.arrayBuffer());
        pyodide.FS.writeFile("/pycore/" + f, buf);
      }

      // 在 Python 侧定义给 JS 调用的接口
      pyodide.runPython(`
import sys
sys.path.insert(0, '/')
import json
import pycore.style_packs as _sp

def _list_packs():
    out = {'order': [], 'packs': {}}
    for k, p in _sp.PACKS.items():
        out['order'].append(k)
        fields = []
        for fld in p['fields']:
            opts = []
            for (lab, val) in (fld.get('options') or []):
                opts.append({'label': lab, 'value': val})
            fields.append({
                'key': fld['key'],
                'label': fld['label'],
                'kind': fld.get('kind'),
                'video': bool(fld.get('video')),
                'min': fld.get('min'),
                'max': fld.get('max'),
                'default': fld.get('default'),
                'options': opts,
            })
        out['packs'][k] = {
            'name': p['name'],
            'desc': p['desc'],
            'architectures': p['architectures'],
            'fields': fields,
        }
    return json.dumps(out, ensure_ascii=False)

def _build(style, arch, params_json):
    p = json.loads(params_json) if params_json else {}
    if hasattr(_sp, 'resolve_randoms'):
        p = _sp.resolve_randoms(style, p)
    en, js, zh = _sp.build(style, arch, p)
    warns = []
    try:
        warns = json.loads(js).get('warnings', []) or []
    except Exception:
        warns = []
    return json.dumps({'en': en, 'zh': zh, 'warnings': warns}, ensure_ascii=False)
`);
      window._pgList = pyodide.globals.get("_list_packs");
      window._pgBuild = pyodide.globals.get("_build");
      return true;
    })();
    try {
      await _ready;
    } catch (e) {
      _ready = null; // 允许重试
      throw e;
    }
    return true;
  }

  const API = {
    get ready() {
      return !!pyodide && !!window._pgBuild;
    },
    init,
    whenReady() {
      return init();
    },
    async listPacks() {
      await init();
      return JSON.parse(String(window._pgList()));
    },
    async build(style, arch, params) {
      await init();
      return JSON.parse(String(window._pgBuild(style, arch, JSON.stringify(params || {}))));
    },
  };

  window.PromptGen = API;
})();
