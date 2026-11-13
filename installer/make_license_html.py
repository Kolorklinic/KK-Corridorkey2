#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# CorridorKey 2 for Resolve - installer licence page
#
# From Creative Video Tips (CVT)  |  https://creativevideotips.com
# Licence: CC BY-NC-SA 4.0 with the CorridorKey additional terms (see LICENSE).
#
# Turns LICENSE (plain text, wrapped at about 78 characters) into the HTML
# page the Installer shows, with each paragraph on one line so it wraps to the
# window instead of breaking at the old line ends. Same look as the Read Me.
#
# Usage: python3 make_license_html.py <LICENSE> <out.html>
# ---------------------------------------------------------------------------
import html
import re
import sys

STYLE = """
body { font: 13px/1.5 -apple-system, "Helvetica Neue", Helvetica, sans-serif; margin: 2px 6px; color: #222; }
h1 { font-size: 17px; margin: 0 0 2px; }
p { margin: 0 0 10px; }
.sub { color: #777; font-size: 11px; margin: 0 0 12px; }
a { color: inherit; }
@media (prefers-color-scheme: dark) { body { color: #ddd; } .sub { color: #999; } }
"""


def paragraphs(text: str) -> list[str]:
    """Blank-line separated paragraphs, each joined into one line. A line that
    ends in a hyphen joins the next without a space (Attribution-NonCommercial-
    ShareAlike)."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        joined = ""
        for line in block.splitlines():
            line = line.strip()
            if not joined:
                joined = line
            elif joined.endswith("-"):
                joined += line
            else:
                joined += " " + line
        out.append(joined)
    return out


def linkify(escaped: str) -> str:
    # A full stop or comma after a link ends the sentence, not the address.
    return re.sub(r"(https?://[^\s)<]*[^\s)<.,;:])", r'<a href="\1">\1</a>', escaped)


def main() -> int:
    text = open(sys.argv[1], encoding="utf-8").read()
    # Only our notice: the full CorridorKey and CC texts (600 lines) stay in
    # the LICENSE file installed with the plugin.
    text = text.split("=== FULL LICENCE TEXTS ===")[0]
    paras = paragraphs(text)
    title_lines = paras[0].split(" Copyright ", 1)
    body = [f"<h1>{html.escape(title_lines[0])}</h1>"]
    if len(title_lines) > 1:
        body.append(f'<p class="sub">Copyright {linkify(html.escape(title_lines[1]))}</p>')
    body += [f"<p>{linkify(html.escape(p))}</p>" for p in paras[1:]
             if "are below, and the" not in p]
    body.append("<p>The full texts of the CorridorKey Licence and CC BY-NC-SA 4.0, and the "
                "licences of the included components, are in the LICENSE and notice files "
                "inside the plugin (/Library/OFX/Plugins/CorridorKey2.ofx.bundle/Contents/"
                "Resources) and in the plugin's GitHub repository.</p>")
    page = ('<!DOCTYPE html>\n<html><head><meta charset="utf-8"><style>' + STYLE +
            "</style></head><body>\n" + "\n".join(body) + "\n</body></html>\n")
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(page)
    return 0


if __name__ == "__main__":
    sys.exit(main())
