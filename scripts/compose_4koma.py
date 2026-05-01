#!/usr/bin/env python3
"""
四コマ合成スクリプト（コマ画像4枚 → 縦長完成画像）
Usage: python scripts/compose_4koma.py panel1.png panel2.png panel3.png panel4.png --output 4koma-2026-05-01.png --title "月曜日の朝から" --date 2026-05-01
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import datetime

CANVAS_W   = 1080
TITLE_H    = 80
GAP        = 6
BORDER_W   = 4
TITLE_BG   = "#B5352A"
BORDER_COL = "#333333"

BASE_DIR   = Path(__file__).parent.parent
IMAGES_DIR = BASE_DIR / "public" / "images"
BLOG_DIR   = BASE_DIR / "src" / "content" / "blog"

def load_font(size):
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def compose(panel_paths, output_name, episode_title, pub_date):
    # パネル読み込み・正方形にリサイズ
    panels = []
    panel_w = CANVAS_W - BORDER_W * 2
    for p in panel_paths:
        img = Image.open(p).convert("RGB")
        # アスペクト比維持でcanvas幅に合わせる
        ratio = panel_w / img.width
        panel_h = int(img.height * ratio)
        img = img.resize((panel_w, panel_h), Image.LANCZOS)
        panels.append(img)

    total_h = sum(p.height for p in panels) + GAP * (len(panels) - 1)
    canvas = Image.new("RGB", (CANVAS_W, total_h), "#F8F0EC")
    draw = ImageDraw.Draw(canvas)

    # コマを縦に並べる（タイトルなし・枠線なし）
    y = 0
    for i, panel in enumerate(panels):
        if i > 0:
            y += GAP
        canvas.paste(panel, (0, y))
        y += panel.height

    # 保存
    out_path = IMAGES_DIR / output_name
    canvas.save(out_path, "PNG")
    print(f"画像: {out_path}")

    # ブログ記事生成
    slug = output_name.replace(".png", "")
    md_path = BLOG_DIR / f"{slug}.md"
    md = f"""---
title: "【四コマ】{episode_title}"
description: "ぽんのラーメン四コマ日誌"
pubDate: {pub_date}
emoji: "🍜"
image: "/images/{output_name}"
---

![{episode_title}](/images/{output_name})
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"記事:  {md_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("panels", nargs=4, help="コマ画像 panel1 panel2 panel3 panel4")
    parser.add_argument("--output", required=True, help="出力ファイル名 (例: 4koma-2026-05-01.png)")
    parser.add_argument("--title", default="ラーメン四コマ", help="エピソードタイトル")
    parser.add_argument("--date", default=datetime.date.today().isoformat(), help="公開日 YYYY-MM-DD")
    args = parser.parse_args()
    compose(args.panels, args.output, args.title, args.date)
