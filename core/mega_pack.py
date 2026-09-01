# -*- coding: utf-8 -*-
"""
JIUMI PromptForge — 巨构 / 多风格 AI 提示词生成器 ComfyUI 插件
移植自《巨构提示词生成器.html》v5.3 的内置词库与生成逻辑。
节点：
  PromptForgeImage : 出图提示词（普通模式 + 巨构六维模式），输出 positive / negative 文本
  PromptForgeH3    : MiniMax H3 视频提示词（T2VA 结构），输出 h3_prompt / image_prompt
把 positive 接到 CLIPTextEncode(text)，negative 接到另一个 CLIPTextEncode(text) 即可出图。
"""

import random

# ===================== 内置词库（v5.3） =====================
STYLES = {
    'rand':     {'label': '🎲 随机'},
    'real':     {'label': '写实摄影', 'prefix': 'A photorealistic photograph', 'qual': 'photorealistic, 8k resolution, ultra-sharp, high detail, shot on 50mm, natural lighting, masterpiece'},
    'ink':      {'label': '水墨', 'prefix': 'A traditional Chinese ink-wash painting', 'qual': 'ink wash, sumi-e, monochrome with subtle color, brush texture, elegant negative space, masterpiece'},
    'anime':    {'label': '2D 动漫', 'prefix': 'A cel-shaded anime illustration', 'qual': 'anime style, vibrant colors, clean linework, flat shading, detailed, masterpiece'},
    'paint':    {'label': '2D 厚涂', 'prefix': 'A digital painterly illustration', 'qual': 'digital painting, thick brushstrokes, rich texture, vibrant, artstation trending, masterpiece'},
    'render3d': {'label': '3D 渲染', 'prefix': 'A 3D octane render', 'qual': 'octane render, ray tracing, volumetric lighting, 8k, physically based rendering, masterpiece'},
    'cyber':    {'label': '赛博朋克', 'prefix': 'A cyberpunk illustration', 'qual': 'neon-lit, high contrast, rain-slick streets, holographic signage, blade runner mood, masterpiece'},
    'scifi':    {'label': '科幻', 'prefix': 'A science-fiction concept illustration', 'qual': 'futuristic, high-tech, sleek brushed-metal surfaces, subtle glowing energy lines, crisp detailing, epic scale, masterpiece'},
    'guofeng':  {'label': '国风工笔', 'prefix': 'A traditional Chinese gongbi painting', 'qual': 'fine brushwork, elegant line, soft mineral pigments, classical composition, masterpiece'},
    'pixel':    {'label': '像素风', 'prefix': 'A pixel art illustration', 'qual': 'retro 16-bit, limited palette, crisp pixels, game sprite aesthetic, masterpiece'},
    'cinema':   {'label': '电影感胶片', 'prefix': 'A cinematic film still', 'qual': '35mm film, anamorphic flare, film grain, teal and orange grading, shallow depth, masterpiece'},
    'oil':      {'label': '油画', 'prefix': 'An oil painting', 'qual': 'visible brushstrokes, impasto, chiaroscuro, classical realism, museum quality'},
    'lowpoly':  {'label': '低多边形', 'prefix': 'A low-poly 3D render', 'qual': 'faceted geometry, flat shading, minimalist, clean pastel palette, isometric'},
    'vapor':    {'label': '蒸汽波', 'prefix': 'A vaporwave illustration', 'qual': 'pink and cyan gradients, grids, retro 80s aesthetic, glitch, glow'},
}

MEGA_STYLE = {
    'rand': '', 'real': 'photorealistic live-action cinematography', 'ink': 'rendered in traditional Chinese ink-wash',
    'anime': 'cel-shaded anime rendering', 'paint': 'digital painterly rendering', 'render3d': '3D octane render',
    'cyber': 'cyberpunk neon rendering', 'guofeng': 'traditional gongbi brushwork', 'pixel': 'pixel-art rendering',
    'cinema': 'cinematic film-still look', 'oil': 'oil-painting look', 'lowpoly': 'low-poly 3D render', 'vapor': 'vaporwave rendering', 'scifi': 'futuristic sci-fi rendering',
}

CATS = {
    'rand':       {'label': '🎲 随机'},
    'portrait':   {'label': '人像', 'framing': ['a close-up portrait', 'a headshot', 'an upper-body portrait'], 'dof': 'shallow depth of field, soft bokeh', 'subjects': ['a serene young woman', 'an elderly swordsman', 'a mysterious cultivator', 'a child holding a lantern', 'a graceful celestial maiden', 'a white-haired sage with a staff', 'a veiled priestess', 'a scarred warrior in bronze armor', 'a scholar with a jade flute', 'a moonlit dancer with flowing sleeves', 'a blind seer touching a talisman', 'a young apprentice carrying scrolls']},
    'character':  {'label': '人物 / 角色', 'framing': ['a full-body view', 'a dynamic action pose', 'a mid-shot'], 'dof': '', 'subjects': ['a white-robed swordsman', 'a celestial maiden', 'an armored warrior', 'a wandering monk', 'a mechanical guardian', 'a cyan-robed sword cultivator', 'a beast-taming maiden', 'an alms-bowl monk', 'a black-armored general', 'a night-walking assassin', 'a kite-flying child', 'a star-gazing astrologer']},
    'object':     {'label': '物体', 'framing': ['a product shot', 'a macro close-up', 'a hero shot'], 'dof': 'studio lighting, clean background', 'subjects': ['an ancient bronze bell', 'a jade wine cup', 'a floating lantern', 'a glowing mechanical core', 'a lacquered wooden box', 'a jade ruyi scepter', 'a bronze mirror with cloud patterns', 'a floating scroll unfurling itself', 'a glazed purity vase', 'a mechanical puzzle box', 'a brass astrolabe', 'a silk sachet of herbs']},
    'scene':      {'label': '场景', 'framing': ['a wide establishing shot', 'a panoramic view', 'a cinematic wide shot'], 'dof': '', 'subjects': ['a misty mountain range', 'a floating celestial palace', 'a neon cyberpunk alley', 'a quiet bamboo forest', 'a vast desert oasis', 'a floating immortal isle above clouds', 'a deep neon-lit slum', 'a secluded valley of falling leaves', 'a frozen expanse of silent snow', 'a ruined temple overgrown with vines', 'a terraced rice field at dawn', 'a volcanic crater under ash sky']},
    'architecture': {'label': '建筑', 'framing': ['an architectural wide shot', 'an exterior establishing shot', 'a symmetrical facade view'], 'dof': '', 'subjects': ['a gothic cathedral', 'a brutalist concrete tower', 'a traditional courtyard mansion', 'a glass skyscraper', 'a wooden pagoda', 'a cliff-hanging temple', 'a glazed-tile treasure pagoda', 'a towering bronze gate', 'a ruined shrine', 'a vermilion palace hall', 'a stacked modern villa', 'a stone watchtower']},
    'creature':   {'label': '生物 / 神兽', 'framing': ['a creature portrait', 'a full-body creature shot', 'a dynamic creature pose'], 'dof': '', 'subjects': ['a coiled azure dragon', 'a nine-tailed fox spirit', 'a majestic qilin', 'a glowing jellyfish', 'a mechanical wolf', 'a giant black tortoise', 'a phoenix wreathed in flame', 'a gluttonous taotie beast', 'a soaring kunpeng bird', 'a candle dragon of primordial dark', 'a winged yingzhao beast', 'a coral-antlered spirit deer']},
    'vehicle':    {'label': '载具 / 机甲', 'framing': ['a hero shot of a vehicle', 'a side profile of a machine', 'a dynamic action shot'], 'dof': '', 'subjects': ['a sleek hovercar', 'a towering mecha', 'a steam-powered airship', 'a retro motorcycle', 'a futuristic train', 'a flying sword glinting with light', 'a bronze war chariot', 'a star-sailing skiff', 'a towering mech-god warrior', 'a silk-wrapped hot-air balloon', 'a clockwork centipede craft', 'a magnetic levitation pod']},
    'food':       {'label': '食物', 'framing': ['a top-down food shot', 'a close-up plating', 'a studio food photo'], 'dof': 'soft bokeh, studio lighting', 'subjects': ['a bowl of ramen', 'a matcha dessert', 'a Peking duck', 'a fruit tart', 'a steaming dumpling basket', 'an osmanthus flower cake', 'a cup of Longjing tea', 'a candied hawthorn stick', 'a bowl of Buddha-jumps-over-wall stew', 'a mooncake with egg yolk', 'a plate of sizzling hotpot', 'a chilled lychee bowl']},
    'abstract':   {'label': '抽象', 'framing': ['an abstract composition', 'a surreal visual', 'a minimalist form'], 'dof': '', 'subjects': ['flowing liquid metal', 'fragmented geometric shards', 'a swirl of smoke', 'crystalline structures', 'a field of floating orbs', 'a rift in spacetime', 'a quantum-fluctuating flower', 'a river of flowing stardust', 'a mosaic of mirror shards', 'a prismatic rainbow crystal', 'a vortex of folding dimensions', 'a lattice of glowing nodes']},
    'interior':   {'label': '室内', 'framing': ['an interior wide shot', 'a cozy room view', 'a symmetrical interior'], 'dof': '', 'subjects': ["a scholar's study", 'a temple hall', 'a futuristic control room', 'a rustic tea house', 'a grand library', 'a sutra archive hall', 'an alchemy chamber', 'an observatory star platform', 'a mirror-water audience hall', 'a zen meditation cell', 'a neon-lit hacker den', 'a greenhouse of spirit herbs']},
}

LENSES = {
    'rand':     {'label': '🎲 随机'},
    'f85':      {'label': '85mm 人像', 'v': '85mm portrait lens, shallow depth of field, soft bokeh'},
    'f50':      {'label': '50mm 标准', 'v': '50mm standard lens, natural perspective'},
    'f35':      {'label': '35mm 轻度压缩', 'v': '35mm lens, subtle compression'},
    'tele':     {'label': '800mm 超长焦+微透视', 'v': 'an extreme 800mm super telephoto lens, heavy spatial compression with a subtle thread of perspective'},
    'wide':     {'label': '14mm 超广角', 'v': 'a 14mm ultra-wide angle lens, exaggerated perspective'},
    'macro':    {'label': '微距', 'v': 'a macro lens, extreme close-up detail'},
    'bird':     {'label': '正交鸟瞰', 'v': "an orthographic bird's-eye view"},
    'tilt':     {'label': '移轴', 'v': 'a tilt-shift lens, miniature effect'},
    'close':    {'label': '特写', 'v': 'a dramatic close-up shot'},
    'fisheye':  {'label': '鱼眼', 'v': 'a fisheye lens, extreme wide-angle distortion'},
    'ana':      {'label': '变形宽银幕', 'v': 'an anamorphic lens, cinematic horizontal flare, 2.39:1 feel'},
    'f135':     {'label': '135mm 中长焦', 'v': 'a 135mm lens, gentle compression, shallow depth'},
    'drone':    {'label': '无人机俯拍', 'v': 'an aerial drone shot, top-down dynamic angle'},
    'overhead': {'label': '正顶视', 'v': 'a straight overhead top-down view'},
}

LIGHTS = {
    'rand':      {'label': '🎲 随机'},
    'golden':    {'label': '黄金时刻', 'v': 'golden hour, warm rim light'},
    'rembrandt': {'label': '伦勃朗光', 'v': 'Rembrandt lighting, dramatic chiaroscuro'},
    'neon':      {'label': '霓虹', 'v': 'neon glow, cyberpunk color grading'},
    'vol':       {'label': '体积光', 'v': 'volumetric god rays, atmospheric haze'},
    'studio':    {'label': '影棚光', 'v': 'soft studio lighting, clean highlights'},
    'moon':      {'label': '月光', 'v': 'moonlit night, cool blue tones'},
    'back':      {'label': '逆光剪影', 'v': 'backlit silhouette, glowing edge light'},
    'dappled':   {'label': '斑驳阳光', 'v': 'dappled sunlight through leaves'},
    'tyndall':   {'label': '丁达尔光', 'v': 'tyndall light beams, dust-filled air'},
    'biolum':    {'label': '生物荧光', 'v': 'bioluminescent glow, soft cyan-green light'},
    'candle':    {'label': '烛光', 'v': 'warm candlelight, intimate flicker'},
    'bicolor':   {'label': '双色温', 'v': 'dual-tone lighting, warm key and cool fill'},
    'hard':      {'label': '高反差硬光', 'v': 'hard directional light, deep shadows, high contrast'},
    'overcast':  {'label': '阴天柔光', 'v': 'soft overcast daylight, even diffuse light'},
    'stage':     {'label': '舞台光', 'v': 'dramatic stage lighting, colored spotlights'},
    'paper':     {'label': '宣纸窗光', 'v': 'soft window light filtering through rice-paper screens, gentle diffuse glow'},
    'mist':      {'label': '晨雾柔光', 'v': 'early-morning mist, soft diffused ambient light, low contrast'},
    'lantern':   {'label': '灯笼暖光', 'v': 'warm lantern glow, intimate soft amber light'},
    'moonclear': {'label': '月下清辉', 'v': 'clear moonlit radiance, cool silvery even light'},
}

# 中式画种(水墨 / 国风工笔)柔光池：随机光影时优先从中抽取，避开强立体写实光(伦勃朗 / 逆光 / 双色温 / 霓虹 / 硬光 / 高反差 / 舞台 / 黄金时刻)
CHINA_SOFT_LIGHTS = ['paper', 'mist', 'lantern', 'moonclear', 'moon', 'studio', 'dappled', 'vol', 'overcast', 'tyndall', 'candle', 'biolum']

ENVS = {
    'rand':      {'label': '🎲 随机'},
    'clouds':    {'label': '云海', 'v': 'above an endless sea of clouds'},
    'mountain':  {'label': '云雾山峦', 'v': 'within a misty mountain range'},
    'cyber':     {'label': '霓虹赛博城', 'v': 'in a neon cyberpunk city'},
    'forest':    {'label': '竹林', 'v': 'in a quiet bamboo forest'},
    'palace':    {'label': '天宫', 'v': 'within a vast celestial palace'},
    'ruins':     {'label': '古迹废墟', 'v': 'among ancient stone ruins'},
    'void':      {'label': '纯黑虚空', 'v': 'against a pure dark void'},
    'ocean':     {'label': '海面', 'v': 'above a pristine ocean'},
    'desert':    {'label': '沙漠', 'v': 'in a vast golden desert'},
    'snow':      {'label': '雪原', 'v': 'in a silent snowfield'},
    'rain':      {'label': '雨夜', 'v': 'on a rainy neon-lit night'},
    'galaxy':    {'label': '星空银河', 'v': 'beneath a glowing galaxy and starfield'},
    'lava':      {'label': '熔岩火山', 'v': 'above a glowing lava field and volcanic peaks'},
    'aurora':    {'label': '极光', 'v': 'under shifting aurora borealis'},
    'underwater': {'label': '水下', 'v': 'beneath the water surface, caustic light'},
    'flowers':   {'label': '花海', 'v': 'within an endless field of blooming flowers'},
    'ruinsCity': {'label': '废墟都市', 'v': 'among the ruins of a collapsed futuristic city'},
    'space':     {'label': '太空', 'v': 'in the silent void of deep space'},
    'guangxi':   {'label': '广西·壮乡', 'v': 'in a Guangxi karst landscape of bronze-drum Zhuang villages and terraced rice fields'},
    'nanfang':   {'label': '南方·江南', 'v': 'in a misty southern Jiangnan canal town of white walls, dark tiles and arched stone bridges'},
    'beifang':   {'label': '北方·苍劲', 'v': 'in a vast northern loess plain of grey-brick siheyuan and windswept poplars'},
}

MVAR = {
    'rand': {'label': '🎲 随机'},
    'v1':   {'label': '压迫悬顶·巨物出画', 'v': 'looming directly overhead and out of frame on all sides, only a sliver of its underside visible, an overwhelming mass that suggests infinite scale'},
    'v2':   {'label': '无限延伸·多向出画', 'v': 'bleeding out of the left, right and top edges, showing only a terrifying fraction of its true mass, implying infinite extension into an endless sea of clouds'},
    'v3':   {'label': '全高展现·局部出画', 'v': 'its full height of {H} meters rising from base to summit, while the rest of the structure bleeds out of the left and right edges into the clouds'},
    'v4':   {'label': '完整留白·全身+负空间', 'v': 'fully revealed in its complete form yet embraced by vast negative space, its full vertical height of {H} meters rising from base to summit while endless tiers of {TIERS} dissolve softly into an endless sea of clouds'},
    'v5':   {'label': '低空掠影·擦框而过', 'v': 'skimming just beneath the top edge and tearing past the right side of the frame, only a sliver of its {H}-meter bulk caught mid-motion, a sense of colossal mass in transit'},
    'v6':   {'label': '仰视攀升·直插云霄', 'v': 'shot from far below looking straight up, its {H}-meter height piercing the clouds overhead, the viewer a speck at its base gazing into endless verticality'},
    'v7':   {'label': '镜像倒影·上下对称', 'v': 'split by a still mirror-plane at its midsection, the upper {H} meters reflected perfectly downward so the structure doubles upon itself in flawless vertical symmetry'},
    'v8':   {'label': '部分沉没·半隐半现', 'v': 'half-submerged and slowly emerging from the ground and cloud layer, only the top {H} meters breaching into view while the rest stays swallowed in shadow below'},
    'v9':   {'label': '螺旋环绕·环抱视野', 'v': 'wrapping the frame in a slow spiral so its {TIERS} coil around the sightline, no single edge containing its mass'},
    'v10':  {'label': '居中巨像·正面压迫', 'v': 'presented face-on and dead-center, filling the frame from floor to ceiling with its {H}-meter frontage, an unblinking monolithic presence dominating the composition'},
}

# 普通模式「宏大视角/出画框法」：去尺度化的 10 种框法（不依赖 {H}/{TIERS}/colossal），
# 复用 variant 的构图思路、作用在普通主体上，让普通模式也有巨构那种压迫/延伸/攀升的框感。
NORMAL_VIEW = {
    'rand': {'label': '🎲 随机'},
    'none': {'label': '⚪ 无（标准框）'},
    'v1': {'label': '普·压迫悬顶·出画', 'v': 'looming directly overhead and out of frame on all sides, only a sliver of it visible, an overwhelming presence that suggests infinite scale'},
    'v2': {'label': '普·无限延伸·多向出画', 'v': 'bleeding out of the left, right and top edges, showing only a fraction of its mass, implying infinite extension'},
    'v3': {'label': '普·全高展现·局部出画', 'v': 'its full form rising from base to summit, while the rest bleeds out of the left and right edges'},
    'v4': {'label': '普·完整留白·全身+负空间', 'v': 'fully revealed yet embraced by vast negative space, rising from base to summit and dissolving softly into the surroundings'},
    'v5': {'label': '普·低空掠影·擦框而过', 'v': 'skimming just beneath the top edge and tearing past the right side of the frame, only a sliver caught mid-motion, a sense of great mass in transit'},
    'v6': {'label': '普·仰视攀升·直插云霄', 'v': 'shot from far below looking straight up, piercing the clouds overhead, the viewer a speck at its base gazing into endless verticality'},
    'v7': {'label': '普·镜像倒影·上下对称', 'v': 'split by a still mirror-plane at its midsection, the upper half reflected perfectly downward so it doubles upon itself in flawless vertical symmetry'},
    'v8': {'label': '普·部分沉没·半隐半现', 'v': 'half-submerged and slowly emerging, only the top breaching into view while the rest stays swallowed in shadow below'},
    'v9': {'label': '普·螺旋环绕·环抱视野', 'v': 'wrapping the frame in a slow spiral so it coils around the sightline, no single edge containing its mass'},
    'v10': {'label': '普·居中巨像·正面压迫', 'v': 'presented face-on and dead-center, filling the frame from floor to ceiling, a dominant monolithic presence'},
}

MEGA = {
    'rand':       {'label': '🎲 随机'},
    'xiangong':   {'name': '仙宫', 'subject': 'ancient Chinese celestial palace', 'micro': 'intricate dougong brackets, upturned flying eaves, vermilion lacquered wood, weathered white marble, carved lattice windows, railing-less floating bridges, coiled dragon columns, cloud-patterned balustrades, golden wind-bells, jade-inlaid panels, immortal-crane reliefs, drifting spirit-lanterns, lingering mist wreathing the eaves', 'materials': 'weathered white marble, lacquered vermilion wood, gilded bronze, glazed azure tiles, inlaid jade and mother-of-pearl', 'tiers': 'vermilion pavilions', 'refs': ['white-robed cultivator', 'old monk', 'crane', 'jade maiden', 'cloud-riding immortal', 'star-gazing astrologer']},
    'yunque':     {'name': '云上仙阙', 'subject': 'vast cloud-wreathed celestial jade gate', 'micro': 'spiraling cloud-step staircases, suspended jade pavilions, floating immortal islets, drifting crane flocks, upside-down reflecting pools, star-woven railings, wind-chime corridors, mist-veiled marble terraces', 'materials': 'translucent jade, gilded cloud motifs, mist-veiled marble, inlaid mother-of-pearl', 'tiers': 'floating jade terraces', 'refs': ['cloud-riding immortal', 'white crane', 'star spirit', 'jade maiden']},
    'robot':      {'name': '机器人', 'subject': 'humanoid war-construct', 'micro': 'riveted armor panels, hydraulic piston segments, coiled cable bundles, tiny observation portholes and repair gantries', 'materials': 'weathered titanium alloy, oxidized steel, brushed metal and carbon-fiber plating', 'tiers': 'armored plating', 'refs': ['maintenance worker', 'cargo truck', 'exploration drone']},
    'futureCity': {'name': '未来都市', 'subject': 'vertically layered megacity', 'micro': 'stacked transit tubes, vertical farms, neon billboard facades, drone docks and suspended walkways', 'materials': 'glass curtain walls, carbon composite, brushed steel and luminescent signage', 'tiers': 'neon districts', 'refs': ['commuter', 'delivery drone', 'patrol mech']},
    'megaship':   {'name': '巨舰', 'subject': 'colossal interstellar battleship', 'micro': 'armor plating, sensor arrays, launch bays, greebled hull details and maintenance crawlways', 'materials': 'weathered battleship grey steel, titanium alloy, glowing thrusters', 'tiers': 'hull segments', 'refs': ['crew member', 'shuttle', 'repair bot']},
    'worldtree':  {'name': '世界树', 'subject': 'colossal world tree', 'micro': 'interlocking branches, hanging root bridges, nested villages in the canopy, glowing leaf clusters', 'materials': 'ancient bark, living wood, bioluminescent moss and woven rope', 'tiers': 'canopy tiers', 'refs': ['villager', 'flying mount', 'spirit']},
    # 地域巨构：环境选对应地域时自动切到这些本地巨构主体
    'guangxiMega':  {'name': '铜鼓寨巨构', 'subject': 'stilted bronze-drum Zhuang mega-village', 'micro': 'bronze drum finials, stilted ganlan wooden platforms, indigo tie-dye banners, terraced rice steps climbing the structure, and ox-horn carved ridge beams', 'materials': 'weathered cedar, bronze drums, indigo-dyed cloth and karst stone', 'tiers': 'stilted ganlan tiers', 'refs': ['Zhuang elder in indigo robe', 'water buffalo', 'bronze-drum bearer']},
    'karstMega':    {'name': '喀斯特峰林巨构', 'subject': 'karst peak-forest mega-formation', 'micro': 'towering limestone fingers, dripping stalactite curtains, swallows-nest caverns, clinging banyan roots and mirror-pools at the base', 'materials': 'pitted limestone, stalactite, travertine and clinging moss', 'tiers': 'peak-forest tiers', 'refs': ['raft fisherman with cormorant', 'herb-gatherer on a ledge', 'singing boat girl']},
    'longjiMega':   {'name': '龙脊梯田巨构', 'subject': 'terraced rice-field megastructure', 'micro': 'sweeping curved terrace steps, drowned mirror-pools reflecting sky, rice-stalk fringes, stone-lined irrigation channels and stilted grain storehouses', 'materials': 'rammed-earth paddy walls, flooded loess, rice straw and fieldstone', 'tiers': 'terrace tiers', 'refs': ['Yao woman in embroidered robe', 'rice-planting child', 'pack-horse with baskets']},
    'nanfangMega':  {'name': '江南水阁巨构', 'subject': 'Jiangnan water-town pavilion complex', 'micro': 'white-washed walls, dark tile roofs, horse-head gables, arched stone bridges spanning water channels, and lattice-carved wooden screens', 'materials': 'white-washed walls, dark clay tiles, grey brick and carved stone', 'tiers': 'water-pavilion tiers', 'refs': ['boatman in bamboo hat', 'tea-serving maid', 'scholar with umbrella']},
    'gardenMega':   {'name': '江南园林巨构', 'subject': 'Suzhou scholar-garden megastructure', 'micro': 'pierced taihu rocks, leak-window galleries, zigzag covered corridors, lotus ponds and hexagonal viewing pavilions', 'materials': 'pitted taihu limestone, grey brick, carved wood and bamboo', 'tiers': 'courtyard tiers', 'refs': ['gardener with shears', 'poet on a zigzag bridge', 'boy chasing butterflies']},
    'bridgeMega':   {'name': '水乡廊桥巨构', 'subject': 'covered corridor-bridge megastructure', 'micro': 'overlapping xieshan rooflines, timber corridor columns, hanging fish-skin wind chimes, mid-bridge shrine alcoves and mooring steps', 'materials': 'weathered timber, grey tile, lacquered wood and stone piers', 'tiers': 'corridor tiers', 'refs': ['boatwoman sculling a skiff', 'peddler with pole', 'child releasing a lantern']},
    'beifangMega':  {'name': '黄土窑塔巨构', 'subject': 'northern loess yaodong pagoda-fortress', 'micro': 'carved loess arches, grey-brick buttresses, cave-dwelling tiers, wind-eroded ramparts, and poplar-lined ramparts', 'materials': 'carved loess, grey brick, weathered timber and rammed earth', 'tiers': 'yaodong cave tiers', 'refs': ['northern peasant in padded cotton coat', 'stone lion', 'courier on horseback']},
    'wallMega':     {'name': '长城烽燧巨构', 'subject': 'great-wall beacon-fortress megastructure', 'micro': 'crenellated battlements, beacon towers, watch-post buttresses, winding rampart spines and fortified mountain passes', 'materials': 'grey granite, rammed earth, weathered brick and flagstone', 'tiers': 'beacon tiers', 'refs': ['garrison soldier in lamellar', 'signal-fire tender', 'mounted courier']},
    'iceMega':      {'name': '冰雕巨构', 'subject': 'northern ice-carved palace', 'micro': 'translucent ice blocks, frozen colonnades, snow-brick vaults, embedded ice-lantern cores and frosted crystal spires', 'materials': 'river ice, packed snow, frost crystal and frozen timber', 'tiers': 'ice-vault tiers', 'refs': ['fur-coated hunter', 'child with a spinning top', 'lantern-bearer']},
    # —— 有机 / 异形 / 生物错位 ——
    'biomass':    {'name': '有机物巨构', 'subject': 'living biomass conglomeration', 'micro': 'pulsing vein networks, exposed muscle bundles, nested organ cavities, glistening mucous membranes and calcified bone scaffolding', 'materials': 'living tissue, sinew, cartilage and keratin', 'tiers': 'organ chambers', 'refs': ['surgeon in sterile gown', 'lost explorer', 'medical drone']},
    'cthulhu':    {'name': '克苏鲁巨构', 'subject': 'eldritch tentacled titan', 'micro': 'writhing tentacle clusters, suckered appendages, barnacled hide, scattered cyclopean eyes and membranous wing-folds', 'materials': 'wet rubbery hide, chitin, slime-slicked flesh and barnacle-encrusted ancient stone', 'tiers': 'tentacle crowns', 'refs': ['robed cultist', 'drowning sailor', 'tiny submarine']},
    'skinbeast':  {'name': '皮肉巨兽', 'subject': 'fleshy skin-beast', 'micro': 'folds of drooping skin, puckered pores, subcutaneous veins, soft wobbling fat masses and weeping wounds', 'materials': 'living skin, fat, sinew and exposed muscle', 'tiers': 'skin folds', 'refs': ['fleeing villager', 'biologist with sampler', 'torch-bearer']},
    'insectoid':  {'name': '巨虫母巢', 'subject': 'insectoid hive-queen', 'micro': 'compound eyes, segmented chitin plates, buzzing membranous wings, ovipositor tubes and resinous honeycomb cells', 'materials': 'chitin, resin, silk and wax', 'tiers': 'abdominal segments', 'refs': ['beekeeper in veil', 'lone soldier', 'scout drone']},
    'oceanland':  {'name': '搁浅鲸教堂', 'subject': 'beached whale-cathedral', 'micro': 'barnacled skin, rib-vault arches, anemone gardens, coral-encrusted jaw bones and tide-pool chapels', 'materials': 'weathered bone, coral, barnacle and salt-bleached wood', 'tiers': 'rib-vault tiers', 'refs': ['fisherman in slicker', 'shell-collector child', 'lighthouse keeper']},
    'landocean':  {'name': '沉没森林巨构', 'subject': 'submerged forest-monolith', 'micro': 'drowned pine trunks, kelp-strangled branches, fish-swirling hollows, fossilized root buttresses and silt-covered stone shrines', 'materials': 'waterlogged wood, kelp, fossilized stone and salt crystal', 'tiers': 'drowned canopy tiers', 'refs': ['diver in brass suit', 'sea turtle', 'drifting jellyfish']},
    'crystal':    {'name': '巨型水晶', 'subject': 'translucent crystal formation', 'micro': 'refractive facets, internal light caustics, inclusions of frozen figures, faceted cleavage planes and rainbow prism cores', 'materials': 'quartz, amethyst, beryl and luminescent inclusion', 'tiers': 'crystal clusters', 'refs': ['miner with pickaxe', 'crystal-gazing seer', 'spire-climber']},
    # —— 神佛 / 中式宗教 ——
    'buddha':     {'name': '大佛巨构', 'subject': 'seated Buddha colossus', 'micro': 'snail-shell curls of hair, ushnisha crown, draping monastic robes, lotus-throne petals and carved sutra niches', 'materials': 'gilded bronze, sandstone, jade and lacquered wood', 'tiers': 'lotus-tier platforms', 'refs': ['praying pilgrim', 'incense-bearing monk', 'lotus-bearing child']},
    'taoist':     {'name': '道家神祇巨构', 'subject': 'Taoist deity construct', 'micro': 'taiji bagua diagrams, floating talisman arrays, coiling azure-black tortoise shells, suspended sword pavilions and cloud-stepping platforms', 'materials': 'bronze, jade, lacquered black wood and ink-stained silk', 'tiers': 'bagua tiers', 'refs': ['Daoist priest in topknot', 'paper-crane rider', 'sword-bearing immortal']},
    'clayidol':   {'name': '风化泥像', 'subject': 'weathered clay idol', 'micro': 'cracked terracotta skin, exposed straw armature, eroded facial features, embedded pottery shards and wind-hollowed cavities', 'materials': 'sun-baked terracotta, straw, river clay and weathered sandstone', 'tiers': 'eroded strata', 'refs': ['kneeling worshipper', 'archeologist with brush', 'goat herd']},
    # —— 联想补充 ——
    'ossuary':    {'name': '白骨教堂', 'subject': 'cathedral of stacked bones', 'micro': 'rib-vault arches, skull mosaics, femur columns, jawbone chandeliers and pelvis buttresses', 'materials': 'yellowed bone, ivory, marrow and calcified cartilage', 'tiers': 'bone-strata tiers', 'refs': ['hooded monk', 'gravedigger', 'raven']},
    'fungal':     {'name': '真菌巨构', 'subject': 'fungal titan', 'micro': 'gilled caps, mycelium threads, spore-dusting gills, bracket-fungus shelves and bioluminescent veins', 'materials': 'fungal flesh, chitin, mycelium and spore dust', 'tiers': 'cap tiers', 'refs': ['spore-masked forager', 'glowing beetle', 'tiny druid']},
    'mask':       {'name': '仪式面具巨构', 'subject': 'floating ritual mask', 'micro': 'lacquered grin, inlaid shell eyes, dangling tassel beards, painted spirit patterns and hollow echoing mouth-cave', 'materials': 'lacquered wood, nacre, pigment and silk', 'tiers': 'mask tiers', 'refs': ['masked dancer', 'drummer', 'child bearer']},
    # —— 暗黑 / 恐怖 / 血腥 / 克苏鲁 ——
    'abysseyes':  {'name': '深渊凝视之眼', 'subject': 'colossal abyssal gazing eye', 'micro': 'a lidless hemisphere of pale cornea, a dilated black pupil swallowing the horizon, veined sclera, drifting cataracts of blind fish, and barnacle-ringed iris ridges', 'materials': 'wet sclera, polished obsidian pupil, calcified eyelid rims and cold abyssal stone', 'tiers': 'iris strata', 'refs': ['drowned sailor', 'mad oracle', 'tiny submarine']},
    'fleshtemple': {'name': '血肉祭坛巨构', 'subject': 'colossal flesh altar', 'micro': 'glistening muscle walls, pulsing artery columns, weeping sacrificial basins, stretched sinew awnings and a throbbing heart-shrine at the core', 'materials': 'living meat, coagulated blood, stretched skin and bone clasps', 'tiers': 'organ tiers', 'refs': ['hooded cultist', 'flayed acolyte', 'ritual blade']},
    'plague':     {'name': '瘟疫巨构', 'subject': 'colossal plague colossus', 'micro': 'bursting pustules, streams of black bile, swarming rats in the crevices, festering bandage wraps and a crown of buzzing flies', 'materials': 'rotting flesh, tarry pus, tattered shroud cloth and corroded bell metal', 'tiers': 'festering tiers', 'refs': ['plague doctor with beak mask', 'collapsing villager', 'carrion crow']},
    # —— 彩蛋 ——
    'suzanne':    {'name': 'Blender 猴头（建模）', 'subject': 'Blender Suzanne monkey head 3D model', 'micro': 'the classic Blender Suzanne head: oversized rounded cranium, large bulging round eyes with recessed sockets, a small heart-shaped mouth and nostrils, two big floppy ears, smooth subdivision-surface shading, neutral expression, rendered as a matte grey 3D software model inside the Blender viewport', 'materials': 'matte grey Blender-default plastic, smooth clay-like subdivision surface, soft viewport shading', 'tiers': 'subdivision levels', 'refs': ['3D artist with stylus', 'floating 3D cursor', 'viewport grid reflected in the eyes']},
    # —— 新增主体多样性 ——
    'bookmount':  {'name': '书山巨构', 'subject': 'colossal mountain of books', 'micro': 'spine-ladders, gilded page edges, drifting book-scorpions, candle-lit reading terraces, scroll-bridges and ink-stained marble stairs', 'materials': 'aged paper, gilded leather binding, dark wood and brass fittings', 'tiers': 'stacked shelf tiers', 'refs': ['scholar with a ladder', 'sleeping cat on a folio', 'floating page']},
    'gearfort':   {'name': '齿轮机械城', 'subject': 'colossal clockwork gear fortress', 'micro': 'meshing brass gears, pendulum spines, steam-vent crowns, pressure-gauge eyes and ratchet buttresses', 'materials': 'oxidized brass, blackened steel, riveted copper and glass dials', 'tiers': 'gear-ring tiers', 'refs': ['oil-smudged machinist', 'clockwork sparrow', 'pressure-gauge gnome']},
    'volcano':    {'name': '熔岩火山巨构', 'subject': 'colossal volcanic megastructure', 'micro': 'glowing lava fissures, basalt column flutes, ember-cascading vents, obsidian shard spires and ash-drift ridgelines', 'materials': 'basalt, glowing magma rock, cooled obsidian and scorched iron', 'tiers': 'magma-strata tiers', 'refs': ['molten-helm smith', 'ash-winged phoenix', 'lava-skiff pilot']},
    'lighthouse': {'name': '星空灯塔', 'subject': 'colossal star-lighthouse', 'micro': 'rotating beam-lanterns, constellation-engraved rails, tide-worn spiral stairs, mooring rings and frosted glass galleries', 'materials': 'weathered stone, patinated copper, leaded glass and iron rivets', 'tiers': 'lantern-gallery tiers', 'refs': ['lamp-keeper in oilskin', 'migratory star-bird', 'small sailing ship']},
}
# 巨构形态：控制"重复感"。默认蜂窝重复即原行为；其余形态改写表面描述，打破千篇一律的"无数相同单元"骨架
MEGA_MORPH = {
    'rand': {'label': '🎲 随机'},
    'honeycomb': {'label': '蜂窝重复（默认）', 'name': '蜂窝重复'},
    'monolith':  {'label': '单体巨构', 'name': '单体巨构'},
    'tiered':    {'label': '层叠塔式', 'name': '层叠塔式'},
    'organic':   {'label': '有机生长', 'name': '有机生长'},
    'fragment':  {'label': '碎片拼合', 'name': '碎片拼合'},
    'woven':    {'label': '编织缠绕', 'name': '编织缠绕'},
    'spiral':    {'label': '螺旋攀升', 'name': '螺旋攀升'},
    'lattice':   {'label': '晶格阵列', 'name': '晶格阵列'},
    'floating':  {'label': '层叠悬浮', 'name': '层叠悬浮'},
    'burst':     {'label': '放射爆裂', 'name': '放射爆裂'},
}
# 环境→地域巨构池 自动映射：环境选广西/南方/北方时，巨构主体从对应地域巨构池随机抽
# 广西 3 个（铜鼓寨/喀斯特峰林/龙脊梯田），南方/北方各 1 个
ENV_MEGA_POOL = {
    'guangxi': ['guangxiMega', 'karstMega', 'longjiMega'],
    'nanfang': ['nanfangMega', 'gardenMega', 'bridgeMega'],
    'beifang': ['beifangMega', 'wallMega', 'iceMega'],
}

NEG_ENVS = ['a misty cloud sea', 'a starry sky', 'morning mist', 'an endless sea of clouds']

NEG = {
    'real':     'low quality, blurry, out of focus, artifacts, deformed, watermark, text, extra fingers',
    'ink':      'colorful clutter, harsh outlines, low ink control, smudges, watermark, text',
    'anime':    'realistic photo, 3d render, low quality, deformed hands, extra limbs, watermark, text',
    'paint':    'flat, low detail, muddy colors, watermark, text, blurry',
    'render3d': 'noise, low poly, unfinished render, artifacts, watermark, text, blurry',
    'cyber':    'low quality, blurry, deformed, watermark, text, washed out',
    'guofeng':  'harsh outlines, muddy colors, western style, watermark, text',
    'pixel':    'smooth gradients, anti-aliasing, realistic photo, blurry, watermark, text',
    'cinema':   'flat, no film grain, oversaturated, blurry, watermark, text',
    'oil':      'flat digital, low detail, blurry, watermark, text',
    'lowpoly':  'realistic photo, smooth shading, high poly, blurry, watermark, text',
    'vapor':    'muddy colors, realistic photo, low quality, watermark, text',
}

# 防文字/铭牌：古典油画、宗教画等风格容易在画面底部联想出题签/铭牌乱码，
# 统一追加一组针对「文字、签名、题字、标签」的负面词（不论何种风格都生效）。
ANTI_TEXT = 'caption, plaque, inscription, signature, words, letters, labels, frame text, typography, written text, engraved text'

# 负面提示词按环境适配：针对特殊环境追加针对性负面词（出图节点 negative 拼接）
NEG_ENV_MAP = {
    'underwater': 'above water, dry, terrestrial plants',
    'snow':       'warm summer tones, green foliage',
    'desert':     'water, snow, lush green, humidity',
    'rain':       'dry, sunny, clear sky',
    'lava':       'water, snow, ice, cold tones',
    'space':      'ground, buildings, atmosphere, clouds',
    'galaxy':     'ground, buildings, atmosphere, clouds',
    'void':       'clutter, busy background, furniture',
    'ocean':      'land, buildings, desert',
    'aurora':     'daytime, sun, tropical',
    'flowers':    'withered, dead, winter',
    'guangxi':    'desert, snow, urban concrete',
    'nanfang':    'desert, snow, arid',
    'beifang':    'tropical, humidity, lush green, water town',
    'cyber':      'rural, nature, daylight, green plants',
    'forest':     'desert, neon, urban',
}

FLAVOR = {
    'real':     {'props': ['natural foliage', 'weathered stone', 'soft fabric', 'an old wooden door', 'moss-covered rocks', 'a worn linen robe'], 'atmos': ['soft daylight', 'gentle haze'], 'palette': 'natural muted tones'},
    'ink':      {'props': ['drifting ink mist', 'a lone pine', 'a flowing stream', 'a solitary skiff', 'a distant mountain silhouette', 'a broken lotus leaf'], 'atmos': ['expansive white negative space', 'soft diffused wash'], 'palette': 'monochrome ink tones with faint mineral color'},
    'anime':    {'props': ['floating petals', 'a glowing sigil', 'wind-blown ribbon', 'a streaming scarf', 'light-woven wings', 'trailing stardust'], 'atmos': ['clean flat sky', 'vibrant gradient backdrop'], 'palette': 'saturated cel-shaded colors'},
    'paint':    {'props': ['thick palette-knife strokes', 'impasto highlights', 'a visible canvas weave', 'a glob of pure pigment', 'a scored-through highlight'], 'atmos': ['painterly atmosphere', 'rich textured brushwork'], 'palette': 'vivid oil-like palette'},
    'render3d': {'props': ['subsurface scattering', 'glossy PBR materials', 'ray-traced reflections', 'caustic light patterns', 'ambient occlusion contact shadows', 'a frosted glass surface'], 'atmos': ['volumetric atmosphere'], 'palette': 'physically accurate lighting'},
    'cyber':    {'props': ['neon signage', 'holographic UI fragments', 'chromium plating', 'a streaming data feed', 'a rain-streaked screen', 'a glowing circuit tattoo'], 'atmos': ['rain-slick streets', 'neon-bathed haze'], 'palette': 'magenta-cyan neon palette'},
    'scifi':    {'props': ['a holographic HUD overlay', 'a glowing energy core', 'chrome plating', 'fiber-optic light strands', 'a levitating drone', 'magnetic rail tracks'], 'atmos': ['a faint reactor hum', 'cool electric haze'], 'palette': 'cool steel-blue with cyan energy accents'},
    'guofeng':  {'props': ['gold-leaf detail', 'a jade ruyi', 'silk tassels', 'interlocking vine patterns', 'a coral-inlaid frame', 'a cinnabar seal'], 'atmos': ['fine mineral-pigment wash', 'classical symmetry'], 'palette': 'elegant mineral palette of azurite and malachite'},
    'pixel':    {'props': ['dithered shading', '8-bit particle effects', 'a limited-band sky', 'a crisp grid backdrop', 'a tiled cloud sprite', 'a blinking cursor'], 'atmos': ['limited-band sky', 'crisp grid backdrop'], 'palette': 'restricted 16-color palette'},
    'cinema':   {'props': ['anamorphic lens flare', 'volumetric god rays', 'a horizontal streak of light', 'a dust-moted sun shaft', 'a teal-to-orange transition'], 'atmos': ['atmospheric haze', 'teal-orange grade'], 'palette': 'cinematic teal and orange palette'},
    'oil':      {'props': ['visible brushwork', 'thick impasto ridges', 'a warm shadow gradient', 'a palette-scraped highlight', 'a glazed scumble layer'], 'atmos': ['chiaroscuro shadow', 'warm gallery light'], 'palette': 'rich earthy oil palette'},
    'lowpoly':  {'props': ['faceted geometric forms', 'flat-shaded planes', 'a hard-edged silhouette', 'a crisp facet boundary', 'a gradient-banded surface'], 'atmos': ['minimalist gradient backdrop'], 'palette': 'clean pastel low-poly palette'},
    'vapor':    {'props': ['a glowing grid floor', 'retro CRT scanlines', 'a marble bust', 'a drifting palm frond', 'a chromed dolphin statue'], 'atmos': ['pink-cyan gradient haze'], 'palette': 'pink-and-cyan vaporwave palette'},
}

H3_SOUND = {
    'clouds': 'a low wind drifting through an endless sea of clouds', 'mountain': 'a mountain breeze with distant birdsong',
    'cyber': 'rain hissing on neon and a distant traffic hum', 'forest': 'leaves rustling and a quiet stream',
    'palace': 'wind chimes and distant temple bells', 'ruins': 'wind threading through broken stone',
    'void': 'near-total silence with a faint low drone', 'ocean': 'waves lapping and distant gull cries',
    'desert': 'a dry wind moving over sand', 'snow': 'the soft hush of falling snow',
    'rain': 'rain pattering on neon and puddles', 'galaxy': 'a silent cosmic hum',
    'lava': 'cracking rock and a deep volcanic roar', 'aurora': 'a crisp arctic wind',
    'underwater': 'muffled water pressure and drifting bubbles', 'flowers': 'a gentle breeze through blossoms',
    'ruinsCity': 'wind through collapsed towers', 'space': 'the void with a faint electronic pulse',
    'guangxi': 'a bronze drum and lusheng folk ambience with distant mountain echoes', 'nanfang': 'misty rain on canal water with a distant flute',
    'beifang': 'a dry wind over loess with a distant suona',
}

H3_MUSIC = {
    'real': 'a restrained, cinematic score', 'ink': 'a guzheng and erhu led ambient', 'guofeng': 'a guzheng and erhu led ambient',
    'anime': 'a bright, uplifting theme', 'paint': 'a bright, uplifting theme', 'cyber': 'a driving synthwave pulse',
    'pixel': 'a playful chiptune loop', 'cinema': 'a restrained, cinematic score', 'oil': 'a warm, classical piano',
    'render3d': 'an epic, sweeping orchestral score',
    'lowpoly': 'a dreamy ambient pad', 'vapor': 'a nostalgic synth pad', 'scifi': 'an ambient electronic score',
}

MOODS = ['ethereal', 'serene', 'majestic', 'ominous', 'intimate', 'epic', 'melancholic', 'triumphant', 'otherworldly', 'haunting']

# 题材包：一个简洁「题材」下拉背后挂庞大元素池，选中后向提示词注入该题材氛围 + 随机 3-5 个元素细节
# 非色情成人向氛围（暗黑/恐怖/血腥/克苏鲁），覆盖尽量多可能出现的物象
THEME_POOL = {
    'rand': {'label': '🎲 随机'},
    'none': {'label': '无（默认）'},
    'cthulhu': {
        'label': '暗黑克苏鲁',
        'aura': 'an eldritch, lovecraftian atmosphere of cosmic dread and the unknowable',
        'elems': [
            'writhing black tentacles coiling from the deep', 'cyclopean non-euclidean geometry that hurts the eye',
            'a vast lidless eye of pale moonlight', 'whispering voices leaking from the abyss',
            'barnacle-crusted monoliths of dead gods', 'a drowned city of Rlyeh half-risen from the sea',
            'star-spawned sigils glowing faint sickly green', 'an ink-black ocean trench without bottom',
            'a writhing mass of blind eyestalks', 'mad spiraling constellations that should not exist',
            'a gaping maw of infinite concentric teeth', 'gelatinous translucent flesh that breathes',
            'a cthulhuoid silhouette half-submerged in brine', 'fungal spores of the outer mythos',
            'elder sign carvings weeping black ichor', 'a pulsing leviathan heart the size of a cathedral',
            'tentacles fused with cathedral spires', 'a sky torn open with green lightning',
            'abyssal pressure crushing the last of the light', 'a drowned chorus of gibbering cultists',
            'a spiral staircase descending into the mind', 'a book bound in something that was never skin',
        ],
    },
    'gore': {
        'label': '血腥恐怖',
        'aura': 'a visceral, blood-soaked atmosphere of raw horror and slaughter',
        'elems': [
            'rivers of congealing black blood', 'exposed pulsating organs still warm',
            'cracked bone jutting from torn flesh', 'a butcher hook of rusted iron',
            'flayed skin draped like wet curtains', 'a pool of weeping viscera',
            'bloody handprints smeared across stone', 'a rack strung with stretched sinew',
            'dripping viscera from the ceiling', 'a mask stitched from many faces',
            'a flood of crimson over white marble', 'gnashing teeth of yellowed bone',
            'a throne built from stacked skulls', 'candlelit altars crusted with old flesh',
            'a wound that breathes when no one watches', 'a corridor hung with flayed carcasses',
            'blade-sliced flesh with steaming severed edges', 'a chalice brimming with warm blood',
            'a wall packed with pressed pale bodies', 'a heart still beating on a cold plate',
            'a bone saw half-buried in red pulp', 'eyes gouged and replaced with writhing worms',
        ],
    },
    'creepy': {
        'label': '诡异惊悚',
        'aura': 'an uncanny, creeping atmosphere of quiet dread and the fundamentally wrong',
        'elems': [
            'a porcelain doll with hairline-cracked eyes', 'a rocking chair that moves with no one in it',
            'whispering shadows behind the wallpaper', 'a corridor that loops back on itself',
            "a child's laughter with no child present", 'a mirror showing a different empty room',
            'a pale handprint pressed on the inside of the window', 'candles that gutter in still air',
            'a music box grinding a broken tune', 'a door that was not there the night before',
            'footsteps echoing above empty rooms', 'a portrait whose eyes follow you down the hall',
            'a telephone ringing from a long-dead line', 'a noose swaying in a windless room',
            'a phonograph spinning down to silence', 'a clock stopped at the hour of someone death',
            'a veil that hides something far too tall', 'a lullaby sung slowly in reverse',
            'a staircase descending into absolute dark', 'a cold breath on the back of the neck',
            'a second shadow that lags behind yours', 'wallpaper peeling to reveal a watching face',
        ],
    },
    # —— 横向扩充题材包（与暗黑三题材同机制：氛围句 + 随机 3-5 元素） ——
    'scifi_waste': {
        'label': '科幻废土',
        'aura': 'a desolate sci-fi wasteland of rust, faded tech and abandoned futures',
        'elems': [
            'a half-buried rusted mech husk', 'collapsed neon signs flickering dead slogans',
            'drifting toxic smog and ash', 'a shattered orbital ring on the horizon',
            'broken drone swarms stitched from scrap', 'a drowned server farm leaking data-rain',
            'vine-choked blast doors of a sealed vault', 'a childs toy fused with circuit boards',
            'a rusted elevator climbing to nothing', 'corroded maglev rails swallowed by sand',
            'a floating billboard looping a century-old ad', 'a lone wind-turbine still turning',
            'a bunker mural of a forgotten flag', 'scrap-cities built on dead megastructures',
            'a cracked VR headset showing a green field', 'a feral robot herding mutant goats',
        ],
    },
    'dreamcore': {
        'label': '童话梦核',
        'aura': 'a surreal dreamcore liminal space of childhood memory and impossible comfort',
        'elems': [
            'a pastel ballroom with no doors', 'endless neon ball-pits under a soft sky',
            'a carousel of faceless porcelain ponies', 'a giant teddy with button eyes weeping',
            'a school hallway that loops forever', 'a birthday cake the size of a house',
            'a swimming pool filled with warm milk', 'clouds you can sit on like furniture',
            'a Ferris wheel turning in a bedroom', 'a hallway of identical yellow doors',
            'a lullaby hummed by the walls themselves', 'a slide descending into soft clouds',
            'a dollhouse larger than the sky', 'candy rain falling upward',
            'a staircase made of fluffy clouds', 'a sun with a sleepy smiling face',
        ],
    },
    'steampunk': {
        'label': '蒸汽朋克',
        'aura': 'a brass-and-copper steampunk world of clockwork, steam and imperial invention',
        'elems': [
            'a roaring boiler-core of riveted brass', 'whirring gear-trains the size of buildings',
            'a steam locomotive fused with an airship', 'a clockwork automaton pouring tea',
            'a pressure-gauge forest of hissing dials', 'brass diving-suits walking the seabed',
            'a floating city held by balloon-dirigibles', 'a gramophone broadcasting thunder',
            'a hydraulic walking-tower with a chimney heart', 'cogs raining from a punctured sky',
            'a copper octopus-submersible surfacing', 'a steam-pipe organ played by the wind',
            'a pocketwatch city where time is currency', 'airships tethered to a glass dome',
            'a brass telescope aimed at a second moon', 'a mechanic with a gear for a heart',
        ],
    },
    'mythic': {
        'label': '神话史诗',
        'aura': 'a mythic, larger-than-life epic atmosphere of gods, oaths and the founding of worlds',
        'elems': [
            'a thunderbolt-forged sword embedded in stone', 'a golden chariot crossing the dawn',
            'a titan-scale staircase to a cloud realm', 'a constellation taking human form',
            'a horn that wakes sleeping mountains', 'a river of liquid starlight',
            'a phoenix cradled in a warriors hands', 'a god weighing a soul on golden scales',
            'a bridge of frozen rainbow spanning the abyss', 'a library of every word ever spoken',
            'a spear that never misses its fate', 'a tree bearing fruits of forgotten empires',
            'a cauldron that restores the fallen', 'a serpent circling the world',
            'a hall of heroes with a thousand shields', 'a mountain that is a sleeping god back',
        ],
    },
    'ghost_cn': {
        'label': '东方志怪',
        'aura': 'a Chinese folklore atmosphere of wandering spirits, fox magic and the thin veil between worlds',
        'elems': [
            'a nine-tailed fox spirit weaving illusions', 'a paper effigy burning into a living servant',
            'a lantern-lit bridge to the underworld', 'a drought demon withering the land',
            'a river-fetching ghost girl with wet hair', 'a taotie mask devouring the moon',
            'immortals playing chess on a floating cloud', 'a coffin that walks at midnight',
            'a fox bride in a red bridal veil', 'a jiangshi hopping under a talisman',
            'a peach-tree sword cutting through mirage', 'a moonrabbit pounding elixir of life',
            'a blue-faced yaksha guarding a gate', 'a grievance-ghost rattling chained bones',
            'a dragon-king palace beneath the waves', 'a scholar haunted by a brush-spirit',
        ],
    },
    'space_dead': {
        'label': '太空寂灭',
        'aura': 'an eerie silent void of dead space, cold machinery and the end of everything',
        'elems': [
            'a derelict station drifting with no power', 'a frozen astronaut tumbling in vacuum',
            'a black hole swallowing a lost fleet', 'a red giant breathing its last light',
            'a broken ringworld cracked like an egg', 'a signal repeating from a dead star',
            'a comet graveyard of shattered moons', 'a silent AI core still running prayers',
            'a wormhole leaking another universe', 'a frozen ocean on a moon with no sun',
            'a satellite forest of dead eyes', 'a cosmic string humming the universes end',
            'a tomb-ship of a vanished civilization', 'a nebula shaped like a screaming face',
            'a lone lighthouse at the edge of reality', 'a clock ticking in zero gravity',
        ],
    },
    'deepsea': {
        'label': '深海',
        'aura': 'a crushing abyssal deep-sea atmosphere of bioluminescence, pressure and the alien dark',
        'elems': [
            'an anglerfish lantern in the endless black', 'a whale-fall cathedral of bone',
            'a hydrothermal vent garden of tubes', 'a jelly-forest pulsing soft light',
            'a giant squid unfolding in the murk', 'a sunken temple guarded by eels',
            'a trench wall of eyeless pale crabs', 'a bioluminescent current spelling words',
            'a creeping octopus wearing a shell-crown', 'a pressure dome cracking inward',
            'a drowned city beneath the waves', 'a glowing plankton storm',
            'a leviathan circling the sonar', 'a coral spire taller than cathedrals',
            'a submarine crushed like a tin can', 'a silent abyssal snail dragging its tower',
        ],
    },
    'apocalypse': {
        'label': '末日丧尸',
        'aura': 'a post-apocalyptic zombie-horde atmosphere of collapse, decay and the last survivors',
        'elems': [
            'a shambling horde pouring from a subway', 'a bus overturned and rusted shut',
            'a quarantined zone of yellow tape', 'a bonfire of burning infected',
            'a survivor camp behind razor wire', 'a skyscraper draped in creeping vines',
            'a severed arm still clutching a phone', 'a roadblock of burnt-out cars',
            'a church bell tolling for no one', 'a gas-mask wanderer with a cricket bat',
            'a feral dog pack in the mall', 'a helicopter crash smoldering on a roof',
            'a wall of stacked corpses and sandbags', 'a flickering emergency broadcast',
            'a childs drawing of the world before', 'a horde silhouette against a blood moon',
        ],
    },
    'cyber_neon': {
        'label': '赛博霓虹',
        'aura': 'a hyper-saturated cyber-neon megacity of augmented life, data and endless night',
        'elems': [
            'a waterfall of holographic kanji ads', 'a street ramen stall under pink neon',
            'a cybernetic geisha with fiber-optic hair', 'a drone-delivery swarm overhead',
            'a rain-slick arcade of claw machines', 'a back-alley chrome clinic',
            'a data-ghost flickering through walls', 'a pachinko tower of blinding light',
            'a neural-jack bar with no bouncer', 'a cat-ear android selling memory-chips',
            'a billboard idol singing to no one', 'a cable-sea of power lines overhead',
            'a vending machine dispensing dreams', 'a rooftop garden above the smog',
            'a black-market augment surgeon', 'a neon torii gate to a digital shrine',
        ],
    },
    'surreal': {
        'label': '超现实悖论',
        'aura': 'a surreal, impossible atmosphere where physics, scale and logic quietly break',
        'elems': [
            'a staircase that loops into itself', 'a sky made of upside-down oceans',
            'a hand larger than the city it holds', 'a clock melting over a cliff edge',
            'a door opening onto a different season', 'a mountain floating inside a room',
            'a river flowing upward to the clouds', 'a face formed by a crowd of birds',
            'a forest of chairs growing from soil', 'an eye blinking in the desert floor',
            'a building turned inside-out', 'a road that ends at the horizon it started from',
            'a moon you can climb like a staircase', 'a shadow that detaches and walks',
            'a book whose pages are windows', 'a horizon line that curves upward',
        ],
    },
}

# ===================== 风格亲和层：world / era 标签 + 隔离·碰撞 =====================
# 给「风格」与「内容维度（题材）」各打世界观标签。隔离模式下，内容 world 不在风格容忍集内 → 不注入 + 警告；
# 碰撞模式下保留，并补一句桥接渲染词把违和转成「艺术火花」。复古(retro)可桥接国风/古典（用户要的火花），
# 未来科幻(futuristic)不桥接传统风格（默认隔离）。自由文本物体只做软警告、绝不吞字。
STYLE_WORLD = {
    'real': 'neutral', 'ink': 'guofeng', 'anime': 'anime', 'paint': 'neutral',
    'render3d': 'neutral', 'cyber': 'scifi', 'guofeng': 'guofeng', 'pixel': 'retro',
    'cinema': 'neutral', 'oil': 'classical', 'lowpoly': 'neutral', 'vapor': 'retro', 'scifi': 'scifi',
}
_ALL_TAGS = {'guofeng', 'classical', 'scifi', 'futuristic', 'retro', 'modern', 'anime',
             'neutral', 'mythic', 'horror', 'surreal', 'dream', 'deepsea', 'apocalypse'}
# 隔离模式下各风格容忍的内容标签集；未列出的风格默认全容忍（写实/动漫/厚涂/3D/电影/低多边形可承载任何题材）
STYLE_COMPAT = {
    'ink':     {'guofeng', 'classical', 'retro', 'mythic', 'neutral'},
    'guofeng': {'guofeng', 'classical', 'retro', 'mythic', 'neutral'},
    'oil':     {'classical', 'mythic', 'retro', 'horror', 'neutral'},
    'cyber':   {'scifi', 'futuristic', 'modern', 'retro', 'neutral', 'surreal'},
    'pixel':   {'retro', 'scifi', 'neutral', 'anime', 'surreal', 'modern'},
    'vapor':   {'retro', 'scifi', 'surreal', 'neutral', 'modern'},
    'scifi':   {'scifi', 'futuristic', 'modern', 'retro', 'neutral', 'surreal'},
    'real': set(_ALL_TAGS), 'anime': set(_ALL_TAGS), 'paint': set(_ALL_TAGS),
    'render3d': set(_ALL_TAGS), 'cinema': set(_ALL_TAGS), 'lowpoly': set(_ALL_TAGS),
    'neutral': set(_ALL_TAGS),
}
THEME_TAGS = {
    'cthulhu': {'horror', 'mythic', 'surreal'},
    'gore': {'horror'},
    'creepy': {'horror', 'surreal'},
    'scifi_waste': {'scifi', 'futuristic'},
    'dreamcore': {'dream', 'surreal'},
    'steampunk': {'scifi', 'retro'},
    'mythic': {'mythic', 'classical'},
    'ghost_cn': {'guofeng'},
    'space_dead': {'scifi', 'futuristic'},
    'deepsea': {'neutral'},
    'apocalypse': {'scifi', 'modern', 'horror'},
    'cyber_neon': {'scifi', 'futuristic', 'modern'},
    'surreal': {'surreal', 'neutral'},
}
THEME_WORLD = {
    'cthulhu': 'horror', 'gore': 'horror', 'creepy': 'horror',
    'scifi_waste': 'scifi', 'space_dead': 'scifi', 'cyber_neon': 'scifi', 'apocalypse': 'scifi',
    'steampunk': 'scifi', 'dreamcore': 'dream', 'mythic': 'mythic', 'ghost_cn': 'guofeng',
    'deepsea': 'neutral', 'surreal': 'surreal',
}
# 自由文本物体：命中未来科幻关键词 → 传统风格下软警告（不吞字）；命中复古/年代词则不警告（可桥接国风/古典）。
# 同时命中未来词与复古词（如「蒸汽机器人」）按复古处理——复古被当作可桥接的年代碰撞。
OBJ_FUTURE_KW = {
    # 机械 / 智能体
    '机甲': 'scifi', '机器人': 'scifi', '机械臂': 'scifi', '机械义肢': 'scifi', '义体': 'scifi',
    '仿生': 'scifi', '人工智能': 'scifi', 'AI': 'scifi', '生化人': 'scifi', '克隆体': 'scifi',
    '赛博': 'scifi', '电子脑': 'scifi', '神经接驳': 'scifi',
    # 武器 / 能源
    '激光': 'futuristic', '光剑': 'futuristic', '等离子': 'futuristic', '电浆': 'futuristic',
    '量子': 'futuristic', '反物质': 'futuristic', '核聚变': 'futuristic', '粒子炮': 'futuristic',
    '能量护盾': 'futuristic', '力场': 'futuristic',
    # 交通 / 飞行
    '飞船': 'futuristic', '飞碟': 'futuristic', 'UFO': 'futuristic', '磁悬': 'futuristic',
    '悬浮': 'futuristic', '飞行器': 'futuristic', '无人机': 'futuristic', '曲速': 'futuristic',
    '推进器': 'futuristic',
    # 显示 / 计算 / 数码
    '全息': 'futuristic', '芯片': 'futuristic', '霓虹': 'futuristic', '纳米': 'futuristic',
    '虚拟': 'futuristic', '元宇宙': 'futuristic', '数字': 'futuristic', '代码': 'futuristic',
    '程序': 'futuristic', '光纤': 'futuristic', '脉冲': 'futuristic', '数据流': 'futuristic',
    # 空间 / 改造
    '太空': 'futuristic', '星际': 'futuristic', '基因改造': 'futuristic', '装甲': 'futuristic',
    '电子': 'futuristic', '机械': 'futuristic', '维度': 'futuristic',
}
OBJ_RETRO_KW = {
    '蒸汽': 'retro', '黄铜': 'retro', '齿轮': 'retro', '发条': 'retro', '怀表': 'retro',
    '木质': 'retro', '木纹': 'retro', '煤油灯': 'retro', '留声机': 'retro', '复古': 'retro',
    '做旧': 'retro', '青铜': 'retro', '铸铁': 'retro', '锈迹': 'retro', '维多利亚': 'retro',
    '羊皮纸': 'retro', '蒸汽机': 'retro', '机械钟': 'retro', '风箱': 'retro', '老式': 'retro',
    '黄铜钟': 'retro', '皮箱': 'retro', '旧式': 'retro',
}
BRIDGE = {
    frozenset({'guofeng', 'scifi'}): "a deliberate anachronism where ancient Chinese aesthetics collide with retro-futuristic machinery, forging a striking visual tension",
    frozenset({'guofeng', 'classical'}): "a quiet cultural dialogue where Eastern brushwork meets Western classical form",
    frozenset({'classical', 'scifi'}): "a deliberate clash of old-master painting and speculative technology",
    frozenset({'guofeng', 'mythic'}): "where Chinese folklore and universal myth intertwine",
    frozenset({'guofeng', 'horror'}): "where Eastern ink aesthetics meet eldritch dread",
    frozenset({'classical', 'horror'}): "where classical oil realism meets gothic horror",
    frozenset({'scifi', 'mythic'}): "where speculative technology meets ancient myth",
}
BRIDGE_GENERIC = "a deliberate genre collision, blending contrasting worlds into one coherent frame"
def _bridge(sw, cw):
    return BRIDGE.get(frozenset({sw, cw}), BRIDGE_GENERIC)

def _affinity(sk, thk, mix_mode, obj_text):
    """风格亲和层：返回 (题材是否注入, 警告列表, 桥接渲染词)。mix_mode='隔离'|'碰撞'。"""
    warns, bridge = [], ''
    theme_inject = thk
    s_world = STYLE_WORLD.get(sk, 'neutral')
    s_compat = STYLE_COMPAT.get(sk, _ALL_TAGS)
    if thk and thk != 'none':
        ttags = THEME_TAGS.get(thk, set())
        t_world = THEME_WORLD.get(thk, 'neutral')
        conflict = not (ttags & s_compat)
        cross = (t_world not in ('neutral', s_world)) and (s_world != 'neutral')
        if conflict:
            if mix_mode == '隔离':
                theme_inject = 'none'
                warns.append(f"已隔离题材[{THEME_POOL[thk]['label']}]（与[{STYLES[sk]['label']}]风格冲突）；开「风格混合=碰撞」可保留")
            else:
                bridge = _bridge(s_world, t_world)
        elif cross:
            bridge = _bridge(s_world, t_world)
    if obj_text and obj_text.strip():
        o = obj_text.strip()
        retro_hits = [k for k in OBJ_RETRO_KW if k in o]
        future_hits = [k for k in OBJ_FUTURE_KW if k in o]
        # 同时命中复古词 → 视作可桥接的年代碰撞（如「蒸汽机器人」），不警告
        if future_hits and not retro_hits and s_world in ('guofeng', 'classical'):
            warns.append(f"物体含科幻词[{','.join(future_hits)}]，与[{STYLES[sk]['label']}]可能违和；如需保留请开「风格混合=碰撞」")
    return theme_inject, warns, bridge

MIX_OPTS = ["🛡 隔离（默认）", "🔥 允许跨风格碰撞"]
MIX_L2K = {"🛡 隔离（默认）": "隔离", "🔥 允许跨风格碰撞": "碰撞"}

# ===================== 维度联想池：环境 / 光影 / 风格 =====================
# 选了某个环境/光影/风格，就从对应池随机抽 1-2 个细节注入，让每次出图不雷同。
# key 与 ENVS / LIGHTS / STYLES 的 key 对齐（rand 不注入）。
ENV_DETAIL = {
    'clouds': ['drifting wisps of isolated cloud', 'a lone crane crossing the void', 'a hidden immortal isle in the distance', 'sunbeams piercing the sea of clouds'],
    'mountain': ['weathered pine on a cliff ledge', 'a drifting fishing skiff on a lake', 'a stone pagoda half-lost in mist', 'a coiled mountain road of flagstone', 'a cold spring steaming at the rocks'],
    'cyber': ['rain-slick neon billboards', 'a hovering food-cart of steam', 'a crowd of mirrored visors', 'a cable-sea of power lines overhead', 'puddles reflecting magenta signage'],
    'forest': ['nodding bamboo in green shadow', 'a stone path of mossy steps', 'a hanging birdcage by the eaves', 'a tea-brewing hermit in the glade', 'fallen leaves drifting on a brook'],
    'palace': ['floating silk banners', 'a jade bridge over a star-pond', 'cloud-veiled palace lanterns', 'a phoenix carved on every beam', 'immortal maidens scattering petals'],
    'ruins': ['toppled columns draped in ivy', 'a cracked altar with cold incense', 'a root splitting an old staircase', 'a shard of a fallen stele', 'wildflowers claiming the stones'],
    'void': ['a single point of cold light', 'no horizon, no edge, no depth', 'a floating geometric fragment', 'absolute silence as texture'],
    'ocean': ['a distant sail on the line', 'a pod of breaching dolphins', 'foam lace on black sand', 'a mirrored sky with no shore', 'a lone buoy ringing in the wind'],
    'desert': ['a caravan of small silhouettes', 'wind-combed dune ridges', 'a lone acacia and its shade', 'heat-shimmer over the flats', 'a buried half-dome of tile'],
    'snow': ['a single red lantern in white', 'a frozen waterfall like glass', 'bare branches in rime', 'a distant smoke from a cottage', 'footprints leading nowhere'],
    'rain': ['neon smeared by wet glass', 'a bicycle splashing a puddle', 'steam from a subway grate', 'a forgotten umbrella in a gutter', 'reflections doubling the city'],
    'galaxy': ['a meteor stitching the dark', 'a nebula glowing violet', 'a lone campfire under stars', 'the milky way as a river', 'a shooting star caught mid-fall'],
    'lava': ['a curtain of falling embers', 'a bridge of cooled black rock', 'sulfur smoke on the wind', 'a river of molten gold', 'glass formed where lava met sea'],
    'aurora': ['a silent herd on the tundra', 'a tent glowing from within', 'snow lit green and violet', 'a frozen lake mirroring the sky', 'a lone figure watching the lights'],
    'underwater': ['a school of silver fish turning', 'a sunbeam bent by the surface', 'a drifting jellyfish bell', 'coral in slow breathing color', 'a sunken anchor wrapped in weed'],
    'flowers': ['a butterfly resting mid-flight', 'a bee path between blooms', 'a wooden fence of weathered posts', 'a distant cottage with a thatch roof', 'petals on a slow wind'],
    'ruinsCity': ['a broken billboard in a dead tongue', 'a vine through a cracked window', 'a tilted maglev rail', 'a still-working streetlamp', 'pigeons nesting in the rebar'],
    'space': ['a silent ring of debris', 'a distant blue planet', 'a solar panel array adrift', 'the cold curve of a dead moon', 'a long-exposure star trail'],
    'guangxi': ['a bronze drum echoing in the valley', 'terraced lines like emerald steps', 'a bamboo hat bobbing in the field', 'mist threading the karst peaks', 'a water buffalo in the paddy'],
    'nanfang': ['a stone bridge arching the canal', 'a wisteria dripping from the eaves', 'a sculling boat with a lantern', 'wet slate reflecting the moon', 'a scholar pausing on the bridge'],
    'beifang': ['a wind-bent poplar row', 'a grey-brick wall in dust light', 'a coal-smoke thread from a chimney', 'a cart rutted in the loess', 'a lone watchtower on the plain'],
}
LIGHT_DETAIL = {
    'golden': ['long raking shadows', 'warm dust in the light', 'a honeyed rim on every edge', 'lens flare through the leaves'],
    'rembrandt': ['a single lit cheek in darkness', 'deep chiaroscuro pools', 'a candle of light on the face', 'velvet shadow swallowing the room'],
    'neon': ['magenta and cyan spill on wet ground', 'a sign reflected in the eyes', 'chromatic halo around the edges', 'electric haze in the air'],
    'vol': ['god-rays through suspended dust', 'a soft haze of floating motes', 'light colonnades in the smoke', 'a glow blooming from behind forms'],
    'studio': ['clean rounded highlights', 'a seamless sweep of grey', 'soft box reflections', 'even light with no surprise'],
    'moon': ['cool blue cast on stone', 'silver edges and black pools', 'a long quiet shadow', 'breath visible in the cold'],
    'back': ['a glowing outline of the form', 'sparks at the rim of light', 'silhouette cut from brightness', 'a halo bleeding the edges'],
    'dappled': ['leaf-shadow freckles on the skin', 'a shifting mosaic of light', 'sun-coin on the ground', 'green-gold flicker in motion'],
    'tyndall': ['dust-lanced light beams', 'a cathedral of faint rays', 'motes turning in the column', 'a hush of glowing air'],
    'biolum': ['soft cyan-green self-light', 'glowing veins in the dark', 'a quiet pulse of lantern-flesh', 'phosphor trails in the water'],
    'candle': ['a small warm flicker', 'a trembling pool of light', 'shadow that leans and returns', 'amber on the closest surface'],
    'bicolor': ['a warm key, a cool fill', 'orange and blue fighting at the edge', 'two moods on one face', 'a split temperature in the frame'],
    'hard': ['razor shadow lines', 'deep unsparing contrast', 'a single stark direction', 'no softness anywhere'],
    'overcast': ['flat even daylight', 'no shadow to hide in', 'a calm diffuse wash', 'colors slightly muted'],
    'stage': ['a colored spotlight from above', 'a pool of theatrical light', 'a backlit veil of haze', 'saturation pushed for drama'],
    'paper': ['soft light through rice screens', 'a gentle lattice shadow', 'warm diffuse glow at the window', 'a quiet interior hush'],
    'mist': ['low-contrast morning air', 'edges dissolved in haze', 'a pearl-grey softness', 'form emerging from white'],
    'lantern': ['intimate amber pools', 'a warm glow held close', 'soft light on nearby faces', 'shadow leaning away from the flame'],
    'moonclear': ['cool silvery even light', 'crisp edges under the moon', 'a clean wash of pale radiance', 'no warm in the world'],
}
STYLE_DETAIL = {
    'real': ['true-to-life skin and grain', 'a captured instant, not staged', 'honest natural color', 'subtle environmental imperfections'],
    'ink': ['visible brush-bleed at the edges', 'a breath of negative space', 'wet ink pooling in the corners', 'a faint seal in vermilion'],
    'anime': ['clean cel boundaries', 'expressive sparkle in the eyes', 'flat confident color blocks', 'dynamic speed lines'],
    'paint': ['thick impasto stroke texture', 'visible bristle direction', 'rich layered glaze', 'a painterly looseness in the edges'],
    'render3d': ['ray-traced reflections', 'physically based material sheen', 'clean volumetric scatter', 'crisp contact shadows'],
    'cyber': ['neon edge-glow', 'rain-slick specular streaks', 'high-contrast color grade', 'holographic shimmer'],
    'guofeng': ['fine gongbi linework', 'soft mineral pigment washes', 'elegant classical framing', 'a faint gold outline'],
    'pixel': ['crisp 16-bit pixels', 'limited retro palette', 'visible dithering', 'sprite-like flatness'],
    'cinema': ['anamorphic flare', 'teal-orange grade', 'gentle film grain', 'shallow cinematic depth'],
    'oil': ['visible impasto ridges', 'warm chiaroscuro depth', 'classical glazed color', 'museum varnish glow'],
    'lowpoly': ['clean faceted planes', 'flat matte pastel', 'minimalist geometry', 'isometric calm'],
    'vapor': ['pink-cyan gradient wash', 'gridded horizon glow', 'glitch artifacts', 'soft retro bloom'],
    'scifi': ['sleek brushed-metal paneling', 'glowing energy conduits', 'crisp holographic interface', 'subtle volumetric scan lines'],
}

def _detail_tail(pool_dict, key, rng, lo=1, hi=2):
    """维度联想池注入：从 pool_dict[key] 随机抽 lo-hi 个细节，返回 ' with x, y.' 句式。key 不存在/rand 返回空。"""
    if not key or key == 'rand' or key not in pool_dict:
        return ''
    pool = list(pool_dict[key])
    if not pool:
        return ''
    k = min(rng.ri(lo, hi), len(pool))
    picks = []
    for _ in range(k):
        x = rng.rnd(pool)
        picks.append(x)
        pool.remove(x)
    return f" with {', '.join(picks)}."

COMPOS = ['centered composition', 'rule-of-thirds framing', 'symmetrical framing', 'dynamic diagonal composition', 'low-angle heroic framing', 'high-angle overview']
# 叙事短句库：buildNormal 60% / buildMega 40% 概率在末尾追加一句，让随机出词自带故事感
STORY_BANK = [
    'Legends whisper of a forgotten age',
    'The figure moves with quiet purpose',
    'Dawn breaks over silent stones',
    'A vow spoken beneath an ancient moon',
    'The wanderer pauses, listening to the wind',
    'Smoke rises from a hearth long cold',
    'A single bell tolls across the water',
    'The path ahead is shrouded in mist',
    'Memories linger in the drifting dust',
    'A storm gathers on the far horizon',
    'The old guardian keeps an unspoken vigil',
    'Footprints fade into the snow',
    'A lantern burns for one who may never return',
    'The world holds its breath before the turning',
    'Shadows stretch long beneath a dying sun',
    'A promise binds the living and the lost',
]

# ===================== 种子 RNG (mulberry32, 与 HTML 版一致) =====================
class RNG:
    def __init__(self, seed):
        self.s = (seed & 0xFFFFFFFF) or 1

    def rnd(self, arr):
        self.s = (self.s + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.s
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        inner = ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF
        t = (t ^ ((t + inner) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return arr[((t ^ (t >> 14)) & 0xFFFFFFFF) % len(arr)]

    def ri(self, lo, hi):
        n = hi - lo + 1
        return lo + self.rnd(list(range(n)))


# ===================== 生成逻辑 =====================
import re
import json
_ENV_RE = re.compile(r'^(in |above |within |under |beneath |among |against |on |at |into )', re.I)

def envPhrase(k):
    e = ENVS.get(k)
    v = e['v'] if e else 'an endless sea of clouds'
    s = _ENV_RE.sub('', v)
    return s or v

def _mega_surface(morph_key, p, micro):
    """根据巨构形态返回表面描述句（含结尾句号+空格）。打破原版所有预设共用同一句蜂窝重复骨架的雷同观感。"""
    tiers = p.get('tiers', 'strata')
    if morph_key == 'monolith':
        return (f"The structure is a single unbroken monolithic mass with a seamless, continuous surface, {micro}. "
                f"It reads as one solid whole rather than an assembly of parts. ")
    if morph_key == 'tiered':
        return (f"The structure rises as a strict stack of {tiers} in concentric tiers, "
                f"each tier a self-contained band of detail, {micro}. ")
    if morph_key == 'organic':
        return (f"The structure grows as a non-repeating organic organism, asymmetrical and branch-like, "
                f"never resolving into a uniform grid, {micro}. ")
    if morph_key == 'fragment':
        return (f"The structure is an agglomeration of countless disparate fractured blocks and drifting shards "
                f"fused into one silhouette, {micro}. ")
    if morph_key == 'woven':
        return (f"The structure is an interlocking woven lattice of interlaced strands and braided bands, {micro}, "
                f"reading as one taut woven whole rather than stacked parts. ")
    if morph_key == 'spiral':
        return (f"The structure coils upward in a single unbroken spiral, each revolution a tighter band of {tiers}, "
                f"{micro}, never resolving into a flat grid. ")
    if morph_key == 'lattice':
        return (f"The structure resolves into a rigid crystalline lattice grid of repeating geometric cells, {micro}, "
                f"a precise modular array rather than organic growth. ")
    if morph_key == 'floating':
        return (f"The structure hangs as a stack of detached floating {tiers}, each disc adrift on its own plane, "
                f"{micro}, bound only by negative space between them. ")
    if morph_key == 'burst':
        return (f"The structure radiates outward from a single dense core in spokes and shards, {micro}, "
                f"exploding symmetrically beyond every frame edge. ")
    # 默认：蜂窝重复（原行为）
    return (f"The structure's surface is a hyper-dense honeycomb grid of tens of millions of human-scaled components, {micro}. ")


def _theme_tail(theme_key, rng):
    """题材包注入：暗黑/恐怖/血腥/克苏鲁。返回氛围句 + 随机 3-5 个元素细节（带句号结尾）。无题材返回空。"""
    if not theme_key or theme_key == 'none':
        return ''
    t = THEME_POOL.get(theme_key)
    if not t:
        return ''
    pool = list(t['elems'])
    k = min(rng.ri(3, 5), len(pool))
    picks = []
    for _ in range(k):
        x = rng.rnd(pool)
        picks.append(x)
        pool.remove(x)
    line = ', '.join(picks)
    return f" {t['aura']}, with {line}. "

# ===================== 题材 × 巨构 风格冲突守卫 =====================
# 现代/科幻/异界题材的氛围 与 中式古典巨构主体 搭配易违和。命中就在 JSON 里给 warnings，
# 不改提示词本身（用户/下游可据此判断），避免擅自改动用户已选的组合。
THEME_WESTERN = {'cthulhu', 'gore', 'creepy', 'scifi_waste', 'steampunk', 'space_dead',
                 'deepsea', 'apocalypse', 'cyber_neon', 'surreal', 'dreamcore'}
MEGA_CHINESE = {'xiangong', 'yunque', 'buddha', 'taoist', 'clayidol',
                'guangxiMega', 'karstMega', 'longjiMega', 'nanfangMega', 'gardenMega', 'bridgeMega',
                'beifangMega', 'wallMega', 'iceMega'}

def _conflict_warnings(theme_key, mega_key):
    w = []
    if theme_key in THEME_WESTERN and mega_key in MEGA_CHINESE:
        w.append(f"题材[{THEME_POOL[theme_key]['label']}]的氛围 与 中式古典巨构[{MEGA[mega_key]['name']}] 风格可能冲突")
    return w


def _to_json(fields, negative):
    """把结构化字段 + 负面词组装为 Krea2 JSON 结构化提示词字符串（维度拆字段，便于下游结构化管线消费）。"""
    obj = dict(fields)
    obj['negative_prompt'] = negative
    return json.dumps(obj, ensure_ascii=False, indent=2)

def buildMega(pk, lensKey, varKey, lightKey, envKey, styleKey, rng, custom_subject="", custom_object="", custom_story="", enable_weight=True, intensity=100, morphKey='honeycomb', theme='none', bridge=''):
    p = MEGA[pk]
    H = rng.ri(3000, 12000)
    # 画幅占比 / 负空间：对齐巨构规范（主体占 75–95%、保留 10–25% 环境空间）
    occ = rng.ri(75, 92)
    negPct = rng.ri(12, 25)
    # 参照物占比：规范要求 <0.1%。原 1–3% 太大，参照物一可辨就削弱巨构尺度冲击。
    refPct = rng.ri(3, 8) / 100.0   # 0.03–0.08%
    custom_ref = custom_subject.strip() if custom_subject and custom_subject.strip() else ''
    ref_raw = custom_ref or rng.rnd(p['refs'])
    ref_phrase = (ref_raw[0].upper() + ref_raw[1:]) if custom_ref else ("A tiny " + ref_raw[0].upper() + ref_raw[1:])
    refPos = rng.rnd(['at the terrace edge', 'at the base', 'on a distant walkway', "at the structure's ankle"])
    light = LIGHTS[lightKey]['v']
    envBare = envPhrase(envKey) if (envKey and envKey != 'rand' and envKey in ENVS) else rng.rnd(NEG_ENVS)
    sq = STYLES[styleKey]['qual'] if (styleKey and styleKey in STYLES and STYLES[styleKey].get('qual')) else '8k resolution, masterpiece, extreme detail'
    ms = MEGA_STYLE.get(styleKey, '')
    lead = (W(ms[0].upper() + ms[1:], 1.2, enable_weight, intensity) + '; ') if ms else ''
    lens_w = W(LENSES[lensKey]['v'], 1.3, enable_weight, intensity)
    subj_core = p['subject']
    # 部分巨构主体本身已含 colossal（如世界树），避免写出 a colossal colossal ...
    subj_full = f"a {subj_core} megastructure" if subj_core.lower().startswith('colossal') else f"a colossal {subj_core} megastructure"
    subj_w = W(subj_full, 1.2, enable_weight, intensity)
    ref_w = W(ref_phrase, 1.2, enable_weight, intensity)
    mat_w = W(p['materials'], 1.1, enable_weight, intensity)
    v = MVAR[varKey]['v'].replace('{H}', str(H)).replace('{TIERS}', p['tiers'])
    surf = _mega_surface(morphKey, p, p['micro'])
    ref_block = (f"{ref_w} stands {refPos}, occupying only {refPct:.2f}% of the frame and locked on the same far depth plane as the architecture, "
                 f"utterly dwarfed to forge a stark semantic conflict of scale. ")
    neg_block = (f"Strictly reserving the top {negPct}% of the frame as pure negative space for {envBare}, {light}, "
                 f"cold-warm contrast between deep structural shadows and warm rim light on the upper edges. ")
    mat_block = f"Hyper-detailed materials of {mat_w}, {sq}, epic scale, extreme detail."
    extras = ''
    custom_obj = custom_object.strip() if custom_object and custom_object.strip() else ''
    if custom_obj:
        obj_cap = custom_obj[0].upper() + custom_obj[1:]
        extras += f" {obj_cap} rests as a quiet, human-scale detail woven into the epic structure."
    if custom_story and custom_story.strip():
        story = custom_story.strip()
        if not story.endswith('.'):
            story += '.'
        extras += ' ' + story
    elif rng.ri(0, 99) < 40:
        story = rng.rnd(STORY_BANK)
        if not story.endswith('.'):
            story += '.'
        extras += ' ' + story
    detail = (_detail_tail(ENV_DETAIL, envKey, rng, 1, 2)
              + _detail_tail(LIGHT_DETAIL, lightKey, rng, 1, 2)
              + _detail_tail(STYLE_DETAIL, styleKey, rng, 1, 2)
              + _theme_tail(theme, rng))
    if bridge:
        detail += ' ' + bridge + '. '
    # 段落（与旧版逐字一致，保证已测输出不回归）
    paragraph = (f"{lead}{lens_w}, of {subj_w} occupying {occ}% of the canvas "
                 f"and rising within {envBare}, {v}. "
                 f"{surf}{ref_block}{neg_block}{mat_block}{extras}{detail}")
    # 结构化字段（JSON 用）
    fields = {
        'subject': subj_w,
        'composition': (f"occupying {occ}% of the canvas and rising within {envBare}, {v}. {ref_block}"),
        'micro_density': surf,
        'lens': lens_w,
        'materials': mat_block,
        'lighting': f"{light}, cold-warm contrast between deep structural shadows and warm rim light on the upper edges",
        'style': (lead.rstrip('; ') if lead else '') or sq,
        'environment': envBare,
        'quality': sq,
        'atmosphere': detail,
        'extras': extras.strip(),
    }
    return paragraph, fields

def buildNormal(styleKey, catKey, lensKey, lightKey, envKey, rng, custom_subject="", custom_object="", custom_story="", enable_weight=True, intensity=100, theme='none', viewKey='none', bridge=''):
    s = STYLES[styleKey]
    c = CATS[catKey]
    f = FLAVOR.get(styleKey, FLAVOR['real'])
    subject = custom_subject.strip() if custom_subject and custom_subject.strip() else rng.rnd(c['subjects'])
    framing = rng.rnd(c['framing']) if c.get('framing') else 'a full-body view'
    mood = rng.rnd(MOODS)
    compos = rng.rnd(COMPOS)
    prop = custom_object.strip() if custom_object and custom_object.strip() else rng.rnd(f['props'])
    atmo = rng.rnd(f['atmos'])
    dof = (c['dof'] + ', ') if c['dof'] else ''
    subject_w = W(subject, 1.2, enable_weight, intensity)
    # 风格专属渲染词：紧贴主体、置于高注意力区，强化风格跟随。
    # 普通模式弱模型只跟主体走、风格差异被冲淡的根因——把风格词从句尾细节提到主语之后。
    style_render = ''
    if styleKey in STYLE_DETAIL:
        style_render = W(rng.rnd(STYLE_DETAIL[styleKey]), 1.15, enable_weight, intensity)
    lens_w = W(LENSES[lensKey]['v'], 1.2, enable_weight, intensity)
    light = LIGHTS[lightKey]['v']
    env = ENVS[envKey]['v']
    qual = s['qual']
    prefix = s['prefix']
    palette = f['palette']
    style_clause = f"{style_render}, " if style_render else ''
    base = (f"{prefix} of {framing} of {subject_w}, {style_clause}framed by {prop} and {atmo}, {palette}, "
            f"set {env}, {compos}, {mood} mood, captured with {lens_w}, "
            f"{light}, {dof}{qual}.")
    extras = ''
    if custom_story and custom_story.strip():
        story = custom_story.strip()
        if not story.endswith('.'):
            story += '.'
        extras += ' ' + story
    elif rng.ri(0, 99) < 60:
        story = rng.rnd(STORY_BANK)
        if not story.endswith('.'):
            story += '.'
        extras += ' ' + story
    detail = (_detail_tail(ENV_DETAIL, envKey, rng, 1, 2)
              + _detail_tail(LIGHT_DETAIL, lightKey, rng, 1, 2)
              + _theme_tail(theme, rng))
    if bridge:
        detail += ' ' + bridge + '. '
    paragraph = base + extras + detail
    view_v = NORMAL_VIEW[viewKey]['v'] if (viewKey and viewKey not in ('none', 'rand')) else None
    if view_v:
        paragraph = paragraph.rstrip('.') + ', ' + view_v + '.'
    fields = {
        'subject': f"{framing} of {subject_w}",
        'composition': f"{compos}, {mood} mood",
        'lens': lens_w,
        'materials': f"{prop}, {atmo}",
        'lighting': (light + (', ' + c['dof'] if c['dof'] else '')),
        'style': f"{prefix}, {palette}",
        'environment': env,
        'quality': qual,
        'atmosphere': detail,
        'extras': extras.strip(),
    }
    if view_v:
        fields['composition'] = fields['composition'] + '; ' + view_v
    return paragraph, fields

# H3 镜头运动池：多镜头时每个 Shot 用不同相机运动
H3_CAM_MEGA = [
    'the camera performs a slow vertical tilt along the full height of the structure, then a gentle push-in; the tiny human figure stays locked on the far depth plane, hammering home the scale',
    'a slow horizontal pan across the hyper-dense honeycomb surface, gradually revealing the sheer breadth of the structure',
    'a low-angle orbital sweep around the base, spiraling upward as the colossal mass looms overhead',
    'a slow top-down descent through the cloud sea, the structure emerging from mist as the camera pushes toward the tiny figure',
    'a creeping dolly through a narrow corridor of the structure, walls rushing past as the tiny figure dwindles ahead',
    'a slow crane rise from the base to the crown, the colossal silhouette filling the frame edge to edge',
]
H3_CAM_NORMAL = [
    'the camera holds a slow, breathing drift with subtle parallax; the subject remains the focal anchor as light and atmosphere shift around it',
    'a gentle push-in toward the subject, rack-focusing from foreground prop to the figure',
    'an arc dolly orbiting the subject at mid-height, revealing the environment beyond',
    'a slow pull-back from the subject, unveiling the vast setting around it',
    'a low tracking slide along the ground, skimming past foreground props toward the figure',
    'a slow vertical boom that lifts from the figure to reveal the towering structure above',
]

# 运镜下拉：把巨构/普通两套预设运镜统一成可选列表，外加「自动循环」默认项。
# 用户可单独指定运镜（与动效 motion 解耦）；auto 沿用原逻辑（按 shot 序号循环对应池 4 条预设）。
H3_CAM_ALL = {
    'auto':         {'label': '🎲 自动循环（默认）',    'mega': None, 'normal': None},
    'mega_tilt':    {'label': '巨构·垂直俯仰推近',      'mega': H3_CAM_MEGA[0],  'normal': None},
    'mega_pan':     {'label': '巨构·横向平摇展开',      'mega': H3_CAM_MEGA[1],  'normal': None},
    'mega_orbit':   {'label': '巨构·低角环绕螺旋升',    'mega': H3_CAM_MEGA[2],  'normal': None},
    'mega_descent': {'label': '巨构·云海俯降穿雾',      'mega': H3_CAM_MEGA[3],  'normal': None},
    'norm_drift':   {'label': '常规·呼吸式漂移视差',    'mega': None, 'normal': H3_CAM_NORMAL[0]},
    'norm_push':    {'label': '常规·推近·变焦重构',      'mega': None, 'normal': H3_CAM_NORMAL[1]},
    'norm_arc':     {'label': '常规·中高弧线环绕',      'mega': None, 'normal': H3_CAM_NORMAL[2]},
    'norm_pull':    {'label': '常规·拉远·展现场景',     'mega': None, 'normal': H3_CAM_NORMAL[3]},
    'mega_corridor':{'label': '巨构·穿廊疾推',          'mega': H3_CAM_MEGA[4], 'normal': None},
    'mega_crane':   {'label': '巨构·升镜展全貌',        'mega': H3_CAM_MEGA[5], 'normal': None},
    'norm_track':   {'label': '常规·地面横移跟拍',      'mega': None, 'normal': H3_CAM_NORMAL[4]},
    'norm_boom':    {'label': '常规·升镜露巨构',        'mega': None, 'normal': H3_CAM_NORMAL[5]},
}
CAM_OPTS = [v['label'] for v in H3_CAM_ALL.values()]
CAM_L2K = {v['label']: k for k, v in H3_CAM_ALL.items()}

# H3 动效层：在「同 krea2 的静帧块」之上叠加运动语言（krea2 管画面，H3 管动效）
# 设计原则：
#   1) 每条 text 只描述「已存在元素的运动」（人物衣袍/发丝、巨构、雪、空气、水汽…），
#      绝不引入新主体名词，避免 H3 重画构图、换掉主体。
#   2) 真正防止「抢权重」的是 buildH3 末尾追加的 MOTION_LOCK 锁定句——
#      H3 不认 (text:1.3) 权重语法，只能用语义约束「画面不变，只加运动/天气」。
#   3) 动效按「被作用的主体类别」做前缀分类：人物动 / 植物动 / 场景·天气动 / 巨构动。
#      下拉里用组标题分隔，一眼看清这条动效作用在「谁」身上；
#      镜头运动（推拉摇移/环绕）由 H3_CAM 池自动处理，不在此列，避免与场景动效混淆。
# H3 动效层：4 类独立下拉，每类可选「无（不动）」或该类具体动效，自由组合出任意「全活」。
# 设计原则：
#   1) 每条 text 只描述「已存在元素的运动」（人物衣袍/发丝、巨构、雪、空气、水汽…），
#      绝不引入新主体名词，避免 H3 重画构图、换掉主体。
#   2) 真正防止「抢权重」的是下方 MOTION_LOCK 锁定句——
#      H3 不认 (text:1.3) 权重语法，只能用语义约束「画面不变，只加运动/天气」。
#   3) 动效按「被作用的主体类别」拆成 4 个独立下拉（人物/植物/场景·天气/巨构），
#      用户逐项开关，组合出想要的「全活」；镜头运动由独立 camera 下拉控制，不在此列。
MOTION_FIGURE = {
    'figure_sway': {'label': '人物缓动·衣摆晃', 'text': 'the tiny human figure sways slightly with the wind, cloak hem swinging, weight shifting from foot to foot'},
    'wind_figure': {'label': '风吹衣袂·发丝扬', 'text': "a gust of wind ripples through the figure's robes and lifts stray hairs, fabric edges flutter and trail behind"},
    'breeze':      {'label': '微风轻拂', 'text': "a soft breeze stirs the hem of the figure's robe and lifts a few loose strands of hair, fabric edges trace gentle curves"},
    'wind_strong': {'label': '强风猎猎', 'text': "a strong gust snaps the figure's cloak wide and bends the surrounding grass, ribbons and straps whip and snap through the air"},
    'figure_look': {'label': '人物抬首·仰望巨构', 'text': "the figure slowly lifts its head and gazes up toward the colossal mass, stray hairs drifting as the wind eases"},
    'figure_turn': {'label': '人物侧身·衣袂旋', 'text': 'the figure turns slowly at the waist, robe sweeping out in a wide arc before settling'},
    'figure_walk': {'label': '人物重心移·原地微调', 'text': 'the tiny figure shifts its weight subtly from one foot to the other without leaving its place, the cloak hem rocking gently as the stance settles, no actual walking or translation'},
    'figure_kneel': {'label': '人物俯身·触地起', 'text': 'the figure bends down and presses a hand to the earth, then rises in a slow uncoil'},
    'figure_breath': {'label': '人物静立·呼吸起伏', 'text': 'the figure stands rooted, shoulders rising and falling with a slow, even breath'},
    'hair_only': {'label': '发丝长飘·身不动', 'text': "only the figure's long hair drifts and lifts on the wind while the body stays perfectly still"},
}
MOTION_PLANT = {
    'foliage_sway': {'label': '草木摇曳', 'text': 'distant trees and grass bend and sway, leaves and petals tumbling across the ground'},
    'flag_flutter': {'label': '旌旗飘扬', 'text': 'banners and prayer flags snap and flutter from the eaves, their long shadows dancing across the wall'},
    'grass_wave': {'label': '草浪起伏', 'text': 'a ripple of wind passes through the tall grass in rolling waves across the foreground'},
    'leaf_fall': {'label': '落叶飘旋', 'text': 'leaves detach and spiral down through the air, catching the slanting light'},
    'reed_sway': {'label': '芦苇轻摆', 'text': 'reeds and slender stems at the water edge bow and sway, tips tracing slow circles'},
    'vine_dance': {'label': '藤蔓垂荡', 'text': 'hanging vines and creepers swing gently from the structure seams, casting weaving shadows'},
    'flower_breathe': {'label': '花苞微绽', 'text': 'buds on the nearby shrubs slowly unfurl a fraction, as if breathing with the wind'},
}
MOTION_SCENE = {
    'snow_weather': {'label': '风雪天气·粒子飘', 'text': 'cold wind drives sheets of snow and dust across the frame, snowflakes and grit drift and swirl through the air, the air fills with drifting white flecks, visibility ebbs and flows'},
    'rain_slant':   {'label': '雨丝斜落', 'text': 'slanting rain needles streak through the air and bead on armor and weathered stone, ripples chase across the wet surfaces'},
    'dust_float':   {'label': '尘埃浮动', 'text': 'fine dust motes drift and rotate slowly in the volumetric light, weightless and suspended'},
    'mist_light':   {'label': '雾气流动·光扫过', 'text': 'mist streams and curls across the scene while volumetric light sweeps slowly through the haze'},
    'water_ripple': {'label': '水波荡漾', 'text': 'a still pool at the base catches the reflection and sends slow concentric ripples outward'},
    'fog_roll': {'label': '云雾翻涌', 'text': 'banks of fog roll and churn across the lower structure, swallowing detail then revealing it'},
    'cloud_drift': {'label': '云层缓移', 'text': 'high clouds drift slowly overhead, their long shadows sliding across the vast wall'},
    'ember_float': {'label': '余烬飞浮', 'text': 'glowing embers and ash float upward from a distant fire, suspended in the cold air'},
    'light_ray': {'label': '光柱斜扫', 'text': 'a shaft of light slowly sweeps across the scene as the sun shifts behind the haze'},
    'snow_settle': {'label': '落雪堆积', 'text': 'fresh snow feathers down and piles softly along the ledges and rails'},
    'heat_haze': {'label': '热气氤氲', 'text': 'shimmering heat haze rises from the ground, softly warping the distant lines'},
    'star_twinkle': {'label': '星河微闪', 'text': 'distant stars and the night sky flicker faintly overhead, the milky way slowly turning'},
    'spark_drift': {'label': '火花飘散', 'text': 'tiny sparks drift from the structure seams like slow fireflies, fading as they rise'},
}
MOTION_MEGA = {
    'mega_micro':  {'label': '巨物微动·能量脉动', 'text': 'the colossal structure breathes with slow micro-shifts, vast panels settle and re-align, energy conduits pulse with light'},
    'energy_flow': {'label': '流光溢彩·辉光流动', 'text': 'threads of light run along the structure seams and energy conduits pulse with a soft glow, a faint aurora shimmers far overhead'},
    'mega_rotate': {'label': '巨构缓转·天枢移', 'text': 'the colossal ring turns with geological slowness, the sky and stars wheeling around its rim'},
    'mega_breathe': {'label': '巨构起伏·如巨兽息', 'text': 'the entire mass rises and falls in one vast slow breath, like a sleeping leviathan'},
    'mega_assemble': {'label': '构件浮合·悬空重组', 'text': 'detached panels and beams drift and lock into place, reassembling in mid-air'},
    'mega_glow': {'label': '巨构辉明·核心亮', 'text': 'a deep core light swells and dims within the structure, pulsing through its bones'},
    'mega_crack': {'label': '巨构裂隙·光涌出', 'text': 'thin seams of light split open across the surface, venting slow beams into the dark'},
    'mega_dust': {'label': '巨构落尘·碎屑坠', 'text': 'fine debris and dust shed from the high edges, drifting down the long facade'},
}

def _cat_opts(d):
    """把某类动效字典转成下拉选项 + label→key 映射（含『无（不动）』→None）。"""
    opts = ["无（不动）"]
    l2k = {"无（不动）": None}
    for k, v in d.items():
        opts.append(v['label'])
        l2k[v['label']] = k
    return opts, l2k

FIGURE_OPTS, FIGURE_L2K = _cat_opts(MOTION_FIGURE)
PLANT_OPTS,  PLANT_L2K  = _cat_opts(MOTION_PLANT)
SCENE_OPTS,  SCENE_L2K  = _cat_opts(MOTION_SCENE)
MOTION_MEGA_OPTS, MOTION_MEGA_L2K = _cat_opts(MOTION_MEGA)

# 防抢权重锁定句：任何有运动的镜头，追加在运动语言之后，强制 H3 只加动、不改画。
MOTION_LOCK = ("throughout the shot the framing, subject identity, scale relationship and environment "
               "stay exactly as in the source frame; the lines above add only movement and weather, "
               "never altering the scene itself")

def buildH3(catKey, styleKey, envKey, base, shots=1, motion_text='', camKey='auto'):
    sound = H3_SOUND.get(envKey, 'ambient natural sound')
    music = H3_MUSIC.get(styleKey, 'a subtle ambient score')
    is_mega = (catKey == 'mega')
    cam_pool = H3_CAM_MEGA if is_mega else H3_CAM_NORMAL
    base_clean = base.rstrip('. ').rstrip('.')
    out = []
    for i in range(shots):
        # 运镜：auto=按 shot 序号循环对应池预设；否则取用户指定的那条
        cam_entry = H3_CAM_ALL.get(camKey, H3_CAM_ALL['auto'])
        cam_text = cam_entry.get('mega' if is_mega else 'normal')
        if camKey == 'auto' or cam_text is None:
            cam = cam_pool[i % len(cam_pool)]
        else:
            cam = cam_text
        desc = base_clean + '. ' + cam
        if motion_text:
            desc += '. ' + motion_text + '. ' + MOTION_LOCK
        desc += '.'
        out.append(f"[Shot {i+1}]\n"
                   f"integrated_multimodal_description: {desc}\n"
                   f"overall_soundscape: {sound}.\n"
                   f"non_diegetic_music: {music}.")
    return '\n\n'.join(out)


# ===================== ComfyUI 下拉选项辅助 =====================
def _opts(d):
    """返回 (label列表, {label:key})，rand 排第一。"""
    labels = []
    l2k = {}
    for k, v in d.items():
        label = v.get('label') or v.get('name') or k
        labels.append(label)
        l2k[label] = k
    return labels, l2k

STYLE_OPTS, STYLE_L2K = _opts(STYLES)
# 视觉分组（不破环）：把「实拍/胶片」(写实摄影、电影感胶片) 排到风格栏最前（🎲随机之后），
# 与下游画种(水墨/油画/动漫…) 区分开；label 文字不变，已存工作流按 label 仍能正确解析。
# 分组标题为纯展示项（不进 STYLE_L2K 映射），在 forge 里用 .get(style, 'rand') 兜底，
# 万一选到标题会自动转随机，节点绝不崩。
_PHOTO_STYLES = ['写实摄影', '电影感胶片']
GROUP_PHOTO = '▸ 实拍 / 胶片观感'
GROUP_ART = '▸ 画种 / 渲染介质'
STYLE_OPTS = ([STYLE_OPTS[0]] + [GROUP_PHOTO] + _PHOTO_STYLES
              + [GROUP_ART]
              + [l for l in STYLE_OPTS[1:] if l not in _PHOTO_STYLES])
CAT_OPTS, CAT_L2K = _opts(CATS)
LENS_OPTS, LENS_L2K = _opts(LENSES)
LIGHT_OPTS, LIGHT_L2K = _opts(LIGHTS)
ENV_OPTS, ENV_L2K = _opts(ENVS)
VAR_OPTS, VAR_L2K = _opts(MVAR)
MEGA_OPTS, MEGA_L2K = _opts(MEGA)
# 普通模式用「⚪ 无」：UI 心理暗示巨构栏不用填；巨构模式选了「无」自动转随机
MEGA_NONE = '⚪ 无（普通模式）'
MEGA_OPTS = [MEGA_NONE] + MEGA_OPTS
MORPH_OPTS, MORPH_L2K = _opts(MEGA_MORPH)
THEME_OPTS, THEME_L2K = _opts(THEME_POOL)
NORMAL_VIEW_OPTS, NORMAL_VIEW_L2K = _opts(NORMAL_VIEW)

_NONRAND = lambda d: [k for k in d if k != 'rand']

# ===================== 中文身份/修饰拼主体（B方案：选中文出英文，零翻译） =====================
# 每项 (中文label, 英文value)；选具体身份+修饰 → 拼成完整英文主体
# 身份按 人/神/魔/非人/动物/机械/植物 七大方向组织，每项再细分联想词；下拉用「大类·细项」单一列表（分类少、联想多）
IDENTITY_TREE = {
 '人': [('侠客','a swordsman'),('书生','a scholar'),('将军','a battle-hardened general'),('医者','a traveling physician'),('渔翁','an old fisherman'),('仕女','a noble lady'),('工匠','a master artisan'),('琴师','a zither player')],
 '神': [('仙人','an immortal sage'),('天女','a celestial maiden'),('道祖','a primordial daoist sage'),('龙王','a dragon king'),('星君','a star lord'),('福神','a fortune deity')],
 '魔': [('魔将','a demon general'),('夜叉','a ferocious yaksha'),('罗刹','a rakshasa'),('骨妖','a bone demon'),('血魔','a bloodthirsty demon')],
 '非人': [('精怪','a mountain spirit'),('狐仙','a fox immortal'),('鬼魂','a wandering ghost'),('树精','a tree sprite'),('石灵','a stone elemental'),('灯灵','a lantern spirit')],
 '动物': [('灵狐','a spirit fox'),('青龙','an azure dragon'),('白鹤','a white crane'),('麒麟','a qilin'),('金乌','a golden sun-crow'),('锦鲤','a koi')],
 '机械': [('机甲卫士','a mech guardian'),('机关傀儡','a clockwork puppet'),('铜人','a bronze automaton'),('飞剑灵','a flying-sword spirit')],
 '植物': [('花灵','a flower spirit'),('柳精','a willow sprite'),('莲童','a lotus child'),('桃仙','a peach immortal')],
}
# 下拉扁平化：🎲随机/无 + 各大类·细项
IDENTITY_ITEMS = [('🎲 随机', ''), ('无', '')] + [(f"{cat}·{lbl}", eng) for cat, items in IDENTITY_TREE.items() for lbl, eng in items]
# 通用修饰池（显式可选）；另设按身份大类联想的修饰池（🎲随机时自动抽取）
MODIFIER_ITEMS = [
    ('🎲 随机', ''), ('无', ''),
    ('持灯夜行', 'holding a lantern on a night journey'),('御风而行', 'riding the wind aloft'),
    ('持卷沉思', 'holding a scroll in thought'),('抚笛而立', 'standing with a jade flute'),
    ('持剑而立', 'standing with a drawn sword'),('跌坐入定', 'seated in deep meditation'),
    ('仰望星空', 'gazing up at the starfield'),('临风而立', 'standing against the wind'),
    ('持杖远眺', 'leaning on a staff, gazing afar'),('拈花一笑', 'holding a flower with a faint smile'),
    ('抚琴低吟', 'cradling a guqin, humming softly'),('踏雪而行', 'treading through silent snow'),
    ('临渊而立', 'standing at the edge of an abyss'),('持伞独行', 'walking alone under a paper umbrella'),
]
# 按身份大类联想的修饰池：🎲随机修饰时按所选身份大类抽取对应氛围动作
IDENTITY_MODIFIERS = {
 '人': [('持剑而立','standing with a drawn sword'),('负手远眺','hands behind back, gazing afar'),('临风吟啸','singing into the wind'),('抚卷沉思','holding a scroll in thought')],
 '神': [('御风而行','riding the wind aloft'),('拈花微笑','holding a flower with a faint smile'),('抚琴低吟','cradling a guqin, humming softly'),('临渊照影','gazing at their reflection in an abyss')],
 '魔': [('血祭而立','standing amid a blood ritual'),('狞笑凝视','grinning with a cruel stare'),('噬魂低语','whispering a soul-devouring curse'),('血雾环绕','wreathed in a blood-red mist')],
 '非人': [('魅惑浅笑','with a beguiling smile'),('化青烟去','dissolving into green smoke'),('附木低语','whispering through the wood'),('灯影摇曳','flickering in lantern light')],
 '动物': [('腾云驾雾','soaring through clouds and mist'),('展翅凌空','spreading wings in mid-air'),('回眸凝望','turning its head with a lingering gaze'),('逐浪而行','treading across the waves')],
 '机械': [('齿轮转动','gears turning with a metallic hum'),('电光流转','electric arcs coursing across its frame'),('悬停半空','hovering weightlessly'),('关节轻响','joints clicking with each motion')],
 '植物': [('随风轻摆','swaying gently in the breeze'),('落英缤纷','petals drifting down around it'),('汲取露华','drinking the morning dew'),('根系延展','roots spreading deep into the earth')],
}
IDENTITY_OPTS = [lbl for lbl, _ in IDENTITY_ITEMS]
IDENTITY_VAL = {lbl: v for lbl, v in IDENTITY_ITEMS}
MODIFIER_OPTS = [lbl for lbl, _ in MODIFIER_ITEMS]
MODIFIER_VAL = {lbl: v for lbl, v in MODIFIER_ITEMS}

def _identity_subject(identity_label, modifier_label, rng):
    """根据中文下拉选词拼出英文主体；🎲随机修饰时按身份大类自动联想对应修饰词。选随机/无则返回 ''。"""
    if not identity_label or identity_label in ('🎲 随机', '无'):
        return ''
    iv = IDENTITY_VAL.get(identity_label, '')
    if not iv:
        return ''
    cat = identity_label.split('·')[0] if '·' in identity_label else ''
    if modifier_label in ('🎲 随机', '无', ''):
        pool = [eng for _, eng in IDENTITY_MODIFIERS.get(cat, [])]
        mv = rng.rnd(pool) if pool else ''
    else:
        mv = MODIFIER_VAL.get(modifier_label, '')
    parts = [iv]
    if mv:
        parts.append(mv)
    return ', '.join(parts)

# ===================== 权重辅助（A方案：ComfyUI CLIPTextEncode 原生支持 (text:1.3)） =====================
def W(text, weight, enabled, intensity=100):
    """enabled 时给文本加 ComfyUI 权重语法；intensity 为百分比(100=原值,0=无权重纯净)。否则原样返回（Krea2网页端友好）。"""
    if not enabled or not text or intensity <= 0:
        return text
    # 防御：布尔或保留字字符串（如 "False"/"True"/"None"）不包权重，
    # 否则会写出 (False:1.2) 这类怪词被图像模型渲染成字。
    if isinstance(text, bool) or (isinstance(text, str) and text.strip() in ('False', 'True', 'None')):
        return text
    w = round(weight * intensity / 100, 2)
    return f"({text}:{w})"


# ===================== 节点：出图提示词 =====================
class PromptForgeImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["普通模式", "巨构模式"], {"default": "普通模式"}),
                "style": (STYLE_OPTS, {"default": "写实摄影"}),
                "category": (CAT_OPTS, {"default": "人像"}),
                "lens": (LENS_OPTS, {"default": "85mm 人像"}),
                "light": (LIGHT_OPTS, {"default": "黄金时刻"}),
                "env": (ENV_OPTS, {"default": "云雾山峦"}),
                "mega_preset": (MEGA_OPTS, {"default": "⚪ 无（普通模式）"}),
                "morph": (MORPH_OPTS, {"default": "蜂窝重复（默认）"}),
                "variant": (VAR_OPTS, {"default": "压迫悬顶·巨物出画"}),
                "巨构视角": (NORMAL_VIEW_OPTS, {"default": "⚪ 无（标准框）"}),
                "题材": (THEME_OPTS, {"default": "无（默认）"}),
                "风格混合": (MIX_OPTS, {"default": "🛡 隔离（默认）"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1, "control_after_generate": ["randomize", "increment", "decrement", "fixed"]}),
                "主体身份": (IDENTITY_OPTS, {"default": "🎲 随机"}),
                "主体修饰": (MODIFIER_OPTS, {"default": "🎲 随机"}),
                "主体": ("STRING", {"default": "", "multiline": False}),
                "物体": ("STRING", {"default": "", "multiline": False}),
                "故事": ("STRING", {"default": "", "multiline": True}),
                "启用权重": ("BOOLEAN", {"default": True}),
                "权重强度": ("INT", {"default": 100, "min": 0, "max": 200, "step": 10}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "prompt_json")
    FUNCTION = "forge"
    CATEGORY = "JIUMI PromptForge/图片提示词"

    def forge(self, mode, style, category, lens, light, env, mega_preset, morph, variant, 巨构视角, 题材, 风格混合, seed, 主体身份="🎲 随机", 主体修饰="🎲 随机", 主体="", 物体="", 故事="", 启用权重=True, 权重强度=100):
        sd = seed if seed and seed != 0 else random.randint(1, 2**31)
        rng = RNG(sd)

        sk = STYLE_L2K.get(style, 'rand')
        ck = CAT_L2K[category]
        lk = LENS_L2K[lens]
        ltk = LIGHT_L2K[light]
        ek = ENV_L2K[env]
        thk = THEME_L2K[题材]
        if thk == 'rand':
            thk = rng.rnd([k for k in _NONRAND(THEME_POOL) if k != 'none'])
        vkn = NORMAL_VIEW_L2K[巨构视角]
        if vkn == 'rand':
            vkn = rng.rnd([k for k in _NONRAND(NORMAL_VIEW) if k != 'none'])

        if sk == 'rand':
            sk = rng.rnd(_NONRAND(STYLES))
        if ck == 'rand':
            ck = rng.rnd(_NONRAND(CATS))
        if lk == 'rand':
            lk = rng.rnd(_NONRAND(LENSES))
        if ltk == 'rand':
            ltk = rng.rnd(CHINA_SOFT_LIGHTS) if sk in ('ink', 'guofeng') else rng.rnd(_NONRAND(LIGHTS))
        if ek == 'rand':
            ek = rng.rnd(_NONRAND(ENVS))

        # 中文下拉拼英文主体：选了具体身份就覆盖「主体」框
        iden_subj = _identity_subject(主体身份, 主体修饰, rng)
        effective_subject = iden_subj if iden_subj else 主体

        # 风格亲和层：隔离模式下冲突题材不注入 + 警告；碰撞模式保留 + 桥接渲染词
        mix_mode = MIX_L2K.get(风格混合, '隔离')
        thk_inject, aff_warns, bridge = _affinity(sk, thk, mix_mode, 物体)

        if mode == "巨构模式":
            # 「⚪ 无」在巨构模式下自动转随机
            if mega_preset == MEGA_NONE:
                mk = 'rand'
            else:
                mk = MEGA_L2K[mega_preset]
            # 地域巨构池：环境是广西/南方/北方且巨构=随机时，从该地域巨构池随机抽
            if ek in ENV_MEGA_POOL and mk == 'rand':
                mk = rng.rnd(ENV_MEGA_POOL[ek])
            vk = VAR_L2K[variant]
            if mk == 'rand':
                mk = rng.rnd(_NONRAND(MEGA))
            if vk == 'rand':
                vk = rng.rnd(_NONRAND(MVAR))
            morphKey = MORPH_L2K[morph]
            if morphKey == 'rand':
                morphKey = rng.rnd(_NONRAND(MEGA_MORPH))
            positive, fields = buildMega(mk, lk, vk, ltk, ek, sk, rng, effective_subject, 物体, 故事, 启用权重, 权重强度, morphKey=morphKey, theme=thk_inject, bridge=bridge)
            _w = _conflict_warnings(thk_inject, mk)
            if _w or aff_warns:
                fields['warnings'] = (_w or []) + aff_warns
        else:
            positive, fields = buildNormal(sk, ck, lk, ltk, ek, rng, effective_subject, 物体, 故事, 启用权重, 权重强度, theme=thk_inject, viewKey=vkn, bridge=bridge)
            if aff_warns:
                fields['warnings'] = aff_warns

        negative = NEG.get(sk, 'low quality, blurry, watermark, text')
        env_neg = NEG_ENV_MAP.get(ek, '')
        if env_neg:
            negative += ', ' + env_neg
        negative += ', ' + ANTI_TEXT
        prompt_json = _to_json(fields, negative)
        return (positive, negative, prompt_json)


# ===================== 节点：H3 视频提示词 =====================
class PromptForgeH3:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "style": (STYLE_OPTS, {"default": "水墨"}),
                "category": (CAT_OPTS, {"default": "场景"}),
                "lens": (LENS_OPTS, {"default": "变形宽银幕"}),
                "light": (LIGHT_OPTS, {"default": "体积光"}),
                "env": (ENV_OPTS, {"default": "天宫"}),
                "use_mega": ("BOOLEAN", {"default": False}),
                "mega_preset": (MEGA_OPTS, {"default": "⚪ 无（普通模式）"}),
                "morph": (MORPH_OPTS, {"default": "蜂窝重复（默认）"}),
                "variant": (VAR_OPTS, {"default": "完整留白·全身+负空间"}),
                "巨构视角": (NORMAL_VIEW_OPTS, {"default": "⚪ 无（标准框）"}),
                "题材": (THEME_OPTS, {"default": "无（默认）"}),
                "风格混合": (MIX_OPTS, {"default": "🛡 隔离（默认）"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1, "control_after_generate": ["randomize", "increment", "decrement", "fixed"]}),
                "主体身份": (IDENTITY_OPTS, {"default": "🎲 随机"}),
                "主体修饰": (MODIFIER_OPTS, {"default": "🎲 随机"}),
                "主体": ("STRING", {"default": "", "multiline": False}),
                "物体": ("STRING", {"default": "", "multiline": False}),
                "故事": ("STRING", {"default": "", "multiline": True}),
                "镜头数": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
                "人物动效": (FIGURE_OPTS, {"default": "无（不动）"}),
                "植物动效": (PLANT_OPTS, {"default": "无（不动）"}),
                "场景天气动效": (SCENE_OPTS, {"default": "无（不动）"}),
                "巨构动效": (MOTION_MEGA_OPTS, {"default": "无（不动）"}),
                "camera": (CAM_OPTS, {"default": "🎲 自动循环（默认）"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("h3_prompt", "image_prompt", "prompt_json")
    FUNCTION = "forge"
    CATEGORY = "JIUMI PromptForge/视频提示词"

    def forge(self, style, category, lens, light, env, use_mega, mega_preset, morph, variant, 巨构视角, 题材, 风格混合, seed, 主体身份="🎲 随机", 主体修饰="🎲 随机", 主体="", 物体="", 故事="", 镜头数=1, 人物动效="无（不动）", 植物动效="无（不动）", 场景天气动效="无（不动）", 巨构动效="无（不动）", camera="🎲 自动循环（默认）"):
        sd = seed if seed and seed != 0 else random.randint(1, 2**31)
        rng = RNG(sd)

        sk = STYLE_L2K.get(style, 'rand')
        ck = CAT_L2K[category]
        lk = LENS_L2K[lens]
        ltk = LIGHT_L2K[light]
        ek = ENV_L2K[env]
        thk = THEME_L2K[题材]
        if thk == 'rand':
            thk = rng.rnd([k for k in _NONRAND(THEME_POOL) if k != 'none'])
        vkn = NORMAL_VIEW_L2K[巨构视角]
        if vkn == 'rand':
            vkn = rng.rnd([k for k in _NONRAND(NORMAL_VIEW) if k != 'none'])
        if sk == 'rand':
            sk = rng.rnd(_NONRAND(STYLES))
        if ck == 'rand':
            ck = rng.rnd(_NONRAND(CATS))
        if lk == 'rand':
            lk = rng.rnd(_NONRAND(LENSES))
        if ltk == 'rand':
            ltk = rng.rnd(CHINA_SOFT_LIGHTS) if sk in ('ink', 'guofeng') else rng.rnd(_NONRAND(LIGHTS))
        if ek == 'rand':
            ek = rng.rnd(_NONRAND(ENVS))

        # 4 类动效逐项开关，组合出任意「全活」；同类只取选中一项
        _parts = []
        _mk_f = FIGURE_L2K.get(人物动效)
        if _mk_f: _parts.append(MOTION_FIGURE[_mk_f]['text'])
        _mk_p = PLANT_L2K.get(植物动效)
        if _mk_p: _parts.append(MOTION_PLANT[_mk_p]['text'])
        _mk_s = SCENE_L2K.get(场景天气动效)
        if _mk_s: _parts.append(MOTION_SCENE[_mk_s]['text'])
        _mk_m = MOTION_MEGA_L2K.get(巨构动效)
        if _mk_m: _parts.append(MOTION_MEGA[_mk_m]['text'])
        motion_text = '. '.join(_parts)
        mk_cam = CAM_L2K.get(camera, 'auto')

        iden_subj = _identity_subject(主体身份, 主体修饰, rng)
        effective_subject = iden_subj if iden_subj else 主体

        # 风格亲和层：隔离模式下冲突题材不注入 + 警告；碰撞模式保留 + 桥接渲染词
        mix_mode = MIX_L2K.get(风格混合, '隔离')
        thk_inject, aff_warns, bridge = _affinity(sk, thk, mix_mode, 物体)

        # use_mega=True 或用户显式选了具体巨构（非「无」、非随机）才走巨构分支
        explicit_mega = (mega_preset != MEGA_NONE) and (mega_preset != '🎲 随机')
        if use_mega or explicit_mega:
            mk = 'rand' if mega_preset == MEGA_NONE else MEGA_L2K[mega_preset]
            # 地域巨构池：环境是广西/南方/北方且巨构=随机时，从该地域巨构池随机抽
            if ek in ENV_MEGA_POOL and mk == 'rand':
                mk = rng.rnd(ENV_MEGA_POOL[ek])
            vk = VAR_L2K[variant]
            if mk == 'rand':
                mk = rng.rnd(_NONRAND(MEGA))
            if vk == 'rand':
                vk = rng.rnd(_NONRAND(MVAR))
            # H3 提示词不带权重（MiniMax H3 不认 (text:1.3) 语法），固定 enable_weight=False
            morphKey = MORPH_L2K[morph]
            if morphKey == 'rand':
                morphKey = rng.rnd(_NONRAND(MEGA_MORPH))
            base, fields = buildMega(mk, lk, vk, ltk, ek, sk, rng, effective_subject, 物体, 故事, False, morphKey=morphKey, theme=thk_inject, bridge=bridge)
            _w = _conflict_warnings(thk_inject, mk)
            if _w or aff_warns:
                fields['warnings'] = (_w or []) + aff_warns
            cat_for_h3 = 'mega'
        else:
            base, fields = buildNormal(sk, ck, lk, ltk, ek, rng, effective_subject, 物体, 故事, False, theme=thk_inject, viewKey=vkn, bridge=bridge)
            if aff_warns:
                fields['warnings'] = aff_warns
            cat_for_h3 = ck

        h3 = buildH3(cat_for_h3, sk, ek, base, 镜头数, motion_text, mk_cam)
        negative = NEG.get(sk, 'low quality, blurry, watermark, text')
        env_neg = NEG_ENV_MAP.get(ek, '')
        if env_neg:
            negative += ', ' + env_neg
        negative += ', ' + ANTI_TEXT
        prompt_json = _to_json(fields, negative)
        return (h3, base, prompt_json)


NODE_CLASS_MAPPINGS = {
    "PromptForgeImage": PromptForgeImage,
    "PromptForgeH3": PromptForgeH3,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptForgeImage": "JIUMI PromptForge 出图提示词",
    "PromptForgeH3": "JIUMI PromptForge H3 视频提示词",
}
