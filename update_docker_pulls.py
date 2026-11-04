#!/usr/bin/env python3
"""Total the Docker Hub pulls for one account and draw them as an animated SVG counter.

Run by .github/workflows/docker-pulls.yml once a day. Reads every repository
under the account from the Docker Hub API, sums `pull_count` (skipping the
repositories listed in EXCLUDE), rounds down to the nearest hundred and writes
assets/docker-pulls.svg, a card whose number counts up from zero when the
profile page loads.

Usage:
    python scripts/update_docker_pulls.py                 # live count from Docker Hub
    python scripts/update_docker_pulls.py --total 10400   # draw a given number
"""

from __future__ import annotations

import argparse
import base64
import json
import urllib.request
from pathlib import Path

ACCOUNT = "chiomab"
EXCLUDE = {"getting-started-todo-app"}  # tutorial image, not research software
OUT = Path(__file__).resolve().parents[1] / "assets" / "docker-pulls.svg"

FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
BOX, EDGE, GLOW, INK, LABEL, NOTE = "#241A14", "#4E3D30", "#6CC3E8", "#FBF4EC", "#6CC3E8", "#D9C7B4"
FRAMES, DURATION = 30, 2.2  # number of count-up steps, seconds


def fetch_pulls(account: str) -> tuple[int, int]:
    url = f"https://hub.docker.com/v2/repositories/{account}/?page_size=100"
    total, images = 0, 0
    while url:
        with urllib.request.urlopen(url, timeout=30) as resp:
            page = json.load(resp)
        for repo in page["results"]:
            if repo["name"] in EXCLUDE:
                continue
            total += int(repo["pull_count"])
            images += 1
        url = page.get("next")
    return total, images


def ease_out(x: float) -> float:
    return 1 - (1 - x) ** 3


def font_face(family: str, filename: str) -> str:
    data = base64.b64encode((FONTS / filename).read_bytes()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{data}) format('woff2')}}"


def svg(total: int, images: int) -> str:
    """Odometer-style counter: each digit rolls into place in a monospaced face."""
    shown = (total // 100) * 100
    text = f"{shown:,}"
    size, line = 50, 60          # font size and roll step (px)
    adv = size * 0.6             # IBM Plex Mono advance width
    x0, base = 32, 96
    digits = [c for c in text if c.isdigit()]
    cols, rules, k = [], [], 0
    for i, ch in enumerate(text):
        x = x0 + i * adv
        if not ch.isdigit():
            cols.append(f'<text class="n" x="{x:.1f}" y="{base}">{ch}</text>')
            continue
        right = k                           # columns further right spin more
        cycles = 1 + right
        seq = [str(d % 10) for d in range(cycles * 10 + int(ch) + 1)]
        stack = "".join(f'<text class="n" x="{x:.1f}" y="{base + j * line}">{d}</text>'
                        for j, d in enumerate(seq))
        shift = (len(seq) - 1) * line
        dur = 1.6 + 0.25 * right
        rules.append(f"@keyframes r{k}{{from{{transform:translateY(0)}}to{{transform:translateY(-{shift}px)}}}}"
                     f".r{k}{{animation:r{k} {dur:.2f}s cubic-bezier(.16,.84,.24,1) forwards}}")
        cols.append(f'<g clip-path="url(#win)"><g class="r{k}">{stack}</g></g>')
        k += 1
    plus_x = x0 + len(text) * adv
    end = 1.6 + 0.25 * (len(digits) - 1)
    faces = (font_face("Flaneur Mono", "IBMPlexMono-SemiBold.woff2")
             + font_face("Flaneur Sans", "SpaceGrotesk-Medium.woff2"))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="150" viewBox="0 0 420 150" role="img" aria-label="{shown:,}+ Docker Hub pulls across {images} genomics images">
<title>{shown:,}+ Docker Hub pulls across {images} genomics images</title>
<defs>
<clipPath id="win"><rect x="0" y="{base - 40}" width="420" height="52"/></clipPath>
<filter id="glow" x="-10%" y="-40%" width="120%" height="180%">
<feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur"/>
<feFlood flood-color="{GLOW}" flood-opacity="0.6"/>
<feComposite in2="blur" operator="in" result="halo"/>
<feMerge><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
</defs>
<style>
{faces}
.card{{fill:{BOX};stroke:{EDGE};stroke-width:1.5}}
.k{{font:600 13px 'Flaneur Mono',monospace;fill:{LABEL};letter-spacing:2px}}
.n{{font:600 {size}px 'Flaneur Mono',monospace;fill:{INK}}}
.s{{font:500 14px 'Flaneur Sans',Helvetica,Arial,sans-serif;fill:{NOTE}}}
.plus{{opacity:0;animation:in .4s ease-out {end:.2f}s forwards}}
@keyframes in{{to{{opacity:1}}}}
{''.join(rules)}
</style>
<rect class="card" x="1" y="1" width="418" height="148" rx="14"/>
<text class="k" x="32" y="38">$ docker hub pulls</text>
<g filter="url(#glow)">{''.join(cols)}<text class="n plus" x="{plus_x:.1f}" y="{base}">+</text></g>
<text class="s" x="32" y="126">across {images} containerised genomics images</text>
</svg>
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--total", type=int, help="draw this total instead of querying Docker Hub")
    p.add_argument("--images", type=int, default=28)
    args = p.parse_args()
    total, images = (args.total, args.images) if args.total else fetch_pulls(ACCOUNT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg(total, images))
    print(f"{total:,} pulls across {images} images -> {OUT}")


if __name__ == "__main__":
    main()
