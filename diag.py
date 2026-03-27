"""Quick diagnostic: how many targets does the detector see right now?"""
import mss, cv2, numpy as np, json, math

config = json.load(open("config.json", encoding="utf-8"))
sct = mss.mss()
mon = sct.monitors[1]
img = np.array(sct.grab(mon))
frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

for c in config["detection"]["colors"]:
    lower = np.array(c["lower_hsv"], dtype=np.uint8)
    upper = np.array(c["upper_hsv"], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    raw_px = cv2.countNonZero(mask)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid = [cnt for cnt in contours if cv2.contourArea(cnt) >= 15]
    print(f"\n{c['name']}: {raw_px} pixels, {len(contours)} contours, {len(valid)} valid")
    for cnt in valid[:15]:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        M = cv2.moments(cnt)
        cx = int(M["m10"] / M["m00"]) if M["m00"] > 0 else x
        cy = int(M["m01"] / M["m00"]) if M["m00"] > 0 else y
        print(f"  center=({cx},{cy}) size={w}x{h} area={int(area)}")

# Save annotated image
vis = frame.copy()
for c in config["detection"]["colors"]:
    lower = np.array(c["lower_hsv"], dtype=np.uint8)
    upper = np.array(c["upper_hsv"], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    color = (0, 165, 255) if "orange" in c["name"] else (255, 200, 0)
    for cnt in contours:
        if cv2.contourArea(cnt) >= 15:
            cv2.drawContours(vis, [cnt], -1, color, 2)
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.putText(vis, c["name"], (x, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

cv2.imwrite("diag_result.png", cv2.resize(vis, (960, 540)))
print("\nSaved diag_result.png")
