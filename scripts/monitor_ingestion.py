#!/usr/bin/env python3
"""Monitor document processing status without uploading new files."""

import sys
import time
import httpx

BASE_URL = "http://localhost:8006"

def main():
    client = httpx.Client(timeout=120.0)

    # 1. Login user
    email = "eval_user@example.com"
    password = "EvalPassword123!"

    print(f"Logging in test user: {email}...")
    try:
        login_res = client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        login_res.raise_for_status()
        user_data = login_res.json()
        print(f"User ID: {user_data.get('id')}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return 1

    cookies = client.cookies

    # 2. Monitor loop
    print("\nMonitoring document processing status...")
    while True:
        try:
            list_res = client.get(f"{BASE_URL}/api/v1/documents?limit=200", cookies=cookies)
            list_res.raise_for_status()
            docs = list_res.json().get("documents", [])
            
            # Map status
            status_counts = {"completed": 0, "failed": 0, "processing": 0, "pending": 0, "uploading": 0}
            for doc in docs:
                status = doc.get("status")
                status_counts[status] = status_counts.get(status, 0) + 1

            total = len(docs)
            completed = status_counts.get("completed", 0)
            failed = status_counts.get("failed", 0)
            processing = status_counts.get("processing", 0)
            pending = status_counts.get("pending", 0)
            uploading = status_counts.get("uploading", 0)

            print(f"Total: {total} | Completed: {completed} | Failed: {failed} | Processing: {processing} | Pending: {pending} | Uploading: {uploading}")
            
            if completed + failed == total and total > 0:
                print("\nAll documents processed successfully!")
                break
            
            time.sleep(15)
        except Exception as e:
            print(f"Error while polling: {e}")
            time.sleep(15)

    print(f"\nUser ID for dataset generation: {user_data.get('id')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
