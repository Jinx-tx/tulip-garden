#!/usr/bin/env python3
"""
NOCTURNAL PINK TULIP GARDEN + BIRTHDAY GREETING + MUSIC
Vectorized 3D Parametric ASCII + 24-bit TrueColor ANSI Renderer (30 FPS)
"""

import os
import sys
import time
import math
import shutil
import traceback
import numpy as np

FPS = 30
CHAR_ASPECT = 2.1
RAMP = " .,:;i1tfLCG08@#"
RESET = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
HOME = "\033[H"
CLEAR = "\033[2J"

MUSIC_FILENAME = "music.mp3"


def resource_path(relative_path: str) -> str:
    """Возвращает путь к файлу как при запуске .py, так и внутри PyInstaller .exe."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def start_music():
    """Запускает музыку в фоне с автоповтором."""
    music_path = resource_path(MUSIC_FILENAME)
    if not os.path.exists(music_path):
        return None
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.85)
        pygame.mixer.music.play(loops=-1)
        return pygame
    except Exception:
        return None


def enable_ansi_and_utf8():
    """Включает поддержку 24-bit ANSI и UTF-8 в консоли Windows."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                DISABLE_NEWLINE_AUTO_RETURN = 0x0008
                kernel32.SetConsoleMode(
                    handle,
                    mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING | DISABLE_NEWLINE_AUTO_RETURN,
                )
        except Exception:
            pass


def build_stars(count=130, seed=42):
    rng = np.random.default_rng(seed)
    stars = []
    palette = [
        (170, 180, 220),
        (225, 185, 215),
        (195, 210, 245),
        (245, 200, 225),
    ]
    for i in range(count):
        stars.append((
            float(rng.uniform(0.01, 0.99)),
            float(rng.uniform(0.02, 0.88)),
            float(rng.uniform(0.0, 2.0 * math.pi)),
            float(rng.uniform(1.4, 3.8)),
            palette[i % len(palette)],
        ))
    return stars


def build_particles(count=28, seed=99):
    rng = np.random.default_rng(seed)
    return {
        "x": rng.uniform(-1.35, 1.35, size=count).astype(np.float32),
        "y": rng.uniform(-0.9, 1.1, size=count).astype(np.float32),
        "z": rng.uniform(-0.4, 0.4, size=count).astype(np.float32),
        "speed": rng.uniform(0.12, 0.28, size=count).astype(np.float32),
        "phase": rng.uniform(0.0, 2.0 * math.pi, size=count).astype(np.float32),
    }


def rotate_xyz(pts, rx, ry, rz):
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)

    x, y, z = pts[..., 0], pts[..., 1], pts[..., 2]

    y1 = y * cx - z * sx
    z1 = y * sx + z * cx
    x1 = x

    x2 = x1 * cy + z1 * sy
    z2 = -x1 * sy + z1 * cy
    y2 = y1

    x3 = x2 * cz - y2 * sz
    y3 = x2 * sz + y2 * cz
    z3 = z2

    return np.stack([x3, y3, z3], axis=-1)


def generate_tulip_head(u_grid, v_grid, scale, bloom, light_dir):
    all_pts = []
    all_cols = []
    all_lum = []

    whorls = [
        (0, 3, 0.0, 1.00, 0.24 + 0.05 * bloom, 1.00),
        (1, 3, math.pi / 3.0, 0.90, 0.18 + 0.03 * bloom, 0.96),
    ]

    sin_pi_v = np.maximum(np.sin(np.pi * v_grid), 0.0)
    base_radius = (0.14 + 0.42 * (sin_pi_v ** 0.72) * (1.0 - 0.22 * (v_grid ** 1.6)))
    petal_half_angle = (0.68 * (sin_pi_v ** 0.55) * (1.0 - 0.15 * v_grid))
    height_y = 1.18 * (v_grid ** 0.92)
    vein = 0.05 * np.cos(u_grid * 16.0) * sin_pi_v

    for whorl_idx, count, phase_offset, r_mult, flare, h_mult in whorls:
        for k in range(count):
            az_center = phase_offset + k * (2.0 * math.pi / count)
            cup_bulge = 0.065 * (1.0 - u_grid ** 2) * sin_pi_v
            r = (base_radius * r_mult + cup_bulge + flare * (v_grid ** 1.4)) * scale
            y = (height_y * h_mult) * scale

            theta = az_center + u_grid * petal_half_angle
            x = r * np.cos(theta)
            z = r * np.sin(theta)

            pts = np.stack([x, y, z], axis=-1)

            nx = np.cos(theta) * (0.85 - 0.35 * v_grid) - np.sin(theta) * (0.35 * u_grid)
            ny = 0.32 * (v_grid - 0.42)
            nz = np.sin(theta) * (0.85 - 0.35 * v_grid) + np.cos(theta) * (0.35 * u_grid)
            norm_len = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
            nx, ny, nz = nx / norm_len, ny / norm_len, nz / norm_len

            ndotl = np.clip(nx * light_dir[0] + ny * light_dir[1] + nz * light_dir[2], -0.4, 1.0)
            rim = (1.0 - np.abs(u_grid)) ** 0.4 * (v_grid ** 0.7)
            diff = np.clip(0.32 + 0.68 * np.maximum(ndotl, 0.0) + 0.18 * rim + vein, 0.08, 1.0)

            t_col = np.clip(0.18 + 0.62 * v_grid + 0.25 * diff + (0.06 if whorl_idx == 0 else -0.04), 0.0, 1.0)

            c_low = np.array([115.0, 22.0, 62.0], dtype=np.float32)
            c_mid = np.array([238.0, 96.0, 152.0], dtype=np.float32)
            c_high = np.array([255.0, 198.0, 222.0], dtype=np.float32)

            w1 = np.clip(t_col * 2.0, 0.0, 1.0)[..., None]
            w2 = np.clip((t_col - 0.5) * 2.0, 0.0, 1.0)[..., None]
            col = c_low * (1.0 - w1) + c_mid * w1
            col = col * (1.0 - w2) + c_high * w2

            shade = (0.48 + 0.58 * diff)[..., None]
            col = np.clip(col * shade, 0, 255).astype(np.uint8)

            all_pts.append(pts.reshape(-1, 3))
            all_cols.append(col.reshape(-1, 3))
            all_lum.append(diff.reshape(-1))

    return (
        np.concatenate(all_pts, axis=0),
        np.concatenate(all_cols, axis=0),
        np.concatenate(all_lum, axis=0),
    )


def generate_stem_and_leaves(base_pos, top_pos, sway_x, sway_z, scale, light_dir):
    all_pts = []
    all_cols = []
    all_lum = []

    t_vals = np.linspace(0.0, 1.0, 44, dtype=np.float32)
    phi_vals = np.linspace(0.0, 2.0 * math.pi, 10, endpoint=False, dtype=np.float32)
    T, PHI = np.meshgrid(t_vals, phi_vals, indexing="ij")

    cx = base_pos[0] * (1.0 - T) + top_pos[0] * (T ** 1.35) + sway_x * (T ** 2) * 0.25
    cy = base_pos[1] * (1.0 - T) + top_pos[1] * T
    cz = base_pos[2] * (1.0 - T) + top_pos[2] * (T ** 1.35) + sway_z * (T ** 2) * 0.25

    stem_r = (0.042 - 0.010 * T) * scale
    sx = cx + stem_r * np.cos(PHI)
    sy = cy
    sz = cz + stem_r * np.sin(PHI)
    s_pts = np.stack([sx, sy, sz], axis=-1).reshape(-1, 3)

    nx, nz = np.cos(PHI), np.sin(PHI)
    ndotl = np.clip(nx * light_dir[0] + nz * light_dir[2], 0.0, 1.0)
    lum = (0.28 + 0.65 * ndotl).reshape(-1)

    c_dark = np.array([18.0, 64.0, 42.0], dtype=np.float32)
    c_light = np.array([76.0, 168.0, 114.0], dtype=np.float32)
    s_col = (c_dark + (c_light - c_dark) * lum[:, None]).astype(np.uint8)

    all_pts.append(s_pts)
    all_cols.append(s_col)
    all_lum.append(lum)

    lu = np.linspace(-1.0, 1.0, 11, dtype=np.float32)
    lv = np.linspace(0.0, 1.0, 32, dtype=np.float32)
    LU, LV = np.meshgrid(lu, lv, indexing="ij")

    leaf_width = 0.19 * scale * np.maximum(np.sin(np.pi * (LV ** 0.72)), 0.0) * (1.0 - 0.25 * LV)
    leaf_len = 1.25 * scale

    for side, attach_t, yaw in [(-1.0, 0.14, 0.35), (1.0, 0.26, -0.45)]:
        idx = int(attach_t * 43)
        ox, oy, oz = cx[idx, 0], cy[idx, 0], cz[idx, 0]

        arch_out = side * (0.58 * (LV ** 1.15) + 0.14 * np.sin(np.pi * LV)) * scale + sway_x * 0.35 * LV
        arch_up = leaf_len * (LV - 0.28 * (LV ** 2.2))
        cup = 0.04 * scale * (1.0 - LU ** 2) * np.maximum(np.sin(np.pi * LV), 0.0)

        lx_local = arch_out + cup * (-side)
        ly_local = arch_up
        lz_local = LU * leaf_width + cup

        cyaw, syaw = math.cos(yaw), math.sin(yaw)
        lx = ox + lx_local * cyaw - lz_local * syaw
        ly = oy + ly_local
        lz = oz + lx_local * syaw + lz_local * cyaw

        l_pts = np.stack([lx, ly, lz], axis=-1).reshape(-1, 3)
        l_shade = np.clip(0.30 + 0.55 * LV + 0.20 * (1.0 - np.abs(LU)), 0.15, 1.0).reshape(-1)
        l_col = (c_dark * 0.85 + (c_light * 1.08 - c_dark) * l_shade[:, None])
        l_col = np.clip(l_col, 0, 255).astype(np.uint8)

        all_pts.append(l_pts)
        all_cols.append(l_col)
        all_lum.append(l_shade)

    return (
        np.concatenate(all_pts, axis=0),
        np.concatenate(all_cols, axis=0),
        np.concatenate(all_lum, axis=0),
    )


def stamp_centered_text(char_buf, color_buf, row_idx, text, rgb):
    """Вписывает строку по центру указанной строки экрана."""
    rows, cols = char_buf.shape
    if not (0 <= row_idx < rows) or not text:
        return
    trimmed = text[: max(1, cols - 4)]
    start_c = max(0, (cols - len(trimmed)) // 2)
    for i, ch in enumerate(trimmed):
        c = start_c + i
        if c < cols:
            char_buf[row_idx, c] = ch
            color_buf[row_idx, c] = rgb


def render_frame(t, stars, particles, light_dir, u_grid, v_grid):
    term_size = shutil.get_terminal_size((120, 40))
    cols = max(40, term_size.columns)
    rows = max(16, term_size.lines - 1)

    char_buf = np.full((rows, cols), " ", dtype="<U1")
    color_buf = np.zeros((rows, cols, 3), dtype=np.uint8)

    for sx, sy, phase, freq, scol in stars:
        c = int(sx * (cols - 1))
        r = int(sy * (rows - 1))
        twinkle = 0.45 + 0.55 * math.sin(t * freq + phase)
        if twinkle > 0.35:
            char_buf[r, c] = "+" if twinkle > 0.85 else ("*" if twinkle > 0.65 else ".")
            color_buf[r, c] = (
                int(scol[0] * twinkle),
                int(scol[1] * twinkle),
                int(scol[2] * twinkle),
            )

    bouquet = [
        (0.00, 0.05, 0.00, 0.42, 0.12, 0.92, 0.02, 0.16, 0.0),
        (-0.34, -0.05, -0.78, 0.24, 0.02, 0.82, 0.28, 0.14, 1.1),
        (0.34, -0.05, 0.78, 0.26, 0.04, 0.83, -0.27, 0.15, 2.2),
        (-0.58, -0.18, -1.32, -0.05, -0.14, 0.74, 0.44, 0.10, 3.3),
        (0.58, -0.18, 1.32, -0.03, -0.12, 0.74, -0.43, 0.12, 4.4),
    ]

    all_pts = []
    all_cols = []
    all_lum = []

    for bx, bz, tx, ty, tz, sc, tilt_z, tilt_x, ph in bouquet:
        sway_x = 0.075 * math.sin(t * 1.45 + ph)
        sway_z = 0.045 * math.cos(t * 1.15 + ph)
        bloom = 0.5 + 0.5 * math.sin(t * 0.9 + ph)

        head_pos = np.array([tx + sway_x, ty, tz + sway_z], dtype=np.float32)
        base_pos = np.array([bx, -1.35, bz], dtype=np.float32)

        s_pts, s_cols, s_lum = generate_stem_and_leaves(
            base_pos, head_pos, sway_x, sway_z, sc, light_dir
        )
        all_pts.append(s_pts)
        all_cols.append(s_cols)
        all_lum.append(s_lum)

        h_pts, h_cols, h_lum = generate_tulip_head(u_grid, v_grid, sc, bloom, light_dir)
        h_pts = rotate_xyz(
            h_pts,
            tilt_x + sway_z * 0.4,
            0.25 * math.sin(t * 0.6 + ph),
            tilt_z - sway_x * 0.5,
        )
        h_pts = h_pts + head_pos[None, :]
        all_pts.append(h_pts)
        all_cols.append(h_cols)
        all_lum.append(h_lum)

    py = ((particles["y"] + t * particles["speed"] + 1.1) % 2.2) - 1.1
    px = particles["x"] + 0.12 * np.sin(t * 1.2 + particles["phase"])
    pz = particles["z"] + 0.12 * np.cos(t * 1.0 + particles["phase"])
    p_pts = np.stack([px, py, pz], axis=-1)
    p_cols = np.tile(np.array([[255, 195, 225]], dtype=np.uint8), (len(px), 1))
    p_lum = 0.55 + 0.45 * np.sin(t * 3.0 + particles["phase"])

    all_pts.append(p_pts)
    all_cols.append(p_cols)
    all_lum.append(p_lum.astype(np.float32))

    pts = np.concatenate(all_pts, axis=0)
    cols_arr = np.concatenate(all_cols, axis=0)
    lum_arr = np.concatenate(all_lum, axis=0)

    cam_dist = 3.65
    fov = min(cols / CHAR_ASPECT, rows) * 1.18
    denom = cam_dist - pts[:, 2]
    valid = denom > 0.4
    pts = pts[valid]
    cols_arr = cols_arr[valid]
    lum_arr = lum_arr[valid]
    denom = denom[valid]

    inv_z = 1.0 / denom
    sx = np.rint(cols * 0.5 + pts[:, 0] * fov * CHAR_ASPECT * inv_z).astype(np.int32)
    sy = np.rint(rows * 0.54 - pts[:, 1] * fov * inv_z).astype(np.int32)

    in_bounds = (sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows)
    sx = sx[in_bounds]
    sy = sy[in_bounds]
    z_vals = pts[in_bounds, 2]
    cols_arr = cols_arr[in_bounds]
    lum_arr = lum_arr[in_bounds]

    order = np.argsort(z_vals)
    sx = sx[order]
    sy = sy[order]
    cols_arr = cols_arr[order]
    lum_arr = lum_arr[order]

    ramp_idx = np.clip((lum_arr * (len(RAMP) - 1)).astype(np.int32), 1, len(RAMP) - 1)
    ramp_chars = np.array(list(RAMP))[ramp_idx]

    char_buf[sy, sx] = ramp_chars
    color_buf[sy, sx] = cols_arr

    # Мягкое пульсирующее свечение для поздравления
    pulse = 0.82 + 0.18 * math.sin(t * 2.4)
    pink_glow = (
        int(255 * pulse),
        int(150 * pulse),
        int(205 * pulse),
    )
    pearl_glow = (
        int(255 * pulse),
        int(215 * pulse),
        int(235 * pulse),
    )

    stamp_centered_text(char_buf, color_buf, 1, "С ДНЁМ РОЖДЕНИЯ, БУБЛИК!", pink_glow)
    stamp_centered_text(char_buf, color_buf, 2, "Пусть каждый день цветёт так же красиво", pearl_glow)
    stamp_centered_text(char_buf, color_buf, max(0, rows - 2), "♪ Молданазар — Махаббатым ♪", pink_glow)

    lines = [HOME]
    for r in range(rows):
        row_chars = char_buf[r]
        row_cols = color_buf[r]
        last_rgb = (-1, -1, -1)
        row_out = []
        for c in range(cols):
            ch = row_chars[c]
            if ch == " ":
                if last_rgb != (-1, -1, -1):
                    row_out.append(RESET)
                    last_rgb = (-1, -1, -1)
                row_out.append(" ")
            else:
                rgb = (int(row_cols[c, 0]), int(row_cols[c, 1]), int(row_cols[c, 2]))
                if rgb != last_rgb:
                    row_out.append(f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m")
                    last_rgb = rgb
                row_out.append(ch)
        if last_rgb != (-1, -1, -1):
            row_out.append(RESET)
        lines.append("".join(row_out))

    if cols < 75 or rows < 24:
        hint = " [Zoom out with Ctrl + - & maximize terminal for full petals] "
        lines[-1] = f"\033[38;2;255;170;205m{hint[:cols]}{RESET}"

    return "\n".join(lines)


def main():
    enable_ansi_and_utf8()
    pygame_mod = start_music()

    stars = build_stars()
    particles = build_particles()
    light_dir = np.array([-0.42, 0.68, 0.60], dtype=np.float32)
    light_dir /= np.linalg.norm(light_dir)

    u = np.linspace(-1.0, 1.0, 22, dtype=np.float32)
    v = np.linspace(0.0, 1.0, 34, dtype=np.float32)
    u_grid, v_grid = np.meshgrid(u, v, indexing="ij")

    sys.stdout.write(CLEAR + HIDE_CURSOR)
    sys.stdout.flush()

    t0 = time.perf_counter()
    frame_dt = 1.0 / FPS

    try:
        while True:
            frame_start = time.perf_counter()
            t = frame_start - t0
            frame = render_frame(t, stars, particles, light_dir, u_grid, v_grid)
            sys.stdout.write(frame)
            sys.stdout.flush()

            elapsed = time.perf_counter() - frame_start
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        if pygame_mod is not None:
            try:
                pygame_mod.mixer.music.stop()
                pygame_mod.mixer.quit()
            except Exception:
                pass
        sys.stdout.write(RESET + SHOW_CURSOR + CLEAR + HOME)
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stdout.write(RESET + SHOW_CURSOR)
        print("\nОшибка при запуске:")
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")