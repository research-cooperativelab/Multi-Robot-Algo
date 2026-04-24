const pptxgen = require("pptxgenjs");
const path    = require("path");

const OUT = "showcase_presentation.pptx";
const FIG = path.join(__dirname, "thesis", "figures");
const PYB = path.join(__dirname, "pybullet_demo", "screenshots");

// ── Palette ───────────────────────────────────────────────────────────────────
const C = {
  bg:      "0C1624",   // near-black blue slate — all content slides
  bgDeep:  "060E18",   // deepest black — hook & title
  bgCard:  "13243A",   // card / panel bg
  bgLight: "1A3050",   // lighter card bg
  bgDiv:   "0A1E32",   // section divider bg
  white:   "EEF2F6",   // primary text
  amber:   "F0A030",   // primary accent — use sparingly
  teal:    "38B2CC",   // secondary accent
  muted:   "4E6E88",   // dim labels, captions
  rule:    "1C3550",   // subtle dividers / borders
  ghost:   "1A2E42",   // very faint text for bg watermarks
};

const pres = new pptxgen();
pres.layout  = "LAYOUT_16x9";
pres.author  = "Fozhan Babaeiyan Ghamsari";
pres.title   = "Multi-Robot Search and Rescue Algorithms — Research Showcase";
pres.subject = "CSULB Honors Thesis, Spring 2026";

// ── Helpers ───────────────────────────────────────────────────────────────────
const R  = pres.ShapeType.rect;
const bg = (s, color) => { s.background = { color: color || C.bg }; };

// thin amber rule under label/title area
function hRule(s, y, color, x, w) {
  s.addShape(R, { x: x||0.42, y: y||0.82, w: w||9.16, h: 0.022,
    fill:{ color: color||C.amber }, line:{ color: color||C.amber } });
}

// small ALL-CAPS section label above title
function label(s, txt) {
  s.addText(txt.toUpperCase(), {
    x:0.42, y:0.14, w:9.16, h:0.22,
    fontFace:"Calibri", fontSize:8, bold:true, color:C.amber,
    align:"left", margin:0, charSpacing:3,
  });
}

// main slide title
function title(s, txt, y, h, sz) {
  s.addText(txt, {
    x:0.42, y:y||0.34, w:9.16, h:h||0.56,
    fontFace:"Calibri", fontSize:sz||28, bold:true,
    color:C.white, align:"left", valign:"middle", margin:0,
  });
}

// body paragraph block
function body(s, lines, x, y, w, h, sz) {
  s.addText(lines, {
    x:x||0.42, y:y||1.06, w:w||9.16, h:h||4.0,
    fontFace:"Calibri", fontSize:sz||13.5,
    color:C.white, align:"left", valign:"top", margin:[0,0,0,0],
    paraSpaceBefore:5, lineSpacingMultiple:1.15,
  });
}

function cap(s, txt, x, y, w) {
  s.addText(txt, {
    x:x||0.42, y:y||5.2, w:w||9.16, h:0.26,
    fontFace:"Calibri", fontSize:9.5, italic:true,
    color:C.muted, align:"center", margin:0,
  });
}

function fig(s, fname, x, y, w, h) {
  s.addImage({ path: path.join(FIG, fname), x, y, w, h });
}

function pybFig(s, fname, x, y, w, h) {
  s.addImage({ path: path.join(PYB, fname), x, y, w, h });
}

function num(s, n) {
  s.addText(`${n}`, {
    x:9.35, y:5.33, w:0.42, h:0.22,
    fontFace:"Calibri", fontSize:9, color:C.muted, align:"right", margin:0,
  });
}

// filled rectangle card
function card(s, x, y, w, h, color) {
  s.addShape(R, { x, y, w, h, fill:{ color: color||C.bgCard }, line:{ color: color||C.bgCard } });
}

// amber-highlighted key stat box
function statBox(s, big, small, x, y, w, h) {
  card(s, x, y, w, h, C.bgLight);
  s.addText(big, {
    x:x+0.1, y:y+0.1, w:w-0.2, h:h*0.55,
    fontFace:"Calibri", fontSize:28, bold:true,
    color:C.amber, align:"center", valign:"bottom", margin:0,
  });
  s.addText(small, {
    x:x+0.1, y:y+h*0.58, w:w-0.2, h:h*0.36,
    fontFace:"Calibri", fontSize:11,
    color:C.white, align:"center", valign:"top", margin:0,
  });
}

// ghost watermark text (background decoration)
function ghost(s, txt, x, y, w, h, sz) {
  s.addText(txt, {
    x, y, w, h, fontFace:"Calibri", fontSize:sz||120, bold:true,
    color:C.ghost, align:"right", valign:"middle", margin:0, transparency:0,
  });
}

// section divider slide
function sectionDiv(s, roman, sectionTitle, subtitle) {
  bg(s, C.bgDiv);
  // left amber bar
  s.addShape(R, { x:0, y:0, w:0.1, h:5.63, fill:{ color:C.amber }, line:{ color:C.amber } });
  // giant muted roman numeral watermark
  ghost(s, roman, 5.5, 0.5, 4.0, 4.6, 140);
  // section number small
  s.addText(roman, {
    x:0.4, y:1.4, w:1.8, h:1.4,
    fontFace:"Calibri", fontSize:72, bold:true,
    color:C.bgLight, align:"left", valign:"middle", margin:0,
  });
  s.addText(sectionTitle, {
    x:0.4, y:3.0, w:8.8, h:0.72,
    fontFace:"Calibri", fontSize:34, bold:true,
    color:C.white, align:"left", valign:"middle", margin:0,
  });
  s.addText(subtitle, {
    x:0.4, y:3.78, w:8.8, h:0.4,
    fontFace:"Calibri", fontSize:14, italic:true,
    color:C.muted, align:"left", margin:0,
  });
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 1 — TITLE
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s, C.bgDeep);

  // left amber column
  s.addShape(R, { x:0, y:0, w:0.1, h:5.63, fill:{ color:C.amber }, line:{ color:C.amber } });

  // ghost watermark
  ghost(s, "SAR", 4.8, 0.5, 5.0, 4.5, 170);

  s.addText("ON THE NUMERICAL ANALYSIS OF\nMULTI-ROBOT SEARCH AND RESCUE ALGORITHMS\nIN UNKNOWN ENVIRONMENTS", {
    x:0.32, y:0.52, w:9.3, h:2.5,
    fontFace:"Calibri", fontSize:30, bold:true, color:C.white,
    align:"left", valign:"top", margin:0, lineSpacingMultiple:1.25,
  });

  hRule(s, 3.1, C.amber, 0.32, 9.3);

  s.addText("CSULB Honors Thesis   |   Research Showcase   |   Spring 2026", {
    x:0.32, y:3.25, w:9.3, h:0.34,
    fontFace:"Calibri", fontSize:13, italic:true, color:C.teal,
    align:"left", margin:0,
  });
  s.addText("Fozhan Babaeiyan Ghamsari", {
    x:0.32, y:3.68, w:9.3, h:0.44,
    fontFace:"Calibri", fontSize:20, bold:true, color:C.white,
    align:"left", margin:0,
  });
  s.addText("Advisor: Dr. Oscar Morales-Ponce  |  Computer Engineering and Computer Science  |  CSULB", {
    x:0.32, y:4.18, w:9.3, h:0.3,
    fontFace:"Calibri", fontSize:12, color:C.muted, align:"left", margin:0,
  });
  s.addText("github.com/foojanbabaeeian/Multi-Robot-Algo", {
    x:0.32, y:4.58, w:9.3, h:0.28,
    fontFace:"Calibri", fontSize:12, color:C.teal, align:"left", margin:0,
  });

  s.addNotes(`Introduce yourself: name, Computer Science / Computer Engineering major, CSULB University Honors Program. Your advisor is Dr. Oscar Morales-Ponce.

Pause after saying the title. Don't rush into the content yet — the next slide will pull the audience in.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 2 — HOOK (TED-TALK STYLE)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s, C.bgDeep);

  // A single haunting number as background
  s.addText("?", {
    x:5.5, y:-0.2, w:4.3, h:5.5,
    fontFace:"Calibri", fontSize:360, bold:true, color:C.ghost,
    align:"right", valign:"middle", margin:0,
  });

  // The scenario — staged, plain, white
  s.addText("A building collapses.", {
    x:0.55, y:0.75, w:7.5, h:0.65,
    fontFace:"Calibri", fontSize:32, bold:false, color:C.white,
    align:"left", valign:"middle", margin:0,
  });
  s.addText("A survivor is somewhere inside.", {
    x:0.55, y:1.48, w:7.5, h:0.65,
    fontFace:"Calibri", fontSize:32, bold:false, color:C.white,
    align:"left", valign:"middle", margin:0,
  });
  s.addText("You have three autonomous robots", {
    x:0.55, y:2.22, w:7.5, h:0.65,
    fontFace:"Calibri", fontSize:32, bold:false, color:C.white,
    align:"left", valign:"middle", margin:0,
  });
  s.addText("and limited battery.", {
    x:0.55, y:2.95, w:7.5, h:0.65,
    fontFace:"Calibri", fontSize:32, bold:false, color:C.white,
    align:"left", valign:"middle", margin:0,
  });

  // The question — bigger, amber
  hRule(s, 3.85, C.amber, 0.55, 7.0);
  s.addText("Where do you send them first?", {
    x:0.55, y:4.0, w:9.0, h:0.7,
    fontFace:"Calibri", fontSize:36, bold:true, color:C.amber,
    align:"left", valign:"middle", margin:0,
  });

  s.addNotes(`PAUSE before this slide appears. Let it breathe.

Read the lines slowly, one by one — there's a reason they're broken up. Let the audience feel the weight of each sentence.

When you get to "Where do you send them first?" — pause again. Let the audience sit with the question.

Then say: "It turns out this question has a mathematically optimal answer. And the difference between a good answer and a bad one is the difference between finding the survivor in the first pass, or running out of battery having found nothing."

This hook works for any audience — from computer science faculty to first-year students to community members. No jargon, just stakes.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SECTION DIVIDER I — THE PROBLEM
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  sectionDiv(s, "I", "The Problem", "What makes autonomous search hard — and how do we measure success?");
  s.addNotes(`Short bridging moment. Say: "Let's start with the problem itself — not the algorithm, not the results — just what we're trying to solve and why it's hard."`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 4 — OPERATIONAL FAILURES
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Motivation");
  title(s, "Three Coordination Failures That Cost Lives", 0.34, 0.52, 25);
  hRule(s, 0.9);

  const cols = [
    {
      icon: "Coverage\nduplication",
      body: "Without communication, multiple robots fly to the same debris pile while other zones go unsearched. Probability mass is wasted.",
      x: 0.42,
    },
    {
      icon: "Battery\nexhaustion",
      body: "Robots traveling inefficiently to distant sites return empty-handed. Limited battery means every wasted sortie is unrecoverable.",
      x: 3.55,
    },
    {
      icon: "Radio\nblackout",
      body: "Structural rubble blocks wireless signals during flight. Site assignments must be finalized before robots depart — no mid-sortie updates.",
      x: 6.68,
    },
  ];

  cols.forEach((c) => {
    card(s, c.x, 1.06, 2.84, 3.42, C.bgCard);
    // amber top band
    s.addShape(R, { x:c.x, y:1.06, w:2.84, h:0.06, fill:{ color:C.amber }, line:{ color:C.amber } });
    s.addText(c.icon, {
      x:c.x+0.18, y:1.22, w:2.48, h:0.72,
      fontFace:"Calibri", fontSize:14, bold:true, color:C.amber,
      align:"left", valign:"top", margin:0,
    });
    s.addShape(R, { x:c.x+0.18, y:1.98, w:2.48, h:0.02,
      fill:{ color:C.rule }, line:{ color:C.rule } });
    s.addText(c.body, {
      x:c.x+0.18, y:2.08, w:2.48, h:2.22,
      fontFace:"Calibri", fontSize:12.5, color:C.white,
      align:"left", valign:"top", margin:0, lineSpacingMultiple:1.2,
    });
  });

  s.addText("February 2023, Turkey-Syria earthquake: 160,000+ structures damaged, autonomous systems deployed — all three failure modes documented in post-mission reports.", {
    x:0.42, y:4.65, w:9.16, h:0.55,
    fontFace:"Calibri", fontSize:11.5, italic:true, color:C.muted,
    align:"left", margin:0,
  });

  num(s, 4);
  s.addNotes(`Open with human stakes — survival probability drops sharply with every minute after structural collapse.

The three cards describe documented coordination failures. They share a common root: no rigorous framework for energy-constrained, probabilistically-guided coordination.

Transition: "These three failures are what this thesis tackles. Not separately — together, as a single formal problem."`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 5 — FORMAL PROBLEM
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Problem Formulation");
  title(s, "The Formal Setup", 0.34, 0.52, 27);
  hRule(s, 0.9);

  ghost(s, "n·R·E", 5.5, 1.0, 4.2, 3.8, 90);

  // four parameter cards, left column
  const params = [
    ["n sites", "Each site i carries a prior probability pᵢ of containing the survivor. Probabilities are Bayesian-updated as sites are cleared."],
    ["R robots", "All start at a shared base station. Energy budget E per sortie, spent as Euclidean travel distance."],
    ["No mid-flight radio", "Communication only at base. Assignments are finalized before departure — robots cannot coordinate during the sortie."],
    ["Finder-centric objective", "Minimize the travel distance of the robot that finds the target — not fleet total, not time to clear all sites."],
  ];
  params.forEach(([hd, bd], i) => {
    const yy = 1.08 + i * 1.04;
    s.addText(hd, {
      x:0.42, y:yy, w:5.0, h:0.3,
      fontFace:"Calibri", fontSize:13.5, bold:true, color:C.amber,
      align:"left", margin:0,
    });
    s.addText(bd, {
      x:0.42, y:yy+0.32, w:5.0, h:0.62,
      fontFace:"Calibri", fontSize:12.5, color:C.white,
      align:"left", valign:"top", margin:0,
    });
  });

  // right panel: instance
  card(s, 5.65, 1.04, 4.0, 4.18, C.bgCard);
  s.addText("DEFAULT INSTANCE", {
    x:5.82, y:1.15, w:3.66, h:0.28,
    fontFace:"Calibri", fontSize:8.5, bold:true, charSpacing:3,
    color:C.amber, align:"center", margin:0,
  });
  s.addShape(R, { x:5.82, y:1.46, w:3.66, h:0.02, fill:{ color:C.rule }, line:{ color:C.rule } });
  const defaults = [
    ["n", "30 candidate sites"],
    ["R", "3 robots"],
    ["E", "14 energy units per sortie"],
    ["L", "10 × 10 search area"],
    ["Trials", "5,000 paired Monte Carlo"],
  ];
  defaults.forEach(([k, v], i) => {
    s.addText(k, {
      x:5.82, y:1.58+i*0.58, w:0.5, h:0.44,
      fontFace:"Calibri", fontSize:14, bold:true, color:C.amber,
      align:"center", valign:"middle", margin:0,
    });
    s.addText(v, {
      x:6.38, y:1.58+i*0.58, w:3.1, h:0.44,
      fontFace:"Calibri", fontSize:12.5, color:C.white,
      align:"left", valign:"middle", margin:0,
    });
  });

  num(s, 5);
  s.addNotes(`Walk through the four parameters. Draw attention to what makes this hard:

1. Robots cannot communicate during flight — so the optimal strategy must be decided in advance.
2. Limited battery means they cannot just exhaustively check everything.
3. The target location is unknown — we have probabilistic beliefs, not certainty.
4. The objective is finder-centric — we care about the specific robot that succeeds, not the fleet average.

The default parameters (n=30, R=3, E=14) were chosen to be tractable for analysis while capturing the essential structure of real deployment scenarios.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 6 — FCR METRIC (with figure)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Evaluation Metric");
  title(s, "How Do We Measure Performance?", 0.34, 0.52, 27);
  hRule(s, 0.9);

  // Left: metric definition
  s.addText("Finder Competitive Ratio", {
    x:0.42, y:1.06, w:4.8, h:0.36,
    fontFace:"Calibri", fontSize:16, bold:true, color:C.teal,
    align:"left", margin:0,
  });
  card(s, 0.42, 1.48, 4.8, 0.72, C.bgLight);
  s.addText("FCR  =  D_finder  ÷  D_optimal", {
    x:0.42, y:1.48, w:4.8, h:0.72,
    fontFace:"Calibri", fontSize:22, bold:true, color:C.amber,
    align:"center", valign:"middle", margin:0,
  });

  s.addText("D_finder", {
    x:0.42, y:2.3, w:1.5, h:0.3,
    fontFace:"Calibri", fontSize:12, bold:true, color:C.amber,
    align:"left", margin:0,
  });
  s.addText("Distance traveled by the robot that finds the survivor", {
    x:2.05, y:2.3, w:3.17, h:0.3,
    fontFace:"Calibri", fontSize:12, color:C.white,
    align:"left", margin:0,
  });
  s.addText("D_optimal", {
    x:0.42, y:2.65, w:1.5, h:0.3,
    fontFace:"Calibri", fontSize:12, bold:true, color:C.teal,
    align:"left", margin:0,
  });
  s.addText("Direct path an omniscient robot would take (knowing the location)", {
    x:2.05, y:2.65, w:3.17, h:0.3,
    fontFace:"Calibri", fontSize:12, color:C.white,
    align:"left", margin:0,
  });

  s.addShape(R, { x:0.42, y:3.06, w:4.8, h:0.02, fill:{ color:C.rule }, line:{ color:C.rule } });

  const interp = [
    ["FCR = 1.0", "Perfect — the finder took the theoretical shortest path.", C.teal],
    ["FCR > 1.0", "Overhead from uncertainty and coordination constraints.", C.white],
    ["Lower is better", "The best algorithms minimize wasted search distance.", C.amber],
  ];
  interp.forEach(([k, v, col], i) => {
    s.addText(k, { x:0.42, y:3.16+i*0.46, w:1.6, h:0.38,
      fontFace:"Calibri", fontSize:12, bold:true, color:col, align:"left", margin:0 });
    s.addText(v, { x:2.1, y:3.16+i*0.46, w:3.12, h:0.38,
      fontFace:"Calibri", fontSize:12, color:C.white, align:"left", margin:0 });
  });

  // Right: figure
  fig(s, "fig_fcr_explanation.png", 5.55, 1.0, 4.1, 3.52);
  cap(s, "Worked example: robot visits A and B, then finds T. FCR = 9.98 ÷ 6.67 = 1.50.", 5.55, 4.56, 4.1);

  num(s, 6);
  s.addNotes(`FCR is the primary contribution of the thesis as an evaluation metric.

Walk through the worked example: the robot checks site A (wrong), then site B (wrong), then finds the target T. Its total path is 9.98 units. An omniscient robot would have gone directly — 6.67 units. FCR = 1.50.

Key insight: this is finder-centric. We only look at the robot that succeeds — because that robot's path determines how quickly the survivor is reached for extraction. The other robots are irrelevant to this metric.

FCR = 1 is a theoretical lower bound requiring perfect information. Real algorithms with uncertainty and energy constraints will always exceed 1. The question is how close we can get.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SECTION DIVIDER II — THE FRAMEWORK
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  sectionDiv(s, "II", "The Framework", "Four models, each adding one capability — the gaps between them are the science.");
  s.addNotes(`Transition: "Now I'll walk you through the four algorithmic models this thesis compares. Think of them as a staircase — each step adds one new capability, and the height of each step tells you exactly what that capability is worth."`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 8 — FOUR MODELS (with model tree)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Algorithmic Framework");
  title(s, "A Staircase of Four Models", 0.34, 0.52, 27);
  hRule(s, 0.9);

  fig(s, "fig_model_tree.png", 0.32, 1.0, 4.9, 4.35);
  cap(s, "The four models form a hierarchy. Each gap isolates the value of a single design decision.", 0.32, 5.4, 4.9);

  // right: model table
  const rows = [
    [
      { text: "Model",       options: { bold:true, color:C.amber, fontFace:"Calibri", fontSize:12 } },
      { text: "Capability Added",    options: { bold:true, color:C.amber, fontFace:"Calibri", fontSize:12 } },
      { text: "FCR",         options: { bold:true, color:C.amber, fontFace:"Calibri", fontSize:12 } },
    ],
    [
      { text: "M1  Random",          options: { color:C.muted,  fontFace:"Calibri", fontSize:12 } },
      { text: "Baseline — no coordination", options: { color:C.muted, fontFace:"Calibri", fontSize:12 } },
      { text: "18.74",               options: { color:C.muted,  fontFace:"Calibri", fontSize:12, bold:true } },
    ],
    [
      { text: "M2  Auction",         options: { color:C.white,  fontFace:"Calibri", fontSize:12 } },
      { text: "SSI auction, no battery limit", options: { color:C.white, fontFace:"Calibri", fontSize:12 } },
      { text: "2.83",                options: { color:C.teal,   fontFace:"Calibri", fontSize:12, bold:true } },
    ],
    [
      { text: "M3  Constrained",     options: { color:C.white,  fontFace:"Calibri", fontSize:12 } },
      { text: "Battery reintroduced, one site per sortie", options: { color:C.white, fontFace:"Calibri", fontSize:12 } },
      { text: "6.32",                options: { color:C.white,  fontFace:"Calibri", fontSize:12, bold:true } },
    ],
    [
      { text: "M4*  Multi-sortie",   options: { color:C.amber,  fontFace:"Calibri", fontSize:12, bold:true } },
      { text: "Chained sites + novel p/d² bid", options: { color:C.amber, fontFace:"Calibri", fontSize:12 } },
      { text: "3.11",                options: { color:C.amber,  fontFace:"Calibri", fontSize:12, bold:true } },
    ],
  ];
  s.addTable(rows, {
    x:5.45, y:1.06, w:4.2, rowH:0.78,
    fill: C.bgCard,
    border: { pt:1, color:C.rule },
    align:"left", valign:"middle", margin:[4,8,4,8],
  });

  s.addText("Each model answers one question:\nWhat is this capability worth?", {
    x:5.45, y:5.03, w:4.2, h:0.45,
    fontFace:"Calibri", fontSize:11.5, italic:true, color:C.muted,
    align:"center", margin:0,
  });

  num(s, 8);
  s.addNotes(`This is the intellectual architecture of the thesis.

M1 is the floor — zero coordination, random site selection. It is deliberately a bad algorithm.
M2 is the ceiling — what is achievable with perfect coordination and unlimited battery.
M3 adds back the battery constraint but keeps the SSI auction.
M4/M4* adds multi-site sorties and the novel p/d² bid function.

The key insight: by comparing consecutive models, we can precisely isolate the value of each design decision. The 18.74 → 2.83 gap is the value of coordination. The 2.83 → 6.32 gap is the cost of battery. The 6.32 → 3.11 gap is what chaining and the novel bid recover.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 9 — SSI AUCTION
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Coordination Mechanism");
  title(s, "The SSI Auction: How Robots Coordinate", 0.34, 0.52, 27);
  hRule(s, 0.9);

  ghost(s, "BID", 6.0, 1.2, 3.8, 3.6, 100);

  const steps = [
    ["1", "Return to base",    "All robots return after a sortie. Posterior probabilities are updated from cleared sites."],
    ["2", "Each robot bids",   "Every unassigned robot submits a bid for every unassigned site. The bid encodes how valuable that site is from the robot's current position."],
    ["3", "Highest bid wins",  "The site-robot pair with the highest bid is allocated. Both are removed from contention."],
    ["4", "Repeat until done", "Steps 2–3 iterate until all robots have assignments. Robots depart simultaneously."],
  ];

  steps.forEach(([n2, hd, bd], i) => {
    const yy = 1.08 + i * 1.04;
    // step number circle
    card(s, 0.42, yy, 0.52, 0.52, C.amber);
    s.addText(n2, {
      x:0.42, y:yy, w:0.52, h:0.52,
      fontFace:"Calibri", fontSize:18, bold:true, color:C.bgDeep,
      align:"center", valign:"middle", margin:0,
    });
    s.addText(hd, {
      x:1.1, y:yy, w:8.2, h:0.3,
      fontFace:"Calibri", fontSize:13.5, bold:true, color:C.white,
      align:"left", margin:0,
    });
    s.addText(bd, {
      x:1.1, y:yy+0.32, w:8.2, h:0.62,
      fontFace:"Calibri", fontSize:12.5, color:C.muted,
      align:"left", margin:0,
    });
  });

  card(s, 0.42, 5.12, 9.16, 0.38, C.bgLight);
  s.addText("SSI (M3 FCR = 6.32) beats centralized Hungarian assignment (H\u1D48 FCR = 6.88) by 8.1% — the iterative structure adapts assignments to fleet geometry.", {
    x:0.58, y:5.12, w:9.0, h:0.38,
    fontFace:"Calibri", fontSize:12, color:C.white,
    align:"left", valign:"middle", margin:0,
  });

  num(s, 9);
  s.addNotes(`Walk through the four steps.

The key insight that makes SSI better than Hungarian assignment: SSI is sequential. After robot k is assigned to site A, the next bidding round knows where robot k will be — and assigns the next robot accordingly. This cascading adaptation to fleet geometry is what produces the 8.1% improvement over Hungarian.

If asked: "Why not just solve the full combinatorial assignment optimally?" — the answer is that the exact optimal assignment is NP-hard for large instances. SSI is a polynomial-time greedy approximation that, in practice, outperforms the Hungarian algorithm on this metric because the metric is finder-centric, not fleet-total.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 10 — SORTIE CHAINING
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Model Design");
  title(s, "From Single-Site to Multi-Site Sorties", 0.34, 0.52, 26);
  hRule(s, 0.9);

  // M3 problem
  card(s, 0.42, 1.08, 4.3, 1.75, C.bgCard);
  s.addShape(R, { x:0.42, y:1.08, w:4.3, h:0.05, fill:{ color:C.muted }, line:{ color:C.muted } });
  s.addText("Model 3 — The Problem", {
    x:0.58, y:1.18, w:3.98, h:0.3,
    fontFace:"Calibri", fontSize:12.5, bold:true, color:C.muted,
    align:"left", margin:0,
  });
  s.addText("Each sortie visits exactly one site. Round-trip cost = 2d. With E = 14 and d = 3: the robot uses 6 of 14 energy units on transit — 57% wasted on getting there and back.", {
    x:0.58, y:1.52, w:3.98, h:1.2,
    fontFace:"Calibri", fontSize:12.5, color:C.white,
    align:"left", margin:0, lineSpacingMultiple:1.2,
  });

  // M4 solution
  card(s, 0.42, 3.0, 4.3, 1.85, C.bgCard);
  s.addShape(R, { x:0.42, y:3.0, w:4.3, h:0.05, fill:{ color:C.amber }, line:{ color:C.amber } });
  s.addText("Model 4 — The Solution", {
    x:0.58, y:3.1, w:3.98, h:0.3,
    fontFace:"Calibri", fontSize:12.5, bold:true, color:C.amber,
    align:"left", margin:0,
  });
  s.addText("After reaching site 1, check: can we visit site 2 and still return? If yes, extend. Chain as many sites as the budget permits.", {
    x:0.58, y:3.44, w:3.98, h:0.9,
    fontFace:"Calibri", fontSize:12.5, color:C.white,
    align:"left", margin:0, lineSpacingMultiple:1.2,
  });

  // energy check equation
  card(s, 0.42, 4.98, 4.3, 0.5, C.bgLight);
  s.addText("d(current → next) + d(next → base)  ≤  E_remaining", {
    x:0.52, y:4.98, w:4.1, h:0.5,
    fontFace:"Calibri", fontSize:14, bold:true, color:C.white,
    align:"center", valign:"middle", margin:0,
  });

  // right: stats
  const facts = [
    { big: "~90%", small: "of M2→M3 gap\nrecovered by M4" },
    { big: "6.32", small: "M3 FCR\n(1 site per sortie)" },
    { big: "3.11", small: "M4* FCR\n(chained sorties)" },
  ];
  facts.forEach((f, i) => {
    statBox(s, f.big, f.small, 5.05, 1.08 + i * 1.7, 4.5, 1.5);
  });

  num(s, 10);
  s.addNotes(`The sortie chaining insight is elegant: the energy that M3 wastes on early returns is recoverable by simply staying out longer.

The energy check is the critical safety condition — it guarantees the robot always has enough energy to return to base. This is not an approximation; it's an exact feasibility check.

The result: ~90% of the M2-to-M3 performance gap is recovered by this simple extension. Multi-site chaining is the single most impactful mechanism in the thesis.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 11 — p/d² BID (with figure)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Primary Contribution");
  title(s, "The p/d\u00B2 Bid Function: Novel Algorithmic Contribution", 0.3, 0.6, 24);
  hRule(s, 0.94);

  // Classic vs new
  card(s, 0.42, 1.06, 2.6, 0.68, C.bgCard);
  s.addText("Classical  p/d", {
    x:0.52, y:1.06, w:2.4, h:0.68,
    fontFace:"Calibri", fontSize:22, bold:true, color:C.muted,
    align:"center", valign:"middle", margin:0,
  });

  s.addText("→", {
    x:3.1, y:1.06, w:0.6, h:0.68,
    fontFace:"Calibri", fontSize:20, bold:true, color:C.rule,
    align:"center", valign:"middle", margin:0,
  });

  card(s, 3.78, 1.06, 2.6, 0.68, C.bgLight);
  s.addText("This thesis  p/d\u00B2", {
    x:3.88, y:1.06, w:2.4, h:0.68,
    fontFace:"Calibri", fontSize:22, bold:true, color:C.amber,
    align:"center", valign:"middle", margin:0,
  });

  // Cost-foreclosure argument
  s.addText("The cost-foreclosure argument:", {
    x:0.42, y:1.9, w:6.1, h:0.3,
    fontFace:"Calibri", fontSize:13, bold:true, color:C.teal,
    align:"left", margin:0,
  });

  const steps = [
    "1.  Anchor at distance d costs at least 2d energy (round-trip minimum).",
    "2.  Remaining budget for chain extensions  =  E − 2d   (linear in d).",
    "3.  Every extra unit of d shrinks the extension budget by 2 units.",
    "4.  Effective cost of distance is superlinear, not linear.",
    "5.  Therefore the bid should penalize d more than linearly — p/d² is the natural approximation.",
  ];
  steps.forEach((st, i) => {
    s.addText(st, {
      x:0.42, y:2.26+i*0.5, w:6.1, h:0.42,
      fontFace:"Calibri", fontSize:12.5, color: i===4 ? C.amber : C.white,
      bold: i===4,
      align:"left", margin:0,
    });
  });

  // right: figure
  fig(s, "fig_bid_variants.png", 6.72, 1.0, 2.88, 4.42);
  cap(s, "FCR distributions:\np/d vs p/d² vs uniform", 6.72, 5.46, 2.88);

  num(s, 11);
  s.addNotes(`This is the primary algorithmic contribution. Spend time here.

The cost-foreclosure argument in plain English: "Going far doesn't just cost more energy up front — it also shrinks the budget you have left for the rest of the sortie. So the true cost of distance is superlinear. Quadratic is the right approximation."

The figure shows the FCR distributions: p/d² (proposed) produces a tighter, lower distribution — particularly at the tail, meaning it fails less catastrophically on hard instances.

At default parameters, p/d² achieves FCR = 3.11 vs p/d's 3.16 — a 1.5% improvement. The gap grows substantially at large instance sizes and tight energy budgets, where the cost-foreclosure effect is most pronounced.

If asked about intuition: draw an analogy to GPS routing — going slightly out of your way to avoid a highway on-ramp when your gas tank is nearly empty. The quadratic penalty on distance is doing exactly that.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 12 — M4* WALKTHROUGH (full figure)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Algorithm Walkthrough");
  title(s, "One Complete Iteration of M4*", 0.34, 0.52, 27);
  hRule(s, 0.9);

  fig(s, "fig_m4star_walkthrough.png", 0.32, 1.0, 9.36, 4.1);
  cap(s, "A: Prior probabilities (circle size = pᵢ).   B: Auction assigns anchor sites to 3 robots.   C: p/d² chain extends each sortie.   D: Bayesian update after round completion.", 0.32, 5.14, 9.36);

  num(s, 12);
  s.addNotes(`Walk through each panel slowly — this figure is the most important visual in the thesis.

Panel A: 30 sites with prior probabilities shown as circle sizes. Larger circles are more likely to contain the survivor. Three robots (triangles) start at the base.

Panel B: The SSI auction runs. Each robot is assigned one anchor site. Notice the assignments are spread across the space — the auction avoids redundant coverage.

Panel C: From each anchor, the greedy p/d² chain extends. Robots visit additional sites while energy permits. Notice they prioritize nearby, high-probability sites.

Panel D: After all robots return, Bayesian update — cleared sites have their probability redistributed to remaining sites. The next round begins with a sharper posterior.

Let this visual breathe. The audience should be able to see the algorithm "working" — three robots solving a genuinely hard optimization problem, round by round.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SECTION DIVIDER III — THE RESULTS
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  sectionDiv(s, "III", "The Results", "Five experiments, 5,000 trials each — what the numbers actually say.");
  s.addNotes(`Transition: "Now let's look at what the experiments found. I'll walk through the five key results, starting with the headline number and then drilling into each component."`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 14 — MAIN RESULTS
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Main Results");
  title(s, "5,000 Paired Monte Carlo Trials — Headline Numbers", 0.3, 0.6, 24);
  hRule(s, 0.94);

  fig(s, "fig_main_comparison.png", 0.32, 1.0, 5.2, 4.35);
  cap(s, "Mean FCR per model. n=30, R=3, E=14, L=10. 95% confidence intervals shown.", 0.32, 5.38, 5.2);

  // right: key numbers stacked
  const entries = [
    { m:"M1  Random",               fcr:"18.74", color:C.muted },
    { m:"M2  Auction (no battery)",  fcr:"2.83",  color:C.teal  },
    { m:"H_d  Hungarian (distance)", fcr:"6.88",  color:C.muted },
    { m:"M3  Single-site sortie",    fcr:"6.32",  color:C.white },
    { m:"M4  Multi-sortie (p/d)",    fcr:"3.16",  color:C.white },
    { m:"M4*  Multi-sortie (p/d²)",  fcr:"3.11",  color:C.amber },
  ];
  entries.forEach((e, i) => {
    s.addText(e.m, {
      x:5.68, y:1.06+i*0.62, w:3.3, h:0.48,
      fontFace:"Calibri", fontSize:11.5, color:e.color,
      align:"left", valign:"middle", margin:0, bold: e.color===C.amber,
    });
    s.addText(e.fcr, {
      x:9.0, y:1.06+i*0.62, w:0.68, h:0.48,
      fontFace:"Calibri", fontSize:14, bold:true, color:e.color,
      align:"right", valign:"middle", margin:0,
    });
  });

  s.addShape(R, { x:5.68, y:4.88, w:4.0, h:0.02, fill:{ color:C.rule }, line:{ color:C.rule } });
  s.addText("Wilcoxon signed-rank, Bonferroni corrected, p < 0.001 for H1–H4", {
    x:5.68, y:4.95, w:4.0, h:0.28,
    fontFace:"Calibri", fontSize:10, italic:true, color:C.muted,
    align:"left", margin:0,
  });

  num(s, 14);
  s.addNotes(`This is the primary results slide. Walk through each gap and narrate it.

18.74 → 2.83: the value of coordination. A 6.6x improvement purely from communication.
2.83 → 6.32: the cost of battery constraints. Adding energy limits degrades performance significantly.
6.32 → 3.11: what the combination of chaining and p/d² recovers. Nearly the whole battery penalty is erased.
6.88 → 6.32: SSI auction beats centralized Hungarian by 8.1% — the mechanism matters.
3.16 → 3.11: the p/d² bid improvement — 1.5% at default, growing with instance size.

All comparisons statistically significant at p < 0.001 after Bonferroni correction (paired Wilcoxon, non-parametric test appropriate for skewed FCR distributions).`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 15 — COORDINATION GAIN (M1 vs M4*)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Finding 1 — Coordination Gain");
  title(s, "6.6× Improvement from Coordination Alone", 0.34, 0.52, 27);
  hRule(s, 0.9);

  fig(s, "fig_m1_vs_m4star.png", 0.32, 1.0, 9.36, 4.15);
  cap(s, "Same 30-site instance. Left: M1 uncoordinated (FCR = 53.65). Right: M4* coordinated (FCR = 3.02). Same robots. Same battery. Same target location. Different algorithm.", 0.32, 5.2, 9.36);

  num(s, 15);
  s.addNotes(`Let this figure speak. Pause here and let the audience absorb it.

Left panel: M1 with no coordination. Robots duplicate effort. Multiple paths lead to the same sites. High-probability sites (large circles) are neglected while low-probability sites get redundant visits. The finder's path is long, inefficient, and expensive.

Right panel: M4* on the exact same instance. Non-overlapping tours. High-probability sites are visited early. Compact chain extensions maximize coverage per unit of energy.

The specific FCRs on this one instance: 53.65 and 3.02 — a 17x difference. Across 5,000 trials: 18.74 vs 3.11, a 6x difference.

Say to the audience: "What changed between these two panels? Only the algorithm. Same robots, same battery, same uncertainty, same target. The coordination is entirely in software."

This is the thesis in one slide.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 16 — TARGET-DELAY ANOMALY
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Finding 2 — Target-Delay Anomaly");
  title(s, "When Making a Tour Shorter Makes the Search Worse", 0.3, 0.6, 24);
  hRule(s, 0.94);

  // left text
  s.addText("Hypothesis:", {
    x:0.42, y:1.06, w:4.8, h:0.3,
    fontFace:"Calibri", fontSize:13, bold:true, color:C.teal, align:"left", margin:0,
  });
  s.addText("Apply 2-opt post-processing — the standard tour-length optimizer — to M4* tours. Shorter tours should mean faster search.", {
    x:0.42, y:1.4, w:4.8, h:0.72,
    fontFace:"Calibri", fontSize:12.5, color:C.white, align:"left", margin:0, lineSpacingMultiple:1.2,
  });

  s.addText("Result (1,000 trials):", {
    x:0.42, y:2.26, w:4.8, h:0.3,
    fontFace:"Calibri", fontSize:13, bold:true, color:C.amber, align:"left", margin:0,
  });

  const results2 = [
    ["Tour length", "12.567 → 12.024   (−0.543 units)", C.teal,  false],
    ["Mean FCR",    "3.093 → 3.257       (+5.3%)",       C.amber, true ],
  ];
  results2.forEach(([k, v, col, big], i) => {
    card(s, 0.42, 2.62+i*0.76, 4.8, 0.64, C.bgCard);
    s.addText(k, {
      x:0.58, y:2.62+i*0.76, w:1.6, h:0.64,
      fontFace:"Calibri", fontSize:12, bold:true, color:C.muted,
      align:"left", valign:"middle", margin:0,
    });
    s.addText(v, {
      x:2.25, y:2.62+i*0.76, w:3.0, h:0.64,
      fontFace:"Calibri", fontSize: big ? 15 : 12, bold:big,
      color:col, align:"left", valign:"middle", margin:0,
    });
  });

  s.addText("Why: 2-opt optimizes geometric tour length — it is blind to site probabilities. The greedy p/d² chain already places high-probability sites early, where the target is most likely to be. 2-opt reorders by geometry alone, diluting this probability-weighted prefix.\n\nThe standard \"build, then polish with 2-opt\" pipeline is not merely neutral — it is actively harmful under Bayesian priors and finder-centric objectives.", {
    x:0.42, y:4.2, w:4.8, h:1.3,
    fontFace:"Calibri", fontSize:12, color:C.white,
    align:"left", margin:0, lineSpacingMultiple:1.2,
  });

  fig(s, "fig_target_delay.png", 5.5, 1.0, 4.16, 4.42);
  cap(s, "Left: target rank distribution (greedy vs 2-opt). Right: per-trial scatter — upper-right = anomaly.", 5.5, 5.46, 4.16);

  num(s, 16);
  s.addNotes(`This is the most counterintuitive result in the thesis. Open with the hypothesis — the audience will almost certainly agree that shorter tours should be better. Then reveal the result.

The mechanism: the greedy chain is already doing something intelligent — it front-loads high-probability sites. When the target is drawn from the prior, it's most likely to be in a high-probability site — so the greedy ordering puts the target early in the tour. 2-opt destroys this probability-weighted ordering in favor of pure geometry.

Named finding: the Target-Delay Anomaly.

Practical message for the audience: tour optimizers built for the Traveling Salesman Problem are the WRONG tool for probabilistic Bayesian search. This has implications for any robot task-planning pipeline that ends with a "polish" step.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 17 — ENERGY SWEEP
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Parametric Sweep — Energy");
  title(s, "Results Hold Across Battery Budgets (E = 8 to 30)", 0.3, 0.6, 24);
  hRule(s, 0.94);

  fig(s, "fig_energy_sweep.png", 0.32, 1.0, 5.5, 4.3);
  cap(s, "FCR vs energy budget E. At E = 30, M4* surpasses the unconstrained M2 ceiling (2.83 → 2.67).", 0.32, 5.34, 5.5);

  const obs3 = [
    ["Monotone improvement", "M4* FCR decreases from 3.18 at E=8 to 2.67 at E=30. More battery always helps."],
    ["Ceiling crossover", "At high E, M4* surpasses unconstrained M2 — chaining leverages extra battery better than node-to-node movement."],
    ["p/d² advantage grows", "The M4* vs M4 gap widens at tight budgets, confirming the cost-foreclosure theory."],
    ["M1 is flat", "Uncoordinated search gains nothing from more battery — the coordination structure is the limiting factor."],
  ];
  obs3.forEach(([hd, bd], i) => {
    s.addText(hd, {
      x:6.0, y:1.1+i*1.08, w:3.65, h:0.3,
      fontFace:"Calibri", fontSize:12.5, bold:true, color:C.amber, align:"left", margin:0,
    });
    s.addText(bd, {
      x:6.0, y:1.44+i*1.08, w:3.65, h:0.58,
      fontFace:"Calibri", fontSize:12, color:C.white, align:"left", margin:0,
    });
    if (i < obs3.length-1) {
      s.addShape(R, { x:6.0, y:2.06+i*1.08, w:3.65, h:0.02,
        fill:{ color:C.rule }, line:{ color:C.rule } });
    }
  });

  num(s, 17);
  s.addNotes(`The energy sweep confirms the main results are not an artifact of the default parameter setting.

The most striking observation: at E = 30, M4* (FCR = 2.67) surpasses the unconstrained ceiling M2 (FCR = 2.83). This is possible because ample battery allows the chains to be so long that round-trip overhead becomes negligible, and the p/d² ordering recovers more than the node-to-node M2.

The p/d² advantage growing at tight budgets confirms the cost-foreclosure theory: when E is small, the foreclosure effect is largest, and penalizing d quadratically makes the most difference.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 18 — INSTANCE SIZE SWEEP
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Parametric Sweep — Instance Size");
  title(s, "Coordination Advantage Grows with Problem Scale", 0.34, 0.52, 26);
  hRule(s, 0.9);

  fig(s, "fig_instance_scaling.png", 0.32, 1.0, 5.5, 4.3);
  cap(s, "FCR vs instance size n = 30, 50, 100. Model ranking preserved; coordination gap widens.", 0.32, 5.34, 5.5);

  card(s, 6.0, 1.06, 3.65, 2.6, C.bgCard);
  s.addText("At n = 100 sites:", {
    x:6.15, y:1.18, w:3.35, h:0.3,
    fontFace:"Calibri", fontSize:13, bold:true, color:C.amber, align:"left", margin:0,
  });
  s.addText("M1 FCR  =  60.65", {
    x:6.15, y:1.56, w:3.35, h:0.38,
    fontFace:"Calibri", fontSize:14, bold:true, color:C.muted, align:"left", margin:0,
  });
  s.addText("M4* FCR  =  5.60", {
    x:6.15, y:1.98, w:3.35, h:0.38,
    fontFace:"Calibri", fontSize:14, bold:true, color:C.amber, align:"left", margin:0,
  });
  s.addText("Coordination gain: 10.8×", {
    x:6.15, y:2.44, w:3.35, h:0.38,
    fontFace:"Calibri", fontSize:14, bold:true, color:C.teal, align:"left", margin:0,
  });
  s.addText("vs 6.6× at n = 30", {
    x:6.15, y:2.85, w:3.35, h:0.32,
    fontFace:"Calibri", fontSize:11.5, italic:true, color:C.muted, align:"left", margin:0,
  });

  s.addText("The larger the disaster scene, the more critical coordination becomes. Real deployments with hundreds of locations will see even larger gains from the M4* framework.", {
    x:6.0, y:3.84, w:3.65, h:1.18,
    fontFace:"Calibri", fontSize:12.5, color:C.white, align:"left", margin:0, lineSpacingMultiple:1.2,
  });
  s.addText("Model ranking preserved at all n.", {
    x:6.0, y:5.08, w:3.65, h:0.3,
    fontFace:"Calibri", fontSize:12, bold:true, italic:true, color:C.teal, align:"left", margin:0,
  });

  num(s, 18);
  s.addNotes(`The instance size sweep is perhaps the most practically important parametric result.

At n = 100 sites, the coordination gap grows to 10.8x (M1 = 60.65 vs M4* = 5.60). Compare this to the 6.6x gap at n = 30.

The practical message: as autonomous search systems scale toward real disaster scenes with hundreds or thousands of candidate locations, proper coordination becomes proportionally MORE important — not less.

Model ranking is fully preserved at all instance sizes — no crossover effects. The hierarchy is robust.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 19 — FLEET SIZE SWEEP
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Parametric Sweep — Fleet Size");
  title(s, "Diminishing Returns, But No Ceiling for Coordination", 0.3, 0.6, 24);
  hRule(s, 0.94);

  fig(s, "fig_robot_sweep.png", 0.32, 1.0, 5.5, 4.3);
  cap(s, "FCR vs fleet size R = 1 to 10. At R = 10, M4* (1.81) surpasses the unconstrained M2 (1.84).", 0.32, 5.34, 5.5);

  const obs4 = [
    ["R = 1", "All models converge — coordination requires multiple robots."],
    ["R = 3", "Default: M4* = 3.11, M2 = 2.83."],
    ["R = 10", "M4* = 1.81 surpasses unconstrained M2 = 1.84."],
    ["Diminishing returns", "Practical sweet spot is R = 3–5 for most instances."],
  ];
  obs4.forEach(([hd, bd], i) => {
    card(s, 6.0, 1.06+i*1.04, 3.65, 0.9, C.bgCard);
    s.addText(hd, {
      x:6.15, y:1.14+i*1.04, w:3.35, h:0.3,
      fontFace:"Calibri", fontSize:12.5, bold:true, color:C.amber, align:"left", margin:0,
    });
    s.addText(bd, {
      x:6.15, y:1.48+i*1.04, w:3.35, h:0.38,
      fontFace:"Calibri", fontSize:12, color:C.white, align:"left", margin:0,
    });
  });

  num(s, 19);
  s.addNotes(`At R = 1, there's nothing to coordinate and all models are equivalent. The gap between coordinated and uncoordinated search opens immediately at R = 2 and widens through R = 5.

The same ceiling-crossover phenomenon as the energy sweep: at R = 10, M4* surpasses M2. Ample fleet size allows such dense coverage that energy constraints matter less.

Practical implication: fleets of 3–5 robots capture most of the coordination benefit. Returns diminish sharply above R = 5, suggesting the most cost-effective deployment size is in this range.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 20 — STATISTICAL VALIDATION
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Statistical Validation");
  title(s, "All Key Findings Are Statistically Significant", 0.34, 0.52, 26);
  hRule(s, 0.9);

  fig(s, "fig_significance_ci.png", 0.32, 1.0, 5.2, 4.35);
  cap(s, "95% confidence intervals for mean FCR differences. Non-overlapping CIs confirm significance.", 0.32, 5.38, 5.2);

  const hyps = [
    ["H1", "M2 vs M1 — coordination gain",     "p < 0.001"],
    ["H2", "M3 vs M2 — energy penalty",         "p < 0.001"],
    ["H3", "M4* vs M3 — multi-sortie recovery", "p < 0.001"],
    ["H4", "M4* vs M4 — p/d² vs p/d",           "p < 0.001"],
  ];
  hyps.forEach(([id, txt, res], i) => {
    card(s, 5.62, 1.06+i*1.05, 4.05, 0.9, C.bgCard);
    s.addText(id, {
      x:5.74, y:1.14+i*1.05, w:0.52, h:0.38,
      fontFace:"Calibri", fontSize:16, bold:true, color:C.amber,
      align:"center", valign:"middle", margin:0,
    });
    s.addText(txt, {
      x:6.32, y:1.14+i*1.05, w:2.55, h:0.38,
      fontFace:"Calibri", fontSize:11.5, color:C.white,
      align:"left", valign:"middle", margin:0,
    });
    s.addText(res, {
      x:8.9, y:1.14+i*1.05, w:0.64, h:0.38,
      fontFace:"Calibri", fontSize:11, bold:true, color:C.teal,
      align:"right", valign:"middle", margin:0,
    });
    s.addShape(R, { x:5.74, y:1.56+i*1.05, w:3.78, h:0.02,
      fill:{ color:C.rule }, line:{ color:C.rule } });
    s.addText("Wilcoxon signed-rank (paired) · Bonferroni correction", {
      x:5.74, y:1.6+i*1.05, w:3.78, h:0.28,
      fontFace:"Calibri", fontSize:9.5, italic:true, color:C.muted,
      align:"left", margin:0,
    });
  });

  num(s, 20);
  s.addNotes(`Rigorous statistical testing is important for a thesis making comparative claims.

Wilcoxon signed-rank is appropriate because: (1) the FCR distributions are non-Gaussian (right-skewed due to catastrophic failures on hard instances), and (2) paired trials on the same instance control for instance-level variability.

Bonferroni correction controls the family-wise error rate across four simultaneous hypotheses.

H4 (p/d² vs p/d) is the subtlest — the effect at default parameters is 1.5%, which is significant only due to the large sample (5,000 trials). At larger instances and tighter budgets, the effect is substantially larger.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SECTION DIVIDER IV — THE TOOLS
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  sectionDiv(s, "IV", "The Tools", "Open-source library, interactive simulator, and 3D physical demo.");
  s.addNotes(`Transition: "Everything I've shown you is open-source and fully reproducible. Let me show you the tools — and if I have a laptop set up, walk you through a live demo."`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 22 — PYBULLET DEMO
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s, C.bgDeep);
  label(s, "Physical Simulation");
  title(s, "3D Physics Simulation: Drones in Action", 0.34, 0.52, 27);
  hRule(s, 0.9);

  const shots = [
    { file:"01_initial_scene.png",   label:"Scene setup — 3 drones at base, 10 candidate sites" },
    { file:"02_drones_in_flight.png",label:"M4* sorties in progress" },
    { file:"03_target_found.png",    label:"Finder locates the survivor" },
    { file:"04_replay_finished.png", label:"Mission complete — paths rendered" },
  ];
  [[0.32,1.02],[5.08,1.02],[0.32,3.14],[5.08,3.14]].forEach(([px,py], i) => {
    pybFig(s, shots[i].file, px, py, 4.44, 1.92);
    s.addText(shots[i].label, {
      x:px, y:py+1.94, w:4.44, h:0.22,
      fontFace:"Calibri", fontSize:9.5, italic:true, color:C.muted, align:"center", margin:0,
    });
  });

  num(s, 22);
  s.addNotes(`The PyBullet simulation validates the algorithmic results in 3D physical space. Three drones with physics-based dynamics (thrust, drag, inertia) execute M4* assignments.

If you can run the simulation live, do it — it's visually compelling and makes the abstract algorithms tangible.

Check the pybullet_demo/ directory in the repository for run instructions.

The simulation is not the primary contribution (the analysis and algorithms are), but it demonstrates that the coordination logic transfers to physical agents with realistic dynamics.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 23 — INTERACTIVE SIMULATOR + DEMO GUIDE
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Live Demo");
  title(s, "Interactive Web Simulator — Live Demo Guide", 0.34, 0.52, 26);
  hRule(s, 0.9);

  fig(s, "fig_simulation_snapshot_v2.png", 0.32, 1.0, 5.0, 4.3);
  cap(s, "Simulator: configure n, R, E, select model, watch search unfold step by step.", 0.32, 5.34, 5.0);

  // right: numbered steps
  s.addText("Run it live:", {
    x:5.5, y:1.08, w:4.15, h:0.3,
    fontFace:"Calibri", fontSize:13, bold:true, color:C.amber, align:"left", margin:0,
  });

  const demoSteps = [
    "Clone: github.com/foojanbabaeeian/Multi-Robot-Algo",
    "Install: pip install -r requirements.txt",
    "Launch: python simulator/app.py",
    "Set: n = 10, R = 3, E = 14",
    "Run M1 — watch robots duplicate coverage",
    "Switch to M4* — watch compact non-overlapping tours",
    "Compare FCR values in real time",
  ];
  demoSteps.forEach((st, i) => {
    const yy = 1.48 + i * 0.52;
    card(s, 5.5, yy, 4.15, 0.44, i%2===0 ? C.bgCard : C.bgLight);
    s.addText(`${i+1}`, {
      x:5.58, y:yy, w:0.36, h:0.44,
      fontFace:"Calibri", fontSize:12, bold:true, color:C.amber,
      align:"center", valign:"middle", margin:0,
    });
    s.addText(st, {
      x:6.0, y:yy, w:3.55, h:0.44,
      fontFace:"Calibri", fontSize:11.5, color:C.white,
      align:"left", valign:"middle", margin:0,
    });
  });

  s.addText("No laptop? Show fig_m1_vs_m4star.png and narrate the contrast.", {
    x:5.5, y:5.18, w:4.15, h:0.3,
    fontFace:"Calibri", fontSize:10, italic:true, color:C.muted, align:"left", margin:0,
  });

  num(s, 23);
  s.addNotes(`DEMO OPPORTUNITY. This is the highest-impact moment in the showcase if you have a laptop.

The most effective demo flow:
1. Start with M1 on n=10 sites, R=3 robots. Let it run 2-3 rounds. Point out the duplication.
2. Reset. Run M4* on the SAME instance. Let the audience see the difference immediately.
3. Show the FCR values updating in real time.

The visual contrast is immediate and visceral — the audience doesn't need to understand the math to appreciate the improvement.

If you cannot run code live, the fig_m1_vs_m4star.png figure (slide 15) gives the same contrast as a static visual. Point to specific robot paths and narrate what each is doing.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 24 — OPEN SOURCE
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Reproducibility");
  title(s, "Fully Open-Source and Reproducible", 0.34, 0.52, 27);
  hRule(s, 0.9);

  const comps = [
    { title:"SearchFCR Python Library",
      body: "All 5 models as importable classes. Single API: run_model(name, n, R, E, seed).", x:0.42, y:1.06 },
    { title:"8 Reproducible Experiments",
      body: "python experiments/exp8_ci_table.py reproduces Table 1 exactly.", x:0.42, y:2.34 },
    { title:"Archived Trial Data",
      body: "All 5,000 trial results in experiments/data/ as CSV. Verifiable without re-running.", x:5.08, y:1.06 },
    { title:"All Figures Reproducible",
      body: "Every thesis figure is generated by a script. No manual figure creation.", x:5.08, y:2.34 },
  ];
  comps.forEach((c) => {
    card(s, c.x, c.y, 4.3, 1.16, C.bgCard);
    s.addShape(R, { x:c.x, y:c.y, w:4.3, h:0.05,
      fill:{ color:C.bgLight }, line:{ color:C.bgLight } });
    s.addText(c.title, {
      x:c.x+0.16, y:c.y+0.12, w:3.98, h:0.3,
      fontFace:"Calibri", fontSize:13, bold:true, color:C.amber, align:"left", margin:0,
    });
    s.addText(c.body, {
      x:c.x+0.16, y:c.y+0.48, w:3.98, h:0.6,
      fontFace:"Calibri", fontSize:12.5, color:C.white, align:"left", margin:0,
    });
  });

  // repo callout
  card(s, 0.42, 3.68, 9.16, 0.78, "0D2B1A");
  s.addShape(R, { x:0.42, y:3.68, w:9.16, h:0.05, fill:{ color:C.teal }, line:{ color:C.teal } });
  s.addText("github.com/foojanbabaeeian/Multi-Robot-Algo", {
    x:0.42, y:3.73, w:9.16, h:0.73,
    fontFace:"Calibri", fontSize:20, bold:true, color:C.teal,
    align:"center", valign:"middle", margin:0,
  });

  s.addText("Open issues and extension points are tracked in the repository's issue tracker.", {
    x:0.42, y:4.6, w:9.16, h:0.36,
    fontFace:"Calibri", fontSize:11.5, italic:true, color:C.muted, align:"center", margin:0,
  });

  num(s, 24);
  s.addNotes(`Reproducibility is a first-class property of this work.

Every number in the thesis can be reproduced with a single command. Every figure can be regenerated from the scripts. All trial data is archived.

If a judge asks "how do I verify this?" — you can point to the exact command: python experiments/exp8_ci_table.py

The repository also includes the thesis PDF, the simulator, and documentation. Encourage interested attendees to star or fork it.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 25 — FUTURE WORK
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s);
  label(s, "Future Directions");
  title(s, "Open Problems and Next Steps", 0.34, 0.52, 27);
  hRule(s, 0.9);

  ghost(s, "+", 7.5, 0.8, 2.3, 4.8, 200);

  const items = [
    { title:"Analytical Bounds",
      body:"Prove a formal competitive ratio for M4*. The empirical FCR of 3.11 strongly suggests a multiplicative bound near 3 is achievable." },
    { title:"Dynamic Environments",
      body:"Extend to moving targets and time-varying priors. Survivor state changes over time — the posterior update must account for survival probability decay." },
    { title:"Heterogeneous Fleets",
      body:"Relax the identical-robot assumption. Real deployments mix ground vehicles (high endurance, slow) and aerial drones (fast, short range)." },
    { title:"Partial Mid-Flight Communication",
      body:"Explore relay robots or intermittent contact. How much coordination gain is recoverable with limited mid-sortie updates?" },
  ];

  [[0.42,1.06],[0.42,2.62],[5.08,1.06],[5.08,2.62]].forEach(([px,py], i) => {
    card(s, px, py, 4.3, 1.42, C.bgCard);
    s.addText(items[i].title, {
      x:px+0.16, y:py+0.1, w:3.98, h:0.3,
      fontFace:"Calibri", fontSize:13, bold:true, color:C.amber, align:"left", margin:0,
    });
    s.addText(items[i].body, {
      x:px+0.16, y:py+0.46, w:3.98, h:0.88,
      fontFace:"Calibri", fontSize:12, color:C.white,
      align:"left", valign:"top", margin:0, lineSpacingMultiple:1.15,
    });
  });

  s.addText("The framework is modular — all four extensions are independent and can be pursued in parallel.", {
    x:0.42, y:4.22, w:9.16, h:0.38,
    fontFace:"Calibri", fontSize:12, italic:true, color:C.muted, align:"center", margin:0,
  });

  num(s, 25);
  s.addNotes(`Future work signals that this thesis opens doors rather than closes them.

Most tractable next step: formal bounds. The empirical results are consistent with a competitive ratio of approximately 3, and a formal proof would significantly strengthen the theoretical contribution.

Dynamic environments and heterogeneous fleets are the path toward real-world deployment.

If a judge asks about limitations: acknowledge that the current model assumes a fixed discrete prior, synchronous return to base, and identical robots. These are productive abstractions for analysis — the extensions here are the roadmap to removing them.`);
}

// ═════════════════════════════════════════════════════════════════════════════
//  SLIDE 26 — CLOSING
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  bg(s, C.bgDeep);

  s.addShape(R, { x:0, y:0, w:0.1, h:5.63, fill:{ color:C.amber }, line:{ color:C.amber } });
  ghost(s, "SAR", 4.8, 0.5, 5.0, 4.5, 170);

  s.addText("FOUR FINDINGS", {
    x:0.32, y:0.22, w:9.3, h:0.3,
    fontFace:"Calibri", fontSize:9, bold:true, charSpacing:3,
    color:C.amber, align:"left", margin:0,
  });
  s.addText("One Framework for Robot Coordination", {
    x:0.32, y:0.6, w:9.3, h:0.58,
    fontFace:"Calibri", fontSize:28, bold:true, color:C.white,
    align:"left", margin:0,
  });
  hRule(s, 1.25, C.amber, 0.32, 9.3);

  const findings = [
    ["Coordination gain",      "6.6× lower FCR through communication alone — the single largest lever."],
    ["Multi-sortie recovery",  "Greedy chain extension recovers ~90% of the energy-penalty gap."],
    ["p/d² bid function",      "Quadratic distance penalty — justified by cost-foreclosure — grows with instance scale."],
    ["Target-Delay Anomaly",   "2-opt tour polishing worsens FCR by 5.3%. Geometry and probability are orthogonal objectives."],
  ];
  findings.forEach(([hd, bd], i) => {
    s.addText(`\u2022  ${hd}`, {
      x:0.32, y:1.42+i*0.92, w:9.3, h:0.32,
      fontFace:"Calibri", fontSize:14, bold:true, color:C.amber, align:"left", margin:0,
    });
    s.addText(bd, {
      x:0.55, y:1.76+i*0.92, w:9.07, h:0.36,
      fontFace:"Calibri", fontSize:12.5, color:C.white, align:"left", margin:0,
    });
  });

  hRule(s, 5.13, C.rule, 0.32, 9.3);
  s.addText("github.com/foojanbabaeeian/Multi-Robot-Algo   |   CSULB Honors Thesis, Spring 2026", {
    x:0.32, y:5.2, w:9.3, h:0.3,
    fontFace:"Calibri", fontSize:11.5, color:C.muted, align:"left", margin:0,
  });

  num(s, 26);
  s.addNotes(`Return to the opening question: "A building collapses. A survivor is inside. Three robots, limited battery. Where do you send them first?"

Read the four findings aloud. Let the fourth one (the anomaly) land — it's the most surprising.

Closing line: "All of this is open-source, fully reproducible, and designed to be extended. The repository is in your hands. I'd be happy to answer questions — or show you a live demo."

Thank the audience. Smile. You've earned it.`);
}

// ═════════════════════════════════════════════════════════════════════════════
pres.writeFile({ fileName: OUT }).then(() => {
  console.log(`Done — ${OUT}`);
}).catch((err) => { console.error(err); process.exit(1); });
