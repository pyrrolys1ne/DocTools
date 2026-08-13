# DocTools 更新计划：参照 FlyingMouse Format 的代码与部署优化

> 状态：**已确认（2026-xx）**。拍板结果：P0 + P1 全做；X1 OCR 本期不做，列入下期；X2 LibreOffice 捆绑本期不做，以 O4 能力探测提示替代。
> 参照对象：[LaoFeng-mouse/flyingmouse-format](https://github.com/LaoFeng-mouse/flyingmouse-format)（MIT，v0.5.1）

## 1. 背景与目标

对比飞鼠后确认的差距（详见对话记录）：

| # | 差距 | 飞鼠做法 | 我们的现状 |
|---|------|----------|-----------|
| G1 | PDF→Word 无回退链 | pdf2docx 引擎 → 文字提取回退 → OCR 回退 | 只走 pdf2docx，异常 PDF/扫描件直接失败 |
| G2 | 错误不可结构化 | `error.code` + 中英双语消息 | 裸 `str(exc)` 中文文本 |
| G3 | 无资源预算 | 单图 50MP、图片合并 100MP、页数/批量上限 | 无限制，长 PDF/大图可能内存爆炸 |
| G4 | 无引擎能力探测 | `GET /api/capabilities` + 转换前探测 | 仅 office.py 构造时探测一次 |
| G5 | 无安装器 | NSIS/AppX/dmg | zip 解压即用 |
| G6 | 无自动更新 | electron-updater（带渠道判断） | 手动去 Release 下载 |
| G7 | 无诊断导出 | 一键导出版本/引擎/环境/日志 | 无 |
| G8 | CI 无冒烟验证 | 引擎清单校验 + 产物检查 | 只构建打包 |

**目标**：以低风险、小改动面优先，分阶段补齐上述差距；保持"纯库核心 + CLI/Web/桌面三端共享"的现有架构不变。

## 2. 优化项总览

| 编号 | 优化项 | 优先级 | 工作量 | 风险 |
|------|--------|--------|--------|------|
| O2 | 结构化错误码（先行，O1/O3 依赖） | P0 | 中 | 低 |
| O1 | PDF→Word 降级链（文字提取回退） | P0 | 小 | 低 |
| O3 | 资源预算（页数/像素上限） | P0 | 小 | 低 |
| O4 | 引擎探测 + `/api/v1/capabilities` | P0 | 中 | 低 |
| O5 | 测试补强（pdf→docx 特征/回退链/预算） | P0 | 小 | 低 |
| D2 | 诊断导出（API + 桌面端按钮） | P1 | 小 | 低 |
| D3 | CI 冒烟测试（构建后真转一个文件） | P1 | 小 | 低 |
| D1 | 安装器（Inno Setup） | P1 | 中 | 中 |
| D4 | 自动更新（查 GitHub Release + 校验替换） | P1 | 中 | 中 |
| X1 | OCR 回退（扫描件→Word，Tesseract） | P2 待拍板 | 中 | 中 |
| X2 | LibreOffice 捆绑（替代 Office COM） | P2 待拍板 | 大 | 高 |
| X3 | 转换子进程化 + 超时 | P2 待拍板 | 中 | 中 |

## 3. 代码优化（P0）

### O2 结构化错误码

- **现状**：各模块抛 `RuntimeError`/`ValueError` + 中文文本，`FileResult.error` 为裸字符串，Web 端无错误码字段。
- **参照飞鼠**：`error.code`（如 `PDF_OCR_REQUIRED`）+ `messages.zhCN/enUS`；错误分类（引擎缺失/引擎失败/文件损坏/资源超限）。
- **方案**：
  1. 新增 `src/doctools/errors.py`：`class DoctoolsError(Exception)`，字段 `code`、`zh`、`en`（en 可缺省）。
  2. 各 handler/worker 的失败路径抛出带 code 的错误，常用 code 列表：
     `PDF_CONVERT_ENGINE_FAILED`、`PDF_NO_TEXT`、`OFFICE_NOT_INSTALLED`、`OFFICE_CONVERT_FAILED`、`RESOURCE_LIMIT_EXCEEDED`、`UNSUPPORTED_FORMAT`、`PATH_NOT_FOUND`。
  3. `FileResult` 增加 `code: str | None` 字段；`process_batch` 捕获时填充。
  4. CLI 输出 `[FAIL] path: [CODE] message`；Web schema 增加 `error_code`。
- **涉及**：新增 `src/doctools/errors.py`；改 `model.py`、`batch.py`、`pdf_convert.py`、`office.py`、`pdf.py`、`images.py`、`cli.py`、`web/schemas.py`、`web/app.py`。
- **验收**：每个操作失败时 CLI 与 Web 均能给出稳定 code；现有测试不回归。

### O1 PDF→Word 降级链

- **现状**：`pdf_to_docx` 直接 `pdf2docx.Converter.convert`，失败即报错；扫描版 PDF 无解。
- **参照飞鼠**：`convertPdfToDocx` 优先 docengine，失败回退到 PDF.js 文字提取 → 手写 OOXML 极简 docx（多列行→`w:tbl`，单列行→段落）；扫描件再回退 OCR。
- **方案**（第一版两级，OCR 见 X1）：
  1. 第一级：pdf2docx 版式还原（现状不变）。
  2. 第二级：pdf2docx 抛错 → PyMuPDF `page.get_text()` 按页提取 → 用 **python-docx**（已有依赖）生成极简 docx：每页标题段落 + 多列行转表格 + 单列行转段落（对齐飞鼠的 fallback 逻辑）。
  3. 回退发生时在结果里记录说明（`FileResult.note`，如"引擎失败，已回退为文字提取"），CLI/Web 可见，不静默。
  4. 扫描件（全页无文本）保持明确报错 `PDF_NO_TEXT`（X1 落地前）。
- **涉及**：`src/doctools/pdf_convert.py`、`model.py`（note 字段）、新增 `tests/test_pdf_convert.py`。
- **验收**：构造一个 pdf2docx 失败/异常的 PDF，输出仍是合法 docx（含 `word/document.xml`）且 CLI 标注回退。

### O3 资源预算

- **现状**：无限制。
- **参照飞鼠**：`resource-policy.js`：单图 50MP/16384px、图片合并 PDF 解码预算 100MP、批量 2GB、PDF 页数上限（500）。
- **方案**（轻量版，默认值对齐飞鼠，环境变量可调）：
  1. 新增 `src/doctools/resource_policy.py`：`MAX_PDF_PAGES`（默认 1000）、`IMAGE_TO_PDF_MAX_PIXELS`（默认 100MP）、`PDF_IMAGE_MAX_PIXELS`（单页渲染上限）。
  2. 接入点：`pdf_to_docx`/`pdf_to_pptx`/`pdf_to_images` 入口检查页数；`merge_images_to_pdf` 累计像素预算；超限抛 `RESOURCE_LIMIT_EXCEEDED`（O2）。
  3. limits 随 capabilities API 暴露（O4）。
- **涉及**：新增 `src/doctools/resource_policy.py`；改 `pdf_convert.py`、`images.py`、`pdf.py`。
- **验收**：超限输入得到带 code 的明确报错；正常输入行为不变。

### O4 引擎探测 + capabilities API

- **现状**：CLI 无能力感知；Web 无 capabilities 接口；桌面端所有功能按钮恒可用。
- **参照飞鼠**：`GET /api/capabilities` 返回可用引擎 + limits；转换前探测引擎存在性。
- **方案**：
  1. 新增 `src/doctools/capabilities.py`：`get_capabilities()` 返回
     `{office, pdf2docx, pymupdf, pypdf, pillow}` 及 `limits`。
     office 探测用注册表查 `Word.Application`/`PowerPoint.Application` CLSID 存在性（**不启动进程**），pywin32 缺失时直接 false。
  2. Web 新增 `GET /api/v1/capabilities`。
  3. 桌面端启动时拉取，`word-to-pdf`/`ppt-to-pdf` 在 office 不可用时禁用并提示原因。
- **涉及**：新增 `capabilities.py`、`web/routers/capabilities.py`；改 `web/app.py`、`desktop/.../DocToolsApi.cs`、`MainViewModel.cs`。
- **验收**：无 Office 的机器上 capabilities.office=false，桌面端对应按钮禁用。

### O5 测试补强

- **参照飞鼠**：`tests/pdf2docx.test.js` 校验输出 zip 魔数 + `word/media/` 特征；回退链用静态断言。
- **方案**：
  1. `tests/test_pdf_convert.py`：pdf→docx 输出为合法 zip 且含 `word/document.xml`；monkeypatch 让 pdf2docx 抛错 → 断言走回退链且输出可打开；纯图片 PDF（reportlab 生成）→ 断言 `PDF_NO_TEXT`。
  2. `tests/test_resource_policy.py`：页数/像素超限抛 `RESOURCE_LIMIT_EXCEEDED`。
  3. `tests/test_capabilities.py`：结构断言（键齐全、类型正确）。
- **涉及**：`tests/`。
- **验收**：`pytest` 全绿。

## 4. 部署优化（P1）

### D2 诊断导出

- **参照飞鼠**：一键导出诊断报告（版本/平台/引擎/环境/日志）。
- **方案**：Web 新增 `GET /api/v1/diagnostics`（版本、平台、Python 版本、capabilities、环境变量白名单、docserver 日志尾部）；WPF 主界面加"导出诊断报告"按钮 → 调 API 保存为 txt。
- **涉及**：`web/routers/diagnostics.py`、`web/app.py`、`desktop/`。
- **验收**：点击按钮生成的报告含全部字段。

### D3 CI 冒烟测试

- **参照飞鼠**：CI 引擎校验 + 产物检查。
- **方案**：新增 `packaging/smoke_test.ps1`：启动 `dist\docserver\docserver.exe --port 0` → 解析 `DOCSERVER_PORT` → 调 `/api/health` → 用 reportlab 生成测试 PDF → 调 pdf-to-word 任务 → 校验输出 docx 存在且为 zip → 杀进程；CI 构建步骤后追加冒烟步骤，失败即 job 失败。
- **涉及**：新增 `packaging/smoke_test.ps1`；改 `.github/workflows/package.yml`。
- **验收**：CI 绿色且包含冒烟日志。

### D1 安装器（Inno Setup）

- **现状**：zip 解压；README 路线图已有 "[ ] 桌面客户端安装器"。
- **参照飞鼠**：NSIS 安装向导（可选目录、快捷方式、卸载）。
- **方案**：
  1. 新增 `packaging/installer.iss` + `packaging/build_installer.ps1`：打包 `DocTools.exe` + `docserver\`；创建桌面/开始菜单快捷方式；卸载注册；可选安装目录；版本号从 `pyproject.toml` 读取。
  2. CI 增加步骤（choco 装 Inno Setup 或下载便携版 ISCC），产物 `DocTools-Setup-{version}-x64.exe` 附到 Release。
  3. zip 分发包保留（偏好解压即用的用户）。
- **涉及**：`packaging/`、`.github/workflows/package.yml`、`README.md`（安装说明）。
- **验收**：本机安装/卸载走通；快捷方式指向正确；CI 产出安装器。

### D4 自动更新（轻量自研）

- **参照飞鼠**：electron-updater 自动下载 + 退出时安装；**渠道判断教训**：不同包不能互推（我们只有单一 win-x64 包，风险小）。
- **方案**：
  1. WPF 启动后后台线程查 GitHub Releases API（`pyrrolys1ne/DocTools`）最新 tag，与本地版本比较。
  2. 有新版 → 主界面提示 → 用户确认后下载 zip → 校验（大小 + PK 魔数 + SHA256，Release 附 sha256 文件）→ 退出 docserver → 解压替换 → 提示重启。
  3. 设置项 `CheckForUpdates`（默认开）；主界面"检查更新"按钮。
- **涉及**：新增 `desktop/.../Services/UpdateService.cs`；改 `AppSettings.cs`、`MainViewModel.cs`、`MainWindow.xaml`。
- **验收**：发布新 tag 后旧客户端能检测到并完成替换；网络失败静默不打扰。

## 5. 可选优化（P2，待拍板）

### X1 OCR 回退（扫描件 → Word）

- **参照飞鼠**：Tesseract + tesseract.js，扫描 PDF 自动 OCR。
- **方案**：新增 extra `doctools[ocr]`（pytesseract）；运行时探测 tesseract 二进制（环境变量 `DOCTOOLS_TESSERACT_PATH`）；`pdf_to_docx` 检测到全页无文本且 OCR 可用 → 渲染 300dpi → OCR → 极简 docx；OCR 不可用时保持 `PDF_NO_TEXT` 报错（O2）。
- **代价**：用户需自装 Tesseract（~几十 MB + 语言包）；不捆绑（捆绑需评估体积与许可）。
- **拍板点**：是否纳入本期；若纳入，是否接受"用户自装 Tesseract"的形态。

### X2 LibreOffice 捆绑（替代 Office COM）

- **参照飞鼠**：自带 LibreOffice Portable，零机外依赖。
- **代价**：安装包 +300MB 量级；LibreOffice 为 MPL 2.0（可再分发但需注意组件许可）；替换/降级 COM 需要新引擎封装 + 大量回归。与 O4（能力探测）联动。
- **拍板点**：是否立项。建议至少本期不做，先靠 O4 把"未装 Office 时的明确提示"做好。

### X3 转换子进程化 + 超时

- **参照飞鼠**：docengine/LibreOffice/pdftoppm 均带 timeout。
- **方案**：将 pdf2docx 调用放入子进程并加超时（如 10 分钟），超时后回退（与 O1 联动）。Python 侧可用 `multiprocessing` 或 subprocess + 打包入口。
- **代价**：PyInstaller 打包需额外入口；复杂度中等。
- **拍板点**：是否纳入。

## 6. 明确不做（边界）

- PDF→Excel 智能表格提取（飞鼠旗舰功能，独立大工程，本期不立项）
- 音视频转换、NCM/mflac/kgma 解密、电子书、文本格式全家桶（定位不同）
- macOS / Windows 7 兼容版（保持 Windows x64）
- 中英双语 UI（本项目中文定位；错误消息按 O2 结构化，为将来 i18n 留口）
- Web 前端 UI 恢复托管（保持"开发调试工具"定位）

## 7. 实施顺序与版本规划

| 阶段 | 内容 | 建议版本 |
|------|------|----------|
| 阶段一（P0 代码） | O2 → O1 → O3 → O4 → O5 | v1.1.0 |
| 阶段二（P1 部署） | D2 → D3 → D1 → D4 | v1.2.0 |
| 阶段三（P2 可选） | 按拍板结果：X1 / X2 / X3 | v1.3.0 |

阶段一内部顺序：先 O2（错误码）是因为 O1/O3 的新错误需要 code 承载；O5 测试随各优化项同步补充，最后统一回归。

## 8. 实施记录

- **O2 结构化错误码（v1.1.0）** ✅ 新增 `src/doctools/errors.py`（`DoctoolsError` + 稳定错误码）；`FileResult` 增加 `code`/`note`；CLI 输出 `[FAIL] path: [CODE] msg`；Web `JobResult` 增加 `error_code`/`note`；顺带修复 CLI 失败行重复输出。
- **O1 PDF→Word 降级链（v1.1.0）** ✅ `pdf_to_docx` 三级流程：无文本检测（扫描件报 `PDF_NO_TEXT`）→ pdf2docx 版式还原 → 失败回退 PyMuPDF 文本 + `find_tables` 生成极简 docx（返回附注标注回退）。
- **O3 资源预算（v1.1.0）** ✅ 新增 `src/doctools/resource_policy.py`（页数/单页像素/合并像素预算，`DOCTOOLS_*` 可调），接入 pdf_to_docx/pptx/images、image-to-pdf、merge-pdf。
- **O4 能力探测（v1.1.0）** ✅ 新增 `src/doctools/capabilities.py`（注册表查 Office CLSID，不启动进程）；Web `GET /api/v1/capabilities`；桌面端 `OperationDef.IsAvailable` + 列表禁用 + 启动拦截提示。
- **O5 测试补强（v1.1.0）** ✅ 回退链/扫描件/预算/capabilities/diagnostics 测试，全量 pytest 79 passed + ruff 全过。
- **D2 诊断导出（v1.2.0）** ✅ Web `GET /api/v1/diagnostics`；桌面端标题栏"导出诊断报告"按钮。
- **D3 CI 冒烟（v1.2.0）** ✅ `packaging/smoke_test.ps1`（启动 docserver → health/capabilities → 真实 pdf-to-word → PK 魔数校验），已本地验证通过；workflow 追加冒烟步骤。
- **D1 安装器（v1.2.0）** ✅ `packaging/installer.iss` + `build_installer.ps1`（per-user 安装、快捷方式、卸载；版本号从 pyproject 单一来源）；本机无 Inno Setup，编译验证待 CI。
- **D4 自动更新（v1.2.0）** ✅ `desktop/.../UpdateService.cs`（GitHub Releases 查询 → zip 下载 + PK/大小校验 → update.cmd 退出后替换重启）；启动静默检查（`CheckForUpdates` 设置）+ 标题栏"检查更新"按钮。
- **版本统一（v1.2.0）** ✅ pyproject / `doctools.__version__` / csproj 三处统一为 1.2.0（P0 + P1 一次性发布）。
