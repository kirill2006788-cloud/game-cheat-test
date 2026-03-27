"""
=============================================================================
  TEST BOTS — Simulated Game Window with Yellow-Head Bots
=============================================================================
  Opens a fullscreen-like window with moving bots that have yellow oval heads.
  Use this to test and calibrate the cheat without running the actual game.
  
  Bots move randomly, simulating in-game targets.
  Press ESC or Q to exit.
=============================================================================
"""

import cv2
import numpy as np
import math
import random
import time


class Bot:
    """A simulated bot with a yellow oval head and a body."""

    def __init__(self, x: float, y: float, bounds: tuple):
        self.x = x
        self.y = y
        self.bounds_w, self.bounds_h = bounds
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-1, 1)
        self.head_w = random.randint(20, 35)
        self.head_h = random.randint(25, 45)
        self.body_h = random.randint(60, 100)
        self.body_w = random.randint(30, 50)
        self.change_timer = random.uniform(1, 4)
        self.last_change = time.time()
        self.alive = True
        # Blue shades (BGR: high B, low G, low R)
        self.head_color = (
            random.randint(200, 255),     # B — high blue
            random.randint(50, 120),      # G — low-mid green
            random.randint(0, 50),        # R — low red
        )

    def update(self, dt: float):
        now = time.time()
        if now - self.last_change > self.change_timer:
            self.vx = random.uniform(-3, 3)
            self.vy = random.uniform(-2, 2)
            self.change_timer = random.uniform(1, 4)
            self.last_change = now

        self.x += self.vx
        self.y += self.vy

        # Bounce off walls
        margin = 60
        if self.x < margin:
            self.x = margin
            self.vx = abs(self.vx)
        if self.x > self.bounds_w - margin:
            self.x = self.bounds_w - margin
            self.vx = -abs(self.vx)
        if self.y < margin + self.head_h:
            self.y = margin + self.head_h
            self.vy = abs(self.vy)
        if self.y > self.bounds_h - margin - self.body_h:
            self.y = self.bounds_h - margin - self.body_h
            self.vy = -abs(self.vy)

    def draw(self, frame: np.ndarray):
        cx = int(self.x)
        cy = int(self.y)

        # Body (gray rectangle)
        body_top = cy + self.head_h // 2
        body_left = cx - self.body_w // 2
        cv2.rectangle(frame,
                       (body_left, body_top),
                       (body_left + self.body_w, body_top + self.body_h),
                       (80, 80, 80), -1)
        cv2.rectangle(frame,
                       (body_left, body_top),
                       (body_left + self.body_w, body_top + self.body_h),
                       (50, 50, 50), 2)

        # Arms (lines)
        arm_y = body_top + 15
        cv2.line(frame, (body_left, arm_y), (body_left - 20, arm_y + 30), (80, 80, 80), 6)
        cv2.line(frame, (body_left + self.body_w, arm_y),
                 (body_left + self.body_w + 20, arm_y + 30), (80, 80, 80), 6)

        # Legs
        leg_y = body_top + self.body_h
        cv2.line(frame, (cx - 10, leg_y), (cx - 15, leg_y + 35), (60, 60, 60), 6)
        cv2.line(frame, (cx + 10, leg_y), (cx + 15, leg_y + 35), (60, 60, 60), 6)

        # Head — BLUE OVAL (this is what the cheat should detect)
        cv2.ellipse(frame, (cx, cy), (self.head_w // 2, self.head_h // 2), 0,
                     0, 360, self.head_color, -1)
        # Outline
        cv2.ellipse(frame, (cx, cy), (self.head_w // 2, self.head_h // 2), 0,
                     0, 360, (150, 80, 0), 2)

        # Eyes
        eye_offset_x = self.head_w // 6
        eye_y = cy - 3
        cv2.circle(frame, (cx - eye_offset_x, eye_y), 3, (50, 50, 50), -1)
        cv2.circle(frame, (cx + eye_offset_x, eye_y), 3, (50, 50, 50), -1)

        # Name tag
        cv2.putText(frame, "BOT", (cx - 15, cy - self.head_h // 2 - 8),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)


def main():
    WIDTH = 1280
    HEIGHT = 720
    NUM_BOTS = 8

    print("=" * 50)
    print("  TEST BOTS — Blue Head Bots")
    print("=" * 50)
    print(f"  Window: {WIDTH}x{HEIGHT}")
    print(f"  Bots: {NUM_BOTS} (BLUE heads)")
    print("  Press ESC or Q to exit.")
    print("=" * 50)

    # Create bots at random positions
    bots = []
    for _ in range(NUM_BOTS):
        x = random.randint(100, WIDTH - 100)
        y = random.randint(100, HEIGHT - 200)
        bots.append(Bot(x, y, (WIDTH, HEIGHT)))

    cv2.namedWindow("TEST GAME — Bots with Yellow Heads", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("TEST GAME — Bots with Yellow Heads", WIDTH, HEIGHT)

    last_time = time.time()

    while True:
        now = time.time()
        dt = now - last_time
        last_time = now

        # Dark background (like a game map)
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        # Floor gradient
        for y in range(HEIGHT):
            shade = int(30 + (y / HEIGHT) * 25)
            frame[y, :] = (shade, shade + 5, shade)

        # Grid lines (like a game arena)
        for x in range(0, WIDTH, 80):
            cv2.line(frame, (x, 0), (x, HEIGHT), (40, 40, 40), 1)
        for y in range(0, HEIGHT, 80):
            cv2.line(frame, (0, y), (WIDTH, y), (40, 40, 40), 1)

        # Some obstacles (cover)
        cv2.rectangle(frame, (200, 300), (280, 500), (60, 70, 60), -1)
        cv2.rectangle(frame, (600, 150), (680, 350), (60, 70, 60), -1)
        cv2.rectangle(frame, (900, 400), (1000, 600), (60, 70, 60), -1)
        cv2.rectangle(frame, (400, 500), (550, 550), (70, 60, 50), -1)

        # Update and draw bots
        for bot in bots:
            bot.update(dt)
            bot.draw(frame)

        # HUD
        cv2.putText(frame, "TEST GAME — Yellow Head Bots", (10, 25),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 100), 2)
        cv2.putText(frame, f"Bots: {NUM_BOTS} | Press ESC to exit", (10, 50),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        # Crosshair in center
        cx, cy = WIDTH // 2, HEIGHT // 2
        cv2.line(frame, (cx - 15, cy), (cx + 15, cy), (0, 255, 0), 1)
        cv2.line(frame, (cx, cy - 15), (cx, cy + 15), (0, 255, 0), 1)

        cv2.imshow("TEST GAME — Bots with Yellow Heads", frame)

        key = cv2.waitKey(16) & 0xFF  # ~60fps
        if key == 27 or key == ord("q"):
            break

    cv2.destroyAllWindows()
    print("\n  [OK] Test window closed.")


if __name__ == "__main__":
    main()
