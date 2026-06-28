#!/usr/bin/env python3
"""Register a user, clean old docs, upload the 43-subset documents, and wait for processing to complete."""

import sys
import time
import httpx
from pathlib import Path

BASE_URL = "http://localhost:8006"
DATASET_DIR = Path(__file__).resolve().parents[1] / "dataset"

def main():
    if not DATASET_DIR.exists():
        print(f"Error: dataset folder not found at {DATASET_DIR}")
        return 1

    client = httpx.Client(timeout=120.0)

    # 1. Register test user
    email = "eval_user@example.com"
    password = "EvalPassword123!"
    full_name = "Evaluation User"

    print(f"Registering/Logging in test user: {email}...")
    try:
        # Try logging in first in case user already exists
        login_res = client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        if login_res.status_code == 200:
            user_data = login_res.json()
            print(f"User logged in. User ID: {user_data.get('id')}")
        else:
            # If login fails, register
            reg_res = client.post(f"{BASE_URL}/api/v1/auth/register", json={
                "email": email,
                "password": password,
                "full_name": full_name
            })
            reg_res.raise_for_status()
            user_data = reg_res.json()
            print(f"User registered. User ID: {user_data.get('id')}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return 1

    # Extract cookies to authenticate subsequent requests
    cookies = client.cookies

    # 2. Delete any existing documents for this user to start clean
    print("\nChecking for old documents to clean up...")
    try:
        list_res = client.get(f"{BASE_URL}/api/v1/documents", cookies=cookies)
        list_res.raise_for_status()
        old_docs = list_res.json().get("documents", [])
        if old_docs:
            print(f"Found {len(old_docs)} old documents. Deleting them...")
            for doc in old_docs:
                doc_id = doc.get("id")
                del_res = client.delete(f"{BASE_URL}/api/v1/documents/{doc_id}", cookies=cookies)
                if del_res.status_code == 200:
                    print(f"   Deleted: {doc.get('filename')}")
                else:
                    print(f"   Failed to delete {doc.get('filename')}: {del_res.status_code}")
        else:
            print("No old documents found. Clean start.")
    except Exception as e:
        print(f"Failed to clean old documents: {e}")

    # 3. Gather PDF files from dataset/ directory
    pdf_files = sorted([p for p in DATASET_DIR.glob("*.pdf")])
    pdf_files.extend(sorted([p for p in DATASET_DIR.glob("*.PDF")]))
    pdf_files = sorted(list(set(pdf_files)))

    if not pdf_files:
        print("No PDF files found in dataset/ folder.")
        return 1

    print(f"\nFound {len(pdf_files)} PDF files to upload.")

    # 4. Upload each document
    uploaded_ids = []
    for idx, pdf_path in enumerate(pdf_files, 1):
        print(f"[{idx}/{len(pdf_files)}] Uploading {pdf_path.name}...")
        try:
            with open(pdf_path, "rb") as f:
                res = client.post(
                    f"{BASE_URL}/api/v1/documents/upload",
                    files={"file": (pdf_path.name, f, "application/pdf")},
                    cookies=cookies
                )
                res.raise_for_status()
                doc_info = res.json()
                doc_id = doc_info.get("id")
                uploaded_ids.append(doc_id)
                print(f"   Success: document_id={doc_id}, status={doc_info.get('status')}")
        except Exception as e:
            print(f"   Failed to upload {pdf_path.name}: {e}")

    # 5. Wait/Poll for processing completion
    print("\nWaiting for all documents to finish processing...")
    while True:
        try:
            list_res = client.get(f"{BASE_URL}/api/v1/documents?limit=200", cookies=cookies)
            if list_res.status_code == 401:
                print("Session expired (401). Logging in again to refresh cookies...")
                login_res = client.post(f"{BASE_URL}/api/v1/auth/login", json={
                    "email": email,
                    "password": password
                })
                login_res.raise_for_status()
                cookies = client.cookies
                continue
            list_res.raise_for_status()
            docs = list_res.json().get("documents", [])
            
            # Map status
            status_counts = {"completed": 0, "failed": 0, "processing": 0, "pending": 0}
            pending_or_processing_files = []
            for doc in docs:
                status = doc.get("status")
                status_counts[status] = status_counts.get(status, 0) + 1
                if status in ("pending", "processing"):
                    pending_or_processing_files.append(doc.get("filename"))

            total_uploaded = len(docs)
            completed_count = status_counts.get("completed", 0)
            failed_count = status_counts.get("failed", 0)
            other_count = total_uploaded - completed_count - failed_count
            print(f"Status summary -> Completed: {completed_count}, Failed: {failed_count}, In-Progress/Uploading: {other_count}")
            
            if completed_count + failed_count == total_uploaded and total_uploaded > 0:
                print("\nAll documents processed!")
                break
            else:
                # Print up to 3 files that are still processing
                still_running = ", ".join(pending_or_processing_files[:3])
                if still_running:
                    print(f"   Still processing: {still_running}...")
                time.sleep(10)
        except Exception as e:
            print(f"Error while polling: {e}")
            time.sleep(10)

    user_id = user_data.get('id')
    with open(DATASET_DIR / "user_id.txt", "w") as f:
        f.write(str(user_id))
    print(f"\nUpload and processing complete! User ID saved to dataset/user_id.txt: {user_id}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
