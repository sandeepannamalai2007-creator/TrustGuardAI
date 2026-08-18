import json
import time
import urllib.request
from urllib.error import HTTPError, URLError

import numpy as np

from ml import predictor


def run_benchmarks():
    print("=" * 60)
    print("  TrustGuard AI — Machine Learning Inference Latency Benchmark")
    print("=" * 60)

    # 1. Benchmark local predictor.predict_trust_score execution latency
    mock_features = {
        "avg_dwell_time_ms": 110.5,
        "std_dwell_time_ms": 12.3,
        "avg_flight_time_ms": 140.2,
        "std_flight_time_ms": 15.1,
        "typing_speed_cps": 4.5,
        "avg_mouse_velocity_px_s": 250.0,
        "click_count": 5,
        "keystroke_count": 25,
        "session_duration_s": 10.0
    }

    # Warmup
    for _ in range(100):
        predictor.predict_trust_score(mock_features)

    # Measure 1,000 runs
    latencies_ms = []
    for _ in range(1000):
        t0 = time.perf_counter()
        predictor.predict_trust_score(mock_features)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies = np.array(latencies_ms)
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    avg_lat = np.mean(latencies)

    print("\n[Local ML Inference Latency (1,000 trials)]")
    print(f"  - Average : {avg_lat:.3f} ms")
    print(f"  - p50     : {p50:.3f} ms")
    print(f"  - p95     : {p95:.3f} ms")
    print(f"  - p99     : {p99:.3f} ms")

    # 2. Benchmark Full HTTP API Endpoint Latency (if server is running)
    api_url = "http://127.0.0.1:8000"
    start_url = f"{api_url}/session/start"
    feature_url = f"{api_url}/session/features"

    print("\nAttempting to connect to FastAPI backend on 127.0.0.1:8000...")
    try:
        req_start = urllib.request.Request(
            start_url,
            data=json.dumps({"user_id": "BenchmarkUser", "demo_mode": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req_start) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            session_id = res_data["session_id"]
            access_token = res_data.get("access_token")
        print(f"Created temporary benchmark session: {session_id}")
    except (URLError, HTTPError, OSError) as e:
        print(f"\n[INFO] Backend server not active on localhost:8000 ({e}). Skipping API round-trip latency benchmark.")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    print("Benchmarking full HTTP API /session/features round-trip over 100 trials...")
    feature_payload = json.dumps({
        "session_id": session_id,
        **mock_features
    }).encode("utf-8")

    roundtrip_times = []
    
    # Warmup
    for _ in range(10):
        req_feat = urllib.request.Request(feature_url, data=feature_payload, headers=headers, method="POST")
        with urllib.request.urlopen(req_feat) as res:
            res.read()

    for _ in range(100):
        req_feat = urllib.request.Request(feature_url, data=feature_payload, headers=headers, method="POST")
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req_feat) as response:
                response.read()
            t1 = time.perf_counter()
            roundtrip_times.append((t1 - t0) * 1000)
        except (URLError, HTTPError, OSError) as e:
            print(f"[ERROR] API Request failed during benchmarking: {e}")
            break

    if roundtrip_times:
        rt_arr = np.array(roundtrip_times)
        rt_p50 = np.percentile(rt_arr, 50)
        rt_p95 = np.percentile(rt_arr, 95)
        rt_p99 = np.percentile(rt_arr, 99)
        rt_avg = np.mean(rt_arr)

        print("\n[HTTP API /session/features Round-Trip Latency (100 trials)]")
        print(f"  - Average : {rt_avg:.2f} ms")
        print(f"  - p50     : {rt_p50:.2f} ms")
        print(f"  - p95     : {rt_p95:.2f} ms")
        print(f"  - p99     : {rt_p99:.2f} ms")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    run_benchmarks()
