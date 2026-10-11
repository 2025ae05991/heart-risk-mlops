"""Generate demonstration traffic for the monitoring dashboard."""

import argparse
import json
import time
from pathlib import Path

import httpx

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()
    if args.requests < 1 or args.interval < 0:
        parser.error("Use at least one request and a non-negative interval")
    patient = json.loads(Path("examples/patient.json").read_text())
    with httpx.Client(timeout=20, trust_env=False) as client:
        for i in range(args.requests):
            payload = dict(patient)
            if i % 10 == 0:
                payload["cp"] = 0  # Deliberate validation error to demonstrate the 4xx panel.
            response = client.post(args.url.rstrip("/") + "/predict", json=payload)
            expected = 422 if i % 10 == 0 else 200
            if response.status_code >= 500:
                response.raise_for_status()
            if response.status_code != expected:
                raise RuntimeError(f"Expected HTTP {expected}, received {response.status_code}")
            if i == 0 or (i + 1) % 30 == 0 or i == args.requests - 1:
                print(f"{i + 1:03d}/{args.requests}: HTTP {response.status_code}", flush=True)
            time.sleep(args.interval)
