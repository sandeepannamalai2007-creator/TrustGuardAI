from predictor import predict_trust_score

features = {
    "avg_dwell_time_ms": 120,
    "avg_flight_time_ms": 50,
    "typing_speed_cps": 4.5,
    "avg_mouse_velocity_px_s": 650,
    "click_count": 15
}

score = predict_trust_score(features)

print("Predicted Trust Score:", score)