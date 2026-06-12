# app.py
import streamlit as st
import cv2
import pandas as pd
import os
import time
from datetime import datetime

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="SafeEye — Factory Safety Monitor",
    page_icon="🦺",
    layout="wide"
)

# ─────────────────────────────────────────
# DEMO MODE — True for cloud, False for local
# ─────────────────────────────────────────
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"

# ─────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: #1e2130;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        border: 1px solid #2e3250;
    }
    .title-text {
        font-size: 2rem;
        font-weight: bold;
        color: #00c8ff;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
if "running"         not in st.session_state:
    st.session_state.running         = False
if "violation_count" not in st.session_state:
    st.session_state.violation_count = 0
if "person_count"    not in st.session_state:
    st.session_state.person_count    = 0
if "last_violation"  not in st.session_state:
    st.session_state.last_violation  = "None"
if "alerts"          not in st.session_state:
    st.session_state.alerts          = []

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown('<p class="title-text">🦺 SafeEye — Factory Safety Monitor</p>',
            unsafe_allow_html=True)
st.markdown("**Real-time hard hat & safety vest detection with instant alerts**")

if DEMO_MODE:
    st.info("🌐 **Demo Mode** — Running on cloud. Webcam unavailable. [Clone & run locally](https://github.com/shantanutech7/safeeye) for live detection.")

st.divider()

# ─────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📹 Live Camera Feed")
    frame_window = st.empty()
    status_text  = st.empty()

with col2:
    st.subheader("📊 Live Stats")
    metric_violations = st.empty()
    metric_persons    = st.empty()
    metric_last       = st.empty()
    st.divider()
    st.subheader("🚨 Alert Log")
    alert_table = st.empty()

# ─────────────────────────────────────────
# CONTROLS
# ─────────────────────────────────────────
st.divider()
col_start, col_stop, col_gap = st.columns([1, 1, 4])

with col_start:
    start_btn = st.button("▶ Start Monitoring", type="primary",  use_container_width=True)
with col_stop:
    stop_btn  = st.button("⏹ Stop",             type="secondary", use_container_width=True)

# ─────────────────────────────────────────
# VIOLATION LOG
# ─────────────────────────────────────────
st.divider()
st.subheader("📋 Violation History")
log_placeholder = st.empty()

def load_log():
    log_file = "logs/violation_log.csv"
    if os.path.exists(log_file):
        return pd.read_csv(log_file)
    return pd.DataFrame(columns=["Timestamp", "Screenshot", "Status"])

# ─────────────────────────────────────────
# DEMO DATA
# ─────────────────────────────────────────
DEMO_VIOLATIONS = [
    {"Timestamp": "2026-06-12 09:15:32", "Screenshot": "violation_091532.jpg", "Status": "🔴 VIOLATION"},
    {"Timestamp": "2026-06-12 09:38:47", "Screenshot": "violation_093847.jpg", "Status": "🔴 VIOLATION"},
    {"Timestamp": "2026-06-12 10:02:11", "Screenshot": "violation_100211.jpg", "Status": "🔴 VIOLATION"},
    {"Timestamp": "2026-06-12 10:45:58", "Screenshot": "violation_104558.jpg", "Status": "🔴 VIOLATION"},
    {"Timestamp": "2026-06-12 11:20:03", "Screenshot": "violation_112003.jpg", "Status": "🔴 VIOLATION"},
]

# ─────────────────────────────────────────
# DEMO MODE DISPLAY
# ─────────────────────────────────────────
def run_demo():
    demo_df = pd.DataFrame(DEMO_VIOLATIONS)

    # Show demo camera placeholder
    frame_window.image(
        "https://placehold.co/640x480/1e2130/00c8ff?text=SafeEye+Live+Feed%0ARun+Locally+for+Webcam",
        use_container_width=True
    )

    status_text.success("🟢 Demo Mode Active")

    metric_violations.metric("🚨 Total Violations", 5)
    metric_persons.metric("👷 Persons Detected",   8)
    metric_last.metric("⏱ Last Violation",        "11:20:03")

    alert_table.dataframe(demo_df.tail(3), use_container_width=True)
    log_placeholder.dataframe(demo_df, use_container_width=True)

# ─────────────────────────────────────────
# ALERT CALLBACK
# ─────────────────────────────────────────
def alert_callback(screenshot_path, timestamp):
    from alerter import send_alert
    st.session_state.violation_count += 1
    st.session_state.last_violation   = timestamp
    st.session_state.alerts.append({
        "Time"      : timestamp,
        "Screenshot": screenshot_path or "N/A",
        "Status"    : "🔴 VIOLATION"
    })
    send_alert(screenshot_path, timestamp)

# ─────────────────────────────────────────
# LIVE MONITORING LOOP (local only)
# ─────────────────────────────────────────
def monitoring_loop():
    from ultralytics import YOLO

    model = YOLO("hardhat.pt")
    cap   = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    CONFIDENCE     = 0.4
    ALERT_COOLDOWN = 60
    last_alert     = 0
    frame_count    = 0
    GREEN = (0, 200, 0)
    RED   = (0, 0, 220)
    WHITE = (255, 255, 255)

    while st.session_state.running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.5)
            continue

        frame_count += 1
        if frame_count % 2 != 0:
            continue

        results         = model(frame, conf=CONFIDENCE, verbose=False)
        violation_found = False
        person_count    = 0
        violation_count = 0

        for result in results:
            for box in result.boxes:
                cls          = int(box.cls[0])
                conf_score   = float(box.conf[0])
                x1,y1,x2,y2 = map(int, box.xyxy[0])

                if cls == 1:  # NO-Hardhat — violation
                    violation_found  = True
                    violation_count += 1
                    person_count    += 1
                    label = f"NO HARDHAT {conf_score:.0%}"
                    cv2.rectangle(frame, (x1,y1), (x2,y2), RED, 2)
                    cv2.putText(frame, label, (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)

                elif cls == 0:  # Hardhat — safe
                    person_count += 1
                    label = f"HARDHAT OK {conf_score:.0%}"
                    cv2.rectangle(frame, (x1,y1), (x2,y2), GREEN, 2)
                    cv2.putText(frame, label, (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)

        # HUD bar
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0,0), (w,35), (20,20,20), -1)
        cv2.putText(frame, "SafeEye v1.0", (10,25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,255), 2)
        v_color = RED if violation_count > 0 else GREEN
        cv2.putText(frame, f"Violations: {violation_count}", (w-200,25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, v_color, 2)

        st.session_state.person_count = person_count

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_window.image(frame_rgb, use_container_width=True)

        metric_violations.metric("🚨 Violations", st.session_state.violation_count)
        metric_persons.metric("👷 Persons Detected", person_count)
        metric_last.metric("⏱ Last Violation", st.session_state.last_violation)

        if st.session_state.alerts:
            alert_table.dataframe(
                pd.DataFrame(st.session_state.alerts).tail(5),
                use_container_width=True
            )

        log_placeholder.dataframe(load_log(), use_container_width=True)

        now = time.time()
        if violation_found and (now - last_alert) > ALERT_COOLDOWN:
            timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            last_alert = now
            os.makedirs("alerts", exist_ok=True)
            path = f"alerts/violation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(path, frame)
            alert_callback(path, timestamp)

        status_text.success("🟢 Monitoring Active")

    cap.release()
    status_text.warning("🔴 Monitoring Stopped")

# ─────────────────────────────────────────
# BUTTON LOGIC
# ─────────────────────────────────────────
if DEMO_MODE:
    run_demo()
else:
    if start_btn:
        st.session_state.running = True
        monitoring_loop()

    if stop_btn:
        st.session_state.running = False

    log_placeholder.dataframe(load_log(), use_container_width=True)