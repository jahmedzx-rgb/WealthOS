"""Apply pending database migrations, then start the web process."""

from __future__ import annotations

import os

from deploy.run_migrations import main as run_migrations


def main() -> None:
    run_migrations()
    port = os.environ.get("PORT", "10000")
    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
            "--workers",
            "1",
            "--proxy-headers",
            "--forwarded-allow-ips=*",
        ],
    )


if __name__ == "__main__":
    main()
