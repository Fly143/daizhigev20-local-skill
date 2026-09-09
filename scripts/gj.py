#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gj —— 殆知阁离线检索工具

  gj find   词1 [词2 ...]              按书名/作者/分类/路径找书
  gj grep   词 [词2 ...] [选项]        全文检索（8 核并行）
  gj chapter 书名 [章节名] [--list]    按章节读一本书
  gj toc    词                         按分类列书目
  gj show   路径|书名 [起始行] [行数]    看原文
  gj meta   书名                       元数据 + 外部链接
  gj links  [--prov ctext]             外部参照表
  gj dup    [--hash]                   查重
  gj stats                             库统计

grep 选项:
  --in 书名[，书名]   限定书名/路径（可逗号分隔多个，OR）
  --ctx N             上下文半径（默认 40）
  --near N            多词之间的最大距离（默认 30，0 表示不限）
  --limit N           最多显示条数（默认 30）
  --per N             同一文件最多显示条数（默认 3）
  --variants          繁简/异体字匹配（默认开启，--no-variants 关闭）
  --loan              追加帛书借字变体（仅老子类文献，默认关闭）
  --jobs N            并行进程数（默认 8）
  --all               不跳过 .sources/
  --files             只列文件 + 命中数
  --json              机器可读输出
"""
import os, re, sys, json, shlex, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import (ROOT, KB, IDX, load_index, variant_regex, loan_forms,
                 expand_alias, IndexMissing)

JOBS = 8


# ---------------------------------------------------------------- 索引检查

def _index_hint(e):
    print(f"❌ 索引文件缺失: {e.path}\n"
          f"   请先确认数据目录就位，再重建索引：\n"
          f"     python3 {os.path.join(KB, 'build_index.py')}\n"
          f"   数据目录: {ROOT}", file=sys.stderr)
    return False


# ---------------------------------------------------------------- 工具

def _q(s):
    return shlex.quote(s)


def _book_files(keys):
    """keys: 书名/路径关键词列表，OR 匹配。
    以 = 开头表示精确书名匹配。自动展开同书异名。"""
    exact = [k[1:] for k in keys if k.startswith("=")]
    fuzzy = [k for k in keys if not k.startswith("=")]
    fuzzy = expand_alias(fuzzy)
    out = []
    for path, title, cat, author, size, links in load_index():
        if title in exact:
            out.append(os.path.join(ROOT, path)); continue
        hay = path + " " + title
        if any(k in hay for k in fuzzy):
            out.append(os.path.join(ROOT, path))
    return out


def _run_shell(cmd, max_lines=500000):
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    except FileNotFoundError:
        return []
    out = []
    try:
        for line in p.stdout:
            out.append(line.decode("utf-8", "replace").rstrip("\n"))
            if len(out) >= max_lines:
                break
    finally:
        try: p.stdout.close()
        except Exception: pass
        try: p.terminate()
        except Exception: pass
        try: p.wait(timeout=5)
        except Exception: p.kill()
    return out


def _all_md_files(allsrc):
    """列出正文 md 文件（跳过 .git/.github/.sources）"""
    out = []
    skip = {".git", ".github"} | (set() if allsrc else {".sources"})
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if fn.endswith(".md"):
                out.append(os.path.join(dirpath, fn))
    return out


def _grep_chunk(files, pats):
    """对一个文件分片跑 grep，返回行列表。每个子进程独立收集，避免管道交错"""
    try:
        r = subprocess.run(["grep", "-Hn", "-I", "-E", pats[0]] + files,
                           capture_output=True, timeout=120)
    except Exception:
        return []
    text = r.stdout.decode("utf-8", "replace")
    lines = [l for l in text.split("\n") if l]
    for p in pats[1:]:
        rx = re.compile(p)
        lines = [l for l in lines if rx.search(l)]
    return lines


def _parallel_grep(files, pats, jobs, chunk=400):
    """多进程分片并行检索；结果在 Python 侧合并，无字节交错"""
    from concurrent.futures import ThreadPoolExecutor
    if not files:
        return []
    if len(files) <= chunk or jobs <= 1:
        return _grep_chunk(files, pats)
    chunks = [files[i:i+chunk] for i in range(0, len(files), chunk)]
    out = []
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for res in ex.map(lambda c: _grep_chunk(c, pats), chunks):
            out.extend(res)
    return out


# ---------------------------------------------------------------- find

def cmd_find(args):
    if not args:
        print("用法: gj find 词"); return
    n = 0
    for path, title, cat, author, size, links in load_index():
        hay = f"{path} {title} {cat} {author}"
        if all(a in hay for a in args):
            au = author if author else "（作者未填）"
            lk = "  " + links if links else ""
            print(f"{title}\t{cat}\t{au}\t{path}{lk}")
            n += 1
    print(f"—— {n} 部 ——")


# ---------------------------------------------------------------- toc

def cmd_toc(args):
    key = args[0] if args else ""
    cats = {}
    for path, title, cat, author, size, links in load_index():
        if key and key not in cat and key not in title:
            continue
        cats.setdefault(cat, []).append(title)
    for c in sorted(cats):
        print(f"\n### {c}  ({len(cats[c])} 部)")
        print("  " + "、".join(sorted(cats[c])[:300]))


# ---------------------------------------------------------------- show

def _resolve(key):
    rows = load_index()
    exact = [r[0] for r in rows if r[1] == key]
    if exact:
        return os.path.join(ROOT, exact[0])
    cand = [r[0] for r in rows if key in r[1] or key in r[0]]
    if len(cand) == 1:
        return os.path.join(ROOT, cand[0])
    return None, cand


def cmd_show(args):
    if not args:
        print("用法: gj show 路径|书名 [起始行] [行数]"); return
    key = args[0]
    p = key if os.path.isabs(key) else os.path.join(ROOT, key)
    if not os.path.exists(p):
        r = _resolve(key)
        if isinstance(r, str):
            p = r
        else:
            print(f"未找到（{len(r[1])} 个候选）：")
            for c in r[1][:15]:
                print("  " + c)
            return
    start = int(args[1]) if len(args) > 1 else 1
    n     = int(args[2]) if len(args) > 2 else 80
    with open(p, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if i < start: continue
            if i >= start + n: break
            print(f"{i}\t{line.rstrip()}")


# ---------------------------------------------------------------- chapter

_NUM = r"[〇零一二三四五六七八九十百千0-9０-９]+"
_HEAD_PATS = [
    re.compile(r"^[●·\s\u3000]*卷[之第]?" + _NUM + r"(?:[\s\u3000].{0,20})?$"),
    re.compile(r"^[●·\s\u3000]*第" + _NUM + r"[卷章回出篇节](?:[\s\u3000].{0,20})?$"),
    re.compile(r"^[●·\s\u3000]*" + _NUM + r"[章回]$"),
    re.compile(r"^[●·\s\u3000]*卷[上下]$"),
    re.compile(r"^[●·\s\u3000]*\S{1,10}(?:章|篇|回)第" + _NUM + r"$"),
    re.compile(r"^[●·\s\u3000]*\S{1,6}第" + _NUM + r"$"),
    re.compile(r"^#+[\s\u3000]*卷.*$"),
]


def _is_heading(s):
    if not s or len(s) > 30:
        return False
    return any(p.match(s) for p in _HEAD_PATS)


def _chapters(path):
    """返回 [(起始行, 标题)]，跳过 frontmatter；同一标题重复时保留最后一次
    （很多书正文前有目录页，标题会先出现一遍）"""
    raw = []
    with open(path, encoding="utf-8", errors="replace") as f:
        in_fm = False
        for i, line in enumerate(f, 1):
            s = line.strip()
            if i == 1 and s == "---":
                in_fm = True
                continue
            if in_fm:
                if s == "---":
                    in_fm = False
                continue
            if _is_heading(s):
                raw.append((i, s))
    last = {}
    for ln, t in raw:
        last[t] = ln
    return sorted((ln, t) for t, ln in last.items())


def _looks_like_toc(path):
    """小文件 + 大量指向同级 md 的链接 => 目录页"""
    try:
        if os.path.getsize(path) > 2_000_000:
            return False
        txt = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return False
    return len(re.findall(r"\]\([^)]+\.md\)", txt)) > 20


def cmd_chapter(args):
    if not args:
        print("用法: gj chapter 书名 [章节名] [--list]"); return
    key = args[0]
    want = None
    show_list = "--list" in args
    for a in args[1:]:
        if not a.startswith("--"):
            want = a
            break

    rows = load_index()
    exact = [r for r in rows if r[1] == key]
    if len(exact) == 1:
        p = os.path.join(ROOT, exact[0][0])
        if _looks_like_toc(p):
            base = os.path.dirname(exact[0][0])
            sib = [r for r in rows if r[0].startswith(base + "/" + key + "/")]
            print(f"# 《{key}》是目录页，全书按卷分为 {len(sib)} 个文件：")
            for r in sorted(sib, key=lambda x: x[0])[:300]:
                print(f"  {r[0]}")
            return
    if not exact:
        pref = [r for r in rows if r[1].startswith(key)]
        if len(pref) > 1:
            print(f"# 《{key}》按卷分 {len(pref)} 个文件（直接读对应文件即可）")
            for r in sorted(pref, key=lambda x: x[0])[:300]:
                print(f"  {r[0]}")
            return
    if len(exact) > 1:
        print(f"# 《{key}》有 {len(exact)} 个同名文件")
        for r in sorted(exact, key=lambda x: x[0]):
            print(f"  {r[0]}")
        return

    r = _resolve(key)
    if not isinstance(r, str):
        print(f"未找到或有多解：{key}")
        return

    heads = _chapters(r)
    if not heads:
        print("未识别到章节标题（可能全书无分章），用 gj show 逐行看")
        return
    if show_list or want is None:
        print(f"# {os.path.relpath(r, ROOT)}  共 {len(heads)} 个章节标题")
        for ln, t in heads:
            print(f"{ln:6d}  {t}")
        return
    hit = None
    for idx, (ln, t) in enumerate(heads):
        if want in t:
            hit = idx
            break
    if hit is None:
        print(f"未找到章节「{want}」。用 --list 查看全部标题")
        return
    start = heads[hit][0]
    end = heads[hit + 1][0] - 1 if hit + 1 < len(heads) else 10 ** 9
    with open(r, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if i < start: continue
            if i > end: break
            print(f"{i}\t{line.rstrip()}")


# ---------------------------------------------------------------- meta

def cmd_meta(args):
    if not args:
        print("用法: gj meta 书名 [--limit N]"); return
    limit = 5
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    key = args[0]
    rows = load_index()
    exact = [r for r in rows if r[1] == key]
    cand = exact if exact else [r for r in rows if key in r[1] or key in r[0]]
    if not exact and len(cand) > limit:
        print(f"（子串命中 {len(cand)} 部，只显示前 {limit} 部）\n")
    for path, title, cat, author, size, links in cand[:limit]:
        print(f"书名  : {title}")
        print(f"分类  : {cat}")
        print(f"作者  : {author or '（未填）'}")
        print(f"字节  : {size}")
        print(f"路径  : {ROOT}/{path}")
        if links:
            print("外部链接:")
            for seg in links.split(";"):
                if ":" in seg:
                    k, v = seg.split(":", 1)
                    print(f"  {k:10s} {', '.join(v.split('|'))}")
        print("-" * 60)


# ---------------------------------------------------------------- links

def cmd_links(args):
    prov = None
    if "--prov" in args:
        prov = args[args.index("--prov") + 1]
    rows = [r for r in load_index() if r[5]]
    if prov:
        rows = [r for r in rows if prov in r[5]]
    print(f"# 含外部链接的书: {len(rows)} 部（prov={prov or '全部'}）")
    print("# 路径\t书名\t链接")
    for r in rows:
        print(f"{r[0]}\t{r[1]}\t{r[5]}")


# ---------------------------------------------------------------- dup

def cmd_dup(args):
    import hashlib
    from collections import defaultdict
    by_title = defaultdict(list)
    for r in load_index():
        by_title[r[1]].append(r)
    dups = {k: v for k, v in by_title.items() if len(v) > 1}
    print(f"# 同名书籍: {len(dups)} 组")
    if "--hash" in args:
        print("# 内容哈希比对（相同 = 完全重复）")
    for t, rs in sorted(dups.items(), key=lambda x: -len(x[1])):
        print(f"\n### {t}  ×{len(rs)}")
        for r in rs:
            extra = ""
            if "--hash" in args:
                try:
                    body = open(os.path.join(ROOT, r[0]), encoding="utf-8",
                                errors="replace").read()
                    body = re.sub(r"^---\n.*?\n---", "", body, flags=re.S)
                    extra = "  " + hashlib.md5(body.encode()).hexdigest()[:10]
                except Exception:
                    extra = "  <读取失败>"
            print(f"  {r[2]:40s} {r[4]:>9s} B  {r[0]}{extra}")


# ---------------------------------------------------------------- stats

def cmd_stats(args):
    rows = load_index()
    print(f"书籍数: {len(rows)}")
    cats = {}
    for r in rows:
        cats[r[2]] = cats.get(r[2], 0) + 1
    print("分类 Top20:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1])[:20]:
        print(f"  {n:5d}  {c}")
    n_l = sum(1 for r in rows if r[5])
    n_a = sum(1 for r in rows if r[3])
    print(f"含外部链接: {n_l}    有作者: {n_a} ({n_a*100//max(1,len(rows))}%)")


# ---------------------------------------------------------------- grep

def _build_cmd(groups, book, allsrc, jobs):
    """groups: 每个词一个带括号的正则；多词之间用管道串联实现 AND"""
    if book:
        files = _book_files(book)
        if not files:
            return None
        find_part = "printf '%s\\0' " + " ".join(_q(f) for f in files)
    else:
        find_part = "find " + _q(ROOT) + " -name '*.md'"
        for skip in (".git", ".github") + (() if allsrc else (".sources",)):
            find_part += " -not -path " + _q(os.path.join(ROOT, skip, "*"))
        find_part += " -print0"

    cmd = (find_part
           + " | xargs -0 -P %d -n 100 grep -Hn -I -E %s" % (jobs, _q(groups[0])))
    for g in groups[1:]:
        cmd += " | grep -E " + _q(g)
    return cmd


def cmd_grep(args):
    ctx, limit, per, jobs = 40, 30, 3, JOBS
    variants, loan, allsrc, files_only, as_json = True, False, False, False, False
    near = None                     # 多词之间的最大允许距离
    book_keys, words, i = [], [], 0
    while i < len(args):
        a = args[i]
        if   a == "--ctx":      ctx = int(args[i+1]); i += 2
        elif a == "--limit":    limit = int(args[i+1]); i += 2
        elif a == "--per":      per = int(args[i+1]); i += 2
        elif a == "--jobs":     jobs = int(args[i+1]); i += 2
        elif a == "--near":     near = int(args[i+1]); i += 2
        elif a == "--in":
            book_keys += [x for x in args[i+1].split(",") if x]; i += 2
        elif a == "--variants": variants = True; i += 1
        elif a == "--no-variants": variants = False; i += 1
        elif a == "--loan":     loan = True; i += 1
        elif a == "--all":      allsrc = True; i += 1
        elif a == "--files":    files_only = True; i += 1
        elif a == "--json":     as_json = True; i += 1
        else: words.append(a); i += 1
    if not words:
        print("用法: gj grep 词 [--in 书名] [--ctx 40] [--limit 30]"); return

    # 多词默认要求彼此靠近（默认 30 字），否则同一长行里的巧合会大量误报
    if len(words) > 1 and near is None:
        near = 30

    groups = []
    for w in words:
        alts = [variant_regex(w, variants)]
        if loan:
            alts += [re.escape(f) for f in loan_forms(w)]
        groups.append("(" + "|".join(alts) + ")")

    if book_keys:
        files = _book_files(book_keys)
    else:
        files = _all_md_files(allsrc)
    if not files:
        print("没有匹配的书"); return

    lines = _parallel_grep(files, groups, jobs)

    rxs = [re.compile(g) for g in groups]
    rx = re.compile("|".join(groups))
    hits, files_cnt, dropped = [], {}, 0
    for line in lines:
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        full, lineno, text = parts[0], parts[1], parts[2]
        if not full.endswith(".md"):
            continue
        # 词距过滤：任一两词的最近距离必须 <= near
        if near and len(rxs) > 1:
            spans = [[m.start() for m in r.finditer(text)] for r in rxs]
            if all(spans):
                best = min(abs(a - b) for i in range(len(spans))
                           for j in range(i+1, len(spans))
                           for a in spans[i] for b in spans[j])
                if best > near:
                    dropped += 1
                    continue
        rel = os.path.relpath(full, ROOT)
        files_cnt[rel] = files_cnt.get(rel, 0) + 1
        m = rx.search(text)
        if not m:
            continue
        s, e = max(0, m.start()-ctx), min(len(text), m.end()+ctx)
        hits.append((rel, int(lineno) if lineno.isdigit() else 0,
                     text[s:e].strip(), m.group(0)))

    hits.sort(key=lambda x: (x[0], x[1]))

    if files_only:
        for p in sorted(files_cnt, key=lambda x: (-files_cnt[x], x)):
            print(f"{files_cnt[p]:5d}  {p}")
        tail = f"命中 {len(files_cnt)} 个文件，共 {len(hits)} 处"
        if dropped:
            tail += f"（词距过滤掉 {dropped} 处）"
        print(f"\n—— {tail} ——")
        return

    if as_json:
        print(json.dumps({"files": len(files_cnt), "dropped": dropped,
                          "hits": [{"path": p, "line": n, "text": t, "match": m}
                                   for p, n, t, m in hits[:limit]]},
                         ensure_ascii=False, indent=2))
        return

    shown, per_file = 0, {}
    for path, lineno, frag, mt in hits:
        per_file[path] = per_file.get(path, 0) + 1
        if per_file[path] > per: continue
        if len(frag) > 400:
            frag = frag[:400] + "…（本行过长，已截断）"
        print(f"【{path}:{lineno}】 …{frag}…")
        shown += 1
        if shown >= limit: break

    tail = f"命中 {len(files_cnt)} 个文件，共 {len(hits)} 处"
    if dropped:
        tail += f"（词距 >{near} 字的 {dropped} 处已过滤）"
    print(f"\n—— {tail}，显示 {shown} 条 ——")


# ---------------------------------------------------------------- main

def _check_data():
    """数据目录缺失或为空时给出明确提示，避免静默返回空结果"""
    if not os.path.isdir(ROOT):
        print(f"❌ 数据目录不存在: {ROOT}\n"
              f"   请先下载数据（约 5.2 GB）：\n"
              f"     git clone -b data --depth 1 "
              f"https://github.com/daizhige-org/daizhigev20.git\n"
              f"   或用环境变量指定已有数据：export DZG_DATA=/path/to/daizhigev20")
        return False
    try:
        if not any(fn.endswith(".md") for fn in os.listdir(ROOT)):
            print(f"❌ 数据目录为空: {ROOT}\n"
                  f"   请确认已克隆 daizhige-org/daizhigev20 的 data 分支")
            return False
    except OSError as e:
        print(f"❌ 无法读取数据目录: {ROOT}  ({e})")
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd, args = sys.argv[1], sys.argv[2:]
    table = {"find": cmd_find, "grep": cmd_grep, "chapter": cmd_chapter,
             "toc": cmd_toc, "show": cmd_show, "meta": cmd_meta,
             "links": cmd_links, "dup": cmd_dup, "stats": cmd_stats}
    fn = table.get(cmd)
    if fn is None:
        print(__doc__)
        return
    if not _check_data():
        sys.exit(2)
    try:
        fn(args)
    except IndexMissing as e:
        _index_hint(e)
        sys.exit(2)
    except BrokenPipeError:
        try: sys.stdout.close()
        except Exception: pass
        os._exit(0)
    except KeyboardInterrupt:
        os._exit(130)


if __name__ == "__main__":
    main()
