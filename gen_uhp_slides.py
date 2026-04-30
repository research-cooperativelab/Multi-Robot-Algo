"""
Generate 9-slide UHP Symposium deck — "wow" version for 10-min interdisciplinary talk.
Warm cream aesthetic, big numbers, minimal text, maximum visual impact.
"""
from PIL import Image, ImageDraw, ImageFont
import qrcode
import os, textwrap, math
from pathlib import Path

ROOT   = Path(r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo")
FIGS   = ROOT / "thesis" / "figures"
OUT    = ROOT / "slide_screenshots"
W, H   = 1920, 1080

# ── Palette ──────────────────────────────────────────────────────────────────
BG      = "#F5F2EB"   # warm cream
INK     = "#1A1A1A"   # near-black
RED     = "#B42D1E"   # coral accent
GREEN   = "#1B4332"   # dark forest (M4*)
MUTED   = "#6B6B6B"   # grey
TEAL    = "#0E6B8A"   # blue accent
GOLD    = "#8B6914"   # gold
LINE    = "#D4C9B8"   # subtle divider

# ── Font helpers ──────────────────────────────────────────────────────────────
def font(name, size):
    for path in [
        fr"C:\Windows\Fonts\{name}.ttf",
        fr"C:\Windows\Fonts\{name}bd.ttf",
        fr"C:\Windows\Fonts\{name}b.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def georgia(size):  return font("georgia", size)
def georgiab(size): return font("georgiab", size)
def calibri(size):  return font("calibri", size)
def calibrib(size): return font("calibrib", size)

def new_slide():
    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)
    return img, d

def text_center(d, y, text, fnt, color=INK, x=None):
    bbox = d.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    cx = x if x else W // 2
    d.text((cx - tw // 2, y), text, font=fnt, fill=color)

def wrap_draw(d, x, y, text, fnt, color=INK, max_width=700, line_gap=8):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = d.textbbox((0,0), test, font=fnt)
        if bbox[2] - bbox[0] > max_width and cur:
            lines.append(cur); cur = w
        else:
            cur = test
    if cur: lines.append(cur)
    lh = d.textbbox((0,0), "Ag", font=fnt)[3] + line_gap
    for line in lines:
        d.text((x, y), line, font=fnt, fill=color)
        y += lh
    return y

def tag(d, x, y, label, bg=RED):
    f = calibrib(22)
    bbox = d.textbbox((0,0), label, font=f)
    tw = bbox[2]-bbox[0]
    pad = 12
    d.rounded_rectangle([x, y, x+tw+pad*2, y+36], radius=4, fill=bg)
    d.text((x+pad, y+6), label, font=f, fill="white")

def paste_fig(img, path, x, y, w, h):
    """Paste a figure into the slide, cropped/scaled to fit."""
    if not os.path.exists(path):
        return
    fig = Image.open(path).convert("RGB")
    fw, fh = fig.size
    scale = min(w/fw, h/fh)
    nw, nh = int(fw*scale), int(fh*scale)
    fig = fig.resize((nw, nh), Image.LANCZOS)
    ox = x + (w - nw)//2
    oy = y + (h - nh)//2
    img.paste(fig, (ox, oy))

def top_bar(d, label, slide_num, total=9):
    d.text((60, 36), label, font=calibri(22), fill=MUTED)
    d.text((W-100, 36), f"{slide_num}/{total}", font=calibri(22), fill=MUTED)

def bottom_bar(d, left="", right="SearchFCR · CSULB Honors 2026"):
    d.rectangle([0, H-52, W, H], fill=INK)
    d.text((60, H-36), left, font=calibri(20), fill="#AAAAAA")
    bbox = d.textbbox((0,0), right, font=calibri(20))
    d.text((W-60-bbox[2], H-36), right, font=calibri(20), fill="#AAAAAA")

def rule(d, y, x0=60, x1=None, color=LINE):
    d.line([(x0, y), (x1 or W-60, y)], fill=color, width=2)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITLE
# ═══════════════════════════════════════════════════════════════════════════════
def slide_01():
    img, d = new_slide()

    # Bold red left accent bar
    d.rectangle([0, 0, 8, H], fill=RED)

    # Big headline — left aligned, massive
    d.text((100, 140), "When Robots", font=georgiab(110), fill=INK)
    d.text((100, 265), "Race to", font=georgiab(110), fill=INK)
    d.text((100, 390), "Find You.", font=georgiab(110), fill=RED)

    # Subtitle
    rule(d, 530, x0=100, x1=820)
    d.text((100, 550), "A smarter coordination algorithm for battery-limited", font=calibri(34), fill=MUTED)
    d.text((100, 595), "robot search teams — and why one equation change", font=calibri(34), fill=MUTED)
    d.text((100, 640), "makes them 6× more efficient.", font=calibrib(34), fill=GREEN)

    # Author block bottom-left
    d.text((100, H-200), "Fozhan Babaeiyan Ghamsari", font=georgiab(30), fill=INK)
    d.text((100, H-158), "Thesis Advisor: Dr. Oscar Morales-Ponce", font=calibri(26), fill=MUTED)
    d.text((100, H-118), "California State University, Long Beach", font=calibri(26), fill=MUTED)
    d.text((100, H-80),  "University Honors Program Symposium · Spring 2026", font=calibri(26), fill=MUTED)

    # Right side — embed the side-by-side figure for visual interest
    paste_fig(img, str(FIGS / "fig_m1_vs_m4star.png"), 980, 100, 900, 750)

    img.save(OUT / "uhp_01_title.png")
    print("  ✓ slide 01 — title")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — THE PROBLEM (visual hook)
# ═══════════════════════════════════════════════════════════════════════════════
def slide_02():
    img, d = new_slide()
    top_bar(d, "01 / THE PROBLEM", 2)

    d.text((60, 80), "Disasters are search problems.", font=georgiab(66), fill=INK)
    rule(d, 175, x1=780)

    d.text((60, 200), "A collapsed building. A flood. A lost hiker.", font=calibri(36), fill=INK)
    d.text((60, 252), "A drone fleet can cover it — if the drones", font=calibri(36), fill=INK)
    d.text((60, 304), "don't waste battery revisiting the same spots.", font=calibrib(36), fill=RED)

    d.text((60, 390), "Without coordination:", font=calibrib(30), fill=MUTED)
    d.text((60, 435), "robots overlap, energy is wasted,", font=calibri(30), fill=MUTED)
    d.text((60, 475), "survivors wait longer.", font=calibri(30), fill=MUTED)

    # Big comparison figure right — no title area overlap
    paste_fig(img, str(FIGS / "fig_m1_vs_m4star.png"), 820, 130, 1060, 840)

    # Label the two sides with colored background chips
    d.rounded_rectangle([845, 138, 1060, 178], radius=6, fill=RED)
    text_center(d, 145, "No coordination", calibrib(26), color="white", x=952)
    d.rounded_rectangle([1340, 138, 1530, 178], radius=6, fill=GREEN)
    text_center(d, 145, "Our method", calibrib(26), color="white", x=1435)

    bottom_bar(d, "searchfcr.fozhan.dev")
    img.save(OUT / "uhp_02_problem.png")
    print("  OK slide 02 — problem")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — THE MONEY SHOT (53.65 vs 3.02)
# ═══════════════════════════════════════════════════════════════════════════════
def slide_03():
    img, d = new_slide()
    top_bar(d, "02 / THE RESULT", 3)

    # Dark left panel
    d.rectangle([0, 0, W//2, H], fill="#1A1A1A")

    # Left — bad
    d.text((60, 100), "No\ncoordination.", font=georgiab(60), fill="white")
    d.text((60, 280), "53.65×", font=georgiab(160), fill=RED)
    d.text((60, 455), "extra travel", font=calibri(40), fill="#AAAAAA")
    d.text((60, 510), "vs. a perfect scout.", font=calibri(40), fill="#AAAAAA")

    # Right — good
    d.text((W//2 + 60, 100), "Our method.", font=georgiab(60), fill=GREEN)
    d.text((W//2 + 60, 280), "3.02×", font=georgiab(160), fill=GREEN)
    d.text((W//2 + 60, 455), "extra travel", font=calibri(40), fill=MUTED)
    d.text((W//2 + 60, 510), "vs. a perfect scout.", font=calibri(40), fill=MUTED)

    # Divider
    d.line([(W//2, 100), (W//2, H-100)], fill=LINE, width=3)

    # Bottom callout
    d.rectangle([0, H-130, W, H], fill=RED)
    text_center(d, H-105, "Same map. Same robots. Same battery. One algorithm change.", calibrib(38), color="white")
    text_center(d, H-58,  "18× improvement — confirmed across 5,000 simulations.", calibri(32), color="#FFD0CC")

    img.save(OUT / "uhp_03_moneyshot.png")
    print("  ✓ slide 03 — money shot")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — HOW IT WORKS (auction walkthrough)
# ═══════════════════════════════════════════════════════════════════════════════
def slide_04():
    img, d = new_slide()
    top_bar(d, "03 / HOW IT WORKS", 4)

    d.text((60, 80), "They bid — like an auction.", font=georgiab(64), fill=INK)
    rule(d, 172)

    # Three steps on left — drawn bullet dots instead of unicode
    steps = [
        (RED,   "1  BID",    "Every drone bids on every zone.\n   Highest bid wins — that drone owns it."),
        (TEAL,  "2  CHAIN",  "From its zone, the drone adds nearby stops\n   until it runs out of battery."),
        (GREEN, "3  UPDATE", "Drones return, share what they found,\n   and re-bid for the next round."),
    ]
    y = 210
    for color, title, body in steps:
        d.rectangle([60, y+6, 68, y+76], fill=color)
        d.text((90, y), title, font=calibrib(32), fill=color)
        for i, line in enumerate(body.split("\n")):
            d.text((90, y+42+i*36), line, font=calibri(30), fill=INK)
        y += 155

    # Use the cleaner 4-panel walkthrough figure
    paste_fig(img, str(FIGS / "fig_m4star_walkthrough.png"), 700, 200, 1180, 520)

    # Caption under figure
    d.rectangle([700, 720, 1880, 760], fill="#EAF2EC")
    text_center(d, 727, "A: priors shown   B: auction picks anchors   C: chain fills energy   D: update & re-bid",
                calibri(26), color=GREEN, x=1290)

    bottom_bar(d, "No global map needed — only local bids at base")
    img.save(OUT / "uhp_04_howworks.png")
    print("  OK slide 04 — how it works")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — THE KEY INSIGHT (one equation, big idea)
# ═══════════════════════════════════════════════════════════════════════════════
def slide_05():
    img, d = new_slide()
    top_bar(d, "04 / THE KEY INSIGHT", 5)

    d.text((60, 80), "One small change. Huge difference.", font=georgiab(64), fill=INK)
    rule(d, 172)

    # Left — old
    d.rectangle([60, 210, 580, 530], fill="#F0EDE6", outline=LINE, width=2)
    d.text((90, 230), "BEFORE", font=calibrib(24), fill=MUTED)
    text_center(d, 295, "p / d", georgiab(90), color=MUTED, x=320)
    d.text((90, 435), "Bid = probability ÷ distance", font=calibri(26), fill=MUTED)
    d.text((90, 475), "Doesn't account for battery drain.", font=calibri(26), fill=MUTED)

    # Arrow — drawn, not unicode
    ax, ay = 610, 345
    d.polygon([(ax, ay+20), (ax+60, ay+50), (ax, ay+80)], fill=RED)

    # Right — new
    d.rectangle([680, 210, 1200, 530], fill="#EAF2EC", outline=GREEN, width=3)
    d.text((710, 230), "OUR METHOD", font=calibrib(24), fill=GREEN)
    text_center(d, 295, "p / d²", georgiab(90), color=GREEN, x=940)
    d.text((710, 435), "Bid = probability ÷ distance²", font=calibrib(26), fill=GREEN)
    d.text((710, 475), "Penalizes far zones twice as hard.", font=calibri(26), fill=INK)

    # Right — bar chart figure
    paste_fig(img, str(FIGS / "fig_bid_variants.png"), 1250, 80, 630, 850)

    # Bottom explanation
    d.rectangle([0, H-160, W, H], fill="#EAF2EC")
    d.text((60, H-150), "Why does this matter?", font=calibrib(32), fill=GREEN)
    d.text((60, H-108), "Going far burns battery on the round-trip — leaving less for additional stops.", font=calibri(30), fill=INK)
    d.text((60, H-64),  "The squared penalty forces drones to commit to zones they can actually afford.", font=calibrib(30), fill=GREEN)

    img.save(OUT / "uhp_05_insight.png")
    print("  ✓ slide 05 — key insight")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — RESULTS HOLD UP (robot sweep + energy)
# ═══════════════════════════════════════════════════════════════════════════════
def slide_06():
    img, d = new_slide()
    top_bar(d, "05 / ROBUSTNESS", 6)

    d.text((60, 80), "It always wins.", font=georgiab(80), fill=INK)
    rule(d, 195, x1=700)
    d.text((60, 220), "We tested every configuration we could think of.", font=calibri(36), fill=MUTED)

    # Three stat callouts
    stats = [
        (RED,   "1 to 6",   "robots"),
        (TEAL,  "8 to 30",  "battery levels"),
        (GREEN, "5,000",    "simulations"),
    ]
    x = 60
    for color, big, small in stats:
        d.rectangle([x, 300, x+260, 480], fill=color, outline=color)
        text_center(d, 320, big,   georgiab(64), color="white", x=x+130)
        text_center(d, 410, small, calibri(28),  color="white", x=x+130)
        x += 300

    # Tag line
    d.text((60, 510), "M4* (our method) is lowest — in every single test.", font=calibrib(38), fill=GREEN)
    d.text((60, 562), "The ranking never flips.", font=georgiab(38), fill=INK)

    # Robot sweep figure — large
    paste_fig(img, str(FIGS / "fig_robot_sweep.png"), 960, 60, 920, 900)

    bottom_bar(d, "Works even when the probability map is noisy or wrong")
    img.save(OUT / "uhp_06_robust.png")
    print("  ✓ slide 06 — robustness")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — LIVE DEMO
# ═══════════════════════════════════════════════════════════════════════════════
def slide_07():
    img, d = new_slide()

    # Dark dramatic background for the demo slide
    img2 = Image.new("RGB", (W, H), "#0D1B2A")
    d2   = ImageDraw.Draw(img2)

    # Header
    d2.text((60, 50), "LIVE DEMO", font=calibrib(28), fill=TEAL)
    d2.text((60, 95), "See all 5 algorithms race — right now.", font=georgiab(72), fill="white")
    d2.line([(60, 200), (900, 200)], fill=TEAL, width=3)

    # Big URL
    d2.text((60, 230), "searchfcr.fozhan.dev", font=georgiab(80), fill="#4FC3F7")

    # Feature bullets — drawn dots, no unicode
    features = [
        "Pick any random seed — 5 methods run simultaneously",
        "Watch how each algorithm divides the map in real time",
        "See M4* consistently find the target with less travel",
        "Share your result via URL",
    ]
    y = 370
    for f in features:
        d2.ellipse([80, y+10, 96, y+26], fill=TEAL)
        d2.text((110, y), f, font=calibri(32), fill="#CCDDEE")
        y += 52

    # QR code
    qr = qrcode.QRCode(box_size=7, border=2)
    qr.add_data("https://searchfcr.fozhan.dev")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0D1B2A", back_color="white").convert("RGB")
    qr_img = qr_img.resize((280, 280), Image.LANCZOS)
    # White border
    border = Image.new("RGB", (300, 300), "white")
    border.paste(qr_img, (10, 10))
    img2.paste(border, (60, 600))
    d2.text((60, 920), "Scan to open on your phone", font=calibri(26), fill=MUTED)

    # Simulator screenshot right — positioned below URL so no overlap
    paste_fig(img2, str(FIGS / "fig_simulation_snapshot_v2.png"), 870, 340, 1010, 620)

    # Bottom strip
    d2.rectangle([0, H-60, W, H], fill=TEAL)
    text_center(d2, H-45, "OPEN NOW — watch it live during this talk", calibrib(30), color="white")

    img2.save(OUT / "uhp_07_demo.png")
    print("  ✓ slide 07 — demo")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — 3D / REAL ROBOTS (wow visual)
# ═══════════════════════════════════════════════════════════════════════════════
def slide_08():
    img, d = new_slide()
    top_bar(d, "06 / REAL-WORLD VALIDATION", 8)

    d.text((60, 80),  "From simulation", font=georgiab(60), fill=INK)
    d.text((60, 158), "to real robots.", font=georgiab(60), fill=RED)
    rule(d, 250, x1=700)

    bullets = [
        "3D physics simulation with real robot dynamics",
        "Battery enforced at the hardware level",
        "Algorithm runs on-board — no central server",
        "Scales: UAVs, ground robots, underwater AUVs",
    ]
    y = 280
    for text in bullets:
        d.ellipse([62, y+8, 82, y+28], fill=GREEN)
        d.text((100, y), text, font=calibri(32), fill=INK)
        y += 60

    # Big figure pushed right so bullets don't overlap
    paste_fig(img, str(FIGS / "fig_simulation_snapshot_v2.png"), 920, 60, 960, 900)

    # Caption overlay
    d.rectangle([780, H-110, W-60, H-60], fill="#1B4332")
    d.text((800, H-102), "3D physics sim · 3 robots · M4* auction · target found in 2 sorties", font=calibri(26), fill="white")

    bottom_bar(d, "No GPS, no global map — just local bids at the base")
    img.save(OUT / "uhp_08_realworld.png")
    print("  ✓ slide 08 — real world")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — SO WHAT / CLOSING
# ═══════════════════════════════════════════════════════════════════════════════
def slide_09():
    img, d = new_slide()

    # Full-width dark top band
    d.rectangle([0, 0, W, 300], fill=INK)
    text_center(d, 60,  "One equation change.", georgiab(80),  color="white")
    text_center(d, 165, "6× more efficient search. Fewer lives lost.", calibri(40), color="#CCCCCC")

    top_bar(d, "07 / TAKEAWAYS", 9)

    # Four application cards
    apps = [
        (RED,   "Earthquake\nRescue",    "Drones clear\ncollapsed zones\nfaster."),
        (TEAL,  "Flood\nMapping",        "UAVs divide\nflood area\nautonomously."),
        (GREEN, "Mars\nExploration",     "Rovers with\nlimited power\nmap terrain."),
        (GOLD,  "Underwater\nSearch",    "AUVs find\nobjects on the\nocean floor."),
    ]
    x = 60
    for color, title, desc in apps:
        d.rounded_rectangle([x, 330, x+430, 700], radius=16, fill="#F0EDE6", outline=color, width=4)
        # Colored circle icon
        d.ellipse([x+165, 350, x+265, 430], fill=color)
        for i, line in enumerate(title.split("\n")):
            text_center(d, 448+i*52, line, georgiab(44), color=INK, x=x+215)
        for i, line in enumerate(desc.split("\n")):
            text_center(d, 560+i*36, line, calibri(28), color=MUTED, x=x+215)
        x += 465

    # Bottom section
    rule(d, 730, x0=60, x1=W-60)
    d.text((60, 755),  "The algorithm is open source.", font=calibrib(36), fill=GREEN)
    d.text((60, 805),  "github.com/foojanbabaeeian/Multi-Robot-Algo", font=calibri(32), fill=TEAL)

    d.text((60, 880),  "Questions?   I'd love to hear them.", font=georgiab(40), fill=INK)
    d.text((60, 935),  "foojanbabaeeian@gmail.com  ·  searchfcr.fozhan.dev", font=calibri(30), fill=MUTED)

    # QR on far right
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data("https://searchfcr.fozhan.dev")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=INK, back_color=BG).convert("RGB")
    qr_img = qr_img.resize((200, 200), Image.LANCZOS)
    img.paste(qr_img, (W-240, 880))

    img.save(OUT / "uhp_09_closing.png")
    print("  ✓ slide 09 — closing")


# ── Run all ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating UHP symposium slides...")
    slide_01()
    slide_02()
    slide_03()
    slide_04()
    slide_05()
    slide_06()
    slide_07()
    slide_08()
    slide_09()
    print("\nAll 9 slides generated in slide_screenshots/uhp_*.png")
