import json
import time
from pathlib import Path
from app.core.hashing import hash_bytes


class LicenseLedger:
    def __init__(self, ledger_file: str = "work/credits.txt"):
        self.ledger_file = Path(ledger_file)
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        self.entries = []

    def record_asset(self, asset_id: str, source_url: str, license_name: str, attribution: str, file_path: str):
        sha256_hash = ""
        if Path(file_path).exists():
            with open(file_path, "rb") as f:
                sha256_hash = hash_bytes(f.read())

        entry = {
            "asset_id": asset_id,
            "source_url": source_url,
            "license": license_name,
            "attribution": attribution,
            "sha256": sha256_hash,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.entries.append(entry)
        self.write_ledger()

    def write_ledger(self):
        with open(self.ledger_file, "w", encoding="utf-8") as f:
            f.write("=== ASSET LICENSE & ATTRIBUTION LEDGER ===\n\n")
            for entry in self.entries:
                f.write(f"Asset ID: {entry['asset_id']}\n")
                f.write(f"Source: {entry['source_url']}\n")
                f.write(f"License: {entry['license']}\n")
                f.write(f"Attribution: {entry['attribution']}\n")
                f.write(f"SHA256: {entry['sha256']}\n")
                f.write(f"Retrieved: {entry['timestamp']}\n")
                f.write("-" * 40 + "\n")
