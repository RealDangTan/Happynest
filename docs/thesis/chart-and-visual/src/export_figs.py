"""Export Design-canvas artboards (.dc.html, static markup) to print PNGs.

Usage: python -I export_figs.py <canvas_root> <out_dir> [board ...]
Strips the dc runtime wrappers, renders with headless Chrome at 3x,
trims white margins and re-pads 12 px (at 1x) so every figure sits the same in Word.
"""
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image, ImageChops

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCALE = 3
PAD = 12 * SCALE


def plain_html(src: str) -> str:
    body = re.search(r"<x-dc>(.*)</x-dc>", src, re.S).group(1)
    helmet = re.search(r"<helmet>(.*?)</helmet>", body, re.S)
    head = helmet.group(1) if helmet else ""
    body = re.sub(r"<helmet>.*?</helmet>", "", body, flags=re.S)
    return (
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>" + head +
        "<style>html,body{margin:0;padding:0;background:#fff;overflow:hidden}</style>"
        "</head><body>" + body + "</body></html>"
    )


def trim(png: str) -> tuple[int, int]:
    im = Image.open(png).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 8 else 0)
    box = diff.getbbox()
    if box:
        im = im.crop(box)
    out = Image.new("RGB", (im.width + 2 * PAD, im.height + 2 * PAD), (255, 255, 255))
    out.paste(im, (PAD, PAD))
    out.save(png, dpi=(300, 300))
    return out.size


def main():
    root, outdir = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    only = set(sys.argv[3:])
    os.makedirs(outdir, exist_ok=True)
    prof = os.path.join(outdir, "_chrome_profile")
    canvas = json.load(open(os.path.join(root, "project", "canvas.json"), encoding="utf-8"))
    for name in canvas["order"]:
        stem = name.replace(".dc.html", "")
        if only and stem not in only:
            continue
        b = canvas["boards"][name]
        p = os.path.join(root, "project", name)
        if not os.path.exists(p):
            continue
        html = plain_html(open(p, encoding="utf-8").read())
        hp = os.path.join(outdir, stem + ".html")
        open(hp, "w", encoding="utf-8").write(html)
        png = os.path.join(outdir, stem + ".png")
        cmd = [
            CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--user-data-dir={prof}", f"--force-device-scale-factor={SCALE}",
            "--virtual-time-budget=4000",
            f"--window-size={b['w']},{b['h']}", f"--screenshot={png}",
            "file:///" + hp.replace("\\", "/"),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        size = trim(png)
        print(stem, size)


if __name__ == "__main__":
    main()
