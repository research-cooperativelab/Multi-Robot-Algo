"""
Generate new/fixed slide images for SearchFCR thesis defense presentation.
All images: 1920x1080 px, warm cream aesthetic matching existing slides.
"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1920, 1080
FONT_DIR = r"C:\Windows\Fonts"

# Design tokens (warm cream aesthetic)
BG = (245, 242, 235)
ACCENT = (180, 45, 30)
DARK = (32, 28, 24)
MID = (90, 80, 70)
LIGHT_LINE = (210, 205, 195)
GREEN_NUM = (40, 100, 60)
TEAL_NUM = (30, 90, 110)
CARD_BG = (238, 234, 225)
CARD_BORDER = (200, 195, 185)

def load_font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        return ImageFont.load_default()

F_HEADER   = load_font("georgiab.ttf", 68)
F_HEADER_S = load_font("georgiab.ttf", 44)
F_BODY     = load_font("calibri.ttf",  32)
F_BODY_B   = load_font("calibrib.ttf", 32)
F_SMALL    = load_font("calibri.ttf",  24)
F_SMALL_B  = load_font("calibrib.ttf", 24)
F_TINY     = load_font("calibri.ttf",  20)
F_LABEL    = load_font("calibrib.ttf", 18)
F_MONO_S   = load_font("calibril.ttf", 20)


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_wrapped(draw, x, y, text, font, max_width, fill=None, lh=None):
    fill = fill or DARK
    lines = wrap_text(draw, text, font, max_width)
    line_h = lh or (draw.textbbox((0, 0), "Ag", font=font)[3] + 8)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h
    return y


def base_slide(slide_num, section, title):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 6], fill=ACCENT)
    d.text((80, 26), f"{slide_num:02d}  /  {section}", font=F_LABEL, fill=MID)
    d.text((80, 62), title, font=F_HEADER, fill=DARK)
    title_h = d.textbbox((80, 62), title, font=F_HEADER)[3]
    d.line([80, title_h + 16, W - 80, title_h + 16], fill=LIGHT_LINE, width=1)
    d.text((80, H - 42), "  SearchFCR", font=F_LABEL, fill=ACCENT)
    return img, d, title_h + 28


# ── Slide A: Bid Exponent Sweep ──────────────────────────────────────────────

def make_exponent_sweep():
    img, d, content_y = base_slide(8, "EXPONENT SWEEP", "Confirming α = 2 Is Optimal")
    d.text((W - 230, 26), "NEW / 20+", font=F_LABEL, fill=MID)

    RIGHT_X = 960
    LEFT_W  = RIGHT_X - 120

    bullets = [
        ("Tested p/dᵅ for α ∈ {1.0, 1.5, 2.0, 2.5, 3.0}", False),
        ("α = 2.0 (M4*) achieves lowest FCR — parabolic optimum", True),
        ("α > 2 over-penalizes: robots cluster too close to base", False),
        ("Adaptive α(E_rem) 1.0→2.0 as battery depletes — statistically WORSE than fixed α=2 (p<0.05)", False),
    ]

    y = content_y + 30
    for text, highlighted in bullets:
        dot_color = GREEN_NUM if highlighted else ACCENT
        d.ellipse([80, y + 8, 98, y + 26], fill=dot_color)
        fnt   = F_BODY_B if highlighted else F_BODY
        color = GREEN_NUM if highlighted else DARK
        y = draw_wrapped(d, 112, y, text, fnt, LEFT_W - 32, fill=color, lh=38)
        y += 12

    # callout box
    BOX_Y = H - 220
    d.rectangle([80, BOX_Y, LEFT_W + 80, BOX_Y + 100], outline=ACCENT, width=2, fill=(250, 246, 238))
    d.text((104, BOX_Y + 14), "α = 2 is not arbitrary —", font=F_BODY_B, fill=DARK)
    d.text((104, BOX_Y + 54), "it sits at the minimum of the FCR loss surface", font=F_BODY, fill=DARK)

    d.text((W - 560, H - 42), "08 · Bid Exponent Optimality", font=F_LABEL, fill=MID)

    # Right: figure
    fig_path = r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo\thesis\figures\fig_adaptive_bid.png"
    if os.path.exists(fig_path):
        fig = Image.open(fig_path).convert("RGB")
        fw, fh = fig.size
        tw = W - RIGHT_X - 40
        th = int(fh * tw / fw)
        if th > 800:
            th = 800
            tw = int(fw * th / fh)
        fig = fig.resize((tw, th), Image.LANCZOS)
        fx = RIGHT_X + (W - RIGHT_X - 40 - tw) // 2
        fy = content_y + 10 + (800 - th) // 2
        img.paste(fig, (fx, fy))
        d.text((RIGHT_X + 10, fy + th + 10),
               "1,000 paired trials · n=30 · R=3 · E=14",
               font=F_TINY, fill=MID)
    else:
        d.rectangle([RIGHT_X, content_y, W - 40, H - 80], outline=CARD_BORDER, fill=CARD_BG)
        d.text((RIGHT_X + 20, 500), "[fig_adaptive_bid.png not found]", font=F_SMALL, fill=MID)
    return img


# ── Slide B: Live Web Simulator ──────────────────────────────────────────────

def make_web_simulator():
    img, d, content_y = base_slide(17, "DEMO", "SearchFCR — Interactive Web Simulator")
    d.text((W - 230, 26), "NEW / 20+", font=F_LABEL, fill=MID)

    RIGHT_X = 720

    # URL
    url_font = load_font("georgiab.ttf", 42)
    d.text((80, content_y + 10), "searchfcr.fozhan.dev", font=url_font, fill=TEAL_NUM)

    y = content_y + 72
    features = [
        "5 models side-by-side on the same seed",
        "Real-time FCR timeline & entropy collapse",
        "Benchmark all 5 models automatically",
        "Fully reproducible — share via URL",
    ]
    for feat in features:
        d.text((80, y), "→  " + feat, font=F_BODY, fill=DARK)
        y += 46

    # QR box
    qr_x, qr_y = 130, y + 24
    QR = 200
    d.rectangle([qr_x, qr_y, qr_x + QR, qr_y + QR], outline=TEAL_NUM, width=3, fill=(228, 242, 246))
    d.text((qr_x + 28, qr_y + 60),  "QR CODE",       font=F_BODY_B, fill=TEAL_NUM)
    d.text((qr_x + 12, qr_y + 104), "→ searchfcr",   font=F_SMALL, fill=TEAL_NUM)
    d.text((qr_x + 18, qr_y + 136), ".fozhan.dev",   font=F_SMALL, fill=TEAL_NUM)
    d.text((80, qr_y + QR + 12), "Scan to open on your phone", font=F_SMALL, fill=MID)

    # Bottom coral strip
    d.rectangle([0, H - 64, W, H - 6], fill=ACCENT)
    live_font = load_font("calibrib.ttf", 30)
    d.text((W // 2 - 360, H - 52),
           "LIVE DURING THIS TALK — open the URL now",
           font=live_font, fill=(255, 255, 255))
    d.text((W - 440, H - 42), "17 · Web Simulator Demo", font=F_LABEL, fill=(220, 220, 220))

    # Right: screenshot
    fig_path = r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo\thesis\figures\fig_simulation_snapshot_v2.png"
    if os.path.exists(fig_path):
        fig = Image.open(fig_path).convert("RGB")
        fw, fh = fig.size
        tw = W - RIGHT_X - 40
        th = int(fh * tw / fw)
        if th > 780:
            th = 780
            tw = int(fw * th / fh)
        fig = fig.resize((tw, th), Image.LANCZOS)
        fx = RIGHT_X + (W - RIGHT_X - 40 - tw) // 2
        fy = content_y + 10 + (780 - th) // 2
        img.paste(fig, (fx, fy))
        d.text((RIGHT_X + 10, fy + th + 10),
               "Single mode · M4* · n=30 sites · 3 robots · seed 42",
               font=F_TINY, fill=MID)
    else:
        d.rectangle([RIGHT_X, content_y, W - 40, H - 80], outline=CARD_BORDER, fill=CARD_BG)
        d.text((RIGHT_X + 20, 500), "[fig_simulation_snapshot_v2.png not found]", font=F_SMALL, fill=MID)
    return img


# ── Slide C: Q&A Backup ──────────────────────────────────────────────────────

def make_qa_backup():
    img = Image.new("RGB", (W, H), (226, 222, 214))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 6], fill=ACCENT)
    d.text((80, 26), "BACKUP", font=F_LABEL, fill=ACCENT)
    d.text((W - 270, 26), "BACKUP SLIDE", font=F_LABEL, fill=MID)
    d.text((80, 62), "Anticipated Questions", font=F_HEADER, fill=DARK)
    d.line([80, 148, W - 80, 148], fill=LIGHT_LINE, width=1)
    d.text((80, H - 42), "  SearchFCR", font=F_LABEL, fill=ACCENT)
    d.text((W - 360, H - 42), "Q&A · Backup Slides", font=F_LABEL, fill=MID)

    qas = [
        ("Is M4* vs M4 statistically significant?",
         "At default: no (p=0.88). Significant at E<10, R>=5, n>=50. "
         "Directional advantage is consistent across ALL parameter sweeps."),
        ("Why not deep reinforcement learning?",
         "DRL lacks closed-form bounds. M4* is a one-line bid change "
         "with provable FCR guarantees — interpretable and deployable "
         "on constrained hardware (Kim & Kim 2025 comparison)."),
        ("What about physical robots?",
         "Needs only: site positions + at-base communication. "
         "No global map required. Direct port to UAVs, ground robots, and AUVs."),
        ("Why Euclidean? Real terrain isn’t flat.",
         "Exp 3 tests Manhattan, obstacle detour, and heterogeneous speeds "
         "— p/d^2 wins all four distance metrics. Substitute shortest-path "
         "cost and the framework is unchanged."),
    ]

    CARD_W = W // 2 - 100
    CARD_H = 390
    GX = [80, W // 2 + 20]
    GY = [162, 162 + CARD_H + 24]

    for i, (q, a) in enumerate(qas):
        col = i % 2
        row = i // 2
        cx, cy = GX[col], GY[row]

        d.rectangle([cx, cy, cx + CARD_W, cy + CARD_H],
                    fill=(238, 234, 225), outline=CARD_BORDER, width=1)
        # Question header (red band, auto-height)
        q_lines = wrap_text(d, q, F_SMALL_B, CARD_W - 24)
        header_h = len(q_lines) * 28 + 16
        d.rectangle([cx, cy, cx + CARD_W, cy + header_h], fill=(195, 50, 35))
        qy2 = cy + 8
        for ql in q_lines:
            d.text((cx + 14, qy2), ql, font=F_SMALL_B, fill=(255, 255, 255))
            qy2 += 28
        # Answer
        ay = cy + header_h + 14
        a_wrapped = wrap_text(d, a, F_SMALL, CARD_W - 28)
        for wl in a_wrapped:
            d.text((cx + 14, ay), wl, font=F_SMALL, fill=DARK)
            ay += 29
    return img


# ── Slide 17 fix: corrected bounds table ────────────────────────────────────

def make_bounds_fixed():
    orig = r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo\slide_screenshots\slide_17.png"
    img = Image.open(orig).convert("RGB")
    d = ImageDraw.Draw(img)

    # ── Cover the ENTIRE right column (text + old table + note) ──────────
    # Extend well past the old table bottom (~y=690) and note text (~y=670)
    RX1, RY1, RX2, RY2 = 712, 170, W - 10, 800
    d.rectangle([RX1, RY1, RX2, RY2], fill=(240, 237, 230))

    f28  = load_font("calibri.ttf",  28)
    f28b = load_font("calibrib.ttf", 28)
    f22  = load_font("calibri.ttf",  22)
    f22b = load_font("calibrib.ttf", 22)
    f30  = load_font("calibri.ttf",  30)

    # ── Paragraph text ────────────────────────────────────────────────────
    PX, PY = 730, 190
    para = ("Closed-form upper bounds on the expected FCR for each model "
            "— derived from a feasibility-ellipse argument and a nearest-"
            "neighbor lemma. All four bounds hold empirically.")
    draw_wrapped(d, PX, PY, para, f30, RX2 - PX - 20, fill=DARK, lh=40)

    # ── Table ─────────────────────────────────────────────────────────────
    TX1, TY1, TX2, TY2 = 716, 388, W - 50, 690
    CM, CE, CB, CT = 730, 948, 1108, 1268

    HY = 400
    d.text((CM, HY), "MODEL",     font=F_LABEL, fill=MID)
    d.text((CE, HY), "EMPIRICAL", font=F_LABEL, fill=MID)
    d.text((CB, HY), "BOUND",     font=F_LABEL, fill=MID)
    d.text((CT, HY), "TIGHTNESS", font=F_LABEL, fill=MID)
    d.line([TX1, HY + 28, TX2, HY + 28], fill=LIGHT_LINE, width=1)

    rows = [
        ("M1", "18.74", "34.09", "0.55"),
        ("M2", "2.83",  "3.34",  "0.85"),
        ("M3", "6.32",  "17.32", "0.36"),
        ("M4", "3.16",  "13.87", "0.23"),
    ]
    RH = 60
    for i, (m, e, b, t) in enumerate(rows):
        ry = HY + 40 + i * RH
        if m == "M4":
            d.rectangle([TX1 + 2, ry - 4, TX2 - 2, ry + RH - 12], fill=(230, 228, 220))
        d.text((CM, ry), m, font=f28,  fill=DARK)
        d.text((CE, ry), e, font=f28,  fill=DARK)
        bc = ACCENT if m == "M4" else DARK
        d.text((CB, ry), b, font=f28b, fill=bc)
        d.text((CT, ry), t, font=f28,  fill=DARK)
        if i < len(rows) - 1:
            d.line([TX1, ry + RH - 12, TX2, ry + RH - 12], fill=LIGHT_LINE, width=1)

    note_f = load_font("calibril.ttf", 20)
    d.text((TX1, TY2 + 10),
           "M4 bound is loose: greedy chain visits ~5.3 sites/sortie vs. analytical estimate of 2",
           font=note_f, fill=MID)

    # ── Fix T-labels on bar chart ─────────────────────────────────────────
    # Cover a generous strip across the full chart width at each T-label height,
    # then re-draw with corrected values.
    # Chart x-span ≈ 82–668.  T-label y positions from visual inspection:
    #   M1 bar top: the theoretical bar reaches ~y=370, T label at ~(209, 318)
    #   M2 bar top: smaller bar, label at ~(330, 560)
    #   M3 bar top: ~(450, 450)
    #   M4 bar top: ~(558, 384)
    t_fixes = [
        (209, 319, "T=0.55"),   # M1
        (330, 560, "T=0.85"),   # M2
        (449, 450, "T=0.36"),   # M3
        (558, 384, "T=0.23"),   # M4
    ]
    for tx, ty, label in t_fixes:
        # Wide cream box to fully cover original yellow-bordered label
        d.rectangle([tx - 6, ty - 4, tx + 100, ty + 32],
                    fill=(240, 237, 230), outline=(185, 170, 135), width=1)
        d.text((tx, ty), label, font=f22b, fill=DARK)
    return img


# ── Save ─────────────────────────────────────────────────────────────────────

OUT = r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo\slide_screenshots"

print("Generating exponent sweep slide...")
make_exponent_sweep().save(os.path.join(OUT, "slide_new_exponent.png"))
print("  OK: slide_new_exponent.png")

print("Generating web simulator slide...")
make_web_simulator().save(os.path.join(OUT, "slide_new_simulator.png"))
print("  OK: slide_new_simulator.png")

print("Generating Q&A backup slide...")
make_qa_backup().save(os.path.join(OUT, "slide_new_qa.png"))
print("  OK: slide_new_qa.png")

print("Generating corrected bounds slide...")
make_bounds_fixed().save(os.path.join(OUT, "slide_17_fixed.png"))
print("  OK: slide_17_fixed.png")

print("\nDone.")
