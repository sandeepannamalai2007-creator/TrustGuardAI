# 🔒 Privacy and Data Handling

TrustGuard AI is designed with privacy-first principles for continuous authentication systems, ensuring compliance with GDPR and ethical AI standards.

## Behavioral Biometrics Processing
The system analyzes typing dynamics and mouse kinematics to verify identity:
- **Keystroke Dynamics**: We collect non-intrusive timing metrics:
  - **Dwell Time**: Duration a key is held down.
  - **Flight Time**: Duration between releasing one key and pressing the next.
- **Mouse Kinematics**: We calculate movement velocity and trajectory patterns from cursor coordinates.

## Data Minimization
To uphold strict data privacy:
- **No Raw Text Logged**: Keystroke timing features are strictly decoupled from the actual characters typed. We do not store passwords, messages, or input values.
- **No Keylogging**: Key identities are never transmitted to the backend.
- **Statistical Aggregation**: Only numerical timing arrays and derived statistical features (mean, variance) are processed by the machine learning model.

## Retention Policies
- **Ephemeral Processing**: Telemetry vectors are processed in memory and immediately discarded.
- **Session Eviction**: Redis handles session state with a strict Time-To-Live (TTL) of 3600 seconds (1 hour). Inactive sessions are automatically evicted.
- **Audit Logs**: Historical trust scores and binary classification results are stored in SQLite/PostgreSQL for audit purposes, tied only to anonymous Session IDs without PII.

## Compliance & Ethical AI
By substituting invasive monitoring tools (like screen recording or keylogging) with passive behavioral analysis, TrustGuard AI adheres to GDPR Article 5 (Data Minimization & Storage Limitation). The system is solely purposed for identity verification, eliminating surveillance overreach.
