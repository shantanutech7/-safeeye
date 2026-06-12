# app.py
import streamlit as st
import cv2
import pandas as pd
import os
import threading
import time
from PIL import Image
from detector import run_detection
from alerter import send_alert

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="SafeEye — Factory Safety Monitor",
    page_icon="🦺",
    layout="wide"
)

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
    .violation { border-left: 4px solid #ff4b4b; }
    .safe      { border-left: 4px solid #00c853; }
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
st.divider()

# ─────────────────────────────────────────
# LAYOUT — two columns
# ─────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📹 Live Camera Feed")
    frame_window = st.image([])
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
# VIOLATION LOG TABLE
# ─────────────────────────────────────────
st.divider()
st.subheader("📋 Violation History")
log_placeholder = st.empty()

def load_log():
    log_file = "logs/violation_log.csv"
    if os.path.exists(log_file):
        df = pd.read_csv(log_file)
        return df
    return pd.DataFrame(columns=["Timestamp", "Screenshot", "Status"])

# ─────────────────────────────────────────
# ALERT CALLBACK — called by detector
# ─────────────────────────────────────────
def alert_callback(screenshot_path, timestamp):
    st.session_state.violation_count += 1
    st.session_state.last_violation   = timestamp
    st.session_state.alerts.append({
        "Time"      : timestamp,
        "Screenshot": screenshot_path or "N/A",
        "Status"    : "🔴 VIOLATION"
    })
    send_alert(screenshot_path, timestamp)

# ─────────────────────────────────────────
# MAIN MONITORING LOOP
# ─────────────────────────────────────────
def monitoring_loop():
    from ultralytics import YOLO
    import time

    model = YOLO("yolov8n.pt")
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

        results  = model(frame, conf=CONFIDENCE, verbose=False)
        violation_found = False
        person_count    = 0
        violation_count = 0

        for result in results:
            for box in result.boxes:
                cls        = int(box.cls[0])
                conf       = float(box.conf[0])
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                label_name = model.names[cls]

                if cls == 0:  # person
                    person_count    += 1
                    violation_found  = True
                    violation_count += 1
                    label = f"NO HARDHAT {conf:.0%}"
                    cv2.rectangle(frame, (x1,y1), (x2,y2), RED, 2)
                    cv2.putText(frame, label, (x1,y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)
                else:
                    label = f"{label_name} {conf:.0%}"
                    cv2.rectangle(frame, (x1,y1), (x2,y2), GREEN, 2)
                    cv2.putText(frame, label, (x1,y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)

        # HUD
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0,0), (w,35), (20,20,20), -1)
        cv2.putText(frame, "SafeEye v1.0", (10,25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,255), 2)
        v_color = RED if violation_count > 0 else GREEN
        cv2.putText(frame, f"Violations: {violation_count}", (w-200,25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, v_color, 2)

        # Update stats
        st.session_state.person_count = person_count

        # Show frame in Streamlit
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_window.image(frame_rgb, use_container_width=True)

        # Update metrics
        metric_violations.metric("🚨 Violations", st.session_state.violation_count)
        metric_persons.metric("👷 Persons Detected", person_count)
        metric_last.metric("⏱ Last Violation", st.session_state.last_violation)

        # Alert log
        if st.session_state.alerts:
            alert_table.dataframe(
                pd.DataFrame(st.session_state.alerts).tail(5),
                use_container_width=True
            )

        # Violation log from CSV
        log_placeholder.dataframe(
            load_log(),
            use_container_width=True
        )

        # Trigger alert
        now = time.time()
        if violation_found and (now - last_alert) > ALERT_COOLDOWN:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            last_alert = now

            # Save screenshot
            os.makedirs("alerts", exist_ok=True)
            path = f"alerts/violation_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(path, frame)
            alert_callback(path, timestamp)

        status_text.success("🟢 Monitoring Active")

    cap.release()
    status_text.warning("🔴 Monitoring Stopped")

# ─────────────────────────────────────────
# BUTTON LOGIC
# ─────────────────────────────────────────
if start_btn:
    st.session_state.running = True
    monitoring_loop()

if stop_btn:
    st.session_state.running = False

# Show existing log on load
log_placeholder.dataframe(load_log(), use_container_width=True)