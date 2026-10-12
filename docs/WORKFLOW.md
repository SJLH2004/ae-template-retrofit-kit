# 工作流详解

## 总览

```
模板 .aep ──probe──> 结构 JSON ──> 摘要（人读）
                        │
                        └─> 填 content.json（文案/图片/时间轴）
                                  │
                                  v
                        retrofit_project.py ──> 新工程 .aep
                                  │
                                  v
                        verify_project.py（回读确认）
                                  │
                        fix_timeline.py（时间轴不对时）
                                  │
                                  v
                        AE 内渲染 ──> 成片 mov/mp4
                                  │
                        ┌─────────┴──────────┐
                        v                    v
                 spec_check.py         grade_test.py
                 segcheck.py           （配色不对时零渲染调色）
                 colstat.py
                 preview_mp4.py
```

## 第一步：探模板（不要跳过）

改造前必须搞清三件事，否则配置文件填不出来：

1. **占位文字的关键词** —— 脚本靠关键词识别"哪个文字层该改成什么"。
   跑 `probe_project.py` 看各文字层当前内容，从中挑出稳定的识别词。
2. **合成命名规律** —— `文字合成01~06`、`图片01~06`、`标题`、`总合成`、`1`、`2`。
   不同模板命名不同，靠 `--text-prefix` / `--img-prefix` / `--main` 适配。
3. **时间轴结构** —— 总合成里嵌套层的 `startTime` / `inPoint` / `outPoint`。

```bash
python scripts/ae/probe_project.py --project 模板.aep --out probe.json
python scripts/ae/summarize_project.py --probe probe.json --out summary.txt
```

`summary.txt` 是人读摘要，看它填配置最快。

## 第二步：填 content.json

照抄 `config/example_content.json`，重点改这几块：

```jsonc
{
  "comp_names": { "main": "总合成", "text_prefix": "文字合成", "img_prefix": "图片", ... },
  "markers": {                 // 原模板占位文字的识别关键词
    "l1": "江南",              // 横排两字词
    "updown": ["镇", "古"],    // 竖排上下字
    "pinyin": ["XI", "TANG"],  // 拼音行
    "poem": "船上管弦",        // 诗句行
    "title_main": "会议江南",  // 落版主标题
    "ending": "魅力江南"       // 结尾语
  },
  "title_y": [380, 611, 819, 1020],   // 竖排各字从上到下的 y 坐标
  "timeline": { "split": 24.8, "total": 30 },
  "groups": [ ... 每组文案 ... ],
  "imgs": [ ... 替换图路径 ... ]
}
```

**`title_y` 的取值方法**：`probe_project2.py` 会输出标题合成里每个文字层的
`pos`。取竖排那几个字的 y 值，按从大到小排列填进去。竖排字数少于 y 坐标个数时，
多出来的字会被自动停用（第 4 个字那种）。

## 第三步：改造与校验

```bash
python scripts/ae/retrofit_project.py --src 模板.aep --save 新工程.aep --config content.json
python scripts/ae/verify_project.py  --project 新工程.aep --out verify.json
```

`retrofit` 输出里每组会带一个数字，表示命中并改掉的图层数：

```
"groups": ["文字合成01:5", "文字合成02:5", ...],
"imgs":   ["图片01:1", "图片02:1", ...],
"totalDur": 30
```

**数字是 0 或 `NOTFOUND` 就说明 markers 没命中**，回去核对 probe 结果。

## 第四步：出片

AE 内渲染。若 H.264 直出失败（本机常见），渲 QuickTime / 图像序列，再用 ffmpeg 转：

```bash
python scripts/utils/gen_transcode_bat.py --src 成片.mov --dst 成片.mp4 --out 转MP4.bat
# 用户双击 转MP4.bat 即可
```

需要配乐：

```bash
python scripts/utils/gen_bgm_bat.py --video 成片.mp4 --out 加配乐.bat
# 把音乐文件拖到 bat 上
```

## 第五步：验收

```bash
python scripts/qc/spec_check.py --video 成片.mp4 --expect 1920x1080@25 --min-duration 15
python scripts/qc/segcheck.py   --video 成片.mp4 --out-dir ./seg --threshold 0.18
python scripts/qc/colstat.py    --frames-dir ./seg
python scripts/qc/preview_mp4.py --video 成片.mp4 --times 0.5,3,8,14,19,27
```

怎么读结果：

- **spec_check**：不通过直接 exit 1，逐项列出实测 vs 期望。
- **segcheck**：输出的切换点应该和设计的时间轴吻合。吻合说明渲的是修正后的版本；
  不吻合（比如开头就是第二组内容）说明渲了旧版或时间轴没修对。
- **colstat**：灰色占比高 = 画面发灰；彩色像素的色相分布能看出主色调跑没跑偏。
- **preview_mp4**：出一张联系表供人眼确认。

## 第六步（可选）：零渲染调色

画面颜色不符合主题时，不用重新生成素材、不用重渲 AE：

```bash
python scripts/grade/grade_test.py --video 成片.mp4 --times 3,9,20,27 --out-dir ./grade
# 看 grade_compare.png 选档（行=档位，列=时间点）
```

选定后用同样滤镜串全片输出，同时把工程配色也改掉，以后重渲不用再调：

```bash
python scripts/ae/add_grade_layer.py --project 新工程.aep --cb -12,16,8
```

`--cb` 三个值对应红色/绿色/蓝色平衡（-100..100）。想更绿就加大第二个值、
减小第一个值。这个图层是幂等的，重复运行会先删旧层再重建。

## 关于原模板

全程不修改原模板文件：`retrofit_project.py` 第一步就是 `另存为` 新工程。
