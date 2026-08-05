"""``python -m web`` 启动无头本地服务。

配置见 web/config.py（环境变量前缀 DOCTOOLS_）。桌面客户端以子进程方式
拉起本服务时传 ``--port 0``，服务会自行选择空闲端口，并把实际端口以
``DOCSERVER_PORT=<port>`` 单行形式打印到 stdout 供客户端读取。
"""

from __future__ import annotations

import argparse
import socket

import uvicorn

from web.config import settings


def free_port() -> int:
    """向系统申请一个空闲端口（绑定后立即释放，交给 uvicorn 使用）。"""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="DocTools 本地 API 服务")
    parser.add_argument("--host", default=settings.host, help="监听地址")
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help="监听端口；传 0 表示自动选择空闲端口",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.reload,
        help="开发调试时热重载（打包环境必须关闭）",
    )
    args = parser.parse_args(argv)

    port = args.port if args.port else free_port()
    # 客户端契约：启动完成后从 stdout 读取这一行拿到实际端口。
    print(f"DOCSERVER_PORT={port}", flush=True)

    uvicorn.run(
        "web.app:app",
        host=args.host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
