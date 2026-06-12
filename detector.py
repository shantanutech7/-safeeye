# detector.py
import cv2
from ultralytics import YOLO
import time

MODEL_PATH = "hardhat.pt"
CONFIDENCE = 0.4
FRAME_SKIP = 2
ALERT_COOLDOWN = 60

GREEN  = (0, 200, 0)
RED    = (0, 0, 220)
WHITE  = (255, 255, 255)

def load_model():
    print("[SafeEye] Loading YOLOv8 hardhat model...")
    model = YOLO(MODEL_PATH)
    print("[SafeEye] Model loaded successfully.")
    print(f"[SafeEye] Classes: {model.names}")
    return model

def draw_box(frame, x1, y1, x2, y2, label, color):
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(frame, (x1, y1 - label_size[1] - 8),
                  (x1 + label_size[0] + 4, y1), color, -1)
    cv2.putText(frame, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)

def draw_hud(frame, violation_count, person_count, fps):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 40), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(frame, "SafeEye v1.0", (10, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (w - 120, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1)
    cv2.putText(frame, f"Persons: {person_count}", (220, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1)
    v_color = RED if violation_count > 0 else GREEN
    cv2.putText(frame, f"Violations: {violation_count}", (360, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, v_color, 2)

def save_screenshot(frame):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = f"alerts/violation_{timestamp}.jpg"
    cv2.imwrite(path, frame)
    print(f"[SafeEye] Screenshot saved: {path}")
    return path, timestamp

def run_detection(alert_callback=None):
    model = load_model()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[SafeEye] ERROR: Cannot open webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    cv2.namedWindow("SafeEye — Factory Safety Monitor", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("SafeEye — Factory Safety Monitor", cv2.WND_PROP_TOPMOST, 1)

    print("[SafeEye] Camera started. Press Q to quit.")

    frame_count = 0
    last_alert_time = 0
    fps = 0
    fps_timer = time.time()

    while True:
        ret, frame = cap.read()

        if not ret:
            print("[SafeEye] Frame read failed. Retrying...")
            time.sleep(0.5)
            continue

        frame_count += 1

        if frame_count % 10 == 0:
            fps = 10 / (time.time() - fps_timer)
            fps_timer = time.time()

        if frame_count % FRAME_SKIP != 0:
            cv2.imshow("SafeEye — Factory Safety Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        results = model(frame, conf=CONFIDENCE, verbose=False)

        violation_found = False
        person_count    = 0
        violation_count = 0

        for result in results:
            for box in result.boxes:
                cls  = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                if cls == 1:  # NO-Hardhat — VIOLATION
                    violation_found  = True
                    violation_count += 1
                    person_count    += 1
                    label = f"NO HARDHAT {conf:.0%}"
                    draw_box(frame, x1, y1, x2, y2, label, RED)

                elif cls == 0:  # Hardhat — SAFE
                    person_count += 1
                    label = f"HARDHAT OK {conf:.0%}"
                    draw_box(frame, x1, y1, x2, y2, label, GREEN)

        draw_hud(frame, violation_count, person_count, fps)

        now = time.time()
        if violation_found and (now - last_alert_time) > ALERT_COOLDOWN:
            screenshot_path, timestamp = save_screenshot(frame)
            last_alert_time = now
            if alert_callback:
                alert_callback(screenshot_path, timestamp)
            else:
                print(f"[SafeEye] VIOLATION at {timestamp} — no alert callback set yet.")

        cv2.imshow("SafeEye — Factory Safety Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[SafeEye] Shutting down.")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_detection(alert_callback=None)