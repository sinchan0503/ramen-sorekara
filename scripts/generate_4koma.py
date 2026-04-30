#!/usr/bin/env python3
"""
四コマ漫画自動生成スクリプト
Usage: python scripts/generate_4koma.py scripts/4koma_scripts/episode_001.json
"""

import json
import sys
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ── 設定 ──────────────────────────────────────────────
CANVAS_W = 1080
CANVAS_H = 1350
TITLE_H  = 72
GAP      = 10
PANEL_COUNT = 4
PANEL_H  = (CANVAS_H - TITLE_H - GAP * (PANEL_COUNT + 1)) // PANEL_COUNT

PANEL_COLORS = ["#FFFDE7", "#FCE4EC", "#FFFFFF", "#E3F2FD"]
TITLE_BG     = "#B5352A"
BORDER_COLOR = "#D4C4C0"

BASE_DIR   = Path(__file__).parent.parent
IMAGES_DIR = BASE_DIR / "public" / "images"
BLOG_DIR   = BASE_DIR / "src" / "content" / "blog"

# ── フォント ──────────────────────────────────────────
def load_font(size):
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

# ── 白背景を透明化 ────────────────────────────────────
def remove_white_bg(img, threshold=235):
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > threshold and g > threshold and b > threshold:
                pixels[x, y] = (r, g, b, 0)
    return img

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ── 吹き出し ──────────────────────────────────────────
def draw_bubble(draw, text, bx, by, bw, font, padding=18):
    # 折り返し幅はバブル幅から計算（フォントサイズ基準）
    wrap_width = max(8, bw // (font.size // 2))
    lines = []
    for line in text.split("\n"):
        lines.extend(textwrap.wrap(line, width=wrap_width) or [""])
    line_h = font.size + 10
    bh = line_h * len(lines) + padding * 2 + 4

    draw.rounded_rectangle(
        [bx, by, bx + bw, by + bh],
        radius=18, fill="white", outline="#333333", width=3
    )
    for i, line in enumerate(lines):
        draw.text((bx + padding, by + padding + i * line_h), line, fill="#2a2a2a", font=font)

    return bh

# ── ナレーション ──────────────────────────────────────
def draw_narration(draw, text, px, py, pw, font):
    margin = 24
    bh = font.size + 24
    draw.rounded_rectangle(
        [px + margin, py + 12, px + pw - margin, py + 12 + bh],
        radius=8, fill="#FFF9C4", outline="#CCAA44", width=2
    )
    draw.text((px + margin + 16, py + 24), text, fill="#554400", font=font)

# ── メイン ────────────────────────────────────────────
def generate(script_path):
    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), "#F8F0EC")
    draw   = ImageDraw.Draw(canvas)

    font_title = load_font(30)
    font_text  = load_font(28)
    font_small = load_font(22)

    # タイトル帯
    draw.rectangle([0, 0, CANVAS_W, TITLE_H], fill=TITLE_BG)
    draw.text(
        (CANVAS_W // 2, TITLE_H // 2),
        "ぽんのラーメン四コマ日誌",
        fill="white", font=font_title, anchor="mm"
    )

    char_w_global = 0

    for i, panel in enumerate(script["panels"]):
        py = TITLE_H + GAP * (i + 1) + PANEL_H * i
        px = GAP
        pw = CANVAS_W - GAP * 2

        # パネル背景
        draw.rectangle(
            [px, py, px + pw, py + PANEL_H],
            fill=hex_rgb(PANEL_COLORS[i]), outline=BORDER_COLOR, width=2
        )

        # ナレーション
        if panel.get("narration"):
            draw_narration(draw, panel["narration"], px, py, pw, font_small)

        # キャラクター
        char_w = 0
        char_path = IMAGES_DIR / f"{panel['image']}.png"
        if char_path.exists():
            char_img = remove_white_bg(Image.open(char_path))
            char_h   = int(PANEL_H * 0.82)
            ratio    = char_h / char_img.height
            char_w   = int(char_img.width * ratio)
            char_img = char_img.resize((char_w, char_h), Image.LANCZOS)
            cx = px + 12
            cy = py + PANEL_H - char_h - 4
            canvas.paste(char_img, (cx, cy), char_img)
            char_w_global = char_w

        # 吹き出し
        if panel.get("text"):
            bx = px + char_w + 24
            bw = pw - char_w - 36
            by = py + (50 if panel.get("narration") else 24)
            draw_bubble(draw, panel["text"], bx, by, bw, font_text)

    # 保存
    out_name = script.get("output", f"4koma-{datetime.today().strftime('%Y-%m-%d')}.png")
    out_path = IMAGES_DIR / out_name
    canvas.save(out_path, "PNG")
    print(f"画像: {out_path}")

    # ブログ記事生成
    pub_date = script.get("pub_date", datetime.today().strftime("%Y-%m-%d"))
    slug     = script.get("slug", out_name.replace(".png", ""))
    title    = script.get("episode_title", "四コマ")
    md_path  = BLOG_DIR / f"{slug}.md"

    md = f"""---
title: "{title}"
description: "ぽんのラーメン四コマ日誌"
pubDate: {pub_date}
emoji: "🍜"
image: "/images/{out_name}"
---

![{title}](/images/{out_name})
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"記事:  {md_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_4koma.py <script.json>")
        sys.exit(1)
    generate(sys.argv[1])
