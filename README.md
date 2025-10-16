# poco_u2 — UIAutomator2‑only Poco for AirtestIDE (CN/EN)

AirtestIDE 可对用例进行录制, 但底层使用 uiautomation1, 缺陷是无法在播放状态使用, 而新版本的 uiautomation2 没有这个问题, 因此将底层升级以支持视频播放器 app 的用例录制.


## 简介（CN）
`poco_u2` 是一个仅使用 UIAutomator2 的 Poco 驱动，面向 AirtestIDE 的嵌入式 Python 环境做了专门适配：
- 全面切换到 UIAutomator2，保持 Poco 的 API、返回数据结构和操作行为兼容。
- 坚持保留完整的 XML 属性（含 `package`），修复旧版本“包名丢失”问题。
- 启用非压缩层级（uncompressed hierarchy），在全屏播放场景下也能检测浮层/播放控件。
- 坐标归一化依据 `window_size`（与截图/IDE 高亮一致），解决中下区域“定位下偏”的问题。
- 内置第三方依赖自举逻辑（thirdparty 目录），无需改动 IDE 内置 Python。
- 兼容 Python 3.6 / 老 PIL：提供必要的兼容垫片（如 `UnidentifiedImageError`）。

> 使用时只需“替换 AirtestIDE 目录下的 `poco` 为本版本”。尽管工程名标注为 `poco_u2`，但在 IDE 中目录名仍须为 `poco`（IDE 固定加载）。

## 快速使用（CN）
1) 关闭 AirtestIDE。
2) 将本仓库的 `tmp\\poco` 整个复制并替换到：
   - `C:\\Download\\AirtestIDE-win-1.2.17\\AirtestIDE\\poco`
3) 一键安装依赖（联网）：
   - 运行：`C:\\Download\\git\\uni\\tmp\\poco\\setup_airtest_uia2_deps.bat`
   - 脚本会下载并安装所需依赖到 `poco\\thirdparty\\site-packages`，即使该目录为空也能一次拉齐。
4) 设备初始化（建议一次性在任意 Python 环境执行）：
   - `python -m uiautomator2 init`
5) 打开 AirtestIDE，脚本中保持原有用法：
   ```python
   from poco.drivers.android.uiautomation import AndroidUiautomationPoco
   poco = AndroidUiautomationPoco(device_id="192.168.100.112:5555")
   h = poco.agent.hierarchy.dump()
   ```

## 故障排查（CN）
- ImportError 依赖缺失：运行一键脚本，或确认 `poco\\thirdparty\\site-packages` 下存在 `uiautomator2/adbutils/apkutils2/whichcraft/xmltodict/cigam/progress/...`。
- `progress is not a package`：IDE 自带 `progress.py` 会遮蔽包名，驱动已内置规避与兜底垫片；仍异常时运行一键脚本确保 `progress` 包到位。
- `…uiautomator2-*.whl/.../assets/app-uiautomator.apk not found`：驱动已强制以“解压后的 uiautomator2 包”导入并屏蔽 `.whl`；若你手动加入 `.whl`，请删除之。
- 坐标漂移：本驱动使用 `window_size` 归一化，与 IDE 高亮一致；若仍偏移，请反馈 `window_size`、`device.info` 与目标节点 `bounds`。
- 全屏播放控件缺失：已使用 `dump_hierarchy(compressed=False)`；如仍缺失，请提供目标控件 `resource-id/text` 以便核对。
- 调试开关：设置环境变量 `POCO_THIRDPARTY_DEBUG=1` 可在日志输出被加入的依赖路径。

---

## Overview (EN)
`poco_u2` is a UIAutomator2‑only Poco driver tailored for AirtestIDE’s embedded Python:
- Switches fully to UIAutomator2 while preserving Poco’s API, action behavior and data shape.
- Preserves full XML attributes (incl. `package`) to fix legacy data loss.
- Dumps uncompressed hierarchy to keep overlay/controls visible during fullscreen playback.
- Normalizes coordinates using `window_size` to match screenshots/IDE overlays; fixes lower‑screen drift.
- Bundles a self‑bootstrap for third‑party deps (under `thirdparty`) — no need to modify IDE’s Python.
- Provides compatibility shims for Python 3.6 and old PIL.

> Usage is simple: replace AirtestIDE’s `poco` folder with this version. The project name is `poco_u2`, but the folder must be named `poco` under IDE.

## Quick Start (EN)
1) Close AirtestIDE.
2) Copy this repo’s `tmp\\poco` and replace at:
   - `C:\\Download\\AirtestIDE-win-1.2.17\\AirtestIDE\\poco`
3) One‑click dependency install (online):
   - Run: `C:\\Download\\git\\uni\\tmp\\poco\\setup_airtest_uia2_deps.bat`
   - This populates `poco\\thirdparty\\site-packages` with all required packages even from empty.
4) Device init (recommended once from any Python):
   - `python -m uiautomator2 init`
5) Use in scripts (unchanged):
   ```python
   from poco.drivers.android.uiautomation import AndroidUiautomationPoco
   poco = AndroidUiautomationPoco(device_id="192.168.100.112:5555")
   h = poco.agent.hierarchy.dump()
   ```

## Troubleshooting (EN)
- ImportError deps: run the one‑click script, or check `poco\\thirdparty\\site-packages` for `uiautomator2/adbutils/apkutils2/whichcraft/xmltodict/cigam/progress/...`.
- `progress is not a package`: the IDE’s flat `progress.py` can shadow the real package; the driver mitigates this and shims `progress.bar.Bar`. Ensure the package is present by running the script.
- `…uiautomator2-*.whl/.../assets/app-uiautomator.apk not found`: driver forces file‑based import of `uiautomator2` and strips `.whl`. Remove stray wheels if manually added.
- Coordinate drift: driver uses `window_size`; if a mismatch persists, share `window_size`, `device.info`, and XML `bounds`.
- Playback controls missing: driver uses `dump_hierarchy(compressed=False)`; if still missing, share the `resource-id/text` so we can inspect.
- Debugging: set `POCO_THIRDPARTY_DEBUG=1` to log vendor paths added.

## Notes
- Do NOT vendor Pillow; the driver works with IDE’s built‑in PIL (shims provided for missing symbols).
- This driver does not change Poco’s external API — only the backend and robustness.
- For detailed adoption notes and fixes, see `docs/POCO_UIA2_ADOPTION_NOTES.md`.

