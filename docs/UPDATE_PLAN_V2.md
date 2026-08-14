# DocTools 功能扩展计划 V2（大功能 + UI 重构）

> 状态：**规划中**（部分技术选型已定，MinerU 部分待调研结果后补全）
> 前置：v1.2.0 已发布，P0+P1 优化完成

## 1. 目标清单（来自需求）

### 大功能
1. 扫描 OCR（扫描版 PDF / 图片 → 可编辑文本）
2. 图片格式互转 ✅ 已实现（v1.2.x，Pillow）
3. MinerU 解析 PDF（版面/表格/公式/OCR 综合解析）
4. PDF → Excel 智能表格提取

### 小功能优化
5. 图片转 PDF 队列上移/下移（页序跟随）—— 依赖卡片式 UI 重构一起做
6. 结构化错误码 —— 已具备（v1.2.0），新功能沿用
7. LibreOffice 替代 Office COM（取消客户端本机 Office 依赖）

### UI
8. 桌面端主页卡片式入口，按输入文件格式分组（PDF/Word/图片/PPT…），点卡片进入具体功能

### 重构
9. 必要时先重构：引擎抽象层（Office 双后端）、按格式组织的操作目录

## 2. 技术选型（已定）

### OCR —— RapidOCR（onnxruntime）
- 理由：中文质量与 PaddleOCR 同级（PP-OCRv4 模型）、打包 ~120-160MB（vs Paddle +1GB）、CPU 0.5-2s/页、模型可完全离线、Apache-2.0 + MIT。
- 集成形态：作为**可选 extra** `doctools[ocr]`，PyInstaller 打包时 collect-all onnxruntime + 模型随包分发。
- 流程：`fitz` 渲染 300dpi → 先 `page.get_text()` 抽文本层（有文本跳过 OCR 提速）→ 无文本才 RapidOCR predict。
- ⚠️ 合规：PyMuPDF 是 **AGPL**，闭源商用需评估（MIT 开源分发无碍）。

### LibreOffice —— 探测系统 + 捆绑便携版兜底
- 理由：MPL 2.0 文件级 copyleft，未修改二进制原样打包只需附许可证 + 版权声明，无源码义务；独立进程调用不构成衍生作品。
- 体积：安装包 +~400MB（解压后 ~1GB，单语言可压）。
- 架构：
  1. 注册表 `HKLM\Software\LibreOffice\UNO\InstallPath` 探测系统版 → 命中用系统版；
  2. 未命中 → 用捆绑便携版；
  3. 统一封装 `convert_to_pdf()`：`soffice --headless --norestore --convert-to pdf` + `-env:UserInstallation` 隔离 profile + 超时杀进程 + 输出存在性校验（不信退出码）。
  4. 保留 COM 作为可选加速路径（双后端统一接口）。
- 决策点：是否捆绑便携版（体积 +~400MB），还是仅探测系统 LibreOffice（无体积但用户要自装）。

### PDF → Excel —— 待拍板（调研完成）
候选路线（按体积/质量权衡）：
- **A. PyMuPDF `find_tables` + `pymupdf_layout`**（最轻，已有依赖，有框表格可靠，无框/合并单元格中等）；
- **B. docling（IBM，MIT）**：表格→pandas DataFrame→xlsx 原生，比 MinerU 轻（但仍引入 DL 依赖）；
- **C. MinerU 表格**（复用 MinerU 的表格识别，HTML 表格 → pandas → xlsx，最重）；
- **D. camelot / pdfplumber**（纯规则，最轻但仅文本型表格）。

### MinerU —— 待拍板（调研完成）
- 版本 3.4.4，`pip install "mineru[pipeline]"`，**Windows 锁 Python 3.10-3.12**（不支持 3.13）。
- 依赖 PyTorch（CPU 1.2-1.6GB）+ 模型（pipeline ~1.2-1.5GB，按需下载），解包后 3-6GB，**不建议塞进主 exe**。
- 推荐**可选引擎方案**：轻量主程序 + 首次使用引导安装（`uv pip install "mineru[pipeline]"` + `mineru-models-download`，国内走 modelscope）+ 子进程 `mineru -p in.pdf -o out -b pipeline`。
- 输出 markdown + content_list_v2.json；表格是 HTML，转 Excel 需 pandas 后处理。
- 许可证：Apache 2.0（3.1.0 起，本地桌面捆绑无限制）。

## 3. 分阶段计划（草案）

| 阶段 | 内容 | 状态 |
|------|------|------|
| 阶段 A | 引擎抽象层（Office 双后端） | ✅ 已实现 |
| 阶段 B | LibreOffice 引擎（探测 + 兜底）+ word/ppt→pdf 走新引擎 | ✅ 代码已实现，待真机验证 |
| 阶段 C | OCR（RapidOCR + 扫描 PDF→docx 回退） | ✅ 已实现并真机验证 |
| 阶段 D | PDF→Excel 智能表格提取 | 待拍板路线 |
| 阶段 E | MinerU 解析 PDF（可选引擎） | 待拍板集成形态 |
| 阶段 F | 图片转 PDF 队列排序（桌面端） | 依赖卡片式 UI 重构 |
| 阶段 G | 卡片式主页重构 | 待设计 |
| 部署 | LibreOffice 便携版捆绑 + OCR 模型随包 | 待拍板捆绑范围 |

## 4. 实施记录

- **图片互转（convert-images）** ✅ Pillow，png/jpg/webp/bmp/gif/tiff，CLI + Web + 桌面端。
- **引擎抽象 + LibreOffice 后端** ✅ `office_engine.create_pdf_engine()`（COM 优先、LibreOffice 兜底）；`libreoffice.py`（探测系统/捆绑 + 隔离 profile + 超时 + 输出校验）。
- **扫描 OCR（RapidOCR）** ✅ `ocr.py`（onnxruntime，PP-OCRv6 模型）+ `pdf-to-word` 扫描件自动 OCR 回退；真机验证通过。
- **PDF→Excel** ✅ `pdf_excel.py`（PyMuPDF find_tables，每表一个 sheet）。
- **MinerU 在线 API** ✅ `mineru.py`（可选功能，DOCTOOLS_MINERU_API_URL 配置，`pdf-to-markdown`，零模型）。
- **图片转 PDF 队列排序** ✅ 后端 sources 顺序 + 桌面端队列上移/下移。
- **卡片式主页** ✅ 按输入格式分类（PDF/Word/图片/PPT），三视图导航（主页→分类→操作）。
- **LibreOffice 捆绑部署** ✅ `download_libreoffice.ps1` + `docserver.spec` 条件打包（需手动下载便携版）。

## 5. 待办

- LibreOffice 便携版真机转换验证（下载便携版后跑一次 word-to-pdf）。
- OCR 模型随包分发（PyInstaller collect-all rapidocr/onnxruntime + 模型离线）。
- 版本号 bump 与发布（v1.3.0）。
