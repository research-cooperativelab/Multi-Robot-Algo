"""
Build SearchFCR_UHP_Symposium.html from the 18 slide PNGs extracted from
SearchFCR_Conference_Presentation UHP.pptx
"""
import base64, json
from pathlib import Path

ROOT   = Path(r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo")
SLIDES = ROOT / "slide_screenshots" / "uhp_new"
OUT    = ROOT / "SearchFCR_UHP_Symposium.html"

slide_files = sorted(SLIDES.glob("slide_*.png"))
print(f"Found {len(slide_files)} slides")

# base64-encode each slide
slides_b64 = []
for f in slide_files:
    data = base64.b64encode(f.read_bytes()).decode()
    slides_b64.append(f"data:image/png;base64,{data}")
    print(f"  encoded {f.name} ({f.stat().st_size // 1024} KB)")

slides_json = json.dumps(slides_b64)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SearchFCR · UHP Symposium 2026</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  html, body {{
    background: #0a0a0a;
    width: 100%; height: 100%;
    overflow: hidden;
    font-family: system-ui, sans-serif;
  }}

  #deck {{
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0a0a0a;
  }}

  #slide-box {{
    position: relative;
    width:  min(100vw, 177.78vh);
    height: min(56.25vw, 100vh);
  }}

  .slide {{
    position: absolute;
    inset: 0;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }}
  .slide.active {{
    opacity: 1;
    pointer-events: auto;
  }}
  .slide img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    user-select: none;
    -webkit-user-drag: none;
  }}

  #nav {{
    position: fixed;
    bottom: 18px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(10,10,10,0.75);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 40px;
    padding: 7px 18px;
    z-index: 100;
    opacity: 0;
    transition: opacity 0.25s;
  }}
  body:hover #nav, #nav:hover {{ opacity: 1; }}

  #nav button {{
    background: none;
    border: none;
    color: #e0e0e0;
    cursor: pointer;
    font-size: 0.82rem;
    padding: 4px 10px;
    border-radius: 20px;
    transition: background 0.15s, color 0.15s;
  }}
  #nav button:hover {{ background: rgba(255,255,255,0.1); color: #fff; }}
  #nav button:disabled {{ opacity: 0.3; cursor: default; }}

  #counter {{
    font-size: 0.75rem;
    color: #888;
    min-width: 52px;
    text-align: center;
    letter-spacing: 0.05em;
  }}

  #hint {{
    position: fixed;
    top: 14px;
    right: 16px;
    font-size: 0.68rem;
    color: rgba(255,255,255,0.25);
    z-index: 100;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.25s;
  }}
  body:hover #hint {{ opacity: 1; }}

  :fullscreen #nav, :-webkit-full-screen #nav {{ display: none; }}
</style>
</head>
<body>

<div id="deck">
  <div id="slide-box"></div>
</div>

<div id="nav">
  <button id="btn-first" title="First slide">&#171;</button>
  <button id="btn-prev"  title="Previous (&#8592;)">&#8592;</button>
  <span   id="counter">1 / {len(slide_files)}</span>
  <button id="btn-next"  title="Next (&#8594; or Space)">&#8594;</button>
  <button id="btn-last"  title="Last slide">&#187;</button>
  <button id="btn-fs"    title="Fullscreen (F)">&#x26F6;</button>
</div>

<div id="hint">F &mdash; fullscreen &nbsp;&middot;&nbsp; &larr; &rarr; &mdash; navigate</div>

<script>
const SLIDES = {slides_json};
const N = SLIDES.length;

const box = document.getElementById('slide-box');
const els = SLIDES.map((src, i) => {{
  const div = document.createElement('div');
  div.className = 'slide' + (i === 0 ? ' active' : '');
  const img = document.createElement('img');
  img.src = src;
  img.alt = 'Slide ' + (i + 1);
  img.draggable = false;
  div.appendChild(img);
  box.appendChild(div);
  return div;
}});

let cur = 0;

function go(n) {{
  n = Math.max(0, Math.min(N - 1, n));
  if (n === cur) return;
  els[cur].classList.remove('active');
  cur = n;
  els[cur].classList.add('active');
  update();
}}

function update() {{
  document.getElementById('counter').textContent = (cur + 1) + ' / ' + N;
  document.getElementById('btn-first').disabled = cur === 0;
  document.getElementById('btn-prev').disabled  = cur === 0;
  document.getElementById('btn-next').disabled  = cur === N - 1;
  document.getElementById('btn-last').disabled  = cur === N - 1;
}}

document.getElementById('btn-first').onclick = () => go(0);
document.getElementById('btn-prev').onclick  = () => go(cur - 1);
document.getElementById('btn-next').onclick  = () => go(cur + 1);
document.getElementById('btn-last').onclick  = () => go(N - 1);
document.getElementById('btn-fs').onclick    = () => {{
  if (!document.fullscreenElement) document.documentElement.requestFullscreen();
  else document.exitFullscreen();
}};

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === ' ') {{ e.preventDefault(); go(cur + 1); }}
  if (e.key === 'ArrowLeft')                   {{ e.preventDefault(); go(cur - 1); }}
  if (e.key === 'Home')                        {{ e.preventDefault(); go(0); }}
  if (e.key === 'End')                         {{ e.preventDefault(); go(N - 1); }}
  if (e.key === 'f' || e.key === 'F') {{
    if (!document.fullscreenElement) document.documentElement.requestFullscreen();
    else document.exitFullscreen();
  }}
}});

box.addEventListener('click', () => go(cur + 1));

update();
</script>
</body>
</html>
"""

OUT.write_text(html, encoding='utf-8')
size_mb = OUT.stat().st_size / 1024 / 1024
print(f"\nSaved: {OUT.name} ({size_mb:.1f} MB, {len(slide_files)} slides)")
