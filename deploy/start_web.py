"""Start the web process after the hosting provider's pre-deploy migration step."""

from __future__ import annotations

import os

from deploy.validate_env import validate_environment


def main() -> None:
    validate_environment()
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
