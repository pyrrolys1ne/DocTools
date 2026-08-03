# DocTools

批量文档处理命令行工具 + 本地 Web 界面。

> 项目处于早期阶段（Alpha）。这既是一个实用工具，也是作者积累开源项目经验的练习场。

## 当前能力

- ✅ `remove-headers`：批量去除 Word（`.docx`）文档的页眉（含首页 / 奇偶页变体），
  连同页眉文字下方的**横线**（段落边框 + Header 样式边框）一并移除
  - ✅ 支持**递归**处理子目录（`--recursive`），输出目录镜像源目录结构
  - ✅ 单文件失败不影响整批
- ✅ `word-to-pdf` / `ppt-to-pdf`：Word（`.docx/.doc`）、PPT（`.pptx/.ppt`）转 PDF
  - 基于本机 **Microsoft Office COM 自动化**（需安装 Office + `pip install "doctools[office]"`）
- ✅ `image-to-pdf`：图片（png/jpg/bmp/gif/webp/tiff…）转 PDF ——
  目录内所有图片**合成一个** PDF（每张一页）
- ✅ `merge-pdf`：按选择顺序把多个 PDF 合并为一个
- ✅ `split-pdf`：拆分 PDF —— 每页一个文件，或按自定义页码范围（如 `1-3,5,8-12`）
- ✅ **本地 Web 界面**：浏览器里浏览/选择目录、实时进度与逐文件结果；
  支持 **去页眉 / Word 转 PDF / PPT 转 PDF / 图片转 PDF / 合并 PDF / 拆分 PDF**
  六种操作（FastAPI + React）
- 🚧 PDF 转 PPT（规划中）

## 安装

从源码安装：

```bash
git clone git@github.com:pyrrolys1ne/DocTools.git
cd DocTools
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev,web]"   # 本地 Web 界面所需依赖
pip install -e ".[office]"    # 转 PDF 需要（Windows + 本机已装 Microsoft Office）
```

## 使用

### 命令行

去除单个文件的页眉：

```bash
doctools remove-headers 文档.docx -o 文档_clean.docx
```

批量去除目录下所有 `.docx` 的页眉：

```bash
doctools remove-headers ./docs -o ./docs_cleaned
```

递归处理子目录（输出镜像源目录结构）：

```bash
doctools remove-headers ./docs -o ./docs_cleaned --recursive
```

Word / PPT / 图片 转 PDF（需要本机 Office，图片则无需 Office）：

```bash
doctools word-to-pdf 文档.docx -o 输出目录
doctools ppt-to-pdf ./slides -o ./slides_pdf --recursive
doctools image-to-pdf ./图片 -o 输出目录   # 目录内所有图片合成一个 PDF
# 旧的混合命令仍可用：doctools to-pdf ...
```

合并多个 PDF：

```bash
doctools merge-pdf 1.pdf 2.pdf 3.pdf -o merged.pdf
```

拆分 PDF（每页一个，或按页码范围）：

```bash
doctools split-pdf 文档.pdf -o ./拆分结果
doctools split-pdf 文档.pdf -o ./拆分结果 --ranges "1-3,5,8-12"
```

查看帮助：

```bash
doctools --help
doctools remove-headers --help
```

### 本地 Web 界面

**后端**（终端 1）：

```bash
python -m web        # 启动 http://127.0.0.1:8000
```

**前端**（终端 2，可选，带热更新）：

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173，/api 自动代理到后端
```

**部署形态**（后端直接托管前端构建产物，只需一个进程）：

```bash
cd frontend && npm run build
python -m web        # 打开 http://127.0.0.1:8000 即是界面
```

首页是**功能宫格**，每个功能一个小方块，点开进入对应页面（左上角「返回」回到宫格）。流程：浏览或输入路径 → 开始处理 → 实时进度 + 逐文件 OK/FAIL 结果。

## 架构

见 [ARCHITECTURE.md](ARCHITECTURE.md)：纯库核心（`src/doctools/`）+ 本地 Web 后端（`web/`）+
React 前端（`frontend/`）。核心保持框架无关，Web 与 CLI 共享同一套批量编排层，未来可演进为线上服务。

## 开发

```bash
pytest                        # 运行测试
ruff check src tests web      # 代码检查
```

## 路线图

- [x] 阶段 0：项目脚手架 + Word 批量去页眉
- [x] 去页眉连横线（段落边框 + Header 样式边框）
- [x] 递归子目录
- [x] 本地 Web 界面（shadcn/ui + Tailwind）
- [x] 转 PDF（Word / PPT，基于 Office COM）
- [x] 图片转 PDF（多合一）
- [x] PDF 合并 / 拆分
- [ ] PDF 转 PPT
- [ ] Word 统一格式（字体、页边距等）
- [ ] 文档站（MkDocs）

## 许可

[MIT](LICENSE) © 2026 pyrrolys1ne


