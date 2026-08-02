# DocTools

批量文档处理命令行工具 + 本地 Web 界面。

> 项目处于早期阶段（Alpha）。这既是一个实用工具，也是作者积累开源项目经验的练习场。

## 当前能力

- ✅ `remove-headers`：批量去除 Word（`.docx`）文档的页眉（含首页 / 奇偶页变体），
  连同页眉文字下方的**横线**（段落边框 + Header 样式边框）一并移除
  - ✅ 支持**递归**处理子目录（`--recursive`），输出目录镜像源目录结构
  - ✅ 单文件失败不影响整批；`--dry-run` 预览
- ✅ **本地 Web 界面**：浏览器里浏览/选择目录、扫描预览、实时进度与逐文件结果；
  支持**目录批量**与**单个文件**两种模式（FastAPI + React）
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

pip install -e ".[dev,web]"   # web extra 提供本地 Web 界面所需依赖
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

先预览将要处理哪些文件（不写入）：

```bash
doctools remove-headers ./docs --dry-run
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

界面流程：浏览或输入源目录 / 输出目录 → 扫描预览 → 开始处理 → 实时进度 + 逐文件 OK/FAIL 结果。

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
- [x] 本地 Web 界面骨架
- [ ] PDF 转 PPT
- [ ] Word 统一格式（字体、页边距等）
- [ ] 文档站（MkDocs）

## 许可

[MIT](LICENSE) © 2026 pyrrolys1ne
