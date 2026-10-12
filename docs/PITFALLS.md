# 坑位手册（每一条都是实测踩出来的）

## ExtendScript / AE 侧

### 1. ExtendScript 是 ES3，没有 JSON 对象
AE 2023 (23.5) 实测：`JSON.stringify` 会抛 `"JSON"未定义`。

早期版本在桥接模板里用 `JSON.stringify(RESULT)` 回传结果，写盘被外层的
`catch` 静默吞掉，文件被创建但**内容为空**，Python 侧表现为"一直等不到结果"，
很容易误判成"AE 卡住了"。

**解法**：桥接模板内置手写序列化 `__str()`（`scripts/ae/ae_bridge.py` 的 TEMPLATE）。
不要改用 `JSON.stringify`。

### 2. `.jsx` 必须是纯 ASCII
JSX 里出现中文，ExtendScript 会按系统编码（GBK）解析，轻则乱码，重则啃碎语法。

**解法**：`ae_bridge.py` 的 `cjk_escape()` 会把正文里的非 ASCII 自动转成 `\uXXXX`。
自己写 JSX 文件时也一样，注释和字符串都不能有中文。

### 3. `addSolid` 出来的图层已经在最顶层
新建的调整层默认就是 layer 1，再执行 `moveBefore(comp.layer(1))` 是"移到它自己前面"，
直接抛 `无法将图层进行前后移动`。

**解法**：`if (comp.layer(1) !== adj) adj.moveBefore(comp.layer(1));`

### 4. 匹配总合成要卡时长区间
模板工程里常有同尺寸的内层 precomp。只按 `1920x1080` 匹配，会先命中内层
（比如时长 36.64s 的分镜合成）而不是总合成（30s）。

**解法**：`duration >= 29.5 && duration <= 30.5` 这样卡区间，或显式按名字找。

### 5. 嵌套 precomp 的 `startTime` 可能是负值
模板为了跳过开头，会把嵌套层的 `startTime` 设成 -6.56。改造时只改 `outPoint`
不改 `startTime`，画面就会整体偏移，第一组内容被跳过。

**解法**：`fix_timeline.py` 显式设置 `startTime` / `inPoint` / `outPoint` 三者。

### 6. `replaceSource` 后必须做缩放补偿
新素材分辨率和旧的不一致时，替换后画面会突然变大或变小。
**解法**：`ratio = 旧源宽 / 新源宽`，然后 `scale *= ratio`。

### 7. 效果 matchName 不能靠猜
`ADBE HUE Saturation` / `ADBE Hue/Saturation` / `ADBE Hue Saturation` 三个候选
在 AE 2023 上**全部无法添加**。另外 `ADBE Color Balance` 实测只有 3 个滑块
（红/绿/蓝平衡），不是"阴影/中间调/高光"的 9 滑块版本。

**解法**：加效果前先 `try/catch` 兜住，遍历 `numProperties` 打印真实参数名再设值，
不要照抄网上教程的 matchName。

### 8. `-r` 只在已运行的实例里跑；AE 没开时要用 `-noui`
- AE 已运行：`-r` 直接投给现有实例。
- AE 没运行：`-r` 会拉起 AE 并弹主界面（含崩溃恢复框），自动化场景很烦。
  **加 `-noui` 即可无界面执行**：`AfterFX.exe -noui -r script.jsx`。
- 判断依据是 `ae_running()`。**不要依赖 `tasklist`**——它在受限环境/精简系统上
  常被禁用，`ae_bridge` 已改用 Toolhelp32 API 直接枚举进程。

### 9. `-r` 同时只允许一个脚本在跑
结果是否成功的**唯一可靠依据是结果 JSON 有没有被写出来**，不要看进程是否退出。

### 10. 渲染一律走临时副本
不要在 PR/AE 正在引用的 `.aep` 上直接渲染，曾经丢过未保存的合成。
先另存副本再渲。

### 11. H.264 输出模块在本机恒失败
错误 `-1610153423`。出片走 QuickTime / DNxHR / TIFF 序列，再用 ffmpeg 编码。

### 12. 本机不一定有 PNG 序列输出模板
用 `om_keyword="PNG"` 会落到「多机序列」= PSD 序列（约 4MB/帧）。
出片前先跑 `probe_output_modules.py` 看本机到底有哪些模板。

## ffmpeg / 命令行侧

### 13. ffmpeg 在部分参数组合下读不了中文路径
同一条命令，加 `-ss` / `-frames:v` 后报 `Illegal byte sequence`，
不加却能正常读。

**解法**：复制/硬链接一份 ASCII 文件名的副本给 ffmpeg 用，处理完再改回中文名。
另外注意：8.3 短路径名（`GetShortPathNameW`）在很多卷上是关闭的，
硬链接也需要 NTFS，都不是通用解法。

### 14. 给用户的双击 bat：含中文路径必须用 GBK 编码写盘
UTF-8 写的 bat，CMD 会按 GBK 逐字节解析，命令被啃碎（出现过 `rrorlevel` 这种半截词）。

- **内容不含中文**（纯英文提示）：用 ASCII 写，最稳。
- **内容含中文路径**：必须 `encoding="gbk"` 写盘。
- 文件名可以是中文，只有内容受编码影响。

### 15. bat 里提权检测要用完整性级别
不要用 `net session`（依赖 Server 服务，常被禁用导致误判）：

```bat
whoami /groups | findstr /c:"S-1-16-12288" >nul 2>&1
if errorlevel 1 ( powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs" )
```

## 图像处理侧

### 16. `cv2.imread` 读不了中文路径
**解法**：`cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)`

### 17. 灰色画面提饱和度无效
画面 85% 是纯灰时，`eq=saturation=2.0` 也毫无变化——灰色提饱和还是灰。
必须先用 `colorbalance` 按明度分区打破 R=G=B，再提饱和。

### 18. 像素比对一律用 2-D 配准
比对两张图是否只是平移/缩放时，用 SIFT 仿射或相位相关，**resp > 0.99 才采信**。
一维剖面法在纯平移时会采样越界返回 None，产出过"3.6% 拉伸"的假阳性结论。

### 19. 判断操作成功与否，以磁盘实际状态为准
不要只信命令回显或报错码。
