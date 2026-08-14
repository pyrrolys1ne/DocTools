"""MinerU 在线 API 客户端（可选功能，客户端零模型）。

默认离线可用；用户配置 ``DOCTOOLS_MINERU_API_URL``（自建 mineru-api 服务，
如 ``http://192.168.1.10:8000``）后启用 PDF 解析为 Markdown。也可配置
``DOCTOOLS_MINERU_TOKEN`` 用于需要鉴权的服务。

参照 MinerU 调研结论：不把 torch+模型打进 PyInstaller 包，客户端只用
requests 调远程 API（自建服务 `POST /file_parse` 同步接口，产物为 zip
或 Markdown）。
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from doctools.errors import MINERU_FAILED, MINERU_NOT_CONFIGURED, DoctoolsError

# 单文件解析超时（MinerU 纯 CPU pipeline 解析较大 PDF 可能数分钟）
_PARSE_TIMEOUT_SECONDS = 600


def mineru_available() -> bool:
    """是否配置了 MinerU API（环境变量 DOCTOOLS_MINERU_API_URL）。"""
    return bool(os.environ.get("DOCTOOLS_MINERU_API_URL", "").strip())


def _api_url() -> str:
    return os.environ["DOCTOOLS_MINERU_API_URL"].strip().rstrip("/")


def parse_pdf(src: Path, dst: Path) -> str | None:
    """调 MinerU API 解析 PDF 为 Markdown（作为 process_batch 的 worker 使用）。

    ``dst`` 是输出 ``.md`` 文件路径。响应若是 zip（含 Markdown），解压取
    首个 .md；若是纯文本则直接落盘。返回附注（无附注时返回 None）。
    """
    if not mineru_available():
        raise DoctoolsError(
            MINERU_NOT_CONFIGURED,
            "未配置 MinerU API。请设置 DOCTOOLS_MINERU_API_URL（自建 mineru-api 地址）后重试。",
            "MinerU API not configured. Set DOCTOOLS_MINERU_API_URL.",
        )

    import requests  # noqa: PLC0415

    dst.parent.mkdir(parents=True, exist_ok=True)
    headers = {}
    token = os.environ.get("DOCTOOLS_MINERU_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with src.open("rb") as fh:
            resp = requests.post(
                f"{_api_url()}/file_parse",
                files={"file": (src.name, fh, "application/pdf")},
                data={"backend": "pipeline"},
                headers=headers,
                timeout=_PARSE_TIMEOUT_SECONDS,
            )
        resp.raise_for_status()
    except DoctoolsError:
        raise
    except Exception as exc:  # noqa: BLE001 - 网络/服务错误统一包装
        raise DoctoolsError(
            MINERU_FAILED,
            f"MinerU API 调用失败：{exc}",
            f"MinerU API call failed: {exc}",
        ) from exc

    content = resp.content
    if content[:2] == b"PK":  # zip：解压取首个 .md
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                md_names = [n for n in zf.namelist() if n.endswith(".md")]
                if not md_names:
                    raise DoctoolsError(
                        MINERU_FAILED,
                        "MinerU 返回的 zip 中没有 Markdown 文件。",
                        "No Markdown file in MinerU response zip.",
                    )
                dst.write_bytes(zf.read(md_names[0]))
        except DoctoolsError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DoctoolsError(
                MINERU_FAILED,
                f"MinerU 返回的 zip 无法解析：{exc}",
                f"Failed to parse MinerU zip: {exc}",
            ) from exc
        return "已通过 MinerU 解析为 Markdown。"
    else:  # 直接 Markdown 文本
        text = resp.text or content.decode("utf-8", "replace")
        dst.write_text(text, encoding="utf-8")
        return "已通过 MinerU 解析为 Markdown。"
