"""
Quick Pushover integration test.

Usage:
    python examples/test_pushover.py
    python examples/test_pushover.py --message "Hei fra testscriptet"

The script reads PUSHOVER_TOKEN and PUSHOVER_USER from the environment (including .env)
and attempts to send a short notification. The response body is printed so you can confirm
delivery without checking the mobile app.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv


PUSHOVER_ENDPOINT = "https://api.pushover.net/1/messages.json"
DEFAULT_TIMEOUT = 5


def send_pushover_message(message: str, timeout: int) -> requests.Response:
    """Send a single notification through Pushover."""

    load_dotenv(override=False)

    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")

    if not token or not user:
        missing = []
        if not token:
            missing.append("PUSHOVER_TOKEN")
        if not user:
            missing.append("PUSHOVER_USER")
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Add them to your environment or .env file."
        )

    payload = {
        "token": token,
        "user": user,
        "message": message,
    }

    response = requests.post(PUSHOVER_ENDPOINT, data=payload, timeout=timeout)
    response.raise_for_status()
    return response


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a test notification through Pushover.")
    parser.add_argument(
        "--message",
        default=f"Portfolio bot test message at {datetime.utcnow().isoformat()}Z",
        help="Notification text to send",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        response = send_pushover_message(args.message, timeout=args.timeout)
    except Exception as exc:  # noqa: BLE001 - surface helpful message
        print(f"[!] Failed to send notification: {exc}", file=sys.stderr)
        return 1

    print("[+] Notification accepted by Pushover.")
    print("Request payload:")
    print(f"  message: {args.message}")
    print("Response JSON:")
    try:
        print(response.json())
    except ValueError:
        print(response.text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
