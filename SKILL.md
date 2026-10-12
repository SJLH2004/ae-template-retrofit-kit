---
name: ae-template-retrofit-kit
description: AE 模板工程自动化改造与出片验收工具链。用于把现成的 After Effects 模板工程（水墨、国风、片头、图文分镜类）按配置批量替换文案与图片、重排时间轴、加调色层，并对渲染出的成片做规格校验、分段节奏检测与色彩诊断。触发词：改 AE 模板、批量替换文案、片头改造、换图、调色、成片验收、规格校验、色彩诊断、ffmpeg 转码打包。
---

# AE 模板改造与出片验收工具链

把「拿到一个现成 AE 模板 → 改成自己的内容 → 渲出来 → 验收交片」这条链路脚本化。
所有脚本都是命令行工具，靠配置文件驱动，不依赖任何写死的路径或项目。

## 适用场景

- 教学/工作室批量改造模板片头（换文案、换图、改总时长）
- 成片交片前做规格与内容自检（尺寸/帧率/时长/分段节奏/色彩）
- 片头"颜色不对"时做零渲染调色（不用重新生成素材、不用重新渲染 AE）
- 需要反复复用同一套改造流程，避免每次手写 ExtendScript

## 输入输出

| | 说明 |
|---|---|
| 输入 | AE 模板工程 `.aep`、内容配置 `json`、替换图片若干、渲染出的成片（mov/mp4） |
| 输出 | 改造后的新 `.aep`、工程结构探测 `json`、验收报告（规格/节奏/色彩）、调色成品 mp4、一键转码/配乐 bat |

**原模板文件始终不会被修改**——改造脚本一律先 `另存为` 新工程再操作。

## 依赖

- Windows + After Effects（实测 2023 / 23.5），Mac 未测试
- Python 3.9+，包见 `requirements.txt`：`opencv-python`、`numpy`、`pillow`
- `ffmpeg` / `ffprobe` 在 PATH 中
- AE 首选项需勾选「允许脚本写入文件和访问网络」

## 完整流水线（按顺序）

```bash
# 0. 环境自检
python scripts/ae/ae_bridge.py

# 1. 探明模板结构（关键：先搞清楚占位文字的关键词、合成命名、时间轴）
python scripts/ae/probe_project.py --project 模板.aep --out probe.json
python scripts/ae/summarize_project.py --probe probe.json --out summary.txt
python scripts/ae/probe_project2.py --project 模板.aep --out probe2.json

# 2. 填配置：照抄 config/example_content.json，按 probe 结果改 markers/合成名
#    改完先跑一次轻量验证，确认 markers 命中

# 3. 改造（另存新工程，原模板不动）
python scripts/ae/retrofit_project.py --src 模板.aep --save 新工程.aep --config content.json

# 4. 回读校验
python scripts/ae/verify_project.py --project 新工程.aep --out verify.json

# 5. 时间轴不对时单独修（startTime 是坑，见 docs/PITFALLS.md）
python scripts/ae/fix_timeline.py --project 新工程.aep --main 总合成 --split 24.8 --total 30

# 6. 出片（AE 内渲染；如 H.264 直出失败，渲 QuickTime/序列）
#    出片前确认本机有哪些输出模板：
python scripts/ae/probe_output_modules.py --project 新工程.aep

# 7. 成片验收
python scripts/qc/spec_check.py --video 成片.mp4 --expect 1920x1080@25 --min-duration 15
python scripts/qc/segcheck.py   --video 成片.mp4 --out-dir ./seg
python scripts/qc/colstat.py    --frames-dir ./seg
python scripts/qc/preview_mp4.py --video 成片.mp4 --times 0.5,3,8,14,19,27
```

## 常用脚本参数

| 脚本 | 关键参数 | 说明 |
|---|---|---|
| `probe_project.py` | `--project` `--out` | 只读探测全部合成/图层/文字/素材 |
| `probe_project2.py` | `--main` `--text-prefix` `--img-prefix` `--group-count` | 探缩放与排版参数 |
| `retrofit_project.py` | `--src` `--save` `--config` | 批量改造，配置驱动 |
| `verify_project.py` | `--project` `--out` | 回读确认改对了 |
| `fix_timeline.py` | `--split` `--total` `--pre1` `--pre2` | 修正 precomp 衔接 |
| `add_grade_layer.py` | `--mode gamma\|global` `--gammas` `--cb` `--layer` | 挂调色层，幂等。gamma 模式端点不动只染中间调（推荐）；global 是全局偏移会连白底一起染 |
| `spec_check.py` | `--expect WxH@fps` `--min-duration` | 规格校验，不通过 exit 1 |
| `segcheck.py` | `--step` `--threshold` | 分段切换点检测 |
| `colstat.py` | `--video` 或 `--frames-dir` | 灰色占比/饱和度/主色 |
| `preview_mp4.py` | `--times` `--cols` | 抽帧联系表 |
| `grade_test.py` | `--presets light,mid,heavy` | 三档调色对比图 |
| `gen_transcode_bat.py` | `--src` `--dst` `--out` | 生成双击转码 bat |
| `gen_bgm_bat.py` | `--video` `--out` | 生成拖拽配乐 bat |

## 零渲染调色（画面颜色不符合主题时）

画面大部分是灰色时，**单纯提饱和度无效**（灰色提饱和还是灰）。必须先用
`colorbalance` 按明度分区打破 R=G=B：

```bash
# 1) 出三档对比图挑选
python scripts/grade/grade_test.py --video 成片.mp4 --times 3,9,20,27 --out-dir ./grade

# 2) 用选定档位全片输出（mid 档示例）
ffmpeg -y -i 成片.mp4 \
  -vf "colorbalance=rs=-0.15:gs=0.20:bs=0.10:rm=-0.08:gm=0.16:bm=0.05:rh=0.03:gh=0.01:bh=-0.05,eq=saturation=1.35:contrast=1.06" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart -an 青绿版.mp4

# 3) 同步把工程配色改掉，以后重渲不用再调（gamma 模式：端点不动，只染中间调）
python scripts/ae/add_grade_layer.py --project 新工程.aep --mode gamma --gammas 0.90,1.12,1.00
```

青绿设色（《千里江山图》思路）配色参考：石绿 `#1E7A5A`、竹青 `#3B9E6F`、
石青 `#2A6F8E`、赭石 `#C98A4B`、墨青 `#22343A`，朱砂 `#B03A2E` 作标题点缀。

## 常驻服务（可选，旁路通道）

每次投脚本都要走一遍 `-r`，AE 没开时还要拉起进程。需要频繁交互时可注入常驻任务：

```bash
python -c "import sys; sys.path.insert(0,'scripts/ae/persistent'); import ae_daemon; print(ae_daemon.submit(\"RESULT.layers = app.project.activeItem.numLayers\"))"
```

注入后命令走文件队列，AE 里定时器每 500ms 检查一次，来回更快也不会反复启进程。
依赖 `app.scheduleTask`，AE 重启后需要重新注入一次。

## 坑位清单

**务必先读 `docs/PITFALLS.md`**，里面记了十几个实测踩出来的坑，包括：

- ExtendScript 是 ES3，**没有 JSON 对象**
- `addSolid` 新图层已经在最顶层，再 `moveBefore` 会报错
- 嵌套 precomp 的 `startTime` 可能是负值，只改 `outPoint` 会画面偏移
- ffmpeg 在某些参数组合下读不了中文路径
- 给用户的 bat 含中文路径时必须用 GBK 编码写盘

## 验证状态

见 `docs/VERIFICATION.md`：ffmpeg 侧全链路已实跑通过；AE 侧通过只读探针验证
（AE 未运行时默认跳过，不会擅自启动软件）。
