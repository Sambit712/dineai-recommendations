"""
main.py -- Application entry point
AI-Powered Restaurant Recommendation System

Phase 6: Launches a Uvicorn server that hosts the FastAPI backend.
  - Dataset is loaded and preprocessed once at server startup.
  - POST /recommend exposes the full recommendation pipeline over HTTP.
  - Frontend static files (Phase 7) are served from /frontend at /.

Usage:
    python main.py                  # runs with auto-reload (development)
    python main.py --no-reload      # runs without auto-reload (production)

The server starts at: http://localhost:8000
  API docs (Swagger UI): http://localhost:8000/docs
  Health check         : http://localhost:8000/health
"""

import sys
import argparse
import uvicorn


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restaurant Recommender API Server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload (use in production)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Uvicorn log level (default: info)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    print(
        "\n"
        "  [*] Restaurant Recommender API\n"
        f"  Listening on http://{args.host}:{args.port}\n"
        f"  Swagger UI  : http://localhost:{args.port}/docs\n"
        f"  Health check: http://localhost:{args.port}/health\n"
    )

    uvicorn.run(
        "src.api.app:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
