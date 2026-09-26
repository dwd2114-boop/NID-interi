"""견적서 마감재에 맞춘 SketchUp / 렌더 공용 텍스처 생성 (PIL + numpy).

각 PNG 는 아래 '실제 크기(mm)' 를 한 장으로 표현한다. SketchUp 스크립트와 렌더러가
같은 크기로 반복 배치한다.
  oak.png          1200 x 1200  LG 장판 3.5T 내추럴 오크 (폭 200 x 길이 1200 마루패턴)
  tile_ent.png      600 x  600  현관 포세린 타일 600각
  tile_bf.png       600 x  600  욕실 바닥 300각 (2x2)
  tile_bw.png       600 x  600  욕실 벽 300x600 화이트 (2장)
  tile_bal.png      600 x  600  베란다 바닥 기존 타일 300각
  marble.png        800 x  800  주방 인조대리석 상판
  silk.png          500 x  500  신한 실크 벽지
"""
import os
import numpy as np
from PIL import Image, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "..", "textures")
rng = np.random.default_rng(404)
N = 1024


def smooth_noise(n, scale, seed_shape=None):
    small = rng.random((max(2, n // scale), max(2, n // scale)))
    img = Image.fromarray((small * 255).astype("uint8")).resize((n, n), Image.BICUBIC)
    return np.asarray(img).astype(float) / 255.0


def save(arr, name):
    arr = np.clip(arr, 0, 255).astype("uint8")
    Image.fromarray(arr, "RGB").save(os.path.join(OUT, name), optimize=True)


def oak():
    # 1200mm -> 1024px, 6 rows of 200mm planks, 1200mm long, staggered
    img = np.zeros((N, N, 3))
    base = np.array([203, 166, 124], float)
    row_h = N / 6
    y = np.arange(N)[:, None]
    x = np.arange(N)[None, :]
    for r in range(6):
        y0, y1 = int(r * row_h), int((r + 1) * row_h)
        offset = [0, 0.5, 0.25, 0.75, 0.4, 0.9][r] * N
        for k in range(-1, 2):
            x0 = int(offset + k * N)
            tone = rng.uniform(-14, 14)
            hue = np.array([tone, tone * 0.85, tone * 0.6])
            # grain: stretched noise along x
            h = y1 - y0
            g = rng.random((max(2, h // 3), 12))
            grain = np.asarray(Image.fromarray((g * 255).astype("uint8")).resize((N, h), Image.BICUBIC)).astype(float) / 255
            fine = rng.random((h, N)) * 0.35
            lines = np.sin((np.arange(h)[:, None] / h) * np.pi * rng.uniform(10, 22) + grain * 6) * 0.5 + 0.5
            val = (grain - 0.5) * 22 + (lines - 0.5) * 10 + (fine - 0.17) * 8
            xs = slice(max(0, x0), max(0, min(N, x0 + N)))
            if xs.start >= xs.stop:
                continue
            seg = base + hue + val[:, xs, None] * np.array([1, 0.85, 0.65])
            img[y0:y1, xs] = seg
            # plank end joint
            for xe in (x0, x0 + N - 1):
                if 0 <= xe < N:
                    img[y0:y1, xe:xe + 2] *= 0.82
        img[y0:y0 + 2, :] *= 0.8  # long-edge bevel
    save(img, "oak.png")


def grid_tile(name, base, tile_px, grout, grout_w=4, var=6, speckle=4.0, polish=False):
    img = np.ones((N, N, 3)) * np.array(base, float)
    n = smooth_noise(N, 64)
    img += ((n - 0.5) * var)[:, :, None]
    img += (rng.random((N, N)) - 0.5)[:, :, None] * speckle
    tx, ty = tile_px
    for i in range(0, N, tx):
        tone = 0
    # per-tile tone
    for yy in range(0, N, ty):
        for xx in range(0, N, tx):
            img[yy:yy + ty, xx:xx + tx] += rng.uniform(-var / 2, var / 2)
    for xx in range(0, N + 1, tx):
        img[:, max(0, xx - grout_w // 2):xx + grout_w // 2] = grout
    for yy in range(0, N + 1, ty):
        img[max(0, yy - grout_w // 2):yy + grout_w // 2, :] = grout
    if polish:
        yv = np.linspace(0, 1, N)[:, None]
        img += (np.sin(yv * np.pi) * 6)[:, :, None]
    save(img, name)


def marble():
    base = np.array([240, 238, 233], float)
    img = np.ones((N, N, 3)) * base
    n1 = smooth_noise(N, 128)
    n2 = smooth_noise(N, 32)
    xv = np.linspace(0, 1, N)[None, :]
    yv = np.linspace(0, 1, N)[:, None]
    veins = np.abs(np.sin((xv * 3 + yv * 1.5 + n1 * 2.2 + n2 * 0.4) * np.pi))
    v = np.clip(1 - veins * 18, 0, 1) * 28
    img -= v[:, :, None] * np.array([1, 1, 0.95])
    img += (rng.random((N, N)) - 0.5)[:, :, None] * 5
    save(img, "marble.png")


def silk():
    base = np.array([240, 236, 229], float)
    img = np.ones((N, N, 3)) * base
    h = rng.random((N, 1)) * 5
    v = rng.random((1, N)) * 5
    img += (h + v - 5)[:, :, None]
    img += (rng.random((N, N)) - 0.5)[:, :, None] * 3
    save(img, "silk.png")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    oak()
    grid_tile("tile_ent.png", [138, 136, 132], (N, N), [96, 95, 92], grout_w=5, var=8, speckle=10)
    grid_tile("tile_bf.png", [150, 148, 143], (N // 2, N // 2), [110, 108, 104], grout_w=5, var=6, speckle=8)
    grid_tile("tile_bw.png", [238, 237, 233], (N // 2, N), [205, 203, 198], grout_w=4, var=4, speckle=2, polish=True)
    grid_tile("tile_bal.png", [186, 176, 162], (N // 2, N // 2), [150, 142, 132], grout_w=6, var=10, speckle=9)
    marble()
    silk()
    print("textures ->", os.path.abspath(OUT))
