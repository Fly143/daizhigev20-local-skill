#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从书籍 frontmatter 的 zh-hans / zh-hant 书名对自动生成变体字表。

原理：同一本书的简繁书名逐字对齐，不同之处就是「简繁对应」的实据。
本库有 16319 组可比对的简繁书名，比手工枚举可靠得多。

输出：variants.txt（每行一组，组内字以空格分隔，同组字互为变体）

关键处理：剔除「一简对多繁」造成的语义混淆。例如简体「复」同时对应
「復」(返回) 和「覆」(覆盖)，若合并则搜「复」会误中所有「覆盖」。
这类字在 SPLIT 中列出，不参与合并。

用法：python3 build_variants.py
"""
import os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import ROOT, read_frontmatter, VARIANT_GROUPS as HAND

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "variants.txt")

# 一简对多繁 / 语义不同的字：不与他字合并，避免误报
SPLIT = {
    "覆": "覆盖、颠覆，与「复/復」不同",
    "曆": "历法，与「历/歷」不同",
    "鬍": "胡须，与「胡」不同",
    "衚": "衚衕，与「胡」不同",
    "鐘": "乐器钟，与「锺/鍾」(姓氏)不同",
    "锺": "姓氏锺，与「鐘」不同",
    "彙": "类彙，与「匯」(汇合)不同",
    "讚": "赞美，与「贊」(赞助)不同",
    "鍊": "冶炼，与「煉」(炼)不同",
    "甯": "姓氏甯，与「宁/寧」不同",
    "著": "显著/著述，与「着」不同",
}


def collect_pairs():
    pairs = collections.Counter()
    n_pair = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            fm = read_frontmatter(os.path.join(dirpath, fn))
            if not fm:
                continue
            m = re.search(r"^title:[ \t]*\n((?:[ \t]+.*\n?)+)", fm, re.M)
            if not m:
                continue
            b = m.group(1)
            hs = re.search(r"^\s+zh-hans:\s*(.+)$", b, re.M)
            ht = re.search(r"^\s+zh-hant:\s*(.+)$", b, re.M)
            if not (hs and ht):
                continue
            a = hs.group(1).strip().strip("'\"")
            c = ht.group(1).strip().strip("'\"")
            if len(a) != len(c):
                continue
            n_pair += 1
            for x, y in zip(a, c):
                if x != y and "\u4e00" <= x <= "\u9fff" and "\u4e00" <= y <= "\u9fff":
                    pairs[(x, y)] += 1
    return pairs, n_pair


def main():
    pairs, n_pair = collect_pairs()
    print(f"可比对的简繁书名对: {n_pair}")
    print(f"提取到直接字对: {len(pairs)}")

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in pairs:
        union(a, b)
    for g in HAND:                      # 并入手工表（异体字、避讳字等）
        for ch in g[1:]:
            union(g[0], ch)

    groups = collections.defaultdict(set)
    for ch in list(parent):
        groups[find(ch)].add(ch)

    out = []
    for v in groups.values():
        if len(v) < 2:
            continue
        sub = collections.defaultdict(set)
        for ch in v:
            sub[SPLIT.get(ch, "__main__")].add(ch)
        for s in sub.values():
            if len(s) > 1:
                out.append(sorted(s))
    out.sort(key=lambda s: (-len(s), s))

    with open(OUT, "w", encoding="utf-8") as f:
        for s in out:
            f.write(" ".join(s) + "\n")

    print(f"生成 {len(out)} 组 -> {OUT}")
    print(f"已隔离「一简对多繁」字 {len(SPLIT)} 个：{', '.join(SPLIT)}")


if __name__ == "__main__":
    main()
