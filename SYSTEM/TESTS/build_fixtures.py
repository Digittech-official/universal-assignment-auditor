#!/usr/bin/env python3
"""Builds binary test fixtures from reviewable sources. Maintainers only.

Sources live in SYSTEM/TESTS/fixture_sources/<CASE>/<INPUT-relative path>.<ext>.<src>:
  *.docx.md   -> DOCX  (lines starting '# ' / '## ' / '### ' become Heading 1/2/3; '|' rows become a table)
  *.pdf.md    -> text PDF (pure-Python writer; headings bold, tables flattened)
  *.pptx.md   -> PPTX  (slides separated by a line '---'; first line = title; 'Notes:' line = speaker notes)
  *.xlsx.csv  -> XLSX  (one sheet named after the file stem)
  *.zipdir/   -> ZIP of that directory
Special generated files (see SPECIAL): corrupt DOCX, legacy .doc.
All content is synthetic. Outputs are written to SYSTEM/TESTS/fixtures/<CASE>/INPUT/... and committed.
"""
from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SRC = HERE / "fixture_sources"
OUT = HERE / "fixtures"
FIXED_DATE = (2026, 1, 1, 0, 0, 0)  # deterministic ZIP timestamps

CT_DOCX = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>"""
RELS_DOCX = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>"""
DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>"""
STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">""" + "".join(
    f'<w:style w:type="paragraph" w:styleId="Heading{i}"><w:name w:val="heading {i}"/><w:basedOn w:val="Normal"/>'
    f'<w:pPr><w:outlineLvl w:val="{i-1}"/></w:pPr><w:rPr><w:b/><w:sz w:val="{36-4*i}"/></w:rPr></w:style>' for i in (1, 2, 3)
) + '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>'
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def zwrite(zf: zipfile.ZipFile, name: str, data: str | bytes):
    info = zipfile.ZipInfo(name, FIXED_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)


def para(text: str, style: str | None = None) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def build_docx(md: str, dest: Path):
    body, rows = [], []

    def flush_table():
        if rows:
            trs = "".join("<w:tr>" + "".join(f"<w:tc>{para(c.strip())}</w:tc>" for c in r) + "</w:tr>" for r in rows)
            body.append(f"<w:tbl><w:tblPr><w:tblStyle w:val=\"TableGrid\"/></w:tblPr>{trs}</w:tbl>")
            rows.clear()

    for line in md.splitlines():
        if line.strip().startswith("|"):
            cells = line.strip().strip("|").split("|")
            if not all(set(c.strip()) <= set("-: ") for c in cells):
                rows.append(cells)
            continue
        flush_table()
        if line.startswith("### "):
            body.append(para(line[4:], "Heading3"))
        elif line.startswith("## "):
            body.append(para(line[3:], "Heading2"))
        elif line.startswith("# "):
            body.append(para(line[2:], "Heading1"))
        elif line.strip():
            body.append(para(line))
    flush_table()
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{"".join(body)}</w:body></w:document>'
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w") as zf:
        zwrite(zf, "[Content_Types].xml", CT_DOCX)
        zwrite(zf, "_rels/.rels", RELS_DOCX)
        zwrite(zf, "word/_rels/document.xml.rels", DOC_RELS)
        zwrite(zf, "word/styles.xml", STYLES)
        zwrite(zf, "word/document.xml", doc)


A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def sp(idx: int, name: str, paras: list[str]) -> str:
    ps = "".join(f"<a:p><a:r><a:t>{escape(t)}</a:t></a:r></a:p>" for t in paras) or "<a:p/>"
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{idx}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr/>'
            f'<p:txBody><a:bodyPr/>{ps}</p:txBody></p:sp>')


def build_pptx(md: str, dest: Path):
    slides = [s.strip() for s in md.split("\n---\n") if s.strip()]
    dest.parent.mkdir(parents=True, exist_ok=True)
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>']
    pres_rels, sld_ids = [], []
    with zipfile.ZipFile(dest, "w") as zf:
        for i, s in enumerate(slides, 1):
            lines = [l for l in s.splitlines() if l.strip()]
            notes = [l[6:].strip() for l in lines if l.startswith("Notes:")]
            content = [l.lstrip("- ").strip() for l in lines[1:] if not l.startswith("Notes:")]
            xml = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld {A} {P} {R}><p:cSld><p:spTree>'
                   f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
                   f'{sp(2, "Title", [lines[0].lstrip("# ").strip()])}{sp(3, "Content", content)}</p:spTree></p:cSld></p:sld>')
            zwrite(zf, f"ppt/slides/slide{i}.xml", xml)
            ct.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
            if notes:
                nxml = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:notes {A} {P} {R}><p:cSld><p:spTree>'
                        f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
                        f'{sp(2, "Notes", notes)}</p:spTree></p:cSld></p:notes>')
                zwrite(zf, f"ppt/notesSlides/notesSlide{i}.xml", nxml)
                ct.append(f'<Override PartName="/ppt/notesSlides/notesSlide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>')
            pres_rels.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>')
            sld_ids.append(f'<p:sldId id="{255 + i}" r:id="rId{i}"/>')
        zwrite(zf, "[Content_Types].xml", "".join(ct) + "</Types>")
        zwrite(zf, "_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>')
        zwrite(zf, "ppt/_rels/presentation.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(pres_rels) + "</Relationships>")
        zwrite(zf, "ppt/presentation.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation {A} {P} {R}><p:sldIdLst>{"".join(sld_ids)}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>')


def col(n: int) -> str:
    s = ""
    while n >= 0:
        s = chr(65 + n % 26) + s
        n = n // 26 - 1
    return s


def build_xlsx(csv_text: str, dest: Path, sheet: str):
    rows = list(csv.reader(io.StringIO(csv_text)))
    xml_rows = []
    for r_i, row in enumerate(rows, 1):
        cells = []
        for c_i, v in enumerate(row):
            ref = f"{col(c_i)}{r_i}"
            try:
                float(v)
                cells.append(f'<c r="{ref}"><v>{v}</v></c>')
            except ValueError:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>')
        xml_rows.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    S = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w") as zf:
        zwrite(zf, "[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        zwrite(zf, "_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        zwrite(zf, "xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        zwrite(zf, "xl/workbook.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook {S} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{escape(sheet)}" sheetId="1" r:id="rId1"/></sheets></workbook>')
        zwrite(zf, "xl/worksheets/sheet1.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet {S}><sheetData>{"".join(xml_rows)}</sheetData></worksheet>')


def build_zip(src_dir: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w") as zf:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                zwrite(zf, f"{dest.stem}/{p.relative_to(src_dir).as_posix()}", p.read_bytes())


def _pdf_escape(t: str) -> str:
    t = t.replace("\u2013", "-").replace("\u2014", "-").replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"').replace("\u00a3", "GBP ").replace("\u2026", "...")
    t = t.encode("latin-1", "replace").decode("latin-1")
    return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(md: str, dest: Path) -> bool:
    """Minimal dependency-free text PDF (A4, Helvetica) with a real text layer."""
    import textwrap
    lines: list[tuple[str, str, int]] = []  # (font, text, size)
    for raw in md.splitlines():
        if not raw.strip():
            continue
        if raw.startswith("#"):
            level = len(raw) - len(raw.lstrip("#"))
            lines.append(("F2", "", 11))
            lines.append(("F2", raw.lstrip("#").strip(), 15 - 2 * min(level, 3)))
        elif raw.strip().startswith("|"):
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            for w in textwrap.wrap("   ".join(cells), 95) or [""]:
                lines.append(("F1", w, 9))
        else:
            for w in textwrap.wrap(raw.strip(), 92) or [""]:
                lines.append(("F1", w, 10))
            lines.append(("F1", "", 6))
    pages, cur, y = [], [], 800
    for font, text, size in lines:
        if y - size - 4 < 60:
            pages.append(cur)
            cur, y = [], 800
        y -= size + 4
        if text:
            cur.append(f"BT /{font} {size} Tf 56 {y} Td ({_pdf_escape(text)}) Tj ET")
    pages.append(cur)
    objs: list[bytes] = []
    n_pages = len(pages)
    kids = " ".join(f"{5 + 2 * i} 0 R" for i in range(n_pages))
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    for i, ops in enumerate(pages):
        stream = ("\n".join(ops + [f"BT /F1 8 Tf 290 30 Td (Page {i + 1} of {n_pages}) Tj ET"])).encode("latin-1")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {6 + 2 * i} 0 R >>".encode())
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(bytes(out))
    return True


# Deterministic "bad" files for the unreadable-input case.
SPECIAL = {
    "J_unreadable_unsupported/INPUT/04_COMPLETED_ASSIGNMENT/appendix_data.docx":
        b"PK\x03\x04" + bytes((i * 37 + 11) % 256 for i in range(2048)),  # truncated / corrupt OOXML
    "J_unreadable_unsupported/INPUT/05_SUPPORTING_FILES/old_lecture_notes.doc":
        bytes.fromhex("D0CF11E0A1B11AE1") + bytes((i * 13 + 7) % 256 for i in range(4096)),  # legacy OLE .doc
}


def main() -> int:
    built = 0
    for src in sorted(SRC.rglob("*")):
        rel = src.relative_to(SRC)
        case = rel.parts[0]
        if src.is_dir() and src.name.endswith(".zipdir"):
            dest = OUT / rel.parent / src.name[: -len(".zipdir")]
            build_zip(src, dest.with_suffix(".zip") if dest.suffix != ".zip" else dest)
            built += 1
            continue
        if not src.is_file() or any(p.endswith(".zipdir") for p in rel.parts[:-1]):
            continue
        name = src.name
        if name.endswith(".docx.md"):
            build_docx(src.read_text(encoding="utf-8"), OUT / rel.parent / name[:-3])
        elif name.endswith(".pdf.md"):
            if not build_pdf(src.read_text(encoding="utf-8"), OUT / rel.parent / name[:-3]):
                continue
        elif name.endswith(".pptx.md"):
            build_pptx(src.read_text(encoding="utf-8"), OUT / rel.parent / name[:-3])
        elif name.endswith(".xlsx.csv"):
            build_xlsx(src.read_text(encoding="utf-8"), OUT / rel.parent / name[:-4], Path(name[:-9]).name)
        else:
            continue
        built += 1
        _ = case
    for relpath, data in SPECIAL.items():
        dest = OUT / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        built += 1
    print(f"Built {built} fixture file(s) into {OUT.relative_to(HERE.parents[1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
