"""结构化错误：稳定错误码 + 中文/英文消息。

参照飞鼠（FlyingMouse Format）的 ``error.code`` + ``messages.zhCN/enUS``
设计：CLI、Web API 与桌面端都依赖稳定的错误码做程序化处理（提示、禁用、
分类），而不是解析人类可读文本。错误码是对外契约，不要随意改名。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 稳定错误码（对外契约：CLI 输出 / Web API error_code / 桌面端展示）
# ---------------------------------------------------------------------------

# PDF 处理
PDF_CONVERT_ENGINE_FAILED = "PDF_CONVERT_ENGINE_FAILED"  # pdf2docx 引擎转换失败
PDF_NO_TEXT = "PDF_NO_TEXT"  # PDF 没有可提取文字（疑似扫描件）
PDF_PAGE_LIMIT = "PDF_PAGE_LIMIT"  # 超出页数预算
PDF_IMAGE_PIXEL_LIMIT = "PDF_IMAGE_PIXEL_LIMIT"  # 单页渲染超出像素预算
IMAGE_TO_PDF_PIXEL_LIMIT = "IMAGE_TO_PDF_PIXEL_LIMIT"  # 图片合并 PDF 超出解码预算

# Office（COM / LibreOffice）
OFFICE_NOT_INSTALLED = "OFFICE_NOT_INSTALLED"  # 未安装 Microsoft Office / pywin32
OFFICE_CONVERT_FAILED = "OFFICE_CONVERT_FAILED"  # Office 转换失败

# OCR
OCR_NOT_AVAILABLE = "OCR_NOT_AVAILABLE"  # OCR 引擎（RapidOCR）不可用
OCR_FAILED = "OCR_FAILED"  # OCR 识别失败（无结果）

# MinerU（在线 API，可选功能）
MINERU_NOT_CONFIGURED = "MINERU_NOT_CONFIGURED"  # 未配置 MinerU API 地址
MINERU_FAILED = "MINERU_FAILED"  # MinerU API 调用失败

# 通用
UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"  # 输入格式不支持
PATH_NOT_FOUND = "PATH_NOT_FOUND"  # 输入路径不存在
NO_INPUT_FILES = "NO_INPUT_FILES"  # 目录里没有匹配的文件
MERGE_NO_VALID_INPUT = "MERGE_NO_VALID_INPUT"  # 合并 PDF：全部文件读取失败


class DoctoolsError(Exception):
    """带稳定错误码的业务错误。

    - ``code``：机器可读的稳定标识（见上方常量）
    - ``zh`` / ``en``：人类可读消息（en 可留空，项目当前中文优先）
    """

    def __init__(self, code: str, zh: str, en: str = "") -> None:
        super().__init__(zh)
        self.code = code
        self.zh = zh
        self.en = en

    def __str__(self) -> str:  # pragma: no cover - 仅便于调试
        return f"[{self.code}] {self.zh}"


def error_code(exc: BaseException) -> str | None:
    """从任意异常提取稳定错误码；非 DoctoolsError 返回 None。"""
    return exc.code if isinstance(exc, DoctoolsError) else None
