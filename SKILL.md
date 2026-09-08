---
name: 殆知阁离线检索
description: 离线全文检索 20587 部中国古典文献本地库（5.2 GB，佛藏/道藏/儒藏/史藏/子藏/集藏/诗藏/医藏/易藏/艺藏）。支持繁简异体字通搜、同书异名展开、帛书借字、词距过滤、章节定位。触发词：「离线检索古籍」「本地古籍库」「古籍库检索」「搜古籍库」「全唐诗」「佛藏」「道藏」「查这句话出自哪本书」。
user-invocable: true
tags: [古籍, 检索, 离线, 文献, 国学, 佛藏, 道藏, 儒藏, 史藏, 子藏, 集藏, 诗藏, 全文检索, 出处考证, 变体字, 殆知阁]
version: 1.0.0
---

# 殆知阁离线检索

检索本地 5.2 GB / 20587 部古籍，无需联网。

## 执行入口

```sh
S=/skills/殆知阁离线检索/scripts/gj.py
```

## 命令

| 命令 | 用途 |
|---|---|
| `python3 $S find 词` | 找书（书名/作者/分类/路径） |
| `python3 $S grep 词 [选项]` | 全文检索（8 核并行，3.3 秒） |
| `python3 $S chapter 书名 [章节] [--list]` | 章节定位与阅读 |
| `python3 $S show 路径\|书名 [起始行] [行数]` | 读原文 |
| `python3 $S meta 书名` | 元数据 + 外部链接 |
| `python3 $S links [--prov ctext]` | 外部参照表 |
| `python3 $S dup [--hash]` | 查重 |
| `python3 $S stats` | 库统计 |

## grep 选项

| 参数 | 说明 |
|---|---|
| `--in 书名[，书名]` | 限定书名；`=书名` 精确匹配；自动展开同书异名 |
| `--ctx N` | 上下文半径（默认 40） |
| `--limit N` / `--per N` | 显示条数 / 同文件条数上限（默认 30 / 3） |
| `--near N` | 多词最大距离（默认 30，`0` 关闭） |
| `--loan` | 追加帛书借字变体（**仅老子类**） |
| `--variants` / `--no-variants` | 繁简异体匹配（默认开） |
| `--files` / `--json` / `--all` | 只列文件 / JSON / 含 .sources |

## 执行规则

1. 先 `find` 定位书名 → 再 `grep --in 书名`（0.2 秒，比全库快 15 倍）。
2. 繁简异体匹配默认开启。搜「群」自动含「羣」（全库 11303 → 14210 文件）。
3. 多词默认要求相距 30 字内；误报多调小 `--near`，漏检调大。
4. 搜老子类帛书文本（含「声人」「亓」「胃」）加 `--loan`；其他典籍勿加。
5. 输出含「词距 >N 字的 M 处已过滤」时，需全量加 `--near 0`。
6. 长行超 400 字自动截断，看完整内容用 `show`。
7. 报出处格式：`书名` + 路径:行号 + 原文。

## 自检

```sh
python3 /skills/殆知阁离线检索/scripts/selftest.py
```

11 项检查，退出码 0 为通过。

## 数据位置

查找顺序：`$DZG_DATA` → `/skills/殆知阁离线检索/daizhigev20` → `/workspace/daizhigev20` → `~/daizhigev20`

当前使用：`/workspace/daizhigev20`

## 重建索引（数据更新后）

```sh
python3 /skills/殆知阁离线检索/scripts/build_index.py      # 22 秒
python3 /skills/殆知阁离线检索/scripts/build_variants.py
```
