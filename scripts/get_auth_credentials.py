"""Print auth values needed by local evaluation scripts."""

from __future__ import annotations

import argparse

import httpx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Login/register and print ACCESS_TOKEN plus USER_UUID.",
    )
    parser.add_argument("--base-url", default="http://localhost:8006")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--full-name", default="Evaluation User")
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    base_url = args.base_url.rstrip("/")
    endpoint = "/api/v1/auth/register" if args.register else "/api/v1/auth/login"
    payload = {
        "email": args.email,
        "password": args.password,
    }
    if args.register:
        payload["full_name"] = args.full_name

    with httpx.Client(timeout=args.timeout) as client:
        response = client.post(f"{base_url}{endpoint}", json=payload)

    if response.status_code >= 400:
        print(f"Auth failed {response.status_code}: {response.text}")
        return 1

    user = response.json()
    access_token = response.cookies.get("access_token")
    refresh_token = response.cookies.get("refresh_token")

    if not access_token:
        print("Auth succeeded, but access_token cookie was not returned.")
        return 1

    print(f"USER_UUID={user['id']}")
    print(f"ACCESS_TOKEN={access_token}")
    if refresh_token:
        print(f"REFRESH_TOKEN={refresh_token}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
