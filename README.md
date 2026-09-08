# 殆知阁离线检索 · Skill

对 [daizhige-org/daizhigev20](https://github.com/daizhige-org/daizhigev20) 做**离线全文检索**的工具集。
支持繁简异体字通搜、同书异名展开、帛书借字、词距过滤、章节定位。


---

## 〇、先获取数据（必须）

本工具**不含古籍正文**，需先下载数据（约 5.2 GB）。

```sh
# 下载到工具同级目录（推荐）
cd /skills/殆知阁离线检索
git clone -b data --depth 1 https://github.com/daizhige-org/daizhigev20.git
```

数据来源：[daizhige-org/daizhigev20](https://github.com/daizhige-org/daizhigev20)
（原始作者 [garychowcmu](https://github.com/garychowcmu/daizhigev20)）。

**数据目录查找顺序**（自动探测，找到即用）：

1. 环境变量 `$DZG_DATA`
2. `/skills/殆知阁离线检索/daizhigev20` ← 推荐位置
3. `/workspace/daizhigev20` ← 当前环境使用
4. `~/daizhigev20`

也可以放到任意位置并用环境变量指定：

```sh
export DZG_DATA=/path/to/daizhigev20
```

下载后确认索引可用：

```sh
python3 /skills/殆知阁离线检索/scripts/selftest.py
```

若数据更新过，重建索引：`python3 scripts/build_index.py`（22 秒）。

## 一、适用场景

- 需要**繁简/异体字通搜**（1053 组变体）
- 需要**同书异名展开**（搜「老子」能命中《道德真经》）
- 需要帛书借字、词距过滤、章节定位
- 需要**离线可用**、结果无上限

不适用：环境没有本地数据目录时。

## 二、依赖

```
/skills/殆知阁离线检索/
├── SKILL.md          给 AI 的执行指令
├── README.md         本文件
└── scripts/
    ├── gj.py         主命令（8 个子命令）
    ├── lib.py        frontmatter 解析 + 变体表
    ├── index.tsv     索引（20587 行 × 6 列，2.8 MB）
    ├── variants.txt  变体表（1053 组）
    ├── build_index.py    重建索引
    ├── build_variants.py 重建变体表
    └── selftest.py   自检
```

数据目录查找顺序：

1. 环境变量 `$DZG_DATA`
2. 与 skill 同级：`/skills/殆知阁离线检索/daizhigev20`
3. `/workspace/daizhigev20` ← 当前使用
4. `~/daizhigev20`

## 三、使用

```sh
S=/skills/殆知阁离线检索/scripts/gj.py

python3 $S find    老子              # 找书
python3 $S grep    天地不仁           # 全库检索
python3 $S grep    仁 --in 老子       # 限定书名（自动展开异名）
python3 $S grep    仁 --in =道德真经   # = 精确书名
python3 $S grep    圣人 --in 简帛 --loan   # 帛书借字（声人）
python3 $S grep    天地 刍狗          # 多词 AND + 词距过滤
python3 $S chapter 道德真经 --list    # 列章节
python3 $S chapter 道德真经 虚用章    # 读某一章
python3 $S meta    道德真经           # 元数据 + 外部链接
python3 $S dup --hash               # 查重
```

## 四、检索特性

**变体字匹配（默认开）**
搜「群」带出「羣」：全库 11303 → 14210 个文件。1053 组变体由
16319 组简繁书名对自动提取，已隔离 11 个「一简对多繁」字（如 复/復/覆）。

**同书异名展开**
`--in 老子` 自动展开为「老子/道德经/道德真经/五千文」。否则会漏掉《道德真经》正文
（书名里没有「老子」二字）。

**词距过滤**
多词默认要求相距 30 字内。搜「天地 刍狗」若不做过滤，44% 是同一长行里的巧合
（最远相距 803 字）。`--near N` 可调，`--near 0` 关闭。

**帛书借字（`--loan`）**
搜「圣人」带出「声人」：简帛老子校正 26 → 36 处。**仅老子类文献成立**，其他典籍勿用。

## 五、性能

| 操作 | 耗时 |
|---|---|
| `find` / `meta` / `show` / `chapter` | 0.1–0.2 秒 |
| `grep --in 书名` | 0.2 秒 |
| `grep` 全库（8 核并行） | 3.3 秒 |
| `grep` 全库（串行基线） | 10.6 秒 |
| 重建索引 | 22 秒 |

## 六、自检

```sh
python3 /skills/殆知阁离线检索/scripts/selftest.py
```

11 项检查：数据目录、索引、变体表、索引条目数、外部链接、子命令、回归基准、变体匹配生效。
退出码 0 为通过。

## 七、已知限制

| 限制 | 实情 |
|---|---|
| 无语义检索 | 只能字面/变体匹配 |
| `author` 缺失 11889 部 | 仅 217 部能从书名括号补出 |
| 变体表非完整繁简表 | 1053 组来自书名用字，正文生僻异体可能漏 |
| `--loan` 仅老子类成立 | 47 组借字，其他典籍会误伤 |
| 全库 3.3 秒 | 5.2 GB 顺序读的物理下限 |


## 八、与本地库项目的关系

**两个独立项目，互不依赖。**

| | WEB库工具（在线）[daizhigev20-web-skill](https://github.com/Fly143/daizhigev20-web-skill)) | 本 Skill（离线）|
|---|---|---|
| 位置 | `/skills/殆知阁在线检索/` | `/workspace/kb/` |
| 依赖 | 网络 | 5.2 GB 本地数据 |
| 全库检索 | 2.4–3.1s | 3.3s |
| 繁简/异体匹配 | ❌ | ✅ 1053 组 |
| 帛书借字 | ❌ | ✅ |
| 词距过滤 | ❌ | ✅ |
| 章节定位 | ❌ | ✅ |
| 结果上限 | cap 1000 | 无 |

按用户环境择一即可，也可同时用做交叉验证。

