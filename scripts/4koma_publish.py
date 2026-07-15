#!/usr/bin/env python3
"""
四コマ漫画 合成 → ブログ公開スクリプト
Usage: python scripts/4koma_publish.py

前提（優先順）:
  1. combined.png（1枚の統合プロンプトで生成した4コマ画像）※標準フロー
  2. panel1.png〜panel4.png（旧フロー・個別4枚をcompose_4koma.pyで縦に結合）
  + current_episode.json（4koma_generate_prompt.py が生成）

どちらも scripts/4koma_staging/ に置く。
"""

import json
import shutil
import subprocess
import sys
import datetime
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
STAGING_DIR = Path(__file__).parent / "4koma_staging"
IMAGES_DIR  = BASE_DIR / "public" / "images"
BLOG_DIR    = BASE_DIR / "src" / "content" / "blog"


def check_images():
    """combined.png（優先）または panel1〜4.png を探す。戻り値: ("combined", path) or ("panels", [paths])"""
    combined = STAGING_DIR / "combined.png"
    if combined.exists():
        return "combined", combined

    panels = [STAGING_DIR / f"panel{i}.png" for i in range(1, 5)]
    if all(p.exists() for p in panels):
        return "panels", panels

    print("❌ 画像が見つかりません。")
    print(f"   {combined} （1枚の統合プロンプトで生成した画像）")
    print("   または panel1.png〜panel4.png（旧フロー）")
    print()
    print("ChatGPTで combined_prompt を1回貼り付けて1枚生成し、")
    print(f"  {combined}")
    print("として保存してください。")
    sys.exit(1)


def load_episode() -> dict:
    ep_path = STAGING_DIR / "current_episode.json"
    if not ep_path.exists():
        # JSONがなければデフォルト値を使う
        today = datetime.date.today().isoformat()
        return {
            "episode_title": "ラーメン四コマ",
            "pub_date": today,
            "slug": f"4koma-{today}",
            "output": f"4koma-{today}.png",
        }
    with open(ep_path, encoding="utf-8") as f:
        return json.load(f)


def place_combined(image: Path, episode: dict) -> Path:
    """1枚の統合画像をそのままpublic/images/へ配置し、ブログ記事を生成"""
    output = episode["output"]
    out_path = IMAGES_DIR / output
    shutil.copy(image, out_path)
    print(f"画像: {out_path}")
    _write_blog_md(episode)
    return out_path


def compose(panels: list[Path], episode: dict) -> Path:
    """（旧フロー）compose_4koma.py を呼び出して縦ストリップ画像を生成"""
    output  = episode["output"]
    title   = episode["episode_title"]
    pub_date = episode["pub_date"]

    compose_script = Path(__file__).parent / "compose_4koma.py"
    cmd = [
        sys.executable, str(compose_script),
        str(panels[0]), str(panels[1]), str(panels[2]), str(panels[3]),
        "--output", output,
        "--title", title,
        "--date", pub_date,
    ]
    print("🎨 画像を合成中...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ 合成失敗:")
        print(result.stderr)
        sys.exit(1)
    print(result.stdout.strip())
    return IMAGES_DIR / output


def _write_blog_md(episode: dict):
    slug  = episode["slug"]
    title = episode["episode_title"]
    output = episode["output"]
    pub_date = episode["pub_date"]
    md_path = BLOG_DIR / f"{slug}.md"
    md = f"""---
title: "【四コマ】{title}"
description: "ぽんのラーメン四コマ日誌"
pubDate: {pub_date}
emoji: "🍜"
image: "/images/{output}"
---

![{title}](/images/{output})
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"記事:  {md_path}")


def git_push(episode: dict):
    slug      = episode["slug"]
    title     = episode["episode_title"]
    img_file  = f"public/images/{episode['output']}"
    md_file   = f"src/content/blog/{slug}.md"

    cmds = [
        ["git", "add", img_file, md_file],
        ["git", "commit", "-m", f"feat: 四コマ「{title}」公開"],
        ["git", "push"],
    ]
    print("🚀 GitHubへプッシュ中...")
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ {' '.join(cmd)} 失敗:")
            print(result.stderr)
            sys.exit(1)
    print("✅ プッシュ完了！Vercelが自動デプロイします。")


def cleanup():
    """ステージングフォルダの画像をクリア"""
    combined = STAGING_DIR / "combined.png"
    if combined.exists():
        combined.unlink()
    for f in STAGING_DIR.glob("panel*.png"):
        f.unlink()
    ep = STAGING_DIR / "current_episode.json"
    if ep.exists():
        ep.unlink()
    print("🧹 ステージングフォルダをクリアしました。")


def main():
    print("=" * 50)
    print("  四コマ公開スクリプト")
    print("=" * 50)

    kind, images = check_images()
    episode = load_episode()

    print(f"  タイトル: {episode['episode_title']}")
    print(f"  公開日:   {episode['pub_date']}")
    print(f"  方式:     {'統合1枚画像' if kind == 'combined' else '旧・4枚結合'}")
    print()

    if kind == "combined":
        place_combined(images, episode)
    else:
        compose(images, episode)

    git_push(episode)
    cleanup()

    print()
    print(f"🎉 公開完了: https://ramen-sorekara.com/blog/{episode['slug']}")


if __name__ == "__main__":
    main()
