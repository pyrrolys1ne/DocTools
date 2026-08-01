# DocTools

批量文档处理命令行工具。

> 项目处于早期阶段（Alpha）。这既是一个实用工具，也是作者积累开源项目经验的练习场。

## 当前能力

- ✅ `remove-headers`：批量去除 Word（`.docx`）文档的页眉（含首页 / 奇偶页变体）
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

pip install -e ".[dev]"
```

## 使用

去除单个文件的页眉：

```bash
doctools remove-headers 文档.docx -o 文档_clean.docx
```

批量去除目录下所有 `.docx` 的页眉：

```bash
doctools remove-headers ./docs -o ./docs_cleaned
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

## 开发

```bash
pytest          # 运行测试
ruff check .    # 代码检查
```

## 路线图

- [x] 阶段 0：项目脚手架 + Word 批量去页眉
- [ ] PDF 转 PPT
- [ ] Word 统一格式（字体、页边距等）
- [ ] 文档站（MkDocs）

## 许可

[MIT](LICENSE) © 2026 pyrrolys1ne
