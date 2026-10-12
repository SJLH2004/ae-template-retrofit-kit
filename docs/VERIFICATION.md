# 验证记录

打包前在**独立临时目录**中加载并完整执行了一次（把整个包复制到一个干净目录里跑，
确认没有隐藏依赖、没有引用源项目的路径）。

验证日期：2026-10-12
验证环境：Windows / Python 3.13 / After Effects 2023 (23.5) / ffmpeg 7.x / node 22

## 一、离线自检（ffmpeg 全链路）— 实跑通过 11/11

```
cd <包目录>
python tests/test_offline.py
```

| # | 项目 | 结果 | 说明 |
|---|---|---|---|
| 1 | 生成样例素材 | PASS | ffmpeg lavfi 三段拼接，960×540 25fps 10s，灰度化模拟水墨片 |
| 2 | spec_check | PASS | 规格校验通过（含 `--json-out`） |
| 3 | segcheck | PASS | 检测到切换点 `[3, 6]`，与素材设计一致 |
| 4 | colstat | PASS | 灰度占比 / 饱和度 / 主色统计正常输出 |
| 5 | grade_test | PASS | 三档调色对比图生成 |
| 6 | preview_mp4 | PASS | 联系表生成 |
| 7 | 生成 bat + GBK 校验 | PASS | 中文路径写入 bat 后能被 GBK 正确解码 |
| 8 | 全部 py 语法编译 | PASS | `py_compile` 逐个编译 |
| 9 | jsx 纯 ASCII | PASS | 无 >126 的字节 |
| 10 | 无个人信息残留 | PASS | 扫描全包无用户名 / 工作目录 / 项目路径 |
| 11 | 序列化往返（需 node） | PASS | Windows 路径、引号、换行、中文、嵌套结构均正确往返 |

`RESULT: PASS`

## 二、桥接层序列化逻辑 — 实跑通过

ExtendScript 是 ES3 没有 `JSON` 对象，`ae_bridge` 靠模板内置的 `__str()` 回传结果。
把这段逻辑抽出来用 node 跑复杂数据往返：

```
{"winpath":"C:\\projects\\demo.aep","quote":"he said \"hi\"","backsl":"a\\b",
 "newline":"line1\nline2","cjk":"总合成 标题","empty":"","num":-12.5,
 "nul":null,"arr":[1,"two",false],"nested":{"a":{"b":"deep"}}}
```

全部字段被 Python `json.loads` 正确读回且值不变。**Windows 路径的反斜杠不会被破坏**
（这点很关键，返回结果里大量出现工程路径）。

## 三、JSX 语法 — 静态检查通过

用 `node --check` 校验了三个 JS 文件：

- `scripts/ae/jsx/add_grade_layer.jsx` — syntax OK
- `scripts/ae/persistent/install_daemon.jsx` — syntax OK
- `ae_bridge.TEMPLATE` 生成的脚本 — syntax OK

## 四、AE 侧脚本 — 本次**未**实机运行，原因说明

验证时 AE 未在运行，且**没有自动拉起它**：
用 `-r` 拉起 AE 会弹出主界面，在自动化场景里不受欢迎（本次开发中就出现过一次
"上次会话非正常退出"的崩溃恢复框，虽然不影响工程文件，但会打断使用者）。

因此 AE 侧改为两项保障：

1. **静态保障**：语法检查（第三节）+ 参数化脚本的 `--help` 可用性。
2. **历史实测**：这套脚本的全部 AE 逻辑都来自 2026-10-12 的真实项目改造
   （水墨片头 → 新青年·芳草行）：工程探测、6 组文案替换、6 张图替换+缩放补偿、
   时间轴修正、回读校验、调色层挂载，全部在 AE 2023 上跑通过。打包时做的是
   **参数化重构**（把写死的路径/文案抽成配置），JSX 的 AE 操作逻辑本身未改动。

**首次使用时请自行验证一次**（AE 打开状态下，不会自动启动软件）：

```bash
python tests/test_ae_link.py            # AE 没开会提示 SKIP
python tests/test_ae_link.py --allow-launch   # 明确允许时才自动拉起 AE
```

它会打印 AE 版本、当前工程名、合成数，以及 `hasJSON`（AE 是否内置 JSON 对象）。
返回值正常即说明桥接层在当前机器上可用。

## 五、已知限制

- **仅 Windows 验证过**：Mac 上 `find_ae()` 的路径规则、`-r` 的行为都未测试。
- **模板强相关**：`retrofit_project.py` 依赖模板的合成命名与占位文字关键词。
  换模板必须先跑 `probe_project.py` 探明结构，再填 `markers`，否则命中数为 0。
- **常驻服务未实机验证**：`persistent/ae_daemon.py` 依赖 `app.scheduleTask`，
  语法与逻辑静态检查通过，但没在真实 AE 会话里长跑过，标记为实验性。
- **AE 2023 的 Color Balance 只有 3 个滑块**，不是预期的"阴影/中间调/高光"三区。
  需要分区染色时，请在 ffmpeg 侧用 `colorbalance` 滤镜完成。
- **Hue/Saturation 效果在本机加不上**（三种 matchName 都失败），所以工程调色层
  只做整体色偏，饱和度交给 ffmpeg。
