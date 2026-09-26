"""수림아파트 101동 404호 — 평면 + 견적 품목 배치 데이터 (단일 소스).

좌표: mm, 평면 기준 x 오른쪽 / y 아래(현관이 있는 복도측이 위), z 위(마감 바닥 = 0).
이 파일이 layout.json 을 만들고, SketchUp 스크립트(.rb)와 렌더러가 같은 데이터를 쓴다.

전용 72㎡ : 벽 중심선 기준 9,750 x 8,400 - 좌측 발코니 2곳 = 72.0㎡
공급 90㎡ : 전용 + 공용(계단·복도 등). 발코니(서비스 면적)는 별도.
"""
import json
import math
import os

H = 2300          # 천장고
HDOOR = 2100      # 문 높이(인방 하단)
Z_BASE = -200     # 벽 하단 (단차 바닥 아래까지)

prims = []        # 모든 도형
doors = []        # 2D 도면용 문 궤적
labels = []       # 실 이름 라벨
cur = {"grp": "", "tag": ""}


def group(grp, tag):
    cur["grp"], cur["tag"] = grp, tag


def box(n, x0, y0, x1, y1, z0, z1, m, rot=0, render=True, **kw):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    p = dict(k="box", n=n, x0=x0, y0=y0, x1=x1, y1=y1, z0=z0, z1=z1, m=m,
             grp=kw.pop("grp", cur["grp"]), tag=kw.pop("tag", cur["tag"]))
    if rot:
        p["rot"] = rot
    if not render:
        p["render"] = False
    p.update(kw)
    prims.append(p)
    return p


def cyl(n, cx, cy, rx, ry, z0, z1, m, render=True, **kw):
    p = dict(k="cyl", n=n, cx=cx, cy=cy, rx=rx, ry=ry, z0=z0, z1=z1, m=m,
             grp=kw.pop("grp", cur["grp"]), tag=kw.pop("tag", cur["tag"]))
    if not render:
        p["render"] = False
    p.update(kw)
    prims.append(p)
    return p


# ------------------------------------------------------------------ materials
MATS = {
    # key: (표시 이름, hex, alpha, texture, texture size mm)
    "wall":       ("벽체(신한 실크 도배)", "#ece8e1", 1, "silk.png", 500),
    "wall_bal":   ("베란다 벽(백색 수성페인트)", "#f3f3f0", 1, None, 0),
    "wall_cap":   ("벽 단면(렌더용)", "#2b2b2d", 1, None, 0),
    "oak":        ("LG 장판 3.5T 내추럴오크", "#c9a57c", 1, "oak.png", 1200),
    "tile_ent":   ("현관 포세린타일 600각", "#8a8884", 1, "tile_ent.png", 600),
    "tile_bf":    ("욕실 바닥타일 300각", "#96948f", 1, "tile_bf.png", 600),
    "tile_bw":    ("욕실 벽타일 300x600", "#ecebe7", 1, "tile_bw.png", 600),
    "tile_bal":   ("베란다 바닥(기존 타일)", "#b8ae9f", 1, "tile_bal.png", 600),
    "marble":     ("인조대리석 상판(화이트)", "#f1efea", 1, "marble.png", 800),
    "cab_lower":  ("하부장·키큰장(웜그레이)", "#b5aea3", 1, None, 0),
    "cab_upper":  ("상부장(화이트 무광)", "#f1efea", 1, None, 0),
    "steel":      ("스테인리스", "#b7babd", 1, None, 0),
    "cooktop":    ("인덕션(블랙 글라스)", "#161616", 1, None, 0),
    "shoe":       ("신발장(화이트)", "#efede8", 1, None, 0),
    "led":        ("LED 간접조명", "#fff1cf", 1, None, 0),
    "door":       ("ABS 도어(화이트)", "#f2f0eb", 1, None, 0),
    "casing":     ("9mm 문선/문틀", "#f5f3ef", 1, None, 0),
    "handle":     ("도어 핸들(샤틴)", "#8e9093", 1, None, 0),
    "frontdoor":  ("현관문 인테리어필름(웜그레이)", "#6b6763", 1, None, 0),
    "glass":      ("샤시 유리(로이 복층)", "#b9d3d8", 0.28, None, 0),
    "glass_mid":  ("중문 유리", "#d3dcdc", 0.35, None, 0),
    "alu_black":  ("초슬림 블랙 프레임", "#232323", 1, None, 0),
    "kcc":        ("KCC PVC 샤시(화이트)", "#f6f6f4", 1, None, 0),
    "sash_old":   ("기존 샤시(작은방, 유지)", "#a5a9ac", 1, None, 0),
    "porcelain":  ("위생도기(화이트)", "#fbfbfb", 1, None, 0),
    "chrome":     ("크롬 수전·액세서리", "#c8cbcf", 1, None, 0),
    "mirror":     ("욕실 거울", "#e4ebee", 1, None, 0),
    "vanity":     ("욕실 하부장", "#d9d3c9", 1, None, 0),
    "drain":      ("유가(배수구)", "#5a5a5a", 1, None, 0),
    "trim":       ("천정몰딩·걸레받이(화이트)", "#f4f2ee", 1, None, 0),
    "ceiling":    ("천장 석고보드+도배", "#fafaf8", 1, None, 0),
    "fan_blade":  ("실링팬 날개(월넛)", "#5f432f", 1, None, 0),
    "fan_body":   ("실링팬 모터(매트블랙)", "#2a2a2a", 1, None, 0),
    "fan_light":  ("실링팬 조명(유백)", "#fbf8f0", 1, None, 0),
    "light":      ("LED 등기구", "#fdfdfb", 1, None, 0),
    "threshold":  ("욕실 문턱(인조대리석)", "#e9e6df", 1, None, 0),
}

# ------------------------------------------------------------------ walls
T_EXT, T_INT = 200, 120


def wall(n, axis, c, a, b, t, openings=(), m="wall", ext=True):
    """axis='x': 수평벽(y=c, x a..b) / axis='y': 수직벽(x=c, y a..b).
    openings: dict(s, e, kind, sill, head, ...)"""
    a2, b2 = (a - t / 2, b + t / 2) if ext else (a, b)
    ops = sorted(openings, key=lambda o: o["s"])

    def seg(s, e, z0, z1, tag=None, mm=None, nn=None, render=True):
        if e - s <= 0 or z1 - z0 <= 0:
            return
        kw = {} if tag is None else {"tag": tag}
        if axis == "x":
            box(nn or n, s, c - t / 2, e, c + t / 2, z0, z1, mm or m, render=render, cap=True, **kw)
        else:
            box(nn or n, c - t / 2, s, c + t / 2, e, z0, z1, mm or m, render=render, cap=True, **kw)

    pos = a2
    for o in ops:
        seg(pos, o["s"], Z_BASE, H)
        sill, head = o.get("sill", Z_BASE), o.get("head", HDOOR)
        seg(o["s"], o["e"], Z_BASE, sill, nn=n + " 창하부")
        seg(o["s"], o["e"], head, H, tag="인방(상부벽)", nn=n + " 인방", render=False)
        pos = o["e"]
    seg(pos, b2, Z_BASE, H)


def sash(n, axis, c, s, e, t, sill, head, m="kcc", tracks=2, note=""):
    """미서기 샤시: 외곽틀 + 2짝(레일 2개)."""
    fr = 60
    group(n, "창호(KCC 샤시)" if m == "kcc" else "창호(기존 유지)")

    def B(nn, u0, u1, v0, v1, z0, z1, mm, render=True):
        # u: 벽 길이방향, v: 벽 두께방향 (중심선 기준 오프셋)
        if axis == "x":
            box(nn, u0, c + v0, u1, c + v1, z0, z1, mm, render=render)
        else:
            box(nn, c + v0, u0, c + v1, u1, z0, z1, mm, render=render)

    d = min(t, 160) / 2
    B("하부틀", s, e, -d, d, sill, sill + 30, m)
    B("상부틀", s, e, -d, d, head - 50, head, m, render=False)
    B("좌측틀", s, s + 50, -d, d, sill, head, m)
    B("우측틀", e - 50, e, -d, d, sill, head, m)
    L = e - s - 100
    pw = L / 2 + 30
    for i in range(tracks):
        off = (-d / 2 if i == 0 else d / 2)
        u0 = s + 50 if i == 0 else e - 50 - pw
        u1 = u0 + pw
        z0, z1 = sill + 30, head - 50
        B(f"짝{i+1} 좌", u0, u0 + fr, off - 20, off + 20, z0, z1, m)
        B(f"짝{i+1} 우", u1 - fr, u1, off - 20, off + 20, z0, z1, m)
        B(f"짝{i+1} 하", u0, u1, off - 20, off + 20, z0, z0 + fr, m)
        B(f"짝{i+1} 상", u0, u1, off - 20, off + 20, z1 - fr, z1, m)
        B(f"짝{i+1} 유리", u0 + fr, u1 - fr, off - 10, off + 10, z0 + fr, z1 - fr, "glass")


def door(n, axis, c, s, e, t, hinge, swing, m="door", leaf_h=HDOOR - 20, z0=0, tag="문(교체 5개소)"):
    """여닫이문 — 90도 열린 상태. hinge: 's'|'e', swing: +1/-1 (벽 법선 방향)."""
    group(n, tag)
    jw, lt = 40, 36
    leaf = e - s - 2 * jw
    # 문틀(양쪽) + 9mm 문선(양면)
    for u0, u1 in ((s, s + jw), (e - jw, e)):
        if axis == "x":
            box("문틀", u0, c - t / 2, u1, c + t / 2, z0, HDOOR, "casing")
        else:
            box("문틀", c - t / 2, u0, c + t / 2, u1, z0, HDOOR, "casing")
    if axis == "x":
        box("상부문틀", s, c - t / 2, e, c + t / 2, HDOOR - 40, HDOOR, "casing", render=False)
    else:
        box("상부문틀", c - t / 2, s, c + t / 2, e, HDOOR - 40, HDOOR, "casing", render=False)
    for side in (-1, 1):
        f = c + side * (t / 2 + 4.5)
        for u0, u1 in ((s - 40, s), (e, e + 40)):
            if axis == "x":
                box("9mm 문선", u0, f - 4.5, u1, f + 4.5, z0, HDOOR + 40, "casing")
            else:
                box("9mm 문선", f - 4.5, u0, f + 4.5, u1, z0, HDOOR + 40, "casing")
    face = c + swing * t / 2
    far = face + swing * leaf
    hu = s + jw if hinge == "s" else e - jw
    hu2 = hu + lt if hinge == "s" else hu - lt
    ou = e - jw if hinge == "s" else s + jw
    if axis == "x":
        doors.append(dict(n=n, h=[hu, face], o=[hu, far], c=[ou, face]))
    else:
        doors.append(dict(n=n, h=[face, hu], o=[far, hu], c=[face, ou]))
    if axis == "x":
        box("문짝", hu, face, hu2, far, z0 + 10, z0 + leaf_h, m)
        cyl("손잡이", (hu + hu2) / 2 + (-30 if hinge == "e" else 30) * 0, far - swing * 70, 25, 25, 950, 1010, "handle")
    else:
        box("문짝", face, hu, far, hu2, z0 + 10, z0 + leaf_h, m)
        cyl("손잡이", far - swing * 70, (hu + hu2) / 2, 25, 25, 950, 1010, "handle")


def trims(n, segs):
    """걸레받이(h70) + 천정몰딩(40x40). segs: (axis, face_coord, a, b, dir, base_gaps)
    dir = 실내 방향(+1/-1). base_gaps: 걸레받이만 끊기는 구간(창·문)."""
    group("[19] 천정몰딩 및 걸레받이", "몰딩·걸레받이")
    for axis, f, a, b, d, gaps in segs:
        def mk(nn, u0, u1, dep, z0, z1):
            if u1 - u0 <= 1:
                return
            if axis == "x":
                box(nn, u0, f, u1, f + d * dep, z0, z1, "trim")
            else:
                box(nn, f, u0, f + d * dep, u1, z0, z1, "trim")
        mk("천정몰딩", a, b, 40, H - 40, H)
        pos = a
        for g0, g1 in sorted(gaps):
            mk("걸레받이", pos, g0, 12, 0, 70)
            pos = g1
        mk("걸레받이", pos, b, 12, 0, 70)


# ==================================================================== BUILD
# ---- 벽체 --------------------------------------------------------------
group("벽체", "벽체")
FD = dict(s=5800, e=6750, sill=Z_BASE, head=HDOOR)
wall("외벽(복도측)", "x", 0, 0, 11350, T_EXT, [FD])
wall("외벽(하부)", "x", 8400, 0, 11350, T_EXT)
W_L1 = dict(s=300, e=2400, sill=450, head=2200)
W_L2 = dict(s=3750, e=4650, sill=1100, head=2100)
W_L3 = dict(s=5600, e=8100, sill=450, head=2200)
wall("외벽(좌측)", "y", 0, 0, 8400, T_EXT, [W_L1, W_L2, W_L3], m="wall_bal")
W_R1 = dict(s=300, e=4000, sill=450, head=2200)
W_R2 = dict(s=4400, e=8100, sill=450, head=2200)
wall("앞베란다 외벽", "y", 11350, 0, 8400, T_EXT, [W_R1, W_R2], m="wall_bal")
S_LIV = dict(s=350, e=3750, sill=0, head=2150)
S_MAS = dict(s=4600, e=7900, sill=0, head=2150)
wall("거실·안방 발코니벽", "y", 9750, 0, 8400, T_EXT, [S_LIV, S_MAS])
S_B2 = dict(s=350, e=2350, sill=0, head=2150)
wall("방2 발코니벽", "y", 1700, 0, 2700, T_EXT, [S_B2])
S_B3 = dict(s=5700, e=8000, sill=0, head=2150)
wall("작은방 발코니벽", "y", 1700, 5300, 8400, T_EXT, [S_B3])
wall("뒷베란다·주방 경계벽", "x", 2700, 0, 1700, T_EXT)
D_B2 = dict(s=4180, e=5080)
wall("방2 하부벽", "x", 2700, 1700, 5200, T_INT, [D_B2], ext=False)
wall("방2·현관 경계벽", "y", 5200, 0, 2700, T_INT)
wall("안방 상부벽", "x", 4100, 6900, 9750, T_INT, ext=False)
D_MAS = dict(s=4250, e=5150)
D_BA2 = dict(s=7080, e=7830)
wall("안방 좌측벽", "y", 6900, 4100, 8400, T_INT, [D_MAS, D_BA2], ext=False)
D_B3 = dict(s=2500, e=3400)
D_BA1 = dict(s=4450, e=5250)
wall("주방 하부벽", "x", 5300, 0, 6900, T_EXT, [D_B3, D_BA1])
D_STO = dict(s=7100, e=7750)
wall("작은방 우측벽", "y", 4300, 5300, 8400, T_INT, [D_STO], ext=False)
wall("욕실 경계벽", "x", 6950, 4300, 6900, T_INT, ext=False)
wall("창고·부부욕실 경계벽", "y", 5000, 6950, 8400, T_INT, ext=False)

# ---- 바닥 (벽 중심선 기준 슬래브, 상단 z) -------------------------------
group("[9] 장판(LG 3.5T)", "바닥")
FLOORS = [
    ("방2 장판", 1700, 0, 5200, 2700, 0, "oak"),
    ("작은방 장판", 1700, 5300, 4300, 8400, 0, "oak"),
    ("창고 장판", 4300, 6950, 5000, 8400, 0, "oak"),
    ("안방 장판", 6900, 4100, 9750, 8400, 0, "oak"),
    ("주방·식당 장판", 0, 2700, 6900, 5300, 0, "oak"),
    ("복도 장판", 5200, 1650, 6900, 2700, 0, "oak"),
    ("거실 장판", 6900, 0, 9750, 4100, 0, "oak"),
]
for f in FLOORS:
    box(f[0], f[1], f[2], f[3], f[4], f[5] - 40, f[5], f[6], floor=True)
group("[22] 현관타일", "바닥")
box("현관 바닥타일", 5200, 0, 6900, 1650, -160, -120, "tile_ent", floor=True)
group("[5] 욕실공사", "바닥")
box("공용욕실 바닥타일", 4300, 5300, 6900, 6950, -80, -40, "tile_bf", floor=True)
box("부부욕실 바닥타일", 5000, 6950, 6900, 8400, -80, -40, "tile_bf", floor=True)
group("베란다(기존 바닥)", "바닥")
box("뒷베란다1 바닥", 0, 0, 1700, 2700, -120, -80, "tile_bal", floor=True)
box("뒷베란다2 바닥", 0, 5300, 1700, 8400, -120, -80, "tile_bal", floor=True)
box("앞베란다 바닥", 9750, 0, 11350, 8400, -120, -80, "tile_bal", floor=True)

# 베란다 벽 백색 도장 (실내측 벽면에 얇은 도장면)
group("[16] 앞뒤 베란다 페인트(백색)", "베란다 도장")
for n, x0, y0, x1, y1 in [
    ("앞베란다 도장(상)", 9850, 100, 11250, 108), ("앞베란다 도장(하)", 9850, 8292, 11250, 8300),
    ("뒷베란다1 도장(상)", 100, 100, 1600, 108), ("뒷베란다1 도장(하)", 100, 2592, 1600, 2600),
    ("뒷베란다2 도장(상)", 100, 5400, 1600, 5408), ("뒷베란다2 도장(하)", 100, 8292, 1600, 8300),
]:
    box(n, x0, y0, x1, y1, -80, H, "wall_bal")

# ---- 샤시 [25] (작은방 제외) ---------------------------------------------
for nm, axis, c, o, t in [
    ("[25] KCC 샤시 - 뒷베란다1 외창", "y", 0, W_L1, T_EXT),
    ("[25] KCC 샤시 - 주방창", "y", 0, W_L2, T_EXT),
    ("[25] KCC 샤시 - 뒷베란다2 외창", "y", 0, W_L3, T_EXT),
    ("[25] KCC 샤시 - 앞베란다 외창1", "y", 11350, W_R1, T_EXT),
    ("[25] KCC 샤시 - 앞베란다 외창2", "y", 11350, W_R2, T_EXT),
    ("[25] KCC 샤시 - 거실 분합창", "y", 9750, S_LIV, T_EXT),
    ("[25] KCC 샤시 - 안방 창", "y", 9750, S_MAS, T_EXT),
    ("[25] KCC 샤시 - 방2 창", "y", 1700, S_B2, T_EXT),
]:
    sash(nm, axis, c, o["s"], o["e"], t, max(o["sill"], -80 if o["sill"] <= 0 else o["sill"]), o["head"])
sash("작은방 창(기존 샤시 유지)", "y", 1700, S_B3["s"], S_B3["e"], T_EXT, 0, S_B3["head"], m="sash_old")

# ---- 문 [15] 5개소 + 창고문 필름 [14] ------------------------------------
door("[15] 문 교체 - 방2", "x", 2700, D_B2["s"], D_B2["e"], T_INT, "e", -1)
door("[15] 문 교체 - 작은방", "x", 5300, D_B3["s"], D_B3["e"], T_EXT, "s", +1)
door("[15] 문 교체 - 공용욕실", "x", 5300, D_BA1["s"], D_BA1["e"], T_EXT, "s", +1, z0=0)
door("[15] 문 교체 - 안방", "y", 6900, D_MAS["s"], D_MAS["e"], T_INT, "s", +1)
door("[15] 문 교체 - 부부욕실", "y", 6900, D_BA2["s"], D_BA2["e"], T_INT, "s", -1)
door("[14] 작은방 창고문(필름)", "y", 4300, D_STO["s"], D_STO["e"], T_INT, "e", -1, tag="필름")

group("[5] 욕실공사", "욕실")
box("공용욕실 문턱(인조대리석)", D_BA1["s"] + 40, 5200, D_BA1["e"] - 40, 5400, -40, 10, "threshold")
box("부부욕실 문턱(인조대리석)", 6840, D_BA2["s"] + 40, 6960, D_BA2["e"] - 40, -40, 10, "threshold")

# ---- 현관 [12][13][20][21][22] -------------------------------------------
group("[13] 현관문 필름 앞뒤", "현관")
box("현관문(필름 시공)", FD["s"] + 50, -30, FD["e"] - 50, 30, -120, HDOOR, "frontdoor")
box("현관문틀 좌", FD["s"], -100, FD["s"] + 50, 100, -120, HDOOR, "frontdoor")
box("현관문틀 우", FD["e"] - 50, -100, FD["e"], 100, -120, HDOOR, "frontdoor")
cyl("현관 도어락", FD["e"] - 150, 60, 30, 30, 900, 1100, "handle")

group("[12] 신발장(하부 간접조명)", "가구")
box("신발장 몸통", 5260, 100, 5660, 1610, 180, H, "shoe")
for i, y in enumerate(range(100, 1610, 503)):
    box(f"신발장 도어분할{i+1}", 5658, y + 2, 5662, y + 501, 180, H, "cab_upper")
box("신발장 하부 LED", 5270, 110, 5300, 1600, 170, 180, "led", light=True)

group("[20] 중문(3연동 초슬림)", "현관")
MS, ME, MY = 5660, 6850, 1650
box("중문 좌측틀", MS, MY - 60, MS + 30, MY + 60, -120, H, "alu_black")
box("중문 우측틀", ME - 30, MY - 60, ME, MY + 60, -120, H, "alu_black")
box("중문 상부레일", MS, MY - 60, ME, MY + 60, H - 40, H, "alu_black", render=False)
box("중문 하부레일", MS, MY - 60, ME, MY + 60, -120, -110, "alu_black")
pw = (ME - MS - 60) / 3 + 40
for i in range(3):
    u0 = MS + 30 + i * ((ME - MS - 60 - pw) / 2)
    v = MY - 38 + i * 38
    for nn, a0, a1, zb, zt in [("좌", u0, u0 + 20, -110, H - 45), ("우", u0 + pw - 20, u0 + pw, -110, H - 45),
                               ("하", u0, u0 + pw, -110, -70), ("상", u0, u0 + pw, H - 85, H - 45)]:
        box(f"중문 {i+1}짝 프레임{nn}", a0, v - 12, a1, v + 12, zb, zt, "alu_black")
    box(f"중문 {i+1}짝 유리", u0 + 20, v - 4, u0 + pw - 20, v + 4, -70, H - 85, "glass_mid")

group("[21] 중문가벽(상부유리)", "현관")
box("가벽 하부(목공+도배)", 6850, 100, 6950, 1710, Z_BASE, 1200, "wall", cap=True)
box("가벽 프레임 상단", 6865, 100, 6935, 1710, H - 30, H, "alu_black")
box("가벽 프레임 하단", 6865, 100, 6935, 1710, 1200, 1230, "alu_black")
box("가벽 프레임 앞", 6865, 1680, 6935, 1710, 1230, H - 30, "alu_black")
box("가벽 상부유리", 6895, 100, 6905, 1680, 1230, H - 30, "glass_mid")

# ---- 주방 [10][11] --------------------------------------------------------
group("[11] 키큰장", "주방")
box("키큰장", 100, 2800, 700, 3450, 0, H, "cab_lower")
box("키큰장 도어분할", 698, 3122, 702, 3128, 0, H, "cab_upper")

group("[10] 씽크대(ㄱ자, 인조대리석)", "주방")
box("하부장(좌측 런)", 100, 3450, 650, 5200, 100, 850, "cab_lower")
box("하부장(하부 런)", 650, 4650, 2300, 5200, 100, 850, "cab_lower")
box("걸레받이(좌측 런)", 100, 3450, 600, 5200, 0, 100, "cooktop")
box("걸레받이(하부 런)", 600, 4700, 2300, 5200, 0, 100, "cooktop")
box("인조대리석 상판(좌측 런)", 100, 3450, 720, 5200, 850, 880, "marble")
box("인조대리석 상판(하부 런)", 720, 4580, 2320, 5200, 850, 880, "marble")
box("싱크볼(사각 스텐)", 200, 3900, 640, 4700, 700, 881, "steel")
cyl("싱크 수전", 160, 4300, 28, 28, 880, 1230, "chrome")
box("싱크 수전 토수구", 160, 4288, 360, 4312, 1200, 1225, "chrome")
box("인덕션(3구)", 1350, 4660, 1950, 5170, 880, 888, "cooktop")
box("슬림 후드", 1330, 4850, 1970, 5200, 1500, 1600, "steel")
box("상부장(하부 런)", 100, 4850, 1330, 5200, 1450, H, "cab_upper")
box("상부장(후드 위)", 1330, 4850, 1970, 5200, 1600, H, "cab_upper")
box("상부장(하부 런 끝)", 1970, 4850, 2300, 5200, 1450, H, "cab_upper")
box("상부장(좌측 런)", 100, 3450, 450, 3700, 1450, H, "cab_upper")
box("상부장 하부 LED", 110, 4860, 2290, 4880, 1440, 1450, "led", light=True)

# ---- 욕실 [5][6] ----------------------------------------------------------
def toilet(n, cx, cy, facing):
    """facing: 사용자 쪽 방향 (0,-1)=위를 향함 등. tank 는 반대편 벽쪽."""
    fx, fy = facing
    if fx == 0:
        tank = (cx - 200, cy - fy * 20, cx + 200, cy - fy * 200)
        bowl_c = (cx, cy + fy * 230)
        rx, ry = 185, 250
    else:
        tank = (cx - fx * 20, cy - 200, cx - fx * 200, cy + 200)
        bowl_c = (cx + fx * 230, cy)
        rx, ry = 250, 185
    box(n + " 탱크", tank[0], tank[1], tank[2], tank[3], 0, 780, "porcelain")
    cyl(n + " 변기몸체", bowl_c[0], bowl_c[1], rx, ry, 0, 400, "porcelain")
    cyl(n + " 시트커버", bowl_c[0], bowl_c[1], rx - 5, ry - 5, 400, 430, "porcelain")


def tile_skin(rect, gaps):
    x0, y0, x1, y1 = rect
    tt = 10
    sides = [("x", y0, x0, x1, +1, gaps.get("t", [])), ("x", y1, x0, x1, -1, gaps.get("b", [])),
             ("y", x0, y0, y1, +1, gaps.get("l", [])), ("y", x1, y0, y1, -1, gaps.get("r", []))]
    for axis, f, a, b, d, gp in sides:
        pos = a
        for g0, g1 in sorted(gp) + [(b, b)]:
            if g0 - pos > 1:
                if axis == "x":
                    box("벽타일", pos, f, g0, f + d * tt, -40, H, "tile_bw")
                else:
                    box("벽타일", f, pos, f + d * tt, g0, -40, H, "tile_bw")
            pos = g1


group("[5] 욕실공사 - 공용욕실", "욕실")
B1 = (4360, 5400, 6840, 6890)
tile_skin(B1, {"t": [(D_BA1["s"], D_BA1["e"])]})
toilet("양변기", 5050, 6880, (0, -1))
box("세면대 하부장", 5500, 5410, 6100, 5880, 350, 830, "vanity")
box("세면대 상판", 5500, 5410, 6100, 5890, 830, 850, "porcelain")
cyl("세면볼", 5800, 5660, 220, 150, 850, 870, "chrome")
cyl("세면볼 내부", 5800, 5660, 200, 130, 851, 872, "porcelain")
cyl("세면 수전", 5800, 5460, 22, 22, 850, 1020, "chrome")
box("거울", 5480, 5410, 6120, 5425, 1050, 1900, "mirror")
group("[6] 화장실 간접조명", "욕실")
box("거울 뒤 간접조명", 5500, 5410, 6100, 5418, 1040, 1050, "led", light=True)
box("거울 상부 간접조명", 5500, 5410, 6100, 5418, 1900, 1910, "led", light=True)
group("[5] 욕실공사 - 공용욕실", "욕실")
cyl("샤워 슬라이드바", 6825, 6150, 14, 14, 900, 2000, "chrome")
cyl("해바라기 샤워헤드", 6700, 6150, 120, 120, 2000, 2025, "chrome")
box("해바라기 암", 6700, 6140, 6835, 6160, 2025, 2045, "chrome")
box("샤워 수전", 6800, 6100, 6840, 6200, 1000, 1100, "chrome")
box("유가", 6400, 6520, 6550, 6670, -40, -38, "drain")
box("수건걸이", 4370, 6000, 4395, 6600, 1300, 1330, "chrome")
box("휴지걸이", 4370, 6600, 4400, 6720, 700, 760, "chrome")
box("욕실 선반", 6770, 5500, 6840, 6000, 1300, 1320, "chrome")

group("[5] 욕실공사 - 부부욕실", "욕실")
B2 = (5060, 7010, 6840, 8300)
tile_skin(B2, {"r": [(D_BA2["s"], D_BA2["e"])]})
toilet("양변기", 6400, 8290, (0, -1))
box("세면대 하부장", 5070, 7100, 5540, 7650, 350, 830, "vanity")
box("세면대 상판", 5070, 7100, 5550, 7650, 830, 850, "porcelain")
cyl("세면볼", 5320, 7375, 150, 210, 850, 870, "chrome")
cyl("세면볼 내부", 5320, 7375, 132, 190, 851, 872, "porcelain")
cyl("세면 수전", 5110, 7375, 22, 22, 850, 1020, "chrome")
box("거울", 5070, 7080, 5085, 7670, 1050, 1900, "mirror")
group("[6] 화장실 간접조명", "욕실")
box("거울 뒤 간접조명", 5070, 7100, 5078, 7650, 1040, 1050, "led", light=True)
group("[5] 욕실공사 - 부부욕실", "욕실")
cyl("샤워 슬라이드바", 5450, 8285, 14, 14, 900, 2000, "chrome")
cyl("해바라기 샤워헤드", 5450, 8160, 110, 110, 2000, 2025, "chrome")
box("해바라기 암", 5440, 8160, 5460, 8295, 2025, 2045, "chrome")
box("샤워 수전", 5400, 8260, 5500, 8300, 1000, 1100, "chrome")
box("유가", 5380, 7900, 5520, 8040, -40, -38, "drain")
box("수건걸이", 5700, 7020, 6000, 7045, 1300, 1330, "chrome")
box("휴지걸이", 6700, 8280, 6820, 8300, 700, 760, "chrome")

# ---- 거실 실링팬 [17] -----------------------------------------------------
group("[17] 실링팬", "조명·전기")
FX, FY = 8325, 2050
cyl("실링팬 다운로드", FX, FY, 14, 14, 2130, H, "fan_body")
cyl("실링팬 모터", FX, FY, 115, 115, 2060, 2140, "fan_body")
cyl("실링팬 조명", FX, FY, 95, 95, 2020, 2060, "fan_light")
for i in range(5):
    ang = i * 72 + 18
    r = 115 + 300
    cx, cy = FX + r * math.cos(math.radians(ang)), FY + r * math.sin(math.radians(ang))
    box(f"실링팬 날개{i+1}", cx - 290, cy - 65, cx + 290, cy + 65, 2085, 2095, "fan_blade", rot=ang)
    bx, by = FX + 150 * math.cos(math.radians(ang)), FY + 150 * math.sin(math.radians(ang))
    box(f"실링팬 날개암{i+1}", bx - 60, by - 15, bx + 60, by + 15, 2090, 2105, "fan_body", rot=ang)

# ---- 조명 [7] (천장 — SketchUp 에서만, 숨김 태그) ---------------------------
group("[7] 조명전기공사(LED 등기구)", "천장·조명(숨김)")
LEDS = [("방2", 3450, 1350, 300), ("작은방", 3000, 6850, 280), ("안방", 8325, 6250, 320),
        ("주방", 2000, 4000, 300), ("식당", 4200, 3950, 300), ("복도", 6050, 2300, 150),
        ("현관", 6300, 800, 120), ("공용욕실", 5300, 6000, 130), ("부부욕실", 5900, 7300, 120),
        ("창고", 4650, 8000, 100)]
for nm, x, y, r in LEDS:
    cyl(f"LED 등기구({nm})", x, y, r, r, H - 25, H, "light", render=False)
for x in (8325 - 900, 8325 + 900):
    for y in (800, 3300):
        cyl("거실 LED 다운라이트", x, y, 60, 60, H - 20, H, "light", render=False)

# ---- 천장 목공 [18] (숨김 태그) -------------------------------------------
group("[18] 천정 목공마감", "천장·조명(숨김)")
for f in FLOORS:
    box(f[0].replace("장판", "천장"), f[1], f[2], f[3], f[4], H, H + 10, "ceiling", render=False)
box("현관 천장", 5200, 0, 6900, 1650, H, H + 10, "ceiling", render=False)
for n, r in (("공용욕실 천장돔", (4300, 5300, 6900, 6950)), ("부부욕실 천장돔", (5000, 6950, 6900, 8400))):
    box(n, *r[:2], *r[2:], H - 10, H, "ceiling", render=False)

# ---- 몰딩·걸레받이 [19] ---------------------------------------------------
trims("", [
    # 방2 (x 1800..5140, y 100..2640)
    ("x", 100, 1800, 5140, +1, []),
    ("x", 2640, 1800, 5140, -1, [(4180, 5080)]),
    ("y", 1800, 100, 2640, +1, [(350, 2350)]),
    ("y", 5140, 100, 2640, -1, []),
    # 작은방 (x 1800..4240, y 5400..8300)
    ("x", 5400, 1800, 4240, +1, [(2500, 3400)]),
    ("x", 8300, 1800, 4240, -1, []),
    ("y", 1800, 5400, 8300, +1, [(5700, 8000)]),
    ("y", 4240, 5400, 8300, -1, [(7100, 7750)]),
    # 창고
    ("x", 7010, 4360, 4940, +1, []), ("x", 8300, 4360, 4940, -1, []),
    ("y", 4360, 7010, 8300, +1, [(7100, 7750)]), ("y", 4940, 7010, 8300, -1, []),
    # 안방 (x 6960..9650, y 4160..8300)
    ("x", 4160, 6960, 9650, +1, []),
    ("x", 8300, 6960, 9650, -1, []),
    ("y", 6960, 4160, 8300, +1, [(4250, 5150), (7080, 7830)]),
    ("y", 9650, 4160, 8300, -1, [(4600, 7900)]),
    # 거실·주방·복도
    ("x", 100, 6950, 9650, +1, []),
    ("y", 9650, 100, 4040, -1, [(350, 3750)]),
    ("x", 4040, 6960, 9650, -1, []),
    ("y", 6840, 4040, 5200, -1, [(4250, 5150)]),
    ("x", 5200, 2300, 6840, -1, [(2500, 3400), (4450, 5250)]),
    ("x", 2800, 700, 1700, +1, []),
    ("x", 2760, 1700, 5140, +1, [(4180, 5080)]),
    ("y", 5260, 1650, 2760, +1, []),
    ("y", 6950, 100, 1710, +1, []),
    ("y", 100, 2800, 5200, +1, [(2800, 5200)]),
])

# ---- 실 라벨 --------------------------------------------------------------
def room(name, x, y, area_rect=None, area=None):
    labels.append(dict(name=name, x=x, y=y, area=area))


def rect_area(*rs):
    return round(sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs) / 1e6, 1)


room("거실", 8325, 3350, area=rect_area((6900, 0, 9750, 4100)))
room("주방·식당", 3600, 3900, area=rect_area((0, 2700, 6900, 5300), (5200, 1650, 6900, 2700)))
room("방2", 3450, 1350, area=rect_area((1700, 0, 5200, 2700)))
room("작은방", 3000, 6850, area=rect_area((1700, 5300, 4300, 8400)))
room("안방", 8325, 6250, area=rect_area((6900, 4100, 9750, 8400)))
room("공용욕실", 5550, 6350, area=rect_area((4300, 5300, 6900, 6950)))
room("부부욕실", 6000, 7750, area=rect_area((5000, 6950, 6900, 8400)))
room("창고", 4650, 7600, area=rect_area((4300, 6950, 5000, 8400)))
room("현관", 6250, 900, area=rect_area((5200, 0, 6900, 1650)))
room("앞베란다", 10550, 4200, area=rect_area((9750, 0, 11350, 8400)))
room("뒷베란다", 850, 1350, area=rect_area((0, 0, 1700, 2700)))
room("뒷베란다", 850, 6850, area=rect_area((0, 5300, 1700, 8400)))

EXCL = round((9750 * 8400 - 1700 * 2700 - 1700 * 3100) / 1e6, 2)

if __name__ == "__main__":
    out = dict(
        project="수림아파트 101동 404호",
        area=dict(supply=90, exclusive=72, exclusive_model=EXCL),
        ceiling=H,
        materials={k: dict(name=v[0], color=v[1], alpha=v[2], tex=v[3], texmm=v[4]) for k, v in MATS.items()},
        prims=prims,
        labels=labels,
        doors=doors,
    )
    path = os.path.join(os.path.dirname(__file__), "..", "layout.json")
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, separators=(",", ":"))
    print("prims", len(prims), "exclusive(model)", EXCL, "->", os.path.abspath(path))
