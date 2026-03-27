"""
=============================================================================
  COLOR TUNER — HSV Color Range Calibrator
=============================================================================
  Use this tool to find the perfect HSV range for detecting yellow heads.
  Captures your screen in real-time and shows what the detector "sees".
  
  Adjust sliders to tune detection, then copy values to config.json.
=============================================================================
"""

import cv2
import numpy as np
import mss
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    det = config["detection"]
    lower = det["color_lower_hsv"]
    upper = det["color_upper_hsv"]

    cv2.namedWindow("Color Tuner", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Color Tuner", 800, 600)

    cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Controls", 400, 350)

    # Trackbars
    cv2.createTrackbar("H Low", "Controls", lower[0], 179, lambda x: None)
    cv2.createTrackbar("S Low", "Controls", lower[1], 255, lambda x: None)
    cv2.createTrackbar("V Low", "Controls", lower[2], 255, lambda x: None)
    cv2.createTrackbar("H High", "Controls", upper[0], 179, lambda x: None)
    cv2.createTrackbar("S High", "Controls", upper[1], 255, lambda x: None)
    cv2.createTrackbar("V High", "Controls", upper[2], 255, lambda x: None)
    cv2.createTrackbar("Min Area", "Controls", det["min_contour_area"], 5000, lambda x: None)
    cv2.createTrackbar("Max Area", "Controls", min(det["max_contour_area"], 50000), 50000, lambda x: None)

    sct = mss.mss()
    mon = sct.monitors[config["capture"]["monitor_index"]]

    print("=" * 50)
    print("  COLOR TUNER")
    print("=" * 50)
    print("  Adjust sliders to find yellow head range.")
    print("  Press 'S' to save values to config.json.")
    print("  Press 'Q' or ESC to exit.")
    print("=" * 50)

    while True:
        img = np.array(sct.grab(mon))
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Read trackbar values
        h_low = cv2.getTrackbarPos("H Low", "Controls")
        s_low = cv2.getTrackbarPos("S Low", "Controls")
        v_low = cv2.getTrackbarPos("V Low", "Controls")
        h_high = cv2.getTrackbarPos("H High", "Controls")
        s_high = cv2.getTrackbarPos("S High", "Controls")
        v_high = cv2.getTrackbarPos("V High", "Controls")
        min_area = cv2.getTrackbarPos("Min Area", "Controls")
        max_area = cv2.getTrackbarPos("Max Area", "Controls")

        lower_hsv = np.array([h_low, s_low, v_low], dtype=np.uint8)
        upper_hsv = np.array([h_high, s_high, v_high], dtype=np.uint8)

        # HSV mask
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Find contours and draw on frame
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        result = frame.copy()
        count = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < max(min_area, 1) or area > max(max_area, 1):
                continue
            if len(cnt) < 5:
                continue

            count += 1
            ellipse = cv2.fitEllipse(cnt)
            cv2.ellipse(result, ellipse, (0, 255, 0), 2)

            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 255), 1)

            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.circle(result, (cx, cy), 4, (0, 0, 255), -1)
                cv2.putText(result, f"A={int(area)}", (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        # Info overlay
        info = f"HSV: [{h_low},{s_low},{v_low}]-[{h_high},{s_high},{v_high}] | Objects: {count}"
        cv2.putText(result, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Show mask and result side by side (scaled down)
        scale = 720 / result.shape[0]
        w_disp = int(result.shape[1] * scale)
        h_disp = 720

        result_small = cv2.resize(result, (w_disp, h_disp))
        mask_colored = cv2.cvtColor(cv2.resize(mask, (w_disp, h_disp)), cv2.COLOR_GRAY2BGR)

        combined = np.hstack([result_small, mask_colored])
        cv2.imshow("Color Tuner", combined)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break
        elif key == ord("s"):
            config["detection"]["color_lower_hsv"] = [h_low, s_low, v_low]
            config["detection"]["color_upper_hsv"] = [h_high, s_high, v_high]
            config["detection"]["min_contour_area"] = min_area
            config["detection"]["max_contour_area"] = max_area
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            print(f"  [SAVED] HSV: [{h_low},{s_low},{v_low}]-[{h_high},{s_high},{v_high}]")
            print(f"          Area: {min_area} - {max_area}")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
