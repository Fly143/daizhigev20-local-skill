#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gj 工具共享库：frontmatter 解析、索引加载、变体正则"""
import os, re, json

# 工具自身所在目录（不再硬编码，便于移动与分发）
KB = os.path.dirname(os.path.abspath(__file__))


def _find_data():
    """定位古籍数据目录。
    环境变量 DZG_DATA 一旦设置就**直接采用**（不存在也报错，不静默回退），
    未设置时才按常见位置探测。"""
    env = os.environ.get("DZG_DATA")
    if env:
        return env                      # 显式指定：即使不存在也如实返回
    parent = os.path.dirname(KB)
    for cand in (
        os.path.join(parent, "daizhigev20"),      # 与工具同级
        "/workspace/daizhigev20",
        os.path.join(KB, "daizhigev20"),
        os.path.expanduser("~/daizhigev20"),
    ):
        if os.path.isdir(cand):
            return cand
    return "/workspace/daizhigev20"


ROOT = _find_data()
IDX  = os.path.join(KB, "index.tsv")

# ---------------------------------------------------------------- frontmatter

_FM = re.compile(r"^---\n(.*?)\n---", re.S)


def read_frontmatter(path, limit=8192):
    """返回 frontmatter 文本，没有则返回 ''。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.read(limit)
    except Exception:
        return ""
    m = _FM.match(head)
    return m.group(1) if m else ""


def _scalar(fm, key):
    m = re.search(r"^%s:\s*(.+)$" % key, fm, re.M)
    if not m:
        return ""
    return m.group(1).strip().strip("'\"")


def _title(fm):
    """title 可能是单值，也可能是 {zh-hans, zh-hant} 嵌套，且两键顺序不定"""
    m = re.search(r"^title:[ \t]*\n((?:[ \t]+.*\n?)+)", fm, re.M)
    if m:
        block = m.group(1)
        for key in ("zh-hans", "zh-hant"):
            v = re.search(r"^\s+%s:\s*(.+)$" % key, block, re.M)
            if v:
                return v.group(1).strip().strip("'\"")
        v = re.search(r"^\s+([^:\n]+):\s*(.+)$", block, re.M)   # 任意子键兜底
        if v:
            return v.group(2).strip().strip("'\"")
        return ""
    return _scalar(fm, "title")


def parse_meta(path):
    """返回 (title, category, author, links_dict)"""
    fm = read_frontmatter(path)
    title = category = author = ""
    if fm:
        title = _title(fm)
        category = _scalar(fm, "category")
        author = _scalar(fm, "author")

    if not title:
        title = os.path.splitext(os.path.basename(path))[0]
    if not category:
        rel = os.path.relpath(path, ROOT)
        category = "/" + os.path.dirname(rel).replace(os.sep, "/")

    return title, category, author, parse_links(fm)


def parse_links(fm):
    """抽取 external_links 下的一级键 -> [值, ...]"""
    out = {}
    if not fm:
        return out
    m = re.search(r"^external_links:\n((?:[ \t]+.*\n?)*)", fm, re.M)
    if not m:
        return out
    block = m.group(1)
    cur = None
    for line in block.split("\n"):
        if not line.strip():
            continue
        m1 = re.match(r"^  ([a-z_]+):\s*(.*)$", line)
        if m1:
            cur = m1.group(1)
            out.setdefault(cur, [])
            if m1.group(2).strip():
                out[cur].append(m1.group(2).strip())
            continue
        m2 = re.match(r"^\s+-\s*(.+)$", line)
        if m2 and cur:
            out[cur].append(m2.group(1).strip())
    return {k: v for k, v in out.items() if v}


def links_to_str(links):
    return ";".join("%s:%s" % (k, "|".join(v)) for k, v in links.items())


def links_from_str(s):
    out = {}
    if not s:
        return out
    for seg in s.split(";"):
        if ":" not in seg:
            continue
        k, v = seg.split(":", 1)
        out[k] = [x for x in v.split("|") if x]
    return out


# ---------------------------------------------------------------- 索引

def load_index():
    """-> [(path, title, category, author, size, links_str)]"""
    rows = []
    if not os.path.exists(IDX):
        return rows
    with open(IDX, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            while len(p) < 6:
                p.append("")
            rows.append(p[:6])
    return rows


def index_paths():
    return {r[0] for r in load_index()}


# ---------------------------------------------------------------- 同书异名

# 同一部书的常用异名。检索时自动展开，避免「搜老子找不到道德真经」
ALIASES = [
    ["老子", "道德经", "道德真经", "五千文", "道德经古本篇"],
    ["庄子", "南华经", "南华真经", "南华"],
    ["列子", "冲虚真经", "冲虚至德真经"],
    ["文子", "通玄真经"],
    ["亢仓子", "洞灵真经"],
    ["论语", "鲁论"],
    ["孟子", "孟子注疏"],
    ["荀子", "孙卿子", "荀卿子"],
    ["韩非子", "韩子"],
    ["淮南子", "淮南鸿烈", "淮南鸿烈解"],
    ["抱朴子", "抱朴子内外篇"],
    ["周易", "易经", "易", "周易注", "周易正义"],
    ["诗经", "毛诗", "诗三百"],
    ["尚书", "书经"],
    ["礼记", "礼经", "小戴礼记"],
    ["春秋", "春秋经", "左传", "左氏春秋", "公羊传", "谷梁传"],
    ["黄帝内经", "素问", "灵枢", "黄帝内经素问", "灵枢经"],
    ["本草纲目", "本草"],
    ["史记", "太史公书"],
    ["汉书", "前汉书"],
    ["后汉书", "续汉书"],
    ["资治通鉴", "通鉴"],
    ["说文解字", "说文"],
    ["世说新语", "世说"],
    ["楚辞", "楚词"],
    ["文选", "昭明文选"],
    ["文心雕龙", "文心"],
    ["金刚经", "金刚般若经", "金刚般若波罗蜜经"],
    ["心经", "般若波罗蜜多心经"],
    ["法华经", "妙法莲华经"],
    ["华严经", "大方广佛华严经"],
    ["楞严经", "大佛顶首楞严经"],
    ["维摩经", "维摩诘经"],
    ["坛经", "六祖坛经", "六祖大师法宝坛经"],
    ["阿弥陀经", "佛说阿弥陀经"],
]


def expand_alias(keys):
    """把别名展开成同组全部名称；未命中的原样保留"""
    out = list(keys)
    for g in ALIASES:
        if any(k in name or name in k for k in keys for name in g):
            out += [name for name in g if name not in out]
    # 去重保序
    seen, res = set(), []
    for k in out:
        if k not in seen:
            seen.add(k); res.append(k)
    return res


# ---------------------------------------------------------------- 变体

# 一、繁简/异体字：同一字的不同写法，全局安全
VARIANT_GROUPS = [
    "群羣", "峰峯", "迹蹟跡", "教敎", "既旣", "众衆", "宁甯", "遍徧", "咒呪",
    "粗麤", "冢冡", "概槩", "隶隷", "夐敻", "说說", "为爲", "于於", "无無",
    "却卻", "礼禮", "乐樂", "学學", "国國", "会會", "万萬", "与與", "后後",
    "台臺", "云雲", "复復", "发發", "历歷", "尽盡", "边邊", "尔爾", "体體",
    "宝寶", "举舉", "声聲", "圣聖", "听聽", "岁歲", "归歸", "气氣", "处處",
    "虫蟲", "庄莊", "兴興", "兰蘭", "观觀", "觉覺", "识識", "证證", "论論",
    "译譯", "释釋", "经經", "缘緣", "续續", "继繼", "罗羅", "义義", "议議",
    "仪儀", "严嚴", "医醫", "药藥", "属屬", "变變", "线線", "织織", "总總",
    "纲綱", "练練", "县縣", "悬懸", "乡鄉", "响響", "尝嘗", "赏賞", "党黨",
    "顾顧", "显顯", "风風", "飞飛", "饮飲", "饭飯", "馆館", "马馬", "骑騎",
    "验驗", "惊驚", "书書", "画畫", "读讀", "诗詩", "词詞", "语語", "问問",
    "门門", "开開", "关關", "长長", "东東", "鸟鳥", "鱼魚", "龙龍", "龟龜",
    "齐齊", "斋齋", "仓倉", "凤鳳", "鉴鑑", "录錄", "图圖", "团團", "园園",
    "远遠", "达達", "过過", "还還", "进進", "运運", "连連", "违違", "选選",
    "遗遺", "钟鐘", "铁鐵", "银銀", "钱錢", "镇鎮", "镜鏡", "闻聞", "闲閒",
    "间間", "阳陽", "阴陰", "陈陳", "陆陸", "际際", "险險", "隐隱", "难難",
    "灵靈", "静靜", "韵韻", "顺順", "领領", "题題", "颜顏", "愿願", "类類",
    "养養", "余餘", "驱驅", "驾駕", "鲜鮮", "鹤鶴", "鸿鴻", "鹏鵬", "鸡雞",
    "鸣鳴", "鸦鴉", "鹅鵝", "丽麗", "黄黃", "齿齒", "龄齡", "乌烏", "乌烏",
    "马馬", "驴驢", "骆駱", "骈駢", "骋騁", "骤驟", "骧驤", "骅驊",
]

# 二、帛书/简本借字：整词替换，只对老子类文献成立，默认关闭（--loan）
LOAN_MAP = {
    "圣": ["声", "聽", "听"],
    "其": ["亓"],
    "谓": ["胃"],
    "如": ["奴", "女"],
    "有": ["又"],
    "故": ["古"],
    "物": ["勿"],
    "弱": ["溺"],
    "修": ["攸"],
    "燥": ["澡"],
    "亲": ["新"],
    "在": ["才"],
    "欲": ["谷"],
    "守": ["兽"],
    "焉": ["安"],
    "听": ["圣"],
    "偏": ["便"],
    "治": ["绐"],
    "真": ["贞"],
    "争": ["静"],
    "骄": ["乔"],
    "孰": ["竺"],
    "易": ["惕"],
    "柔": ["至"],
    "却": ["道"],
    "缺": ["块"],
    "记": ["忌"],
    "姓": ["省"],
    "勤": ["堇"],
    "慢": ["曼"],
    "素": ["索"],
    "寡": ["颁"],
    "敦": ["屯"],
    "慎": ["谨"],
    "恶": ["亚"],
    "随": ["堕"],
    "贱": ["戋"],
    "奇": ["畸"],
    "讳": ["韦"],
    "蛇": ["它"],
    "牡": ["戊"],
    "怒": ["恕"],
    "祥": ["羕"],
    "殆": ["怠"],
    "久": ["旧"],
    "动": ["僮"],
    "功": ["攻"],
}


VARIANTS_FILE = os.path.join(KB, "variants.txt")


def _load_variants():
    """优先读 variants.txt（由 build_variants.py 自动生成），否则回退手工表。
    格式：每行一组，组内字以空格分隔（列数固定，GitHub 不会报表格错误）。"""
    groups = []
    if os.path.exists(VARIANTS_FILE):
        with open(VARIANTS_FILE, encoding="utf-8") as f:
            for line in f:
                g = [c for c in line.strip().split() if c]
                if len(g) > 1:
                    groups.append(g)
    if not groups:
        groups = [list(g) for g in VARIANT_GROUPS]
    return groups


def _char_map(groups):
    cmap = {}
    for g in groups:
        for ch in g:
            cmap.setdefault(ch, set()).update(g)
    return cmap


VARIANT_GROUPS = _load_variants()
CHAR_MAP = _char_map(VARIANT_GROUPS)


def variant_regex(word, use_variants=True):
    """把一个词转成带字符类的正则片段"""
    if not use_variants:
        return re.escape(word)
    parts = []
    for ch in word:
        s = CHAR_MAP.get(ch)
        if s and len(s) > 1:
            parts.append("[" + re.escape("".join(sorted(s))) + "]")
        else:
            parts.append(re.escape(ch))
    return "".join(parts)


def loan_forms(word, cap=64):
    """生成帛书借字形式的整词变体"""
    forms = [""]
    for ch in word:
        alts = [ch] + LOAN_MAP.get(ch, [])
        forms = [f + a for f in forms for a in alts]
        if len(forms) > cap:
            forms = forms[:cap]
    return [f for f in forms if f != word]
