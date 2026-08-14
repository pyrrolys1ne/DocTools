"""MinerU 在线 API 客户端（可选功能，客户端零模型）。

默认离线可用；配置环境变量后启用 PDF 解析为 Markdown：

- ``DOCTOOLS_MINERU_API_URL``：自建 mineru-api 服务地址（如 ``http://192.168.1.10:8000``）。
  走官方 FastAPI 的 ``POST /file_parse`` 同步接口（字段名 ``files``，复数）。
- ``DOCTOOLS_MINERU_TOKEN``：mineru.net 官方 API Token（可选，URL 指向 mineru.net 时使用）。

参照 MinerU 调研结论：不把 torch+模型打进 PyInstaller 包，客户端只用 requests
调远程 API。自建 /file_parse 响应优先按 ``response_format_zip=true`` 取 zip
（解出 full.md），否则按 JSON 取 ``results[文件名].md_content``。
"""

from __future__ import annotations

import io
import json
import os
import time
import zipfile
from pathlib import Path

from doctools.errors import MINERU_FAILED, MINERU_NOT_CONFIGURED, DoctoolsError

# 单文件解析超时（秒）。自建 pipeline 纯 CPU 解析较大 PDF 可能数分钟；
# mineru.net 官方流程含上传+排队+解析+下载，整体超时放宽。
_SELF_HOSTED_TIMEOUT_SECONDS = 600
_MINERU_NET_TIMEOUT_SECONDS = 1800
# 官方 API 轮询间隔
_POLL_INTERVAL_SECONDS = 5


def mineru_available() -> bool:
    """是否配置了 MinerU API（DOCTOOLS_MINERU_API_URL）。"""
    return bool(os.environ.get("DOCTOOLS_MINERU_API_URL", "").strip())


def _api_url() -> str:
    return os.environ["DOCTOOLS_MINERU_API_URL"].strip().rstrip("/")


def _token() -> str:
    return os.environ.get("DOCTOOLS_MINERU_TOKEN", "").strip()


def parse_pdf(src: Path, dst: Path) -> str | None:
    """调 MinerU API 解析 PDF 为 Markdown（作为 process_batch 的 worker 使用）。

    ``dst`` 是输出 ``.md`` 文件路径。返回附注（无附注时返回 None）。
    URL 指向 mineru.net 时走官方 API 流程，否则走自建 /file_parse。
    """
    if not mineru_available():
        raise DoctoolsError(
            MINERU_NOT_CONFIGURED,
            "未配置 MinerU API。请设置 DOCTOOLS_MINERU_API_URL（自建 mineru-api 地址）后重试。",
            "MinerU API not configured. Set DOCTOOLS_MINERU_API_URL.",
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    api_url = _api_url()
    if "mineru.net" in api_url:
        _parse_via_mineru_net(src, dst)
    else:
        _parse_via_self_hosted(src, dst, api_url)
    return "已通过 MinerU 解析为 Markdown。"


def _parse_via_self_hosted(src: Path, dst: Path, api_url: str) -> None:
    import requests  # noqa: PLC0415

    try:
        with src.open("rb") as fh:
            resp = requests.post(
                f"{api_url}/file_parse",
                files={"files": (src.name, fh, "application/pdf")},
                data={
                    "backend": "pipeline",
                    "return_md": "true",
                    "response_format_zip": "true",
                },
                timeout=_SELF_HOSTED_TIMEOUT_SECONDS,
            )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - 网络/服务错误统一包装
        raise DoctoolsError(
            MINERU_FAILED,
            f"MinerU API 调用失败：{exc}",
            f"MinerU API call failed: {exc}",
        ) from exc

    content = resp.content
    if content[:2] == b"PK":  # response_format_zip=true → zip
        md = _extract_md_from_zip(content)
        dst.write_text(md, encoding="utf-8")
        return
    # 否则 JSON：results[文件名].md_content
    try:
        data = json.loads(content.decode("utf-8", "replace"))
        md = data["results"][src.name]["md_content"]
        dst.write_text(md, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        raise DoctoolsError(
            MINERU_FAILED,
            f"MinerU 响应解析失败：{exc}",
            f"Failed to parse MinerU response: {exc}",
        ) from exc


def _parse_via_mineru_net(src: Path, dst: Path) -> None:
    import requests  # noqa: PLC0415

    base = _api_url()
    token = _token()
    if not token:
        raise DoctoolsError(
            MINERU_NOT_CONFIGURED,
            "使用 mineru.net 官方 API 需要配置 DOCTOOLS_MINERU_TOKEN。",
            "DOCTOOLS_MINERU_TOKEN is required for mineru.net.",
        )
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    try:
        # 1) 申请签名上传 URL
        batch_resp = requests.post(
            f"{base}/file-urls/batch",
            headers=headers,
            json={"files": [{"name": src.name, "data_id": "d1"}], "model_version": "pipeline"},
            timeout=_MINERU_NET_TIMEOUT_SECONDS,
        )
        batch_resp.raise_for_status()
        batch = batch_resp.json()
        batch_id = batch["data"]["batch_id"]
        file_url = batch["data"]["file_urls"][0]

        # 2) PUT 上传（无 Content-Type）
        with src.open("rb") as fh:
            upload_resp = requests.put(
                file_url, data=fh.read(), timeout=_MINERU_NET_TIMEOUT_SECONDS
            )
        upload_resp.raise_for_status()

        # 3) 轮询结果
        deadline = time.time() + _MINERU_NET_TIMEOUT_SECONDS
        full_zip_url = None
        while time.time() < deadline:
            status_resp = requests.get(
                f"{base}/extract-results/batch/{batch_id}",
                headers=headers,
                timeout=60,
            )
            status_resp.raise_for_status()
            item = status_resp.json()["data"]["extract_result"][0]
            state = item.get("state")
            if state == "done":
                full_zip_url = item.get("full_zip_url")
                break
            if state == "failed":
                raise DoctoolsError(
                    MINERU_FAILED,
                    f"MinerU 解析失败：{item.get('err_msg', 'unknown')}",
                    f"MinerU parse failed: {item.get('err_msg', 'unknown')}",
                )
            time.sleep(_POLL_INTERVAL_SECONDS)
        if not full_zip_url:
            raise DoctoolsError(
                MINERU_FAILED,
                "MinerU 解析超时（未在时限内完成）。",
                "MinerU parse timed out.",
            )

        # 4) 下载 zip 解出 full.md
        zip_resp = requests.get(full_zip_url, timeout=_MINERU_NET_TIMEOUT_SECONDS)
        zip_resp.raise_for_status()
        md = _extract_md_from_zip(zip_resp.content)
        dst.write_text(md, encoding="utf-8")
    except DoctoolsError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DoctoolsError(
            MINERU_FAILED,
            f"MinerU 官方 API 调用失败：{exc}",
            f"MinerU official API call failed: {exc}",
        ) from exc


def _extract_md_from_zip(content: bytes) -> str:
    """从 MinerU 返回的 zip 中提取 Markdown（优先 full.md，其次任意 .md）。"""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            full_md = [n for n in names if n.endswith("full.md")]
            target = full_md[0] if full_md else next((n for n in names if n.endswith(".md")), None)
            if target is None:
                raise DoctoolsError(
                    MINERU_FAILED,
                    "MinerU 返回的 zip 中没有 Markdown 文件。",
                    "No Markdown file in MinerU response zip.",
                )
            return zf.read(target).decode("utf-8", "replace")
    except DoctoolsError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DoctoolsError(
            MINERU_FAILED,
            f"MinerU 返回的 zip 无法解析：{exc}",
            f"Failed to parse MinerU zip: {exc}",
        ) from exc
