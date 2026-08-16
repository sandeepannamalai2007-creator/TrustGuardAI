import time
import json
import urllib.request
import numpy as np
import sys
import os

from ml import predictor

def run_benchmarks():
    print("=" * 60)
    print("TrustGuard AI Latency Benchmarking")
    print("=" * 60)

    # Mock features structure matching incoming telemetry packets
    mock_features = {
        "avg_dwell_time_ms": 120.0,
        "std_dwell_time_ms": 30.0,
        "avg_flight_time_ms": 150.0,
        "std_flight_time_ms": 40.0,
        "typing_speed_cps": 4.5,
        "avg_mouse_velocity_px_s": 250.0,
        "click_count": 10,
        "keystroke_count": 12,
        "session_duration_s": 5.0
    }

    # 1. Benchmark ML Inference Speed
    print("Benchmarking ML predictor.predict_trust_score() over 1000 trials...")
    predictor_times = []
    
    # Warmup
    for _ in range(50):
        predictor.predict_trust_score(mock_features)

    for _ in range(1000):
        t0 = time.perf_counter()
        predictor.predict_trust_score(mock_features)
        t1 = time.perf_counter()
        predictor_times.append((t1 - t0) * 1000)

    avg_ml_ms = np.mean(predictor_times)
    p95_ml_ms = np.percentile(predictor_times, 95)
    print(f"  - Average ML Inference Latency: {avg_ml_ms:.4f} ms")
    print(f"  - 95th Percentile ML Latency  : {p95_ml_ms:.4f} ms")

    # 2. Benchmark full HTTP endpoint roundtrip
    start_url = "http://127.0.0.1:8000/session/start"
    feature_url = "http://127.0.0.1:8000/session/features"
    headers = {"Content-Type": "application/json"}

    # Start Session
    start_payload = json.dumps({"user_id": "BenchmarkUser", "demo_mode": True}).encode("utf-8")
    req_start = urllib.request.Request(start_url, data=start_payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req_start) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            session_id = res_data["session_id"]
        print(f"\nCreated temporary session: {session_id}")
    except Exception as e:
        print(f"\n[ERROR] Backend server not reachable on localhost:8000. Start the server first! ({e})")
        return

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
        except Exception as e:
            print(f"[ERROR] API Request failed during benchmarking: {e}")
            break

    if roundtrip_times:
        avg_rt_ms = np.mean(roundtrip_times)
        p95_rt_ms = np.percentile(roundtrip_times, 95)
        print(f"  - Average Round-Trip Network Latency: {avg_rt_ms:.2f} ms")
        print(f"  - 95th Percentile Round-Trip Latency : {p95_rt_ms:.2f} ms")
    
    print("=" * 60)

if __name__ == "__main__":
    run_benchmarks()
