"""layout.json -> 치수·품목 번호가 들어간 2D 평면도 SVG (견적 No. 대조용)."""
import json
import math
import os

HERE = os.path.dirname(__file__)
D = json.load(open(os.path.join(HERE, "..", "layout.json"), encoding="utf-8"))
S = 0.1  # 1mm -> 0.1px (1:100 @ 10px/m... 화면용)
OX, OY = 1700, 1900  # 원점 여백(mm)
PW = int((11350 + OX + 1200) * S)
PH = int((8400 + OY + 1500) * S)
LEG_W = 760
W, H = PW + LEG_W, max(PH, 1180)

o = []


def X(x):
    return (x + OX) * S


def Y(y):
    return (y + OY) * S


def rect(x0, y0, x1, y1, **a):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    o.append(f'<rect x="{X(x0):.1f}" y="{Y(y0):.1f}" width="{(x1-x0)*S:.1f}" height="{(y1-y0)*S:.1f}" {attrs}/>')


def ell(cx, cy, rx, ry, **a):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    o.append(f'<ellipse cx="{X(cx):.1f}" cy="{Y(cy):.1f}" rx="{rx*S:.1f}" ry="{ry*S:.1f}" {attrs}/>')


def line(x0, y0, x1, y1, **a):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    o.append(f'<line x1="{X(x0):.1f}" y1="{Y(y0):.1f}" x2="{X(x1):.1f}" y2="{Y(y1):.1f}" {attrs}/>')


def text(x, y, s, size=13, **a):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    o.append(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" font-size="{size}" {attrs}>{s}</text>')


FLOOR_FILL = {"oak": "url(#oak)", "tile_ent": "url(#t600)", "tile_bf": "url(#t300)", "tile_bal": "url(#t300b)"}
prims = D["prims"]

# floors
for p in prims:
    if p.get("floor"):
        rect(p["x0"], p["y0"], p["x1"], p["y1"], fill=FLOOR_FILL[p["m"]])

# fixtures (not walls / floors / hidden)
SKIP_M = {"wall", "wall_bal", "glass", "glass_mid", "led", "trim", "tile_bw", "threshold"}
for p in prims:
    if p.get("floor") or p.get("render") is False or p.get("cap") or p["m"] in SKIP_M:
        continue
    if p["tag"] in ("창호(KCC 샤시)", "창호(기존 유지)", "문(교체 5개소)", "필름") and "문짝" not in p["n"]:
        continue
    stroke = "#6b6b6b"
    dash = ""
    fill = {"cab_lower": "#e3ddd3", "cab_upper": "none", "marble": "#f7f6f2", "shoe": "#f1eee8",
            "porcelain": "#ffffff", "vanity": "#ece6dc", "steel": "#d9dcde", "cooktop": "#3a3a3a",
            "door": "#ffffff", "frontdoor": "#77726c", "alu_black": "#222", "fan_blade": "none",
            "fan_body": "#444", "fan_light": "#fff", "drain": "#666", "chrome": "#c9ccd0",
            "mirror": "#cfe0e6", "handle": "#888"}.get(p["m"], "none")
    if p["m"] == "cab_upper" or p["tag"] == "조명·전기":
        dash = 'stroke-dasharray="6 4"'
    if p["m"] == "fan_blade":
        stroke = "#7a5a44"
    if p["k"] == "box":
        cx, cy = (p["x0"] + p["x1"]) / 2, (p["y0"] + p["y1"]) / 2
        tr = f'transform="rotate({p["rot"]} {X(cx):.1f} {Y(cy):.1f})"' if p.get("rot") else ""
        o.append(f'<rect x="{X(p["x0"]):.1f}" y="{Y(p["y0"]):.1f}" width="{(p["x1"]-p["x0"])*S:.1f}" '
                 f'height="{(p["y1"]-p["y0"])*S:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="0.8" {dash} {tr}/>')
    else:
        ell(p["cx"], p["cy"], p["rx"], p["ry"], fill=fill, stroke=stroke, stroke_width=0.8)

# walls: full height = poché, 창하부 = 창 기호
for p in prims:
    if p.get("cap") and p.get("render") is not False:
        if p["z1"] >= D["ceiling"]:
            rect(p["x0"], p["y0"], p["x1"], p["y1"], fill="#2b2b2d")
        else:
            rect(p["x0"], p["y0"], p["x1"], p["y1"], fill="#ffffff", stroke="#2b2b2d", stroke_width=1)
            if p["x1"] - p["x0"] > p["y1"] - p["y0"]:
                ym = (p["y0"] + p["y1"]) / 2
                line(p["x0"], ym, p["x1"], ym, stroke="#2b2b2d", stroke_width=0.8)
            else:
                xm = (p["x0"] + p["x1"]) / 2
                line(xm, p["y0"], xm, p["y1"], stroke="#2b2b2d", stroke_width=0.8)

# sashes: 두 줄 (새 KCC = 파랑, 기존 = 회색)
for p in prims:
    if "유리" in p["n"] and p["tag"].startswith("창호"):
        col = "#1f6fb2" if "KCC" in p["tag"] else "#9aa0a4"
        rect(p["x0"], p["y0"], p["x1"], p["y1"], fill=col, stroke=col, stroke_width=1.6)

# 중문 / 가벽 유리
for p in prims:
    if p["m"] == "glass_mid":
        rect(p["x0"], p["y0"], p["x1"], p["y1"], fill="#6aa9c9", stroke="#222", stroke_width=0.8)

# door swings
for d in D["doors"]:
    hx, hy = d["h"]
    ox_, oy_ = d["o"]
    cx_, cy_ = d["c"]
    r = math.hypot(ox_ - hx, oy_ - hy)
    line(hx, hy, ox_, oy_, stroke="#333", stroke_width=2)
    cross = (ox_ - hx) * (cy_ - hy) - (oy_ - hy) * (cx_ - hx)
    sweep = 1 if cross > 0 else 0
    o.append(f'<path d="M{X(ox_):.1f},{Y(oy_):.1f} A{r*S:.1f},{r*S:.1f} 0 0 {sweep} {X(cx_):.1f},{Y(cy_):.1f}" '
             f'fill="none" stroke="#555" stroke-width="0.8" stroke-dasharray="4 3"/>')

# LED 등기구 (천장) 기호
for p in prims:
    if p["tag"] == "천장·조명(숨김)" and p["k"] == "cyl":
        ell(p["cx"], p["cy"], 110, 110, fill="none", stroke="#d08a00", stroke_width=1.2)
        line(p["cx"] - 80, p["cy"] - 80, p["cx"] + 80, p["cy"] + 80, stroke="#d08a00", stroke_width=1)
        line(p["cx"] - 80, p["cy"] + 80, p["cx"] + 80, p["cy"] - 80, stroke="#d08a00", stroke_width=1)

# room labels
for lb in D["labels"]:
    py = lb["area"] / 3.3058
    text(lb["x"], lb["y"] - 120, lb["name"], 15, text_anchor="middle", font_weight="700", fill="#1b1b1b", stroke="#fff", stroke_width=4, paint_order="stroke")
    text(lb["x"], lb["y"] + 110, f'{lb["area"]}㎡ ({py:.1f}평)', 11, text_anchor="middle", fill="#555", stroke="#fff", stroke_width=3, paint_order="stroke")


# dimensions
def dim_h(xs, y, lab_off=-60):
    for a, b in zip(xs, xs[1:]):
        line(a, y, b, y, stroke="#444", stroke_width=0.8)
        text((a + b) / 2, y + lab_off, f"{b-a:,}", 10.5, text_anchor="middle", fill="#333")
    for x in xs:
        line(x, y - 100, x, y + 100, stroke="#444", stroke_width=0.8)
        line(x - 60, y + 60, x + 60, y - 60, stroke="#444", stroke_width=1.4)


def dim_v(ys, x):
    for a, b in zip(ys, ys[1:]):
        line(x, a, x, b, stroke="#444", stroke_width=0.8)
        m = (a + b) / 2
        o.append(f'<text x="{X(x-70):.1f}" y="{Y(m):.1f}" font-size="10.5" text-anchor="middle" fill="#333" '
                 f'transform="rotate(-90 {X(x-70):.1f} {Y(m):.1f})">{b-a:,}</text>')
    for yv in ys:
        line(x - 100, yv, x + 100, yv, stroke="#444", stroke_width=0.8)
        line(x - 60, yv + 60, x + 60, yv - 60, stroke="#444", stroke_width=1.4)


dim_h([0, 1700, 5200, 6900, 9750, 11350], -700)
dim_h([0, 11350], -1250)
dim_v([0, 2700, 4100, 5300, 6950, 8400], -700)
dim_v([0, 8400], -1250)
dim_h([0, 1700, 4300, 5000, 6900, 9750, 11350], 9050, lab_off=170)

# callouts (견적 No.)
CALL = [
    (5, 6450, 6250), (5, 5700, 8050), (6, 5800, 5540), (9, 2800, 3500), (10, 1250, 4300), (11, 400, 3120),
    (12, 5460, 400), (13, 6275, -330), (14, 4300, 7900), (15, 4630, 2450), (15, 2950, 5550), (15, 4850, 5580),
    (15, 7130, 4700), (15, 6650, 7350), (16, 850, 2300), (16, 850, 7900), (16, 10550, 7600), (17, 8900, 2050),
    (19, 3450, 2450), (20, 6250, 1900), (21, 7150, 900), (22, 6300, 1250), (25, 10550, 2100), (25, 9750, 5200),
    (25, 1700, 1800), (25, 0, 4200), (7, 3450, 1700), (8, 2600, 900),
]
for n, x, y in CALL:
    ell(x, y, 150, 150, fill="#c0392b", stroke="#fff", stroke_width=1.2)
    text(x, y + 45, str(n), 11, text_anchor="middle", fill="#fff", font_weight="700")
text(1700, 7700, "기존 샤시 유지", 9.5, text_anchor="middle", fill="#666", transform="")

# title
text(-1500, -1500, "수림아파트 101동 404호  —  리모델링 평면도 (견적 품목 반영)", 20, font_weight="700", fill="#111")
text(-1500, -1250 + 0, "", 1)

# legend
L = []
LX = PW + 20
L.append(f'<rect x="{PW}" y="0" width="{LEG_W}" height="{H}" fill="#f7f7f5"/>')
L.append(f'<text x="{LX}" y="44" font-size="18" font-weight="700" fill="#111">상세 견적 품목 ↔ 도면 번호</text>')
L.append(f'<text x="{LX}" y="68" font-size="12" fill="#555">공급 90㎡(27평) · 전용 72㎡ · 천장고 2,300 · 단위 mm · NID종합공사 2026.09.26</text>')
ITEMS = [
    (1, "데코타일철거", "거실·방 바닥 전체(약 19평)", "철거"),
    (2, "철거 및 폐기물", "몰딩·문짝·문틀·등기구", "철거"),
    (3, "욕실철거 폐기물", "욕실 2개소 천정·도기", "철거"),
    (4, "공용욕실 벽철거", "공용욕실 벽체 부분", "철거"),
    (5, "욕실공사 2개소", "방수·타일·양변기·세면대·해바라기 샤워", "도면"),
    (6, "화장실 간접조명", "거울 상·하부 LED", "도면"),
    (7, "조명전기공사", "LED 등기구 전체(주황 ⊗ 표시)", "도면"),
    (8, "도배(신한 실크)", "벽+천장 전체", "전체"),
    (9, "장판(LG 3.5T)", "거실·주방·방3·복도·창고", "도면"),
    (10, "씽크대 ㄱ자·인조대리석", "하부 2.35m+1.6m, 상부장, 싱크볼·수전", "도면"),
    (11, "키큰장", "주방 좌측 650×600 천장고", "도면"),
    (12, "신발장(조명)", "현관 좌측 1.5m, 하부 띄움 LED", "도면"),
    (13, "현관문 필름 앞뒤", "현관문 안·밖", "도면"),
    (14, "작은방 창고문 필름", "창고문", "도면"),
    (15, "문 교체 5개소(9mm 문선)", "방2·작은방·안방·공용욕실·부부욕실", "도면"),
    (16, "앞뒤 베란다 페인트", "베란다 3곳 백색 도장", "도면"),
    (17, "실링팬", "거실 중앙", "도면"),
    (18, "천정 목공마감", "천장 전체(도면 생략)", "전체"),
    (19, "천정몰딩·걸레받이", "각 실 둘레", "도면"),
    (20, "중문(3연동 초슬림)", "현관 1,190 폭", "도면"),
    (21, "중문가벽(상부유리)", "현관·거실 사이 H1,200 위 유리", "도면"),
    (22, "현관타일", "현관 바닥 600각", "도면"),
    (23, "엘리베이터 보양", "공용부", "해당없음"),
    (24, "엘리베이터 사용료·동의서", "관리사무소", "해당없음"),
    (25, "전체샤시교체(KCC)", "작은방 제외 8개소(파란 선)", "도면"),
]
yy = 104
for n, name, where, kind in ITEMS:
    col = "#c0392b" if kind == "도면" else "#9a9a9a"
    L.append(f'<circle cx="{LX+12}" cy="{yy-5}" r="11" fill="{col}"/>')
    L.append(f'<text x="{LX+12}" y="{yy-1}" font-size="11" font-weight="700" fill="#fff" text-anchor="middle">{n}</text>')
    L.append(f'<text x="{LX+32}" y="{yy}" font-size="13" font-weight="600" fill="#222">{name}</text>')
    L.append(f'<text x="{LX+262}" y="{yy}" font-size="12" fill="#555">{where}</text>')
    if kind != "도면":
        L.append(f'<text x="{PW+LEG_W-18}" y="{yy}" font-size="11" fill="#888" text-anchor="end">{kind}</text>')
    yy += 34
yy += 10
for sw, lab in [("url(#oak)", "LG 장판 3.5T 내추럴오크"), ("url(#t600)", "현관 포세린 600각"),
                ("url(#t300)", "욕실 바닥 300각"), ("url(#t300b)", "베란다 기존 타일")]:
    L.append(f'<rect x="{LX}" y="{yy-14}" width="36" height="18" fill="{sw}" stroke="#999"/>')
    L.append(f'<text x="{LX+46}" y="{yy}" font-size="12" fill="#333">{lab}</text>')
    yy += 26

DEFS = """<defs>
<pattern id="oak" width="12" height="20" patternUnits="userSpaceOnUse"><rect width="12" height="20" fill="#ead7bd"/><line x1="0" y1="0" x2="12" y2="0" stroke="#d6bf9f" stroke-width="0.8"/></pattern>
<pattern id="t600" width="60" height="60" patternUnits="userSpaceOnUse"><rect width="60" height="60" fill="#d5d3cf"/><path d="M0,0H60M0,0V60" stroke="#aaa" stroke-width="0.8"/></pattern>
<pattern id="t300" width="30" height="30" patternUnits="userSpaceOnUse"><rect width="30" height="30" fill="#dcdcda"/><path d="M0,0H30M0,0V30" stroke="#b3b3b0" stroke-width="0.7"/></pattern>
<pattern id="t300b" width="30" height="30" patternUnits="userSpaceOnUse"><rect width="30" height="30" fill="#ece6dc"/><path d="M0,0H30M0,0V30" stroke="#c9bfb0" stroke-width="0.7"/></pattern>
</defs>"""

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="Noto Sans CJK KR, Noto Sans KR, Malgun Gothic, sans-serif">{DEFS}'
       f'<rect width="{W}" height="{H}" fill="#fff"/>' + "".join(o) + "".join(L) + "</svg>")
out = os.path.join(HERE, "..", "plan_2d.svg")
open(out, "w", encoding="utf-8").write(svg)
print("svg", W, H, "->", os.path.abspath(out))
