"""Pack 9 UHP PNG slides into SearchFCR_UHP_Symposium.pptx"""
import zipfile, shutil, re
from pathlib import Path

ROOT = Path(r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo")
OUT  = ROOT / "slide_screenshots"
UNPACKED = ROOT / "unpacked_uhp"
TEMPLATE = ROOT / "SearchFCR_Conference_Presentation.pptx"  # borrow structure
DEST     = ROOT / "SearchFCR_UHP_Symposium.pptx"

SLIDES = [
    "uhp_01_title.png",
    "uhp_02_problem.png",
    "uhp_03_moneyshot.png",
    "uhp_04_howworks.png",
    "uhp_05_insight.png",
    "uhp_06_robust.png",
    "uhp_07_demo.png",
    "uhp_08_realworld.png",
    "uhp_09_closing.png",
]

SLIDE_XML = '''\
<?xml version="1.0" encoding="utf-8"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld name="{name}">
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
        <a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:pic>
        <p:nvPicPr>
          <p:cNvPr id="2" name="Image" descr="{img}"/>
          <p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>
          <p:nvPr/>
        </p:nvPicPr>
        <p:blipFill>
          <a:blip r:embed="rId1"/>
          <a:stretch><a:fillRect/></a:stretch>
        </p:blipFill>
        <p:spPr>
          <a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''

RELS_XML = '''\
<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{img}"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''

NOTES_XML = '''\
<?xml version="1.0" encoding="utf-8"?>
<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
         xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
         xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr/>
  </p:spTree></p:cSld>
</p:notes>'''

# Unpack existing PPTX for its layouts/masters/theme
if UNPACKED.exists():
    shutil.rmtree(UNPACKED)
with zipfile.ZipFile(TEMPLATE, 'r') as z:
    z.extractall(UNPACKED)

SLD_DIR  = UNPACKED / "ppt" / "slides"
RELS_DIR = UNPACKED / "ppt" / "slides" / "_rels"
NOTES_DIR= UNPACKED / "ppt" / "notesSlides"
MEDIA_DIR= UNPACKED / "ppt" / "media"

# Remove existing slides
for f in SLD_DIR.glob("slide*.xml"):     f.unlink()
for f in RELS_DIR.glob("slide*.xml.rels"): f.unlink()
for f in NOTES_DIR.glob("notesSlide*.xml"): f.unlink()
for f in MEDIA_DIR.glob("image-*"):     f.unlink()

# Write new slides
for idx, png_name in enumerate(SLIDES, 1):
    media_name = f"uhp-{idx}.png"
    shutil.copy(OUT / png_name, MEDIA_DIR / media_name)
    (SLD_DIR  / f"slide{idx}.xml").write_text(
        SLIDE_XML.format(name=png_name.replace(".png",""), img=media_name), encoding="utf-8")
    (RELS_DIR / f"slide{idx}.xml.rels").write_text(
        RELS_XML.format(img=media_name), encoding="utf-8")
    (NOTES_DIR/ f"notesSlide{idx}.xml").write_text(NOTES_XML, encoding="utf-8")
    print(f"  slide{idx} <- {png_name}")

# Update Content_Types.xml
ct = (UNPACKED / "[Content_Types].xml").read_text(encoding="utf-8")
# Remove old slide/notes entries, keep everything else
ct = re.sub(r'\s*<Override PartName="/ppt/slides/slide\d+\.xml"[^/]*/>', '', ct)
ct = re.sub(r'\s*<Override PartName="/ppt/notesSlides/notesSlide\d+\.xml"[^/]*/>', '', ct)
new_entries = []
for i in range(1, len(SLIDES)+1):
    new_entries.append(f'  <Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
    new_entries.append(f'  <Override PartName="/ppt/notesSlides/notesSlide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>')
ct = ct.replace("</Types>", "\n".join(new_entries) + "\n</Types>")
(UNPACKED / "[Content_Types].xml").write_text(ct, encoding="utf-8")

# Update presentation.xml.rels — rebuild slide relationships
pres_rels_path = UNPACKED / "ppt" / "_rels" / "presentation.xml.rels"
pres_rels = pres_rels_path.read_text(encoding="utf-8")
# Remove old slide rels
pres_rels = re.sub(r'\s*<Relationship[^>]*slides/slide\d+[^/]*/>', '', pres_rels)
# Find max non-slide rId
rids = re.findall(r'Id="rId(\d+)"', pres_rels)
max_rid = max(int(r) for r in rids) if rids else 5
slide_rids = {}
for i in range(1, len(SLIDES)+1):
    max_rid += 1
    slide_rids[i] = f"rId{max_rid}"
    tag = f'  <Relationship Id="rId{max_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
    pres_rels = pres_rels.replace("</Relationships>", tag + "\n</Relationships>")
pres_rels_path.write_text(pres_rels, encoding="utf-8")

# Rebuild sldIdLst in presentation.xml
pres_path = UNPACKED / "ppt" / "presentation.xml"
pres = pres_path.read_text(encoding="utf-8")
# Remove old sldIdLst content
pres = re.sub(r'<p:sldIdLst>.*?</p:sldIdLst>', '', pres, flags=re.DOTALL)
# Build new sldIdLst
entries = []
for i in range(1, len(SLIDES)+1):
    entries.append(f'    <p:sldId id="{256+i}" r:id="{slide_rids[i]}"/>')
sld_lst = "<p:sldIdLst>\n" + "\n".join(entries) + "\n  </p:sldIdLst>"
pres = pres.replace("</p:presentation>", f"  {sld_lst}\n</p:presentation>")

# Also fix sldSz if missing (widescreen 10x7.5 inches)
if "sldSz" not in pres:
    pres = pres.replace("</p:presentation>",
        '  <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>\n</p:presentation>')
pres_path.write_text(pres, encoding="utf-8")

# Pack into PPTX
if DEST.exists():
    DEST.unlink()
with zipfile.ZipFile(DEST, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in UNPACKED.rglob("*"):
        if f.is_file():
            z.write(f, f.relative_to(UNPACKED))

print(f"\nDone! {DEST.name} ({DEST.stat().st_size//1024} KB, {len(SLIDES)} slides)")
shutil.rmtree(UNPACKED)
