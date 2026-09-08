#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill 自检：确认数据目录、索引、变体表就位，各子命令正常。

用法: python3 scripts/selftest.py
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GJ = os.path.join(HERE, "gj.py")
sys.path.insert(0, HERE)
FAILED = []


def check(name, cond, detail=""):
    print(f"{'✅' if cond else '❌'} {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        FAILED.append(name)


def run(args, timeout=120):
    r = subprocess.run([sys.executable, GJ] + args, capture_output=True,
                       text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


print("=" * 60)
print("殆知阁离线检索 skill —— 自检")
print("=" * 60)

# 1. 路径与文件
try:
    from lib import ROOT, IDX, VARIANTS_FILE, VARIANT_GROUPS
    check("数据目录存在", os.path.isdir(ROOT), ROOT)
    check("索引文件存在", os.path.exists(IDX),
          f"{os.path.getsize(IDX)//1024} KB" if os.path.exists(IDX) else "缺失")
    check("变体表存在", os.path.exists(VARIANTS_FILE),
          f"{len(VARIANT_GROUPS)} 组" if os.path.exists(VARIANTS_FILE) else "缺失")
except Exception as e:
    check("模块导入", False, f"{type(e).__name__}: {e}")

# 2. 数据规模
try:
    from lib import load_index
    rows = load_index()
    check("索引条目数合理（>20000）", len(rows) > 20000, f"{len(rows)} 部")
    n_link = sum(1 for r in rows if r[5])
    check("外部链接字段已解析（>12000）", n_link > 12000, f"{n_link} 部")
except Exception as e:
    check("索引读取", False, str(e))

# 3. 子命令
for args, must in [
    (["stats"], "书籍数"),
    (["find", "王弼"], "王弼"),
    (["meta", "王弼老子注"], "书名"),
]:
    try:
        rc, out = run(args)
        check(f"gj {' '.join(args[:2])}", rc == 0 and must in out)
    except Exception as e:
        check(f"gj {' '.join(args[:2])}", False, f"{type(e).__name__}: {e}")

# 4. 检索回归基准（命中数应稳定）
for args, key, minimum in [
    (["grep", "天地不仁", "--limit", "1", "--per", "1"], "文件", 200),
    (["grep", "仁", "--in", "=道德真经", "--limit", "1", "--per", "1"], "处", 5),
]:
    try:
        rc, out = run(args)
        nums = [int(t) for t in out.replace("，", " ").split() if t.isdigit()]
        ok = rc == 0 and any(n >= minimum for n in nums)
        check(f"回归 {args[1]}{' ' + args[3] if len(args) > 3 else ''}",
              ok, f"阈值 >={minimum}")
    except Exception as e:
        check(f"回归 {args[1]}", False, str(e))

# 5. 变体匹配是否生效（用全库范围，单本书可能用字统一看不出差异）
try:
    def hit_count(args):
        rc, out = run(args)
        for tok in out.replace("，", " ").split():
            if tok.isdigit():
                return int(tok)
        return 0
    n1 = hit_count(["grep", "群", "--limit", "1", "--per", "1"])
    n2 = hit_count(["grep", "群", "--limit", "1", "--per", "1", "--no-variants"])
    check("变体匹配生效（开启后文件数 > 关闭）", n1 > n2, f"{n2} → {n1} 个文件")
except Exception as e:
    check("变体匹配", False, str(e))

print("=" * 60)
if FAILED:
    print(f"失败 {len(FAILED)} 项: {', '.join(FAILED)}")
    sys.exit(1)
print("全部通过")
