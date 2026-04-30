"""Generate a single-file HTML presentation for the UHP Symposium."""
import json, base64, io
from pathlib import Path
import qrcode

ROOT  = Path(r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo")
FIGS  = ROOT / "thesis" / "figures"

# --- encode figures ---
def b64(path):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()

fig = {
    "compare":  b64(FIGS / "fig_m1_vs_m4star.png"),
    "walk":     b64(FIGS / "fig_m4star_walkthrough.png"),
    "bids":     b64(FIGS / "fig_bid_variants.png"),
    "robots":   b64(FIGS / "fig_robot_sweep.png"),
    "sim":      b64(FIGS / "fig_simulation_snapshot_v2.png"),
}

# --- QR code ---
qr = qrcode.QRCode(box_size=8, border=2)
qr.add_data("https://searchfcr.fozhan.dev")
qr.make(fit=True)
buf = io.BytesIO()
qr.make_image(fill_color="#0D1B2A", back_color="white").save(buf, format="PNG")
fig["qr"] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>When Robots Race to Find You</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --cream:#F5F2EB;--ink:#1A1A1A;--red:#B42D1E;--green:#1B4332;
  --teal:#0E6B8A;--muted:#6B6B6B;--line:#D4C9B8;--dark:#0D1B2A;
  --lg:#EAF2EC;
}
html,body{width:100%;height:100%;background:#111;font-family:Calibri,'Trebuchet MS',Arial,sans-serif;overflow:hidden}
#deck{width:100%;height:100%;display:flex;align-items:center;justify-content:center}
.slide{
  position:absolute;
  width:min(100vw,177.78vh);height:min(56.25vw,100vh);
  background:var(--cream);overflow:hidden;
  opacity:0;pointer-events:none;
  transition:opacity .3s ease,transform .3s ease;
  transform:translateX(50px);
}
.slide.active{opacity:1;pointer-events:all;transform:translateX(0)}
.slide.out{opacity:0;transform:translateX(-50px)}
.serif{font-family:Georgia,'Times New Roman',serif}
#bar{position:fixed;bottom:0;left:0;height:3px;background:var(--red);transition:width .3s;z-index:99}
#ctr{position:fixed;bottom:8px;right:14px;font-size:12px;color:#666;z-index:99}
.nav{position:fixed;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.3);
  color:#fff;border:none;font-size:26px;padding:10px 14px;cursor:pointer;
  z-index:99;border-radius:4px;transition:background .2s}
.nav:hover{background:rgba(0,0,0,.6)}
#prev{left:8px}#next{right:8px}

/* ── S1 TITLE ── */
#s1{background:var(--cream)}
#s1 .accent{position:absolute;left:0;top:0;bottom:0;width:6px;background:var(--red)}
#s1 .L{position:absolute;left:0;top:0;bottom:0;width:52%;padding:7% 5% 5% 7%;
  display:flex;flex-direction:column;justify-content:space-between}
#s1 h1{font-family:Georgia,serif;font-size:clamp(28px,5.5vw,70px);line-height:1.1;color:var(--ink)}
#s1 h1 em{color:var(--red);font-style:normal}
#s1 .sub{font-size:clamp(12px,1.4vw,18px);color:var(--muted);line-height:1.6}
#s1 .sub b{color:var(--green)}
#s1 .who{font-size:clamp(10px,1.1vw,14px);color:var(--muted);line-height:1.9}
#s1 .who b{color:var(--ink);font-size:1.1em}
#s1 .tag{font-size:clamp(9px,1vw,13px);font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);margin-bottom:5%}
#s1 .R{position:absolute;right:0;top:0;bottom:0;width:50%;
  display:flex;align-items:center;justify-content:center;padding:4%}
#s1 .R img{max-width:100%;max-height:100%;object-fit:contain;border-radius:6px}

/* ── S2 PROBLEM ── */
#s2 .L{position:absolute;left:0;top:0;bottom:0;width:37%;
  padding:6% 4% 5% 5%;display:flex;flex-direction:column;justify-content:center;gap:5%}
#s2 .tag{font-size:clamp(9px,1vw,13px);font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted)}
#s2 h2{font-family:Georgia,serif;font-size:clamp(20px,3.2vw,42px);color:var(--ink);line-height:1.2}
#s2 p{font-size:clamp(11px,1.3vw,17px);color:var(--ink);line-height:1.6}
#s2 p b{color:var(--red)}
#s2 .note{font-size:clamp(10px,1.1vw,14px);color:var(--muted);line-height:1.6;
  border-left:3px solid var(--line);padding-left:10px}
#s2 .R{position:absolute;right:0;top:0;bottom:0;width:65%;
  display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3% 3% 6% 0}
#s2 .R img{max-width:100%;max-height:82%;object-fit:contain}
#s2 .lbls{display:flex;width:100%;justify-content:space-around;margin-top:1.5%}
#s2 .bad{background:var(--red);color:#fff;padding:4px 14px;border-radius:4px;
  font-weight:700;font-size:clamp(10px,1vw,13px)}
#s2 .good{background:var(--green);color:#fff;padding:4px 14px;border-radius:4px;
  font-weight:700;font-size:clamp(10px,1vw,13px)}

/* ── S3 MONEY ── */
#s3{background:var(--ink)}
#s3 .H{position:absolute;top:0;bottom:72px;width:50%;
  display:flex;flex-direction:column;justify-content:center;padding:5% 6%}
#s3 .HL{left:0;background:var(--ink)}
#s3 .HR{right:0;background:var(--cream)}
#s3 .div{position:absolute;left:50%;top:5%;bottom:72px;width:1px;background:#333}
#s3 .lbl-l{color:#999;font-size:clamp(13px,1.7vw,21px);margin-bottom:3%}
#s3 .lbl-r{color:var(--green);font-family:Georgia,serif;font-size:clamp(13px,1.7vw,21px);margin-bottom:3%}
#s3 .num-l{font-family:Georgia,serif;font-size:clamp(56px,10.5vw,140px);font-weight:700;color:var(--red);line-height:1}
#s3 .num-r{font-family:Georgia,serif;font-size:clamp(56px,10.5vw,140px);font-weight:700;color:var(--green);line-height:1}
#s3 .s-l{color:#888;font-size:clamp(11px,1.3vw,17px);margin-top:2%;line-height:1.5}
#s3 .s-r{color:var(--muted);font-size:clamp(11px,1.3vw,17px);margin-top:2%;line-height:1.5}
#s3 .ban{position:absolute;bottom:0;left:0;right:0;height:72px;background:var(--red);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px}
#s3 .ban p{color:#fff;font-size:clamp(12px,1.5vw,19px)}
#s3 .ban p:first-child{font-weight:700;font-size:clamp(13px,1.6vw,21px)}

/* ── S4 HOW ── */
#s4 .L{position:absolute;left:0;top:0;bottom:0;width:37%;
  padding:5% 4% 4% 5%;display:flex;flex-direction:column;justify-content:center}
#s4 h2{font-family:Georgia,serif;font-size:clamp(20px,3vw,40px);color:var(--ink);
  line-height:1.2;margin-bottom:7%}
.step{display:flex;gap:12px;margin-bottom:7%}
.sbar{width:5px;border-radius:3px;flex-shrink:0}
.sbody h3{font-size:clamp(11px,1.3vw,16px);font-weight:700;
  letter-spacing:.07em;text-transform:uppercase;margin-bottom:4px}
.sbody p{font-size:clamp(10px,1.2vw,15px);color:var(--ink);line-height:1.55}
#s4 .R{position:absolute;right:0;top:0;bottom:0;width:65%;
  display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3% 3% 8% 1%}
#s4 .R img{max-width:100%;max-height:78%;object-fit:contain}
#s4 .cap{background:var(--lg);border-radius:4px;padding:5px 16px;margin-top:2%;
  font-size:clamp(9px,1vw,13px);color:var(--green);text-align:center}

/* ── S5 INSIGHT ── */
#s5 .hdr{padding:3.5% 5% 1.5%}
#s5 .tag{font-size:clamp(9px,1vw,13px);font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);margin-bottom:.5%}
#s5 h2{font-family:Georgia,serif;font-size:clamp(20px,3.2vw,42px);color:var(--ink)}
#s5 .row{display:flex;gap:1.5%;padding:0 3.5%;height:43%;align-items:stretch}
.cb{flex:1;border:2px solid var(--line);border-radius:10px;background:#F0EDE6;
  padding:4% 5%;display:flex;flex-direction:column;justify-content:center}
.ca{flex:1.2;border:3px solid var(--green);border-radius:10px;background:var(--lg);
  padding:4% 5%;display:flex;flex-direction:column;justify-content:center}
.cb .tg{font-size:clamp(9px,1vw,13px);font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.ca .tg{font-size:clamp(9px,1vw,13px);font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--green)}
.fml{font-family:Georgia,serif;font-size:clamp(32px,5.5vw,74px);line-height:1;margin:3% 0}
.cb .fml{color:var(--muted)}
.ca .fml{color:var(--green);font-weight:700}
.cb p,.ca p{font-size:clamp(10px,1.15vw,15px);line-height:1.5}
.cb p{color:var(--muted)}.ca p{color:var(--ink)}
.ca p b{color:var(--green)}
.arr{display:flex;align-items:center;justify-content:center;
  font-size:clamp(24px,3.5vw,48px);color:var(--red);padding:0 .5%;flex-shrink:0}
.ch{flex:1.1;display:flex;align-items:center;justify-content:center;padding:0 1%}
.ch img{max-width:100%;max-height:100%;object-fit:contain}
#s5 .bot{position:absolute;bottom:0;left:0;right:0;background:var(--lg);
  padding:1.8% 5%;border-top:2px solid var(--green)}
#s5 .bot p{font-size:clamp(10px,1.15vw,15px);color:var(--ink);line-height:1.5}
#s5 .bot p b{color:var(--green)}

/* ── S6 ROBUST ── */
#s6 .L{position:absolute;left:0;top:0;bottom:0;width:42%;
  padding:5% 4% 4% 5%;display:flex;flex-direction:column;justify-content:center}
#s6 .tag{font-size:clamp(9px,1vw,13px);font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);margin-bottom:3%}
#s6 h2{font-family:Georgia,serif;font-size:clamp(26px,4.8vw,64px);
  color:var(--ink);line-height:1.1;margin-bottom:3%}
#s6 .sub{font-size:clamp(11px,1.3vw,17px);color:var(--muted);margin-bottom:5%}
#s6 .stats{display:flex;gap:3%;margin-bottom:5%}
.sbox{flex:1;border-radius:8px;padding:5% 3%;text-align:center;color:#fff}
.sbox .big{font-family:Georgia,serif;font-size:clamp(16px,2.6vw,34px);
  font-weight:700;display:block;margin-bottom:3px}
.sbox .sm{font-size:clamp(9px,1vw,12px);opacity:.9}
#s6 .verd{font-size:clamp(12px,1.4vw,18px);line-height:1.5;color:var(--ink)}
#s6 .verd b{color:var(--green);display:block;font-family:Georgia,serif;
  font-size:clamp(14px,1.8vw,24px);margin-top:2%}
#s6 .R{position:absolute;right:0;top:0;bottom:0;width:60%;
  display:flex;align-items:center;justify-content:center;padding:3%}
#s6 .R img{max-width:100%;max-height:100%;object-fit:contain}

/* ── S7 DEMO ── */
#s7{background:var(--dark)}
#s7 .L{position:absolute;left:0;top:0;bottom:58px;width:50%;
  padding:5% 4% 4% 5%;display:flex;flex-direction:column;justify-content:center}
#s7 .tl{color:var(--teal);font-size:clamp(10px,1.1vw,14px);font-weight:700;
  letter-spacing:.12em;text-transform:uppercase;margin-bottom:3%}
#s7 h2{font-family:Georgia,serif;font-size:clamp(20px,3.2vw,42px);
  color:#fff;line-height:1.2;margin-bottom:4%}
#s7 .url{font-family:Georgia,serif;font-size:clamp(20px,3.6vw,48px);
  color:#4FC3F7;font-weight:700;margin-bottom:5%;word-break:break-all}
#s7 ul{list-style:none;margin-bottom:5%}
#s7 ul li{display:flex;align-items:flex-start;gap:10px;
  color:#BBCCDD;font-size:clamp(11px,1.25vw,16px);margin-bottom:2.5%;line-height:1.5}
#s7 ul li::before{content:'';display:inline-block;width:9px;height:9px;
  border-radius:50%;background:var(--teal);flex-shrink:0;margin-top:5px}
#s7 .qrb{display:flex;align-items:center;gap:14px}
#s7 .qrb img{width:clamp(70px,9vw,120px);border-radius:6px;background:#fff;padding:5px}
#s7 .qrb p{color:#6688aa;font-size:clamp(9px,1vw,13px);line-height:1.5}
#s7 .R{position:absolute;right:0;top:0;bottom:58px;width:52%;
  display:flex;align-items:center;justify-content:center;padding:3%}
#s7 .R img{max-width:100%;max-height:100%;object-fit:contain;
  border-radius:8px;border:1px solid #1e3a52}
#s7 .ban{position:absolute;bottom:0;left:0;right:0;height:58px;
  background:var(--teal);display:flex;align-items:center;justify-content:center}
#s7 .ban p{color:#fff;font-weight:700;font-size:clamp(12px,1.4vw,18px)}

/* ── S8 ROBOTS ── */
#s8 .L{position:absolute;left:0;top:0;bottom:0;width:40%;
  padding:6% 4% 4% 5%;display:flex;flex-direction:column;justify-content:center}
#s8 .tag{font-size:clamp(9px,1vw,13px);font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);margin-bottom:3%}
#s8 h2{font-family:Georgia,serif;font-size:clamp(22px,3.8vw,50px);
  color:var(--ink);line-height:1.15;margin-bottom:5%}
#s8 h2 em{color:var(--red);font-style:normal}
#s8 ul{list-style:none}
#s8 ul li{display:flex;gap:12px;align-items:flex-start;
  font-size:clamp(11px,1.3vw,16px);color:var(--ink);margin-bottom:4%;line-height:1.5}
#s8 ul li .dot{width:11px;height:11px;border-radius:50%;
  background:var(--green);flex-shrink:0;margin-top:4px}
#s8 .R{position:absolute;right:0;top:0;bottom:0;width:62%;
  display:flex;align-items:center;justify-content:center;padding:3%}
#s8 .R img{max-width:100%;max-height:92%;object-fit:contain}
#s8 .cap{position:absolute;bottom:0;right:0;width:62%;
  background:var(--green);padding:9px 18px;
  font-size:clamp(9px,1vw,13px);color:#fff;text-align:center}

/* ── S9 CLOSING ── */
#s9{background:var(--cream)}
#s9 .top{background:var(--ink);padding:4% 6% 3%;text-align:center}
#s9 .top h2{font-family:Georgia,serif;font-size:clamp(26px,5.2vw,68px);color:#fff;line-height:1.1}
#s9 .top p{color:#aaa;font-size:clamp(11px,1.4vw,18px);margin-top:1%}
#s9 .cards{display:flex;gap:1.5%;padding:2.5% 3%;height:40%}
.ac{flex:1;border-radius:12px;background:#F0EDE6;padding:4% 3%;
  display:flex;flex-direction:column;align-items:center;
  justify-content:center;text-align:center;gap:5%}
.ac .ic{width:clamp(24px,3.5vw,48px);height:clamp(24px,3.5vw,48px);border-radius:50%}
.ac h3{font-family:Georgia,serif;font-size:clamp(13px,1.8vw,24px);color:var(--ink);line-height:1.2}
.ac p{font-size:clamp(9px,1vw,13px);color:var(--muted);line-height:1.4}
#s9 .bot{padding:0 5%;display:flex;justify-content:space-between;align-items:flex-end}
#s9 .lnk h3{font-family:Georgia,serif;font-size:clamp(16px,2.3vw,30px);
  color:var(--ink);margin-bottom:2%}
#s9 .lnk p{font-size:clamp(10px,1.1vw,14px);color:var(--teal);margin-bottom:.8%}
#s9 .lnk .em{color:var(--muted);font-size:clamp(9px,1vw,13px)}
#s9 .qri img{width:clamp(72px,9vw,130px);border-radius:6px;background:#fff;padding:5px}
</style>
</head>
<body>
<div id="deck">

<!-- S1 TITLE -->
<section class="slide active" id="s1">
  <div class="accent"></div>
  <div class="L">
    <div class="tag">CSULB Honors Program Symposium &nbsp;·&nbsp; Spring 2026</div>
    <h1 class="serif">When Robots<br>Race to<br><em>Find You.</em></h1>
    <div class="sub">A smarter coordination algorithm for battery-limited robot search teams —<br>
      and why one equation change makes them <b>6&times; more efficient.</b></div>
    <div class="who"><b>Fozhan Babaeiyan Ghamsari</b><br>
      Thesis Advisor: Dr. Oscar Morales-Ponce<br>
      California State University, Long Beach &nbsp;·&nbsp; CECS</div>
  </div>
  <div class="R"><img src="IMG_COMPARE" alt="M1 vs M4*"></div>
</section>

<!-- S2 PROBLEM -->
<section class="slide" id="s2">
  <div class="L">
    <p class="tag">01 &nbsp;/&nbsp; The Problem</p>
    <h2 class="serif">Disasters are<br>search problems.</h2>
    <p>A collapsed building. A flood. A lost hiker. A drone fleet can cover it —
      if the drones <b>don't waste battery revisiting the same spots.</b></p>
    <p class="note">Without coordination: robots overlap, energy is wasted, survivors wait longer.</p>
  </div>
  <div class="R">
    <img src="IMG_COMPARE" alt="Route comparison">
    <div class="lbls">
      <span class="bad">No coordination</span>
      <span class="good">Our method</span>
    </div>
  </div>
</section>

<!-- S3 MONEY SHOT -->
<section class="slide" id="s3">
  <div class="H HL">
    <p class="lbl-l">No coordination</p>
    <div class="num-l">53.65<span style="font-size:.5em">&times;</span></div>
    <p class="s-l">extra travel<br>vs. a perfect scout.</p>
  </div>
  <div class="div"></div>
  <div class="H HR">
    <p class="lbl-r">Our method.</p>
    <div class="num-r">3.02<span style="font-size:.5em">&times;</span></div>
    <p class="s-r">extra travel<br>vs. a perfect scout.</p>
  </div>
  <div class="ban">
    <p>Same map. Same robots. Same battery. One algorithm change.</p>
    <p style="font-weight:normal;opacity:.85">18&times; improvement &mdash; confirmed across 5,000 simulations.</p>
  </div>
</section>

<!-- S4 HOW IT WORKS -->
<section class="slide" id="s4">
  <div class="L">
    <h2 class="serif">They bid &mdash;<br>like an auction.</h2>
    <div class="step">
      <div class="sbar" style="background:var(--red)"></div>
      <div class="sbody">
        <h3 style="color:var(--red)">1 &nbsp;Bid</h3>
        <p>Every drone bids on every zone. Highest bid wins &mdash; that drone owns it.</p>
      </div>
    </div>
    <div class="step">
      <div class="sbar" style="background:var(--teal)"></div>
      <div class="sbody">
        <h3 style="color:var(--teal)">2 &nbsp;Chain</h3>
        <p>From its zone, the drone adds nearby stops until it runs out of battery.</p>
      </div>
    </div>
    <div class="step">
      <div class="sbar" style="background:var(--green)"></div>
      <div class="sbody">
        <h3 style="color:var(--green)">3 &nbsp;Update</h3>
        <p>Drones return, share what they found, and re-bid for the next round.</p>
      </div>
    </div>
  </div>
  <div class="R">
    <img src="IMG_WALK" alt="Algorithm walkthrough">
    <p class="cap">A: priors shown &nbsp;&middot;&nbsp; B: auction picks anchors &nbsp;&middot;&nbsp; C: chain fills energy &nbsp;&middot;&nbsp; D: update &amp; re-bid</p>
  </div>
</section>

<!-- S5 INSIGHT -->
<section class="slide" id="s5">
  <div class="hdr">
    <p class="tag">04 &nbsp;/&nbsp; The Key Insight</p>
    <h2 class="serif">One small change. Huge difference.</h2>
  </div>
  <div class="row">
    <div class="cb">
      <p class="tg">Before</p>
      <div class="fml">p / d</div>
      <p>Bid = probability &divide; distance<br>Doesn&rsquo;t account for battery drain.</p>
    </div>
    <div class="arr">&#9658;</div>
    <div class="ca">
      <p class="tg">Our method</p>
      <div class="fml">p / d&sup2;</div>
      <p><b>Bid = probability &divide; distance&sup2;</b><br>Penalizes far zones twice as hard.</p>
    </div>
    <div class="ch"><img src="IMG_BIDS" alt="Bid variants"></div>
  </div>
  <div class="bot">
    <p><b>Why does this matter?</b> Going far burns battery both ways &mdash; leaving less for additional stops.</p>
    <p>The squared penalty forces drones to commit only to zones they can actually afford.</p>
  </div>
</section>

<!-- S6 ROBUSTNESS -->
<section class="slide" id="s6">
  <div class="L">
    <p class="tag">05 &nbsp;/&nbsp; Robustness</p>
    <h2 class="serif">It always<br>wins.</h2>
    <p class="sub">We tested every configuration we could think of.</p>
    <div class="stats">
      <div class="sbox" style="background:var(--red)"><span class="big">1&ndash;6</span><span class="sm">robots</span></div>
      <div class="sbox" style="background:var(--teal)"><span class="big">8&ndash;30</span><span class="sm">battery levels</span></div>
      <div class="sbox" style="background:var(--green)"><span class="big">5,000</span><span class="sm">simulations</span></div>
    </div>
    <div class="verd">M4* (our method) is lowest &mdash; in every single test.<b>The ranking never flips.</b></div>
  </div>
  <div class="R"><img src="IMG_ROBOTS" alt="Robot sweep"></div>
</section>

<!-- S7 DEMO -->
<section class="slide" id="s7">
  <div class="L">
    <p class="tl">Live Demo</p>
    <h2 class="serif">See all 5 algorithms<br>race &mdash; right now.</h2>
    <div class="url">searchfcr.fozhan.dev</div>
    <ul>
      <li>Pick any seed &mdash; 5 methods run simultaneously</li>
      <li>Watch how each algorithm divides the map in real time</li>
      <li>See M4* consistently find the target with less travel</li>
      <li>Share your result via URL</li>
    </ul>
    <div class="qrb">
      <img src="IMG_QR" alt="QR">
      <p>Scan to open<br>on your phone</p>
    </div>
  </div>
  <div class="R"><img src="IMG_SIM" alt="Simulator"></div>
  <div class="ban"><p>OPEN NOW &mdash; watch it live during this talk</p></div>
</section>

<!-- S8 REAL ROBOTS -->
<section class="slide" id="s8">
  <div class="L">
    <p class="tag">06 &nbsp;/&nbsp; Real-World Validation</p>
    <h2 class="serif">From simulation<br>to <em>real robots.</em></h2>
    <ul>
      <li><div class="dot"></div>3D physics simulation with real robot dynamics</li>
      <li><div class="dot"></div>Battery constraints enforced at hardware level</li>
      <li><div class="dot"></div>Algorithm runs on-board &mdash; no central server needed</li>
      <li><div class="dot"></div>Scales to UAVs, ground robots, underwater AUVs</li>
    </ul>
  </div>
  <div class="R"><img src="IMG_SIM" alt="3D sim"></div>
  <div class="cap">3D physics sim &nbsp;&middot;&nbsp; 3 robots &nbsp;&middot;&nbsp; M4* auction &nbsp;&middot;&nbsp; target found in 2 sorties</div>
</section>

<!-- S9 CLOSING -->
<section class="slide" id="s9">
  <div class="top">
    <h2 class="serif">One equation change.</h2>
    <p>6&times; more efficient search. Fewer lives lost.</p>
  </div>
  <div class="cards">
    <div class="ac" style="border:2px solid var(--red)">
      <div class="ic" style="background:var(--red)"></div>
      <h3 class="serif">Earthquake<br>Rescue</h3>
      <p>Drones clear collapsed zones faster.</p>
    </div>
    <div class="ac" style="border:2px solid var(--teal)">
      <div class="ic" style="background:var(--teal)"></div>
      <h3 class="serif">Flood<br>Mapping</h3>
      <p>UAVs divide flood area autonomously.</p>
    </div>
    <div class="ac" style="border:2px solid var(--green)">
      <div class="ic" style="background:var(--green)"></div>
      <h3 class="serif">Mars<br>Exploration</h3>
      <p>Rovers with limited power map terrain.</p>
    </div>
    <div class="ac" style="border:2px solid #8B6914">
      <div class="ic" style="background:#8B6914"></div>
      <h3 class="serif">Underwater<br>Search</h3>
      <p>AUVs find objects on the ocean floor.</p>
    </div>
  </div>
  <div class="bot">
    <div class="lnk">
      <h3 class="serif">Questions? &nbsp;I&rsquo;d love to hear them.</h3>
      <p>searchfcr.fozhan.dev</p>
      <p>github.com/foojanbabaeeian/Multi-Robot-Algo</p>
      <p class="em">foojanbabaeeian@gmail.com</p>
    </div>
    <div class="qri"><img src="IMG_QR" alt="QR"></div>
  </div>
</section>

</div>

<button class="nav" id="prev">&#8592;</button>
<button class="nav" id="next">&#8594;</button>
<div id="bar"></div>
<div id="ctr">1 / 9</div>

<script>
const slides=Array.from(document.querySelectorAll('.slide'));
const N=slides.length;
let c=0;
function go(n){
  if(n<0||n>=N)return;
  slides[c].classList.remove('active');
  slides[c].classList.add('out');
  setTimeout(()=>slides[c].classList.remove('out'),350);
  c=n;
  slides[c].classList.add('active');
  document.getElementById('bar').style.width=((c+1)/N*100)+'%';
  document.getElementById('ctr').textContent=(c+1)+' / '+N;
}
document.getElementById('next').onclick=()=>go(c+1);
document.getElementById('prev').onclick=()=>go(c-1);
document.addEventListener('keydown',e=>{
  if(e.key==='ArrowRight'||e.key==='ArrowDown'||e.key===' ')go(c+1);
  if(e.key==='ArrowLeft'||e.key==='ArrowUp')go(c-1);
  if(e.key==='f'||e.key==='F')document.documentElement.requestFullscreen?.();
});
document.getElementById('deck').addEventListener('click',e=>{
  if(e.target.closest('.nav'))return;
  go(c+1);
});
document.getElementById('bar').style.width=(1/N*100)+'%';
</script>
</body>
</html>"""

# Substitute image placeholders
html = html.replace("IMG_COMPARE", fig["compare"])
html = html.replace("IMG_WALK",    fig["walk"])
html = html.replace("IMG_BIDS",    fig["bids"])
html = html.replace("IMG_ROBOTS",  fig["robots"])
html = html.replace("IMG_SIM",     fig["sim"])
html = html.replace("IMG_QR",      fig["qr"])

out = ROOT / "SearchFCR_UHP_Symposium.html"
out.write_text(html, encoding="utf-8")
print(f"Written: {out.name}  ({out.stat().st_size//1024} KB)")
