"""
Quick diagnostic: captures screen, shows HSV color at the center
and around the crosshair area. Helps determine exact target color.
"""

import cv2
import numpy as np
import mss
import json
from pathlib import Path

config = json.load(open(Path(__file__).parent / "config.json", encoding="utf-8"))

sct = mss.mss()
mon = sct.monitors[config["capture"]["monitor_index"]]

img = np.array(sct.grab(mon))
frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

h, w = frame.shape[:2]
cx, cy = w // 2, h // 2

print(f"Screen: {w}x{h}")
print(f"Center pixel BGR: {frame[cy, cx]}")
print(f"Center pixel HSV: {hsv[cy, cx]}")
print()

# Sample a grid around center
print("=== HSV values in 100x100 area around center ===")
region_size = 50
unique_colors = {}
for dy in range(-region_size, region_size, 5):
    for dx in range(-region_size, region_size, 5):
        py, px = cy + dy, cx + dx
        if 0 <= py < h and 0 <= px < w:
            bgr = tuple(frame[py, px].tolist())
            hsv_val = tuple(hsv[py, px].tolist())
            # Skip very dark pixels (background)
            if bgr[0] > 60 or bgr[1] > 60 or bgr[2] > 60:
                key = (hsv_val[0] // 5 * 5, hsv_val[1] // 50 * 50, hsv_val[2] // 50 * 50)
                if key not in unique_colors:
                    unique_colors[key] = 0
                unique_colors[key] += 1

print("HSV clusters (H, S, V) -> count:")
for k, v in sorted(unique_colors.items(), key=lambda x: -x[1]):
    print(f"  H={k[0]:3d}, S={k[1]:3d}, V={k[2]:3d} -> {v} pixels")

# Also try to find any bright/colorful objects on screen
print("\n=== Scanning full screen for non-dark colorful areas ===")
# Mask out dark pixels
bright_mask = (frame[:,:,0].astype(int) + frame[:,:,1].astype(int) + frame[:,:,2].astype(int)) > 150
bright_hsv = hsv[bright_mask]
if len(bright_hsv) > 0:
    h_vals = bright_hsv[:, 0]
    print(f"Bright pixels found: {len(bright_hsv)}")
    # Histogram of H values
    hist, bins = np.histogram(h_vals, bins=36, range=(0, 180))
    print("Hue histogram (0-180):")
    for i, count in enumerate(hist):
        if count > 100:
            h_start = int(bins[i])
            h_end = int(bins[i+1])
            bar = "#" * min(count // 500, 50)
            print(f"  H {h_start:3d}-{h_end:3d}: {count:6d} {bar}")

# Save a debug image
cv2.rectangle(frame, (cx-region_size, cy-region_size), (cx+region_size, cy+region_size), (0,255,0), 2)
cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

# Crop center area for inspection
crop = frame[max(0,cy-150):cy+150, max(0,cx-150):cx+150]
cv2.imwrite("C:\\Users\\user\\Projects\\game-cheat-test\\debug_center.png", crop)
cv2.imwrite("C:\\Users\\user\\Projects\\game-cheat-test\\debug_full.png", cv2.resize(frame, (960, 540)))
print("\nSaved: debug_center.png, debug_full.png")
