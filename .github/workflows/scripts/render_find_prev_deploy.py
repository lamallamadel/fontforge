#!/usr/bin/env python3
"""Parse a Render API /services/{id}/deploys JSON list from stdin and print the
ID of the most-recent deploy whose status is 'live'.

Exits with code 0 and prints the deploy ID; prints nothing and exits with 1 if
no live deploy is found or parsing fails.

Usage:
    curl -sf -H "Authorization: Bearer $KEY" "$URL/deploys?limit=5" \
        | python3 render_find_prev_deploy.py
"""
import json
import sys


def main() -> None:
    try:
        deploys = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        sys.exit(1)

    for entry in deploys:
        if entry.get("deploy", {}).get("status") == "live":
            print(entry["deploy"]["id"])
            sys.exit(0)

    sys.exit(1)


if __name__ == "__main__":
    main()
