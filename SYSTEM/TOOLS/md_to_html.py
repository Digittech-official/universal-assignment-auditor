"""Minimal, dependency-free Markdown -> standalone HTML renderer for the audit report.

Supports headings, paragraphs, pipe tables, bullet/numbered lists, task lists,
blockquotes, horizontal rules, fenced code, **bold**, *italic* and `code`.
All input is HTML-escaped first, so report content cannot inject markup.
"""
from __future__ import annotations

import html
import re

CSS = """
:root{--bg:#ffffff;--fg:#1d2330;--muted:#5b6475;--line:#d9dee7;--head:#f3f5f9;--accent:#1f4e8c;--crit:#b3261e;--maj:#b45309}
@media (prefers-color-scheme:dark){:root{--bg:#14171d;--fg:#e6e9ef;--muted:#9aa3b2;--line:#2d333d;--head:#1c2029;--accent:#8ab4f8;--crit:#f28b82;--maj:#fbbc04}}
body{background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:1100px;margin:0 auto;padding:24px 16px}
h1{color:var(--accent);border-bottom:2px solid var(--line);padding-bottom:6px}h2{margin-top:2em;border-bottom:1px solid var(--line);padding-bottom:4px}
table{border-collapse:collapse;width:100%;margin:12px 0;display:block;overflow-x:auto}th,td{border:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left}
th{background:var(--head)}code{background:var(--head);padding:1px 4px;border-radius:3px}pre{background:var(--head);padding:10px;overflow-x:auto}
blockquote{border-left:4px solid var(--accent);margin:0;padding:4px 12px;color:var(--muted)}
.CRITICAL{color:var(--crit);font-weight:700}.MAJOR{color:var(--maj);font-weight:700}
"""


def inline(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\b(CRITICAL|MAJOR)\b", r'<span class="\1">\1</span>', text)
    return text


def render(md: str, title: str = "Final Quality Audit") -> str:
    lines = html.escape(md, quote=False).splitlines()
    out: list[str] = []
    i = 0
    list_stack: list[str] = []

    def close_lists():
        while list_stack:
            out.append(f"</{list_stack.pop()}>")

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            close_lists()
            j = i + 1
            code = []
            while j < len(lines) and not lines[j].startswith("```"):
                code.append(lines[j])
                j += 1
            out.append("<pre><code>" + "\n".join(code) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_lists()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
        elif re.match(r"^\s*\|.*\|\s*$", line) and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            close_lists()
            head = [c.strip() for c in line.strip().strip("|").split("|")]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>")
            i += 2
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                cells = [c.strip() for c in re.split(r"(?<!\\)\|", lines[i].strip().strip("|"))]
                out.append("<tr>" + "".join(f"<td>{inline(c.replace(chr(92) + '|', '|'))}</td>" for c in cells) + "</tr>")
                i += 1
            out.append("</tbody></table>")
            continue
        elif re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            tag = "ol" if re.match(r"^\s*\d+\.\s+", line) else "ul"
            if not list_stack or list_stack[-1] != tag:
                close_lists()
                out.append(f"<{tag}>")
                list_stack.append(tag)
            item = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line)
            item = item.replace("[ ]", "&#9744;", 1).replace("[x]", "&#9745;", 1)
            out.append(f"<li>{inline(item)}</li>")
        elif line.startswith("&gt;"):
            close_lists()
            out.append(f"<blockquote>{inline(line[4:].strip())}</blockquote>")
        elif re.match(r"^\s*(---|\*\*\*)\s*$", line):
            close_lists()
            out.append("<hr>")
        elif not line.strip():
            close_lists()
        else:
            close_lists()
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    close_lists()
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>\n"
            + "\n".join(out) + "\n</body></html>\n")
