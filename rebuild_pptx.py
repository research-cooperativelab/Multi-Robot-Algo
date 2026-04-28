"""
Rebuild SearchFCR_Conference_Presentation.pptx with corrected bounds and new slides.

Changes:
1. Replace slide 17 (Every bound holds) with corrected bounds image
2. Insert NEW slide 9: Bid Exponent Sweep (after slide 8 "Why p/d²?")
3. Insert NEW slide 19: Web Simulator (after what becomes slide 18 "Every bound holds")
4. Append NEW slide 21: Q&A Backup at the end
"""
import os, shutil, re
from pathlib import Path

UNPACKED = Path(r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo\unpacked")
SCREENSHOTS = Path(r"C:\Users\fooja\Documents\GitHub\Multi-Robot-Algo\slide_screenshots")
MEDIA = UNPACKED / "ppt" / "media"
SLIDES = UNPACKED / "ppt" / "slides"
SLIDE_RELS = SLIDES / "_rels"
NOTES_DIR = UNPACKED / "ppt" / "notesSlides"
PRES_XML = UNPACKED / "ppt" / "presentation.xml"

# ── Step 1: Replace slide 17 image with corrected bounds ─────────────────────
print("Step 1: Replacing bounds slide image...")
shutil.copy(SCREENSHOTS / "slide_17_fixed.png", MEDIA / "image-17-1.png")
print("  OK: image-17-1.png replaced with corrected bounds")


# ── Step 2: Add new media images ─────────────────────────────────────────────
print("Step 2: Adding new media images...")
shutil.copy(SCREENSHOTS / "slide_new_exponent.png", MEDIA / "image-21-1.png")
shutil.copy(SCREENSHOTS / "slide_new_simulator.png", MEDIA / "image-22-1.png")
shutil.copy(SCREENSHOTS / "slide_new_qa.png",        MEDIA / "image-23-1.png")
print("  OK: image-21-1.png (exponent), image-22-1.png (simulator), image-23-1.png (qa)")


# ── Step 3: Create slide XML files for new slides ────────────────────────────
print("Step 3: Creating new slide XML files...")

SLIDE_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld name="{slide_name}">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      <p:pic>
        <p:nvPicPr>
          <p:cNvPr id="2" name="Image 0" descr="{img_desc}"/>
          <p:cNvPicPr>
            <a:picLocks noChangeAspect="1"/>
          </p:cNvPicPr>
          <p:nvPr/>
        </p:nvPicPr>
        <p:blipFill>
          <a:blip r:embed="rId1"/>
          <a:stretch>
            <a:fillRect/>
          </a:stretch>
        </p:blipFill>
        <p:spPr>
          <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="12192000" cy="6858000"/>
          </a:xfrm>
          <a:prstGeom prst="rect">
            <a:avLst/>
          </a:prstGeom>
        </p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>"""

RELS_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{media_file}"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide{slide_num}.xml"/>
</Relationships>"""

NOTES_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr/>
    </p:spTree>
  </p:cSld>
</p:notes>"""

new_slides = [
    (21, "Exponent Sweep",      "image-21-1.png"),
    (22, "Web Simulator",       "image-22-1.png"),
    (23, "Q&amp;A Backup",       "image-23-1.png"),
]

for slide_num, slide_name, media_file in new_slides:
    # Write slide XML
    slide_xml = SLIDE_TEMPLATE.format(
        slide_name=slide_name,
        img_desc=media_file
    )
    (SLIDES / f"slide{slide_num}.xml").write_text(slide_xml, encoding="utf-8")

    # Write rels file
    rels_xml = RELS_TEMPLATE.format(
        media_file=media_file,
        slide_num=slide_num
    )
    (SLIDE_RELS / f"slide{slide_num}.xml.rels").write_text(rels_xml, encoding="utf-8")

    # Write empty notes
    (NOTES_DIR / f"notesSlide{slide_num}.xml").write_text(NOTES_TEMPLATE, encoding="utf-8")
    print(f"  OK: slide{slide_num}.xml ({slide_name})")


# ── Step 4: Register new slides in Content_Types.xml ─────────────────────────
print("Step 4: Updating [Content_Types].xml...")
ct_path = UNPACKED / "[Content_Types].xml"
ct_content = ct_path.read_text(encoding="utf-8")

# Add slide content types
additions = []
for slide_num, _, _ in new_slides:
    tag = f'<Override PartName="/ppt/slides/slide{slide_num}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
    if f"slide{slide_num}.xml" not in ct_content:
        additions.append(tag)
    tag_notes = f'<Override PartName="/ppt/notesSlides/notesSlide{slide_num}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
    if f"notesSlide{slide_num}.xml" not in ct_content:
        additions.append(tag_notes)

# Add new media content types
for _, _, media_file in new_slides:
    tag = f'<Default Extension="png" ContentType="image/png"/>'
    # PNG is likely already registered, skip if so

if additions:
    # Insert before </Types>
    ct_content = ct_content.replace("</Types>", "\n  ".join(additions) + "\n</Types>")
    ct_path.write_text(ct_content, encoding="utf-8")
    print(f"  OK: Added {len(additions)} entries to Content_Types.xml")
else:
    print("  OK: No new entries needed in Content_Types.xml")


# ── Step 5: Register slides in presentation.xml relationships ─────────────────
print("Step 5: Updating presentation.xml.rels...")
pres_rels_path = UNPACKED / "ppt" / "_rels" / "presentation.xml.rels"
pres_rels = pres_rels_path.read_text(encoding="utf-8")

# Find highest rId used
rids = re.findall(r'Id="rId(\d+)"', pres_rels)
max_rid = max(int(r) for r in rids) if rids else 30

new_rids = {}
for slide_num, _, _ in new_slides:
    max_rid += 1
    rid = f"rId{max_rid}"
    new_rids[slide_num] = rid
    tag = f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{slide_num}.xml"/>'
    if f"slide{slide_num}.xml" not in pres_rels:
        pres_rels = pres_rels.replace("</Relationships>", f"  {tag}\n</Relationships>")

pres_rels_path.write_text(pres_rels, encoding="utf-8")
print(f"  OK: Added rIds {list(new_rids.values())} to presentation.xml.rels")


# ── Step 6: Update sldIdLst in presentation.xml ──────────────────────────────
print("Step 6: Updating slide order in presentation.xml...")
pres_content = PRES_XML.read_text(encoding="utf-8")

# Current slide list: slides 1-20 at positions rId2-rId21
# We need to insert:
#   - After position 8 (rId9, "Why p/d²?"): add exponent slide (slide21)
#   - After position 17+1=18 (formerly 17): add simulator slide (slide22)
#   - At end: add Q&A slide (slide23)
#
# Current sldIdLst entries:
# rId2=slide1, rId3=slide2, ..., rId9=slide8 (Why p/d²?), rId10=slide9, ...
# rId18=slide17 (bounds), rId19=slide18, rId20=slide19, rId21=slide20

exponent_rid = new_rids[21]
simulator_rid = new_rids[22]
qa_rid = new_rids[23]

# Find next available slide id
slide_ids = re.findall(r'<p:sldId id="(\d+)"', pres_content)
max_slide_id = max(int(i) for i in slide_ids) if slide_ids else 300

exponent_id = max_slide_id + 1
simulator_id = max_slide_id + 2
qa_id = max_slide_id + 3

# Insert exponent slide after rId9 (slide 8, "Why p/d²?")
exponent_tag = f'<p:sldId id="{exponent_id}" r:id="{exponent_rid}"/>'
pres_content = pres_content.replace(
    '<p:sldId id="264" r:id="rId10"/>',
    f'{exponent_tag}\n    <p:sldId id="264" r:id="rId10"/>'
)

# Insert simulator slide after rId18 (slide 17, bounds — now at position 18)
simulator_tag = f'<p:sldId id="{simulator_id}" r:id="{simulator_rid}"/>'
pres_content = pres_content.replace(
    '<p:sldId id="273" r:id="rId19"/>',
    f'{simulator_tag}\n    <p:sldId id="273" r:id="rId19"/>'
)

# Append Q&A slide at end (before </p:sldIdLst>)
qa_tag = f'<p:sldId id="{qa_id}" r:id="{qa_rid}"/>'
pres_content = pres_content.replace(
    '</p:sldIdLst>',
    f'    {qa_tag}\n  </p:sldIdLst>'
)

PRES_XML.write_text(pres_content, encoding="utf-8")
print(f"  OK: Added slides at positions 9, 19, and end")
print(f"      Exponent: id={exponent_id} rid={exponent_rid}")
print(f"      Simulator: id={simulator_id} rid={simulator_rid}")
print(f"      Q&A: id={qa_id} rid={qa_rid}")


# ── Verify slide count ────────────────────────────────────────────────────────
pres_content_final = PRES_XML.read_text(encoding="utf-8")
count = len(re.findall(r'<p:sldId ', pres_content_final))
print(f"\nFinal slide count: {count} (expected 23)")
print("Done! Run clean.py then pack.py to finalize.")
