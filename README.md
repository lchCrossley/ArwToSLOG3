# ARW → Sony S-Gamut3.Cine / S-Log3

把 Sony A7C II 的 `.ARW` 照片转换为 **16-bit S-Gamut3.Cine / S-Log3 TIFF**。使用 Sony 公开的色彩定义，不复刻相机内部的视频处理。

## 操作方法（Windows，新手版）

准备：电脑已经安装 **Python 3.11 或更新版本**，并且在命令行输入 `python --version` 能看到版本号。第一次安装依赖需要联网。**不用提供 GitHub 账号、密码或任何密钥。**

1. 打开[项目 GitHub 页面](https://github.com/lchCrossley/ArwToSLOG3)，点击绿色 **Code** → **Download ZIP**，下载后解压到一个普通文件夹（不要在压缩包预览窗口里运行）。已经会用 Git 的人也可以执行 `git clone https://github.com/lchCrossley/ArwToSLOG3.git`。
2. 打开解压后的项目文件夹，双击 `setup_windows.cmd`。它会在这个文件夹里创建专用的 `.venv` 虚拟环境，并安装本工具需要的库；首次运行请等待安装结束。看到 `Setup complete` 才算成功。这个过程不会把依赖安装进你原有的 Python 环境。
3. 找到要转换的 `.ARW` 文件，把**一个文件**拖到项目文件夹里的 `convert_windows.cmd` 上。黑色窗口会显示处理结果，按任意键关闭。
4. 成功后，在原 `.ARW` 所在文件夹找同名的 `照片名_SLog3.tif`。原 `.ARW` 不会被修改；如果同名 TIFF 已存在，程序会报错并拒绝覆盖。

如果不想使用虚拟环境，也可把依赖安装到你当前正在使用的 Python 环境。在项目文件夹打开 PowerShell，依次执行：

```powershell
python -m pip install -e .
python arw_to_slog3.py "C:\照片\input.ARW" "C:\照片\output.tif"
```

这条路线可能影响现有 Python 环境中的其他包，通常建议使用第 2 步的虚拟环境。命令里的路径只是示例，必须换成你自己的实际文件路径；路径有空格时保留引号。默认曝光补偿是 **0 EV**，工具不会自动提亮。想手动加 1 EV，可在命令末尾加 `--exposure 1.0`。

### 遇到问题

- 显示 `Python 3.11 or newer was not found`：在 PowerShell 输入 `python --version` 检查版本及命令是否可用；只有已安装但命令不可用时，需要修复 Python 的 PATH 设置。
- 显示 `Installation failed`：检查网络连接，重新双击 `setup_windows.cmd`。它会复用已有 `.venv`。如果反复失败，而且你曾用其他 Python 版本手工建立 `.venv`，可先把这个文件夹改名为 `.venv-backup`，再运行安装脚本；确认新环境可用后，再自行删除备份。
- 显示 `Environment not found`：先运行 `setup_windows.cmd`，确认出现 `Setup complete`。
- 显示 `output already exists`：为防止覆盖，先为这次结果选另一个输出名称（使用下方命令行方式），或把旧结果自行移到别处。
- 显示 `input must be an existing Sony .ARW file` 或解码错误：确认拖入的是真实 `.ARW`，且文件没有损坏；仅改扩展名不会把其他图片变成 RAW。

## 在剪辑与修图软件中使用

在 DaVinci Resolve 中，把生成的 TIFF **手动解释**为：

```text
Input Color Space: Sony S-Gamut3.Cine
Input Gamma: Sony S-Log3
Data Levels: Full（若有此选项）
```

Photoshop 可以打开 TIFF，但这个文件没有嵌入 sRGB ICC，也不会被普通看图软件自动正确显示为 S-Log3。若在 Photoshop 使用视频 LUT，需确认 LUT 的输入确实是 **Sony S-Gamut3.Cine / S-Log3、Full 范围**；不匹配的 LUT 可能使颜色或对比度异常。即使匹配，也不保证与 A7C II 机内视频画面一致。

## 进阶：命令行与 EXR

在 Windows 项目文件夹的 PowerShell 中，使用虚拟环境的 Python，无需手动“激活”环境：

```powershell
.\.venv\Scripts\python.exe arw_to_slog3.py "C:\照片\input.ARW" "C:\照片\output.tif"
```

若要输出 **float32 线性 S-Gamut3.Cine EXR**（注意：不是 S-Log3），先额外安装 EXR 依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[exr]"
.\.venv\Scripts\python.exe arw_to_slog3.py "C:\照片\input.ARW" "C:\照片\output.exr"
```

macOS / Linux 用户可在项目文件夹执行 `python3 -m venv .venv`、`.venv/bin/python -m pip install -e .`，再用 `.venv/bin/python arw_to_slog3.py input.ARW output.tif`。Windows 的两个 `.cmd` 文件不适用于 macOS / Linux。

## 转换流程与边界

`rawpy`/LibRaw 以 ARW 中报告的相机白平衡开发 RAW，采用 AHD 去马赛克、线性 gamma `(1, 1)`、16-bit ProPhoto RGB 输出；关闭自动白平衡、自动亮度、自动曝光、降噪与额外 tone curve。LibRaw 的输出虽标记为 “ProPhoto D65”，其转换常数与 Bradford 适应到**标准 ProPhoto D50** 相符，因此本工具按 D50 解释。之后由 `colour-science` 以 Bradford 白点适应转换至线性 S-Gamut3.Cine D65，并直接调用其 Sony S-Log3 编码函数。最后将归一化 S-Log3 数值量化为 16-bit TIFF。

线性输入按 RAW 饱和电平归一化，**并非绝对场景反射率**；0 EV 不保证照片中的灰卡变成 18%。只有线性数值本来就是 0.18 时，标准 S-Log3 才将它编码到约 10-bit CV 420。本工具不分析画面亮度，也不模拟 Sony 未公开的处理。

LibRaw 在 16-bit 中间结果中可能已经裁切高光或色域外数值。TIFF 只在最终转无符号整数时把超出 `[0,1]` 的 S-Log3 编码值裁切。相机白平衡系数必须有效；但 `rawpy` 文档说明这些系数可能直接来自文件，也可能由 LibRaw 计算。没有 A7C II 实拍 ARW 样本时，不能独立验证每个文件的白平衡元数据来源或端到端相机效果。EXR 也从 LibRaw 的 16-bit 中间结果产生，不能恢复此前已裁切的值。

## 技术依据

- [Sony, *Technical Summary for S-Gamut3.Cine/S-Log3 and S-Gamut3/S-Log3*](https://download.pro.sony/FNGP/protein/1237494271390/1237494271406.pdf)：原色、D65 白点、S-Log3 公式和参考 CV。
- [`colour-science` Sony S-Log3 实现](https://colour.readthedocs.io/en/develop/_modules/colour/models/rgb/transfer_functions/sony.html) 与 [S-Gamut3.Cine 定义](https://colour.readthedocs.io/en/develop/generated/colour.models.RGB_COLOURSPACE_S_GAMUT3_CINE.html)。
- [rawpy 参数文档](https://letmaik.github.io/rawpy/api/rawpy.Params.html)；[LibRaw 转换常数](https://github.com/LibRaw/LibRaw/blob/master/src/tables/colorconst.cpp)。

开发者运行测试：`python -m pip install -e ".[test]"`，然后 `python -m pytest -q`。
