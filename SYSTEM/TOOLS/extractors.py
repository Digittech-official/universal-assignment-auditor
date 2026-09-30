"""Text extraction for assignment files. Standard library only.

Every extractor returns an ExtractionResult. Nothing is ever silently dropped:
formats that cannot be processed here are reported with a status and a reason
so Agent 0 can decide whether Claude's own Read tool can analyse them
(PDF and images) or whether they must be reported as unanalysable.
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

# Extraction statuses
EXTRACTED = "EXTRACTED"                # full text extracted by this tool
PARTIAL = "PARTIAL"                    # some content extracted; limits noted
NEEDS_CLAUDE_READ = "NEEDS_CLAUDE_READ"  # must be read with Claude's Read tool (PDF/image)
EMPTY = "EMPTY"                        # readable but contains no content
FAILED = "FAILED"                      # corrupt / encrypted / parse error
UNSUPPORTED = "UNSUPPORTED"            # format not supported

CODE_EXTS = {
    ".py", ".java", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".c", ".h", ".cpp", ".hpp",
    ".cc", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".kts", ".scala", ".r",
    ".m", ".sql", ".sh", ".bash", ".ps1", ".html", ".htm", ".css", ".scss", ".xml", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".json", ".gradle", ".dart", ".lua", ".pl", ".jl",
    ".vb", ".f90", ".asm", ".hs", ".ex", ".exs", ".clj", ".groovy", ".vue", ".svelte",
    ".dockerfile", ".makefile", ".rmd", ".qmd", ".tex", ".bib",
}
TEXT_EXTS = {".txt", ".md", ".markdown", ".rst", ".text", ".log"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
LEGACY_OFFICE = {".doc": "Legacy Word .doc", ".ppt": "Legacy PowerPoint .ppt",
                 ".xls": "Legacy Excel .xls", ".rtf": "RTF", ".odt": "OpenDocument text",
                 ".odp": "OpenDocument presentation", ".ods": "OpenDocument spreadsheet",
                 ".pages": "Apple Pages", ".key": "Apple Keynote", ".numbers": "Apple Numbers"}
SPECIAL_CODE_NAMES = {"makefile", "dockerfile", "readme", "license", "requirements.txt",
                      "package.json", "pom.xml", "build.gradle", "cmakelists.txt", "gemfile"}

MAX_TEXT_BYTES = 20 * 1024 * 1024
ZIP_MAX_FILES = 2000
ZIP_MAX_TOTAL_BYTES = 200 * 1024 * 1024
ZIP_MAX_RATIO = 200

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
S_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


@dataclass
class ExtractionResult:
    status: str
    method: str
    text: str = ""
    notes: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    children: list[Path] = field(default_factory=list)  # files unpacked from archives


def file_kind(path: Path) -> str:
    ext = path.suffix.lower()
    name = path.name.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in (".docx", ".docm", ".dotx"):
        return "docx"
    if ext in (".pptx", ".pptm", ".potx"):
        return "pptx"
    if ext in (".xlsx", ".xlsm", ".xltx"):
        return "xlsx"
    if ext in (".csv", ".tsv"):
        return "csv"
    if ext == ".ipynb":
        return "ipynb"
    if ext == ".zip":
        return "zip"
    if ext in TEXT_EXTS:
        return "text"
    if ext in CODE_EXTS or name in SPECIAL_CODE_NAMES:
        return "code"
    if ext in IMAGE_EXTS:
        return "image"
    if ext in LEGACY_OFFICE:
        return "legacy"
    return "unknown"


def _decode(data: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "utf-16"):
        try:
            text = data.decode(enc)
            if enc == "utf-16" and not data[:2] in (b"\xff\xfe", b"\xfe\xff"):
                raise UnicodeDecodeError(enc, data, 0, 1, "no BOM")
            return text, enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1"), "latin-1"


def _looks_binary(data: bytes) -> bool:
    sample = data[:8192]
    if not sample:
        return False
    if b"\x00" in sample and not sample[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return True
    return False


def extract_plain(path: Path, method: str) -> ExtractionResult:
    data = path.read_bytes()
    if len(data) > MAX_TEXT_BYTES:
        return ExtractionResult(PARTIAL, method, _decode(data[:MAX_TEXT_BYTES])[0],
                                [f"File truncated at {MAX_TEXT_BYTES} bytes."])
    if _looks_binary(data):
        return ExtractionResult(FAILED, method, notes=["File appears to be binary despite its extension."])
    text, enc = _decode(data)
    notes = [] if enc.startswith("utf") else [f"Decoded as {enc}; some characters may be wrong."]
    if not text.strip():
        return ExtractionResult(EMPTY, method, "", ["File contains no text."])
    return ExtractionResult(EXTRACTED, method, text, notes, {"characters": len(text)})


def _open_ooxml(path: Path) -> zipfile.ZipFile:
    if not zipfile.is_zipfile(path):
        raise ValueError("Not a valid Office Open XML package (possibly encrypted, corrupt or mis-named).")
    return zipfile.ZipFile(path)


def extract_docx(path: Path) -> ExtractionResult:
    try:
        zf = _open_ooxml(path)
    except ValueError as exc:
        return ExtractionResult(FAILED, "docx-xml", notes=[str(exc)])
    with zf:
        names = set(zf.namelist())
        if "word/document.xml" not in names:
            return ExtractionResult(FAILED, "docx-xml", notes=["word/document.xml missing."])
        root = ET.fromstring(zf.read("word/document.xml"))
        lines: list[str] = []
        tables = 0
        body = root.find(f"{W_NS}body")
        for block in (list(body) if body is not None else []):
            tag = block.tag.replace(W_NS, "")
            if tag == "p":
                lines.append(_docx_paragraph(block))
            elif tag == "tbl":
                tables += 1
                lines.append(f"[TABLE {tables}]")
                for row in block.iter(f"{W_NS}tr"):
                    cells = [" ".join(_docx_paragraph(p) for p in tc.iter(f"{W_NS}p")).strip()
                             for tc in row.iter(f"{W_NS}tc")]
                    lines.append(" | ".join(cells))
                lines.append(f"[END TABLE {tables}]")
        extra = []
        for part, label in (("word/footnotes.xml", "FOOTNOTES"), ("word/endnotes.xml", "ENDNOTES"),
                            ("word/comments.xml", "DOCUMENT COMMENTS")):
            if part in names:
                proot = ET.fromstring(zf.read(part))
                ptxt = [t for t in (_docx_paragraph(p) for p in proot.iter(f"{W_NS}p")) if t.strip()]
                if ptxt:
                    extra.append(f"\n[{label}]\n" + "\n".join(ptxt))
        header_footer = sorted(n for n in names if re.match(r"word/(header|footer)\d*\.xml", n))
        images = [n for n in names if n.startswith("word/media/")]
        text = "\n".join(lines) + "".join(extra)
        notes = []
        if images:
            notes.append(f"{len(images)} embedded image(s) not transcribed (figures/charts/screenshots).")
        if header_footer:
            notes.append("Headers/footers not included in body text.")
        words = len(re.findall(r"\b\w+\b", "\n".join(lines)))
        status = EXTRACTED if text.strip() else EMPTY
        return ExtractionResult(status, "docx-xml", text, notes,
                                {"body_words_approx": words, "tables": tables, "embedded_images": len(images)})


def _docx_paragraph(p) -> str:
    style = p.find(f"{W_NS}pPr/{W_NS}pStyle")
    parts = []
    for node in p.iter():
        if node.tag == f"{W_NS}t" and node.text:
            parts.append(node.text)
        elif node.tag == f"{W_NS}tab":
            parts.append("\t")
        elif node.tag in (f"{W_NS}br", f"{W_NS}cr"):
            parts.append("\n")
    text = "".join(parts)
    if style is not None:
        val = style.get(f"{W_NS}val", "")
        m = re.match(r"(?i)heading\s*(\d)|title", val)
        if m and text.strip():
            level = int(m.group(1)) if m.group(1) else 1
            return "#" * level + " " + text
    return text


def extract_pptx(path: Path) -> ExtractionResult:
    try:
        zf = _open_ooxml(path)
    except ValueError as exc:
        return ExtractionResult(FAILED, "pptx-xml", notes=[str(exc)])
    with zf:
        names = zf.namelist()
        slides = sorted((n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                        key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
        if not slides:
            return ExtractionResult(FAILED, "pptx-xml", notes=["No slides found."])
        out = []
        notes_count = 0
        media_count = len([n for n in names if n.startswith("ppt/media/")])
        for idx, slide in enumerate(slides, 1):
            root = ET.fromstring(zf.read(slide))
            paras = []
            for p in root.iter(f"{A_NS}p"):
                t = "".join(r.text or "" for r in p.iter(f"{A_NS}t"))
                if t.strip():
                    paras.append(t)
            out.append(f"=== SLIDE {idx} ===")
            out.extend(paras if paras else ["[no text on slide]"])
            notes_part = f"ppt/notesSlides/notesSlide{slide.rsplit('slide', 1)[1]}"
            if notes_part in names:
                nroot = ET.fromstring(zf.read(notes_part))
                ntext = [ "".join(r.text or "" for r in p.iter(f"{A_NS}t")) for p in nroot.iter(f"{A_NS}p")]
                ntext = [t for t in ntext if t.strip() and not t.strip().isdigit()]
                if ntext:
                    notes_count += 1
                    out.append("[SPEAKER NOTES] " + " ".join(ntext))
        notes = []
        if media_count:
            notes.append(f"{media_count} image/media file(s) not transcribed; visual design cannot be fully assessed from text.")
        return ExtractionResult(EXTRACTED, "pptx-xml", "\n".join(out), notes,
                                {"slides": len(slides), "slides_with_speaker_notes": notes_count,
                                 "media_files": media_count})


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def extract_xlsx(path: Path, max_rows: int = 2000) -> ExtractionResult:
    try:
        zf = _open_ooxml(path)
    except ValueError as exc:
        return ExtractionResult(FAILED, "xlsx-xml", notes=[str(exc)])
    with zf:
        names = set(zf.namelist())
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            sroot = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sroot.findall(f"{S_NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{S_NS}t")))
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = {}
        if "xl/_rels/workbook.xml.rels" in names:
            rroot = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            for r in rroot.findall(f"{PKG_REL_NS}Relationship"):
                rels[r.get("Id")] = r.get("Target")
        out, notes, stats = [], [], {"sheets": 0, "formula_cells": 0}
        for sheet in wb.iter(f"{S_NS}sheet"):
            target = rels.get(sheet.get(f"{R_NS}id"), "")
            target = target.lstrip("/")
            part = target if target.startswith("xl/") else f"xl/{target}"
            if part not in names:
                notes.append(f"Sheet '{sheet.get('name')}' could not be located.")
                continue
            stats["sheets"] += 1
            out.append(f"=== SHEET: {sheet.get('name')} ===")
            sroot = ET.fromstring(zf.read(part))
            rows = sroot.iter(f"{S_NS}row")
            for i, row in enumerate(rows):
                if i >= max_rows:
                    notes.append(f"Sheet '{sheet.get('name')}' truncated at {max_rows} rows.")
                    break
                values: dict[int, str] = {}
                for c in row.findall(f"{S_NS}c"):
                    ref = c.get("r") or ""
                    col = _col_index(ref) if ref else len(values)
                    v = c.find(f"{S_NS}v")
                    f = c.find(f"{S_NS}f")
                    t = c.get("t")
                    if t == "s" and v is not None:
                        val = shared[int(v.text)] if v.text and int(v.text) < len(shared) else ""
                    elif t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter(f"{S_NS}t"))
                    else:
                        val = v.text if v is not None and v.text is not None else ""
                    if f is not None:
                        stats["formula_cells"] += 1
                        val = f"{val} {{={f.text or ''}}}"
                    values[col] = val
                if values:
                    width = max(values) + 1
                    out.append(f"R{row.get('r', i + 1)}: " + " | ".join(values.get(k, "") for k in range(width)))
        if any(n.startswith("xl/charts/") for n in names):
            notes.append("Workbook contains chart(s); chart visuals are not transcribed.")
        status = EXTRACTED if out else EMPTY
        if any("truncated" in n for n in notes):
            status = PARTIAL
        return ExtractionResult(status, "xlsx-xml", "\n".join(out), notes, stats)


def extract_csv(path: Path, max_rows: int = 5000) -> ExtractionResult:
    res = extract_plain(path, "csv")
    if res.status not in (EXTRACTED, PARTIAL):
        return res
    delim = "\t" if path.suffix.lower() == ".tsv" else ","
    try:
        rows = list(csv.reader(io.StringIO(res.text), delimiter=delim))
    except csv.Error as exc:
        res.notes.append(f"CSV parse warning: {exc}")
        return res
    res.stats.update({"rows_including_header": len(rows), "columns": max((len(r) for r in rows), default=0)})
    if len(rows) > max_rows:
        res.text = "\n".join(delim.join(r) for r in rows[:max_rows])
        res.status = PARTIAL
        res.notes.append(f"Only the first {max_rows} rows were included in extracted text.")
    return res


def extract_ipynb(path: Path) -> ExtractionResult:
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return ExtractionResult(FAILED, "ipynb-json", notes=[f"Invalid notebook JSON: {exc}"])
    out, stats = [], {"code_cells": 0, "markdown_cells": 0, "cells_with_outputs": 0}
    for i, cell in enumerate(nb.get("cells", []), 1):
        ctype = cell.get("cell_type", "?")
        src = "".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else str(cell.get("source", ""))
        out.append(f"=== CELL {i} [{ctype}] ===")
        out.append(src)
        if ctype == "code":
            stats["code_cells"] += 1
            outputs = cell.get("outputs", [])
            if outputs:
                stats["cells_with_outputs"] += 1
            for o in outputs:
                if "text" in o:
                    out.append("[STORED OUTPUT] " + "".join(o["text"])[:4000])
                elif "data" in o and "text/plain" in o["data"]:
                    out.append("[STORED OUTPUT] " + "".join(o["data"]["text/plain"])[:4000])
                elif "data" in o and any(k.startswith("image/") for k in o["data"]):
                    out.append("[STORED OUTPUT: image/plot not transcribed]")
                elif o.get("output_type") == "error":
                    out.append(f"[STORED ERROR OUTPUT] {o.get('ename')}: {o.get('evalue')}")
        elif ctype == "markdown":
            stats["markdown_cells"] += 1
    notes = ["Stored notebook outputs are shown as saved by the author; they were NOT re-executed."]
    return ExtractionResult(EXTRACTED if out else EMPTY, "ipynb-json", "\n".join(out), notes, stats)


def extract_pdf(path: Path) -> ExtractionResult:
    head = path.read_bytes()[:1024]
    if not head.startswith(b"%PDF"):
        return ExtractionResult(FAILED, "pdf", notes=["File does not start with a PDF header (corrupt or mis-named)."])
    if b"/Encrypt" in path.read_bytes()[-4096:]:
        encrypted_note = ["PDF may be encrypted/password-protected."]
    else:
        encrypted_note = []
    exe = shutil.which("pdftotext")
    if exe:
        try:
            proc = subprocess.run([exe, "-layout", str(path), "-"], capture_output=True, timeout=120)
            text = proc.stdout.decode("utf-8", "replace")
            if proc.returncode == 0 and len(text.strip()) > 50:
                pages = text.count("\f") + 1
                return ExtractionResult(EXTRACTED, "pdftotext", text, encrypted_note, {"pages_approx": pages})
        except (subprocess.SubprocessError, OSError):
            pass
    try:  # optional dependency
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(str(path))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(f"=== PAGE {i} ===\n{t}" for i, t in enumerate(pages, 1))
        if sum(len(t.strip()) for t in pages) > 50:
            return ExtractionResult(EXTRACTED, "pypdf", text, encrypted_note, {"pages": len(pages)})
    except Exception:  # noqa: BLE001 - optional library, any failure falls through
        pass
    return ExtractionResult(
        NEEDS_CLAUDE_READ, "claude-read-tool",
        notes=encrypted_note + ["No local PDF text extractor available or PDF has no text layer. "
                                "Agent 0 must open this file with Claude's Read tool (use the `pages` "
                                "parameter for PDFs over 10 pages) and save the transcription."])


def safe_unzip(path: Path, dest: Path) -> ExtractionResult:
    """Unpack a ZIP without executing anything; blocks path traversal and zip bombs."""
    if not zipfile.is_zipfile(path):
        return ExtractionResult(FAILED, "zip", notes=["Not a valid ZIP archive."])
    children: list[Path] = []
    notes: list[str] = []
    with zipfile.ZipFile(path) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if any(i.flag_bits & 0x1 for i in infos):
            return ExtractionResult(FAILED, "zip", notes=["ZIP is password-protected."])
        total = sum(i.file_size for i in infos)
        packed = sum(i.compress_size for i in infos) or 1
        if len(infos) > ZIP_MAX_FILES or total > ZIP_MAX_TOTAL_BYTES or total / packed > ZIP_MAX_RATIO:
            return ExtractionResult(FAILED, "zip", notes=[
                f"ZIP rejected by safety limits (files={len(infos)}, uncompressed={total} bytes)."])
        dest.mkdir(parents=True, exist_ok=True)
        root = dest.resolve()
        listing = []
        for info in infos:
            name = info.filename.replace("\\", "/")
            parts = [p for p in name.split("/") if p not in ("", ".")]
            if not parts or ".." in parts or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
                notes.append(f"Skipped unsafe path in archive: {info.filename}")
                continue
            if parts[0] in ("__MACOSX",) or parts[-1] in (".DS_Store",) or ".git" in parts \
                    or "node_modules" in parts or "__pycache__" in parts:
                continue
            target = (root.joinpath(*parts)).resolve()
            if root not in target.parents:
                notes.append(f"Skipped unsafe path in archive: {info.filename}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            children.append(target)
            listing.append(f"{'/'.join(parts)}  ({info.file_size} bytes)")
    text = "ARCHIVE CONTENTS (unpacked for analysis; nothing was executed):\n" + "\n".join(listing)
    return ExtractionResult(EXTRACTED if children else EMPTY, "zip-safe-unpack", text, notes,
                            {"files_unpacked": len(children)}, children)


def extract(path: Path, unzip_dest: Path | None = None) -> ExtractionResult:
    kind = file_kind(path)
    try:
        if path.stat().st_size == 0:
            return ExtractionResult(EMPTY, kind, notes=["File is 0 bytes."])
        if kind == "text":
            return extract_plain(path, "plain-text")
        if kind == "code":
            return extract_plain(path, "source-code")
        if kind == "docx":
            return extract_docx(path)
        if kind == "pptx":
            return extract_pptx(path)
        if kind == "xlsx":
            return extract_xlsx(path)
        if kind == "csv":
            return extract_csv(path)
        if kind == "ipynb":
            return extract_ipynb(path)
        if kind == "pdf":
            return extract_pdf(path)
        if kind == "zip":
            return safe_unzip(path, unzip_dest or path.with_suffix(""))
        if kind == "image":
            return ExtractionResult(NEEDS_CLAUDE_READ, "claude-read-tool", notes=[
                "Image file: may be viewed with Claude's Read tool for visual review. "
                "Text inside images is not reliably transcribed (no OCR guarantee)."])
        if kind == "legacy":
            return ExtractionResult(UNSUPPORTED, "none", notes=[
                f"{LEGACY_OFFICE[path.suffix.lower()]} format is not supported. "
                "Save it as DOCX/PPTX/XLSX/PDF and re-run."])
        data = path.read_bytes()[:8192]
        if not _looks_binary(data):
            res = extract_plain(path, "plain-text-guess")
            res.notes.append("Unknown extension; treated as plain text.")
            return res
        return ExtractionResult(UNSUPPORTED, "none", notes=["Unrecognised binary format."])
    except (zipfile.BadZipFile, ET.ParseError, KeyError, ValueError, OSError) as exc:
        return ExtractionResult(FAILED, kind, notes=[f"Parse error: {type(exc).__name__}: {exc}"])
