"""Minimal CLI entry-point for the aifont package."""

from __future__ import annotations


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="aifont", description="AIFont SDK CLI")
    sub = parser.add_subparsers(dest="command")

    serve_p = sub.add_parser("serve", help="Start the AIFont REST API server")
    serve_p.add_argument("--host", default="0.0.0.0")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument("--reload", action="store_true")

    args = parser.parse_args()

    if args.command == "serve":
        try:
            import uvicorn  # noqa: PLC0415
        except ImportError:
            parser.error("uvicorn is required. Install it with: pip install aifont[api]")
        from aifont.api.app import create_app  # noqa: PLC0415

        uvicorn.run(
            create_app(),
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
