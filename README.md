# DocTools

本地优先的批量文档处理工具，提供命令行、Windows 桌面客户端与本地 Web API。支持 Word 页眉/页脚移除、Office 与 PDF 互转、PDF 合并拆分、图片压缩等 13 项操作，所有文件均在本机处理，不上传。


## 目录

- [DocTools](#doctools)
  - [目录](#目录)
  - [功能特性](#功能特性)
  - [环境要求](#环境要求)
  - [安装](#安装)
  - [命令行使用](#命令行使用)
  - [桌面客户端使用](#桌面客户端使用)
  - [Web API 调试](#web-api-调试)
  - [服务配置](#服务配置)
  - [架构](#架构)
  - [开发](#开发)
  - [路线图](#路线图)
  - [许可](#许可)

## 功能特性

| 功能 | CLI 命令 | 说明 |
|------|----------|------|
| Word 去页眉 | `remove-headers` | 含文字旁横线（段落边框 + Header 样式边框） |
| Word 去页脚 | `remove-footers` | 同上 |
| Word 去页眉页脚 | `remove-headers-footers` | 一次完成 |
| Word → PDF | `word-to-pdf` | 基于 Microsoft Office COM |
| PPT → PDF | `ppt-to-pdf` | 同上 |
| 图片 → PDF | `image-to-pdf` | 目录内所有图片合成一个 PDF（每张一页） |
| PDF → Word | `pdf-to-word` | 基于 pdf2docx，有损转换 |
| PDF → PPT | `pdf-to-ppt` | 每页渲染为一张幻灯片 |
| PDF → 图片 | `pdf-to-images` | 每页导出一张 PNG |
| 图片压缩 | `compress-images` | JPEG 重编码，其余转优化 PNG，可选质量 |
| PDF 合并 | `merge-pdf` | 按命令行顺序合并为单个 PDF |
| PDF 拆分 | `split-pdf` | 每页一个，或按自定义页码范围 |

通用能力：

- **递归处理**子目录（`--recursive`），输出目录镜像源目录结构；
- **单文件失败不中断整批**，逐文件上报 OK/FAIL；
- **Windows 桌面客户端**（WPF）：本地服务随包启动，无需安装 Python / Node；

## 环境要求

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | ≥ 3.10 | 核心库、CLI 与 Web API 运行环境 |
| .NET 8 SDK（可选） | ≥ 8.0 | 构建桌面客户端（`packaging/build_client.ps1`） |
| Microsoft Office（可选） | Windows 桌面版 | `word-to-pdf` / `ppt-to-pdf` 使用 COM 自动化 |

## 安装

从源码安装（推荐）：

```bash
git clone git@github.com:pyrrolys1ne/DocTools.git
cd DocTools
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev,web]"    # 完整安装（含测试工具与 Web 后端）
pip install -e ".[office]"     # 启用 Word/PPT → PDF（需已安装 Office）
```

可用 extras：

| Extra | 内容 |
|-------|------|
| 默认 | 核心处理功能（pdf2docx、PyMuPDF、python-docx、pypdf、Pillow、Typer） |
| `dev` | pytest、reportlab、ruff |
| `web` | FastAPI、uvicorn、pydantic-settings |
| `office` | pywin32（Word/PPT → PDF，仅 Windows） |

## 命令行使用

去页眉（单文件 / 目录批量）：

```bash
doctools remove-headers 文档.docx -o 文档_clean.docx
doctools remove-headers ./docs -o ./docs_cleaned
doctools remove-footers ./docs -o ./docs_cleaned
doctools remove-headers ./docs -o ./docs_cleaned --recursive   # 递归子目录
```

Office → PDF：

```bash
doctools word-to-pdf 文档.docx -o 输出目录
doctools ppt-to-pdf ./slides -o ./slides_pdf --recursive
```

图片 → PDF（目录内所有图片合成一个）与图片压缩：

```bash
doctools image-to-pdf ./图片 -o 输出目录
doctools compress-images ./图片 -o 输出目录 -q 60
```

PDF → Word / PPT / 图片：

```bash
doctools pdf-to-word 文档.pdf -o 输出目录
doctools pdf-to-ppt 幻灯片.pdf -o 输出目录
doctools pdf-to-images 文档.pdf -o 输出目录
```

PDF 合并 / 拆分：

```bash
doctools merge-pdf 1.pdf 2.pdf 3.pdf -o merged.pdf
doctools split-pdf 文档.pdf -o ./拆分结果
doctools split-pdf 文档.pdf -o ./拆分结果 --ranges "1-3,5,8-12"
```

> 旧命令 `doctools to-pdf ...` 已弃用（混合转换），请改用 `word-to-pdf` / `ppt-to-pdf`。

各命令详细选项见 `doctools <命令> --help`。

## 桌面客户端使用

桌面客户端是 C/S 形态：`DocTools.exe`（WPF）启动时自动拉起随包的本地 API 服务 `docserver\docserver.exe`（由 `web/` 后端用 PyInstaller 打包），处理完成后随程序退出关闭。交互模型与命令行一致：填写/浏览本地路径，不涉及文件上传。

构建与打包（Windows，需 .NET 8 SDK）：

```bash
.\packaging\package.ps1          # 构建 docserver + DocTools.exe 并打包为 zip
```

产物为 `dist\DocTools-win-x64.zip`，解压后运行 `DocTools.exe` 即可。目录结构：

```
DocTools.exe        桌面客户端
docserver\          本地 API 服务（PyInstaller onedir）
README.txt          使用说明
```

> 旧的 React 前端已归档（tag `archive/frontend-v0.3`），源码保留在 `frontend/` 但不再构建、不再随 Web 后端托管。

## Web API 调试

`web/` 后端保留为个人开发调试工具：提供 `/api/v1` 接口与 `/docs` 调试文档，不托管前端。

```bash
python -m web                           # http://127.0.0.1:8000，打开 /docs 调试
python -m web --port 0                  # 自动选择空闲端口，stdout 打印 DOCSERVER_PORT=<port>
```

桌面客户端即通过该 API 通信（REST 创建/查询任务 + WebSocket 进度流），接口形状见 `web/schemas.py`。

## 服务配置

Web 服务通过环境变量配置（前缀 `DOCTOOLS_`，也支持 `.env` 文件），全部配置见 `web/config.py`：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DOCTOOLS_HOST` | `127.0.0.1` | 监听地址 |
| `DOCTOOLS_PORT` | `8000` | 监听端口；桌面客户端传 `--port 0` 自动选端口 |
| `DOCTOOLS_RELOAD` | `false` | 开发调试时热重载（打包环境必须关闭） |
| `DOCTOOLS_CORS_ORIGINS` | `http://localhost:5173,…` | 浏览器跨域调试来源（逗号分隔）；桌面客户端不走 CORS |

API 统一挂在 `/api/v1` 前缀下；健康检查为 `GET /api/health`。

## 架构

见 [ARCHITECTURE.md](ARCHITECTURE.md)。要点：

- 核心为纯库（`src/doctools/`），不依赖任何 Web / CLI 框架，可被任意消费方复用；
- 所有操作集中在 `OPERATION_HANDLERS` 注册表，CLI 与 Web（以及桌面客户端经 API）共享同一编排层（`batch.py`）；
- 三种消费形态：CLI（`src/doctools/cli.py`）、本地 Web API（`web/`，开发调试）、Windows 桌面客户端（`desktop/`，C/S 产品形态）。

## 开发

```bash
pytest                      # 运行后端与库测试
ruff check .                # 代码检查
dotnet build desktop\DocTools\DocTools.csproj   # 桌面客户端编译检查
```

## 路线图

- [x] 阶段 0：项目脚手架 + Word 批量去页眉
- [x] 去页眉连横线（段落边框 + Header 样式边框）
- [x] 递归子目录
- [x] 本地 Web 界面（Tailwind v4 + shadcn/ui，已归档）
- [x] 转 PDF（Word / PPT，基于 Office COM）
- [x] 图片转 PDF（多合一）
- [x] PDF 合并 / 拆分
- [x] PDF 转 Word / PDF 转 PPT / PDF 转图片 / 图片压缩
- [x] BS 化：API 版本化、任务存储抽象
- [x] C/S 化：WPF 桌面客户端 + PyInstaller 打包分发
- [ ] 桌面客户端安装器（Inno Setup / MSIX）
- [ ] 文档站（MkDocs）

## 许可

[MIT](LICENSE) © 2026 pyrrolys1ne
