#!/usr/bin/env python3
"""
四コマ漫画 合成 → ブログ公開スクリプト
Usage: python scripts/4koma_publish.py

前提:
  scripts/4koma_staging/ に以下が揃っていること:
    - panel1.png
    - panel2.png
    - panel3.png
    - panel4.png
    - current_episode.json  (4koma_generate_prompt.py が生成)
"""

import json
import subprocess
import sys
import datetime
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
STAGING_DIR = Path(__file__).parent / "4koma_staging"
IMAGES_DIR  = BASE_DIR / "public" / "images"
BLOG_DIR    = BASE_DIR / "src" / "content" / "blog"


def check_panels() -> list[Path]:
    panels = [STAGING_DIR / f"panel{i}.png" for i in range(1, 5)]
    missing = [p for p in panels if not p.exists()]
    if missing:
        print("❌ 以下の画像が見つかりません:")
        for m in missing:
            print(f"   {m}")
        print()
        print("ChatGPTで4枚生成して panel1.png〜panel4.png として保存してください。")
        sys.exit(1)
    return panels


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


def compose(panels: list[Path], episode: dict) -> Path:
    """compose_4koma.py を呼び出して縦ストリップ画像を生成"""
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

    panels  = check_panels()
    episode = load_episode()

    print(f"  タイトル: {episode['episode_title']}")
    print(f"  公開日:   {episode['pub_date']}")
    print()

    compose(panels, episode)
    git_push(episode)
    cleanup()

    print()
    print(f"🎉 公開完了: https://ramen-sorekara.com/blog/{episode['slug']}")


if __name__ == "__main__":
    main()
