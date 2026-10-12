# 样例目录

`test_offline.py` 会在这里生成测试用的样例视频 `sample_head.mp4`
（ffmpeg lavfi 三段拼接，960x540 / 25fps / 10 秒，灰度化以模拟水墨片）。

首次运行自动生成，可安全删除，下次会重新生成。为避免把二进制产物带进 Git，
已在根目录 .gitignore 中忽略 `*.mp4` 之外的运行目录（out/ seg/ grade/ preview/）。
