# 参与贡献

欢迎任何形式的贡献：提 issue、修 bug、补文档、加功能。

## 开发环境

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 提交前检查

```bash
ruff check .
pytest
```

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 风格，**提交消息统一使用英文**：

- `feat:` 新功能（new feature）
- `fix:` 修复（bug fix）
- `docs:` 文档（documentation）
- `test:` 测试（tests）
- `refactor:` 重构（refactoring）
- `chore:` 维护（maintenance）

示例：
- `feat: add PDF to PPT conversion`
- `fix: clear headers in multi-section docx`
- `docs: update usage examples`

## 提 PR 流程

1. fork 本项目
2. 新建分支：`git checkout -b feat/xxx`
3. 改代码并保证测试通过
4. 提交并推送到你的 fork
5. 发起 Pull Request
