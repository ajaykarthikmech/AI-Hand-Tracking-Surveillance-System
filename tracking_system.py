import cv2
import serial
import time
import mediapipe as mp
import requests

# 🔴 PUT YOUR NEW TOKEN HERE
TOKEN = "YOUR_CODE"
CHAT_ID = "YOUR_CHAT_ID"

# Timing controls
last_detect_time = 0
DETECT_DELAY = 5

last_alert_time = 0
ALERT_DELAY = 5

last_send_time = 0
SEND_DELAY = 0.05

# SERIAL
arduino = serial.Serial('COM6', 9600, timeout=1)  # change COM if needed
time.sleep(2)

# MEDIAPIPE
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

distance = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (320, 240))
    h, w, _ = frame.shape

    # Draw center "+"
    center_x = w // 2
    center_y = h // 2
    cv2.line(frame, (center_x - 15, center_y), (center_x + 15, center_y), (255,255,255), 2)
    cv2.line(frame, (center_x, center_y - 15), (center_x, center_y + 15), (255,255,255), 2)

    # =========================
    # READ DISTANCE FROM ARDUINO
    # =========================
    try:
        if arduino.in_waiting > 0:
            line = arduino.readline().decode().strip()

            if line.startswith("D:"):
                distance = int(line.split(":")[1])

                current_time = time.time()

                # ⚠️ TOO CLOSE ALERT
                if distance > 0 and distance < 15:
                    if current_time - last_alert_time > ALERT_DELAY:
                        requests.post(
                            f"https://api.telegram.org/bot{YOUR_CODE}/sendMessage",
                            data={
                                "chat_id": YOUR_CHAT_ID,
                                "text": f"⚠️ TOO CLOSE!\nDistance: {distance} cm"
                            }
                        )
                        last_alert_time = current_time
    except:
        pass

    # =========================
    # HAND DETECTION
    # =========================
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:

            x_list = []
            y_list = []

            for lm in hand_landmarks.landmark:
                x_list.append(int(lm.x * w))
                y_list.append(int(lm.y * h))

            x_min, x_max = min(x_list), max(x_list)
            y_min, y_max = min(y_list), max(y_list)

            # Draw red box
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0,0,255), 2)

            # Text
            cv2.putText(frame, "TARGET DETECTED", (10,25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

            current_time = time.time()

            # 🎯 TARGET DETECTED MESSAGE
            if current_time - last_detect_time > DETECT_DELAY:
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{YOUR_CODE}/sendMessage",
                        data={
                            "chat_id": YOUR_CODE,
                            "text": f"🎯 Target detected!\nDistance: {distance} cm"
                        }
                    )
                    last_detect_time = current_time
                except:
                    pass

            # Convert position → angle
            hand_center_x = (x_min + x_max) // 2
            angle = int((hand_center_x / w) * 180)
            angle = max(20, min(160, angle))

            # Send to Arduino (controlled rate)
            if time.time() - last_send_time > SEND_DELAY:
                arduino.write((str(angle) + "\n").encode())
                last_send_time = time.time()

            break

    # =========================
    # DISPLAY INFO
    # =========================
    #cv2.putText(frame, f"Distance: {distance} cm", (10,220),
                #cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)

    if distance > 0 and distance < 15:
        cv2.putText(frame, "TOO CLOSE!", (180,25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

    cv2.imshow("Tracking System", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

# SAFE STOP
arduino.write(b'90\n')

cap.release()
cv2.destroyAllWindows()
