# ae-template-retrofit-kit

把「拿到一个现成 AE 模板 → 改成自己的内容 → 渲出来 → 验收交片」这条链路脚本化。

起源于一次真实的教学项目：把一套国风水墨片头模板改造成「新青年·芳草行」主题片头
（6 组分镜文案 + 6 张图 + 30 秒 + 1920×1080 PAL）。改造过程中踩的坑全部固化在这个
仓库里 —— 尤其是 `docs/PITFALLS.md`，建议动手前先读。

## 能干什么

| 环节 | 工具 | 说明 |
|---|---|---|
| 探模板 | `probe_project.py` / `summarize_project.py` / `probe_project2.py` | 只读，输出合成/图层/文字/素材结构与排版参数 |
| 批量改造 | `retrofit_project.py` | 配置驱动，换文案、换图、改标题、重排时间轴，**原模板不动** |
| 回读校验 | `verify_project.py` | 确认改对了，命中数为 0 会明确报出来 |
| 时间轴修复 | `fix_timeline.py` | 处理嵌套 precomp 的 `startTime` 偏移 |
| 工程调色 | `add_grade_layer.py` | 挂调色调整层，幂等 |
| 规格验收 | `spec_check.py` | 分辨率/帧率/时长/编码/像素格式，不通过 exit 1 |
| 节奏验收 | `segcheck.py` | 分段切换点检测，验证渲的是不是修正后的版本 |
| 色彩诊断 | `colstat.py` | 灰色占比、饱和度、色相分布、主色 |
| 目视验收 | `preview_mp4.py` | 抽帧联系表 |
| 零渲染调色 | `grade_test.py` | 三档滤镜对比图，选好直接用 ffmpeg 出片 |
| 交付辅助 | `gen_transcode_bat.py` / `gen_bgm_bat.py` | 生成双击即用的 bat，给用户免命令行 |
| 旁路常驻 | `persistent/ae_daemon.py` | 注入常驻任务，命令走文件队列，免反复启进程 |

## 快速开始

```bash
# 依赖
pip install -r requirements.txt
# ffmpeg / ffprobe 需在 PATH 中

# 环境自检（会报出 AE 路径、AE 是否在运行）
python scripts/ae/ae_bridge.py

# 1. 探模板
python scripts/ae/probe_project.py --project 模板.aep --out probe.json
python scripts/ae/summarize_project.py --probe probe.json --out summary.txt

# 2. 照抄配置，按 probe 结果改
cp config/example_content.json my_content.json

# 3. 改造（另存新工程）
python scripts/ae/retrofit_project.py --src 模板.aep --save 新工程.aep --config my_content.json

# 4. 校验
python scripts/ae/verify_project.py --project 新工程.aep
```

详细流程见 `docs/WORKFLOW.md`，坑位见 `docs/PITFALLS.md`，
验证记录见 `docs/VERIFICATION.md`。

## 目录结构

```
ae-template-retrofit-kit/
├── SKILL.md                     入口说明（触发场景 / 参数 / 示例）
├── README.md
├── LICENSE                      MIT
├── requirements.txt
├── config/
│   └── example_content.json     改造配置示例（含字段注释）
├── docs/
│   ├── WORKFLOW.md              完整流程
│   ├── PITFALLS.md              坑位手册（重点）
│   └── VERIFICATION.md          验证记录与结论
├── scripts/
│   ├── ae/                      AE 侧（依赖 ExtendScript 桥接）
│   │   ├── ae_bridge.py         桥接核心：探测 AE、投脚本、取结果
│   │   ├── probe_project.py     结构探测
│   │   ├── probe_project2.py    排版/缩放参数探测
│   │   ├── summarize_project.py 人读摘要
│   │   ├── retrofit_project.py  批量改造（配置驱动）
│   │   ├── verify_project.py    回读校验
│   │   ├── fix_timeline.py      时间轴修复
│   │   ├── probe_output_modules.py  输出模板探测
│   │   ├── add_grade_layer.py   工程调色层
│   │   ├── jsx/                 JSX 模板
│   │   └── persistent/          常驻服务（旁路通道）
│   ├── qc/                      成片验收
│   │   ├── spec_check.py
│   │   ├── segcheck.py
│   │   ├── colstat.py
│   │   └── preview_mp4.py
│   ├── grade/
│   │   └── grade_test.py        三档调色对比
│   └── utils/
│       ├── gen_transcode_bat.py
│       └── gen_bgm_bat.py
├── tests/
│   ├── test_offline.py          不依赖 AE 的全链路自检
│   ├── test_ae_link.py          AE 只读探针（默认不自动启动 AE）
│   └── sample/                  自检生成的样例素材
└── tools/
    └── clean_workspace.py       清理临时产物
```

## 环境要求

- Windows + After Effects（实测 2023 / 23.5；Mac 未测试）
- Python 3.9+
- `ffmpeg` / `ffprobe` 在 PATH
- AE 首选项勾选「允许脚本写入文件和访问网络」（否则脚本无法回写结果文件）

## 安全提示

- 改造脚本一律**先另存新工程再操作**，不会动原模板。
- 但 AE 侧的脚本仍会打开/保存工程，**动手前先备份你的 `.aep`**。
- `test_ae_link.py` 默认在 AE 未运行时直接跳过，不会擅自启动软件；
  需要自动拉起时显式加 `--allow-launch`。

## 许可证

MIT（见 LICENSE）。本仓库不含任何第三方模板、素材或受版权保护的内容，
示例配置里的文案均为演示用占位内容。
