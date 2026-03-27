"""
=============================================================================
  AIM TRAINER CHEAT v9 — GOD MODE VIP+
=============================================================================
  1. AUTO-BLACKLIST static UI (logos, icons) — never locks on them
  2. MOTION TRACKING — calculates target velocity in real-time
  3. PREDICTIVE AIM — leads moving targets, fires where they WILL be
  4. ADAPTIVE ENGAGE:
     - Static target: Snap → Verify → Fire (precision)
     - Moving target: Predict → Snap+Fire instant (speed)
  5. AUTO-CALIBRATION from first shot

  SHIFT = Aim+Fire  F5=Calibrate  F8=Game  F10=EXIT
=============================================================================
"""

import json
import math
import time
import ctypes
from pathlib import Path

import cv2
import numpy as np
import mss
import keyboard

ctypes.windll.user32.SetProcessDPIAware()
ctypes.windll.winmm.timeBeginPeriod(1)

# --------------------------------------------------------------------------- #
#  Mouse
# --------------------------------------------------------------------------- #
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [("type", ctypes.c_ulong), ("ii", _INPUT)]


SendInput = ctypes.windll.user32.SendInput
_extra = ctypes.c_ulong(0)
_ep = ctypes.pointer(_extra)


def move_mouse(dx, dy):
    i = INPUT(); i.type = INPUT_MOUSE
    i.ii.mi = MOUSEINPUT(int(dx), int(dy), 0, MOUSEEVENTF_MOVE, 0, _ep)
    SendInput(1, ctypes.pointer(i), ctypes.sizeof(i))


def click():
    d = INPUT(); d.type = INPUT_MOUSE
    d.ii.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, _ep)
    u = INPUT(); u.type = INPUT_MOUSE
    u.ii.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, _ep)
    SendInput(1, ctypes.pointer(d), ctypes.sizeof(d))
    SendInput(1, ctypes.pointer(u), ctypes.sizeof(u))


def snap_and_click(dx, dy):
    """Move + click in ONE system call — zero gap."""
    arr = (INPUT * 3)()
    arr[0].type = INPUT_MOUSE
    arr[0].ii.mi = MOUSEINPUT(int(dx), int(dy), 0, MOUSEEVENTF_MOVE, 0, _ep)
    arr[1].type = INPUT_MOUSE
    arr[1].ii.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, _ep)
    arr[2].type = INPUT_MOUSE
    arr[2].ii.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, _ep)
    SendInput(3, ctypes.pointer(arr[0]), ctypes.sizeof(INPUT))


CONFIG_PATH = Path(__file__).parent / "config.json"
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f: return json.load(f)
def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f: json.dump(cfg, f, indent=4, ensure_ascii=False)


# --------------------------------------------------------------------------- #
#  Detector
# --------------------------------------------------------------------------- #
class Detector:
    def __init__(self, config, ign_top=0, ign_bot=9999):
        det = config["detection"]
        self.merge_dist = det["merge_distance"]
        self.ign_top, self.ign_bot = ign_top, ign_bot
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.strict = True
        bc = next(c for c in det["colors"] if c["name"] == "blue_ring")
        self.blue_lo = np.array(bc["lower_hsv"], np.uint8)
        self.blue_hi = np.array(bc["upper_hsv"], np.uint8)
        self.b_min, self.b_max = bc.get("min_area", 150), bc.get("max_area", 25000)
        self.b_circ = bc.get("min_circularity", 0.35)
        oc = next(c for c in det["colors"] if c["name"] == "orange_center")
        self.or_lo = np.array(oc["lower_hsv"], np.uint8)
        self.or_hi = np.array(oc["upper_hsv"], np.uint8)
        self.o_min, self.o_max = oc.get("min_area", 10), oc.get("max_area", 2000)

    def detect(self, hsv, s=1):
        raw_mask = cv2.inRange(hsv, self.blue_lo, self.blue_hi)
        mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, self.kernel, iterations=1)
        ad = s * s
        bmin, bmax = self.b_min / ad, self.b_max / ad
        it, ib = self.ign_top / s, self.ign_bot / s
        mh, mw = mask.shape[:2]
        blues = []
        for cnt in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            a = cv2.contourArea(cnt)
            if a < bmin or a > bmax: continue
            p = cv2.arcLength(cnt, True)
            if p > 0 and (12.566 * a / (p * p)) < self.b_circ: continue
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 3 and h > 3:
                # Check fill on RAW mask (before morph close filled the gaps)
                # Solid sphere: ~0.65-0.85 | Logo with lines/gaps: ~0.25-0.45
                roi = raw_mask[max(0,y):min(mh,y+h), max(0,x):min(mw,x+w)]
                fill = cv2.countNonZero(roi) / (w * h)
                if fill < 0.50:
                    continue
            M = cv2.moments(cnt)
            if M["m00"] == 0: continue
            cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
            if cy < it or cy > ib: continue
            blues.append({"cx": cx*s, "cy": cy*s, "w": w*s, "h": h*s})
        if not self.strict:
            return blues
        omask = cv2.inRange(hsv, self.or_lo, self.or_hi)
        oranges = []
        for cnt in cv2.findContours(omask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            a = cv2.contourArea(cnt)
            if a < self.o_min/ad or a > self.o_max/ad: continue
            M = cv2.moments(cnt)
            if M["m00"] == 0: continue
            oranges.append({"cx": int(M["m10"]/M["m00"])*s, "cy": int(M["m01"]/M["m00"])*s})
        out = []
        for b in blues:
            for o in oranges:
                if math.hypot(b["cx"]-o["cx"], b["cy"]-o["cy"]) < self.merge_dist:
                    out.append({"cx": o["cx"], "cy": o["cy"], "w": b["w"], "h": b["h"]})
                    break
        return out

    def precise(self, raw, ax, ay, W, H):
        x1, y1 = max(0, ax-50), max(0, ay-50)
        x2, y2 = min(W, ax+50), min(H, ay+50)
        crop = np.ascontiguousarray(raw[y1:y2, x1:x2, :3])
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        m = cv2.inRange(hsv, self.blue_lo, self.blue_hi)
        M = cv2.moments(m)
        if M["m00"] > 30:
            return int(M["m10"]/M["m00"])+x1, int(M["m01"]/M["m00"])+y1
        return ax, ay


# --------------------------------------------------------------------------- #
#  MAIN
# --------------------------------------------------------------------------- #
def main():
    cfg = load_config()
    aim_cfg = cfg["aimbot"]
    sensitivity = aim_cfg.get("sensitivity", 1.0)
    fov = aim_cfg["fov_radius"]
    act_key = aim_cfg["activation_key"]
    center_offset_y = aim_cfg.get("center_offset_y", 0)

    print("=" * 60, flush=True)
    print("  AIM TRAINER CHEAT v9 — GOD MODE VIP+", flush=True)
    print("=" * 60, flush=True)

    sct = mss.mss()
    mon = sct.monitors[cfg["capture"]["monitor_index"]]
    W, H = mon["width"], mon["height"]
    cx, cy = W // 2, H // 2 + center_offset_y

    det_cfg = cfg["detection"]
    det = Detector(cfg, ign_top=det_cfg.get("ignore_top_px", 80),
                   ign_bot=H - det_cfg.get("ignore_bottom_px", 220))
    DS = 2

    # --- TUNING ---
    FIRE_DIST = 8
    PREDICT_S = 0.018     # predict 18ms ahead for moving targets
    MOVE_THRESH = 120     # px/s — above = moving target
    STATIC_THRESH = 20    # frames to blacklist as UI element
    GRID = 15             # grid cell size for static filter
    VERIFY_WAIT = 0.010

    # State
    aim_on = aim_cfg["enabled"]
    fire_on = cfg["triggerbot"]["enabled"]
    esp_on = True
    running = True
    shots = 0
    cal_done = sensitivity != 1.0

    # Motion tracking
    prev_tracked = []
    prev_time = time.time()

    # Static UI blacklist
    static_grid = {}

    fc, fps_t, fps = 0, time.time(), 0.0
    cooldown = 0.0
    radar = np.zeros((220, 320, 3), dtype=np.uint8)

    def grab():
        raw = np.array(sct.grab(mon))
        small = np.ascontiguousarray(raw[::DS, ::DS, :3])
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        return raw, det.detect(hsv, s=DS)

    def closest(tgts):
        return min(tgts, key=lambda t: (t["cx"]-cx)**2 + (t["cy"]-cy)**2)

    def track(new_tgts, old_tgts, dt):
        result = []
        used = set()
        for nt in new_tgts:
            bi, bd = -1, 80
            for i, ot in enumerate(old_tgts):
                if i in used: continue
                d = math.hypot(nt["cx"]-ot["cx"], nt["cy"]-ot["cy"])
                if d < bd: bd, bi = d, i
            if bi >= 0:
                ot = old_tgts[bi]; used.add(bi)
                if dt > 0.001:
                    vx = (nt["cx"]-ot["cx"])/dt * 0.6 + ot.get("vx",0) * 0.4
                    vy = (nt["cy"]-ot["cy"])/dt * 0.6 + ot.get("vy",0) * 0.4
                else:
                    vx, vy = ot.get("vx",0), ot.get("vy",0)
                result.append({**nt, "vx": vx, "vy": vy})
            else:
                result.append({**nt, "vx": 0.0, "vy": 0.0})
        return result

    def update_static(tgts):
        seen = set()
        for t in tgts:
            k = (t["cx"]//GRID, t["cy"]//GRID)
            seen.add(k)
            static_grid[k] = static_grid.get(k, 0) + 1
        for k in list(static_grid):
            if k not in seen:
                static_grid[k] = max(0, static_grid[k] - 2)
                if static_grid[k] == 0: del static_grid[k]

    def is_ui(t):
        return static_grid.get((t["cx"]//GRID, t["cy"]//GRID), 0) > STATIC_THRESH

    # Hotkeys
    def toggle_aim():
        nonlocal aim_on; aim_on = not aim_on
        print(f"  Aim: {'ON' if aim_on else 'OFF'}", flush=True)
    def toggle_esp():
        nonlocal esp_on; esp_on = not esp_on
        if not esp_on:
            try: cv2.destroyAllWindows()
            except: pass
        print(f"  Radar: {'ON' if esp_on else 'OFF'}", flush=True)
    def toggle_fire():
        nonlocal fire_on; fire_on = not fire_on
        print(f"  Fire: {'ON' if fire_on else 'OFF'}", flush=True)
    def do_cal():
        nonlocal sensitivity, cal_done
        print("  [CAL] Measuring...", flush=True)
        time.sleep(0.3)
        _, t1 = grab()
        if not t1: print("  [CAL] No targets!", flush=True); return
        ref = closest(t1)
        move_mouse(150, 0); time.sleep(0.12)
        _, t2 = grab()
        move_mouse(-150, 0)
        if not t2: print("  [CAL] Lost.", flush=True); return
        b = min(t2, key=lambda t: abs(t["cy"]-ref["cy"]))
        mv = ref["cx"] - b["cx"]
        if mv > 10:
            sensitivity = round(mv / 150, 4)
            cfg["aimbot"]["sensitivity"] = sensitivity
            save_config(cfg); cal_done = True
            print(f"  [CAL] sensitivity = {sensitivity} SAVED", flush=True)
        else:
            print(f"  [CAL] Failed ({mv}px)", flush=True)
    def off_up():
        nonlocal center_offset_y, cy
        center_offset_y -= 5; cy = H//2 + center_offset_y
        cfg["aimbot"]["center_offset_y"] = center_offset_y; save_config(cfg)
        print(f"  offset: {center_offset_y}", flush=True)
    def off_dn():
        nonlocal center_offset_y, cy
        center_offset_y += 5; cy = H//2 + center_offset_y
        cfg["aimbot"]["center_offset_y"] = center_offset_y; save_config(cfg)
        print(f"  offset: {center_offset_y}", flush=True)
    def do_exit():
        nonlocal running; running = False
    def toggle_game():
        det.strict = not det.strict
        print(f"  Game: {'3DAim' if det.strict else 'AimLab'}", flush=True)

    hotkeys = cfg["hotkeys"]
    keyboard.on_press_key(hotkeys["toggle_aimbot"], lambda _: toggle_aim())
    keyboard.on_press_key(hotkeys["toggle_esp"], lambda _: toggle_esp())
    keyboard.on_press_key(hotkeys["toggle_triggerbot"], lambda _: toggle_fire())
    keyboard.on_press_key("f5", lambda _: do_cal())
    keyboard.on_press_key("f6", lambda _: off_up())
    keyboard.on_press_key("f7", lambda _: off_dn())
    keyboard.on_press_key("f8", lambda _: toggle_game())
    keyboard.on_press_key(hotkeys["exit"], lambda _: do_exit())

    print(f"  {W}x{H}  cross:({cx},{cy})  sens:{sensitivity}", flush=True)
    if not cal_done:
        print("  >>> F5 to calibrate (or auto-cal on first shot) <<<", flush=True)
    print(f"  Game: {'3DAim' if det.strict else 'AimLab'}", flush=True)
    print("  SHIFT=Fire  F5=Cal  F8=Game  F10=Exit", flush=True)
    print("  [OK] GOD MODE ACTIVE!\n", flush=True)

    # ===== MAIN LOOP =====
    while running:
        t0 = time.time()
        dt = t0 - prev_time
        prev_time = t0

        raw, all_targets = grab()

        # Update static blacklist
        update_static(all_targets)

        # Filter out UI elements (logos, icons)
        targets = [t for t in all_targets if not is_ui(t)]

        # Track motion (velocity)
        tracked = track(targets, prev_tracked, dt)
        prev_tracked = tracked

        aim_state = "SCAN"

        # --- ENGAGE ---
        if aim_on and fire_on and keyboard.is_pressed(act_key) and t0 > cooldown and tracked:
            best = closest(tracked)
            spd = math.sqrt(best["vx"]**2 + best["vy"]**2)
            is_moving = spd > MOVE_THRESH

            bx, by = best["cx"], best["cy"]
            # Precision refinement on first detection
            if not is_moving:
                bx, by = det.precise(raw, bx, by, W, H)

            dx, dy = bx - cx, by - cy
            dist = math.sqrt(dx*dx + dy*dy)

            if dist < fov:
                if is_moving:
                    # === MOVING TARGET: Predict + Snap + Fire ===
                    pred_x = best["cx"] + best["vx"] * PREDICT_S
                    pred_y = best["cy"] + best["vy"] * PREDICT_S
                    pdx = pred_x - cx
                    pdy = pred_y - cy
                    mx = int(round(pdx / sensitivity))
                    my = int(round(pdy / sensitivity))
                    snap_and_click(mx, my)
                    shots += 1
                    cooldown = t0 + 0.010
                    aim_state = "PREDICT+FIRE"

                elif dist <= FIRE_DIST:
                    # Already on target
                    click()
                    shots += 1
                    cooldown = t0 + 0.008
                    aim_state = "FIRE"

                else:
                    # === STATIC TARGET: Snap → Verify → Fire ===
                    smx = int(round(dx / sensitivity))
                    smy = int(round(dy / sensitivity))
                    if smx or smy:
                        move_mouse(smx, smy)

                    fired = False
                    last_d = dist
                    for att in range(3):
                        time.sleep(VERIFY_WAIT)
                        raw2, t2_all = grab()
                        update_static(t2_all)
                        t2 = [t for t in t2_all if not is_ui(t)]
                        if not t2: break

                        b2 = closest(t2)
                        px2, py2 = det.precise(raw2, b2["cx"], b2["cy"], W, H)
                        dx2, dy2 = px2 - cx, py2 - cy
                        d2 = math.sqrt(dx2*dx2 + dy2*dy2)

                        # Auto-calibrate from first snap
                        if att == 0 and not cal_done and abs(smx) > 30:
                            shift = dx - dx2
                            if abs(shift) > 15:
                                ns = shift / smx
                                if 0.3 < ns < 5.0:
                                    sensitivity = round(ns, 4)
                                    cfg["aimbot"]["sensitivity"] = sensitivity
                                    save_config(cfg); cal_done = True
                                    print(f"  AUTO-CAL: {sensitivity}", flush=True)

                        if d2 <= FIRE_DIST:
                            click(); shots += 1; fired = True
                            aim_state = "VERIFIED+FIRE"; break

                        kp = [0.55, 0.45, 0.35][att]
                        cmx = int(round(dx2 * kp / sensitivity))
                        cmy = int(round(dy2 * kp / sensitivity))
                        if cmx or cmy:
                            move_mouse(cmx, cmy)
                        last_d = d2
                        aim_state = "CORRECT"

                    if not fired and last_d < FIRE_DIST * 3:
                        click(); shots += 1
                        aim_state = "FIRE"

                    cooldown = time.time() + 0.008

        # --- RADAR ---
        if esp_on and fc % 12 == 0:
            radar[:] = 20
            rcx, rcy = 160, 110
            cv2.drawMarker(radar, (rcx, rcy), (0, 255, 0), cv2.MARKER_CROSS, 12, 1)
            cv2.circle(radar, (rcx, rcy), fov // 6, (40, 40, 40), 1)
            for t in tracked:
                rx = max(2, min(317, rcx + (t["cx"]-cx)//6))
                ry = max(2, min(217, rcy + (t["cy"]-cy)//6))
                spd = math.sqrt(t["vx"]**2 + t["vy"]**2)
                col = (0, 0, 255) if spd > MOVE_THRESH else (0, 200, 255)
                cv2.circle(radar, (rx, ry), 4, col, -1)
                if spd > MOVE_THRESH:
                    ex = int(rx + t["vx"]*PREDICT_S/6)
                    ey = int(ry + t["vy"]*PREDICT_S/6)
                    cv2.arrowedLine(radar, (rx, ry), (ex, ey), (0, 255, 255), 1)
            # Show blacklisted UI as gray X
            for t in all_targets:
                if is_ui(t):
                    ux = max(2, min(317, rcx + (t["cx"]-cx)//6))
                    uy = max(2, min(217, rcy + (t["cy"]-cy)//6))
                    cv2.drawMarker(radar, (ux, uy), (80, 80, 80), cv2.MARKER_TILTED_CROSS, 6, 1)
            gm = "3DAim" if det.strict else "AimLab"
            cv2.putText(radar, f"FPS:{fps:.0f} T:{len(tracked)} UI:{sum(1 for t in all_targets if is_ui(t))} [{aim_state}]",
                         (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 0), 1)
            cv2.putText(radar, f"{gm} s:{sensitivity:.3f} shots:{shots}",
                         (5, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (150, 150, 150), 1)
            cv2.imshow("GOD MODE", radar)

        fc += 1
        now = time.time()
        if now - fps_t >= 1.0:
            fps = fc / (now - fps_t); fc = 0; fps_t = now

        if esp_on:
            if cv2.waitKey(1) & 0xFF == 27: break
        elif fc % 50 == 0:
            time.sleep(0.001)

    cv2.destroyAllWindows()
    keyboard.unhook_all()
    ctypes.windll.winmm.timeEndPeriod(1)
    print(f"\n  Shots: {shots}", flush=True)


if __name__ == "__main__":
    main()
