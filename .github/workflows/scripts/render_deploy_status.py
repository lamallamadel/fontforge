#!/usr/bin/env python3
"""Parse a Render API /services/{id} JSON response from stdin and print the
deploy status string (e.g. 'live', 'build_in_progress', 'update_in_progress').

Exits with status 0 and prints the status; prints 'unknown' if parsing fails.

Usage:
    curl -sf -H "Authorization: Bearer $KEY" "$URL" | python3 render_deploy_status.py
"""
import json
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
        status = (
            data.get("service", {})
            .get("serviceDetails", {})
            .get("deploy", {})
            .get("status", "unknown")
        )
    except Exception:  # noqa: BLE001
        status = "unknown"
    print(status)


if __name__ == "__main__":
    main()
