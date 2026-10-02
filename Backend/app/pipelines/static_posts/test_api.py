import asyncio
import io
import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_workflow():
    print("1. Testing GET / (Root/Health)...")
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    print("   -> Root OK:", res.json())

    print("2. Testing POST /upload with multiple files...")
    file1 = ("test1.txt", io.BytesIO(b"Hello from test file 1."), "text/plain")
    file2 = ("test2.json", io.BytesIO(b'{"key": "value", "purpose": "testing"}'), "application/json")
    
    upload_res = client.post("/upload", files=[("files", file1), ("files", file2)])
    assert upload_res.status_code == 202, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    job_id = upload_data["job_id"]
    print("   -> Upload OK. Job ID:", job_id)
    assert upload_data["files_count"] == 2
    assert "test1.txt" in upload_data["filenames"]
    assert "test2.json" in upload_data["filenames"]

    print("3. Testing GET /status/{job_id} and waiting for job completion...")
    status_data = {}
    for _ in range(25):
        status_res = client.get(f"/status/{job_id}")
        assert status_res.status_code == 200, f"Status failed: {status_res.text}"
        status_data = status_res.json()
        if status_data["status"] in ["completed", "failed"]:
            break
        time.sleep(1)

    print("   -> Status:", status_data["status"])
    assert status_data["job_id"] == job_id
    assert status_data["files_count"] == 2

    print("4. Testing GET /result/{job_id}...")
    result_res = client.get(f"/result/{job_id}")
    assert result_res.status_code == 200, f"Result failed: {result_res.text}"
    result_data = result_res.json()
    print("   -> Result status:", result_data["status"])
    if result_data.get("result"):
        print("   -> Result payload status:", result_data["result"].get("status"))
        file_analyses = result_data["result"].get("data", {}).get("file_analyses", [])
        print(f"   -> Analyzed file count: {len(file_analyses)}")

    print("5. Testing invalid job ID...")
    missing_res = client.get("/status/non-existent-id")
    assert missing_res.status_code == 404
    print("   -> Correctly returned 404 for missing job ID.")

    print("\nAll integration checks passed successfully!")

if __name__ == "__main__":
    test_workflow()
