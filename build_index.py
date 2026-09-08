#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 daizhigev20 的 YAML frontmatter，生成 index.tsv
列: 相对路径 | 书名 | 分类 | 作者 | 字节数 | 外部链接
用法:
  python3 build_index.py            # 全量重建
  python3 build_index.py --check    # 只报告缺元数据的文件，不写盘
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import ROOT, IDX, parse_meta, links_to_str, read_frontmatter

def main():
    check = "--check" in sys.argv
    rows, no_fm, no_author, no_title = [], [], [], []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel  = os.path.relpath(full, ROOT)
            fm   = read_frontmatter(full)
            title, cat, author, links = parse_meta(full)
            if not fm:
                no_fm.append(rel)
            elif not author:
                no_author.append(rel)
            if not fm or "title:" not in fm:
                no_title.append(rel)
            rows.append((rel, title, cat, author,
                         str(os.path.getsize(full)), links_to_str(links)))

    print(f"扫描 {len(rows)} 部")
    print(f"  无 frontmatter   : {len(no_fm)}")
    print(f"  无 author 字段   : {len(no_author)}")
    print(f"  无 title 字段    : {len(no_title)}")
    if no_fm:
        for r in no_fm[:10]:
            print(f"    - {r}")

    if check:
        return

    with open(IDX, "w", encoding="utf-8") as f:
        for r in rows:
            f.write("\t".join(r) + "\n")
    print(f"索引完成 -> {IDX}")

    n_link = sum(1 for r in rows if r[5])
    print(f"  含外部链接       : {n_link} 部")

if __name__ == "__main__":
    main()
