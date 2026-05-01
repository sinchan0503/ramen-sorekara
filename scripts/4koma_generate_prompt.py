#!/usr/bin/env python3
"""
四コマ漫画 ストーリー & ChatGPTプロンプト自動生成
Usage: python scripts/4koma_generate_prompt.py [--theme テーマ]

実行すると:
  1. Claudeが4コマのストーリーを考案
  2. 各コマのChatGPT用画像生成プロンプトを出力
  3. scripts/4koma_staging/ にプロンプトを保存
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path
import anthropic

BASE_DIR    = Path(__file__).parent.parent
STAGING_DIR = Path(__file__).parent / "4koma_staging"
STAGING_DIR.mkdir(exist_ok=True)

# ── ぽんのキャラクター設定（一貫性のため毎回埋め込む）
PON_CHARACTER = """
キャラクター: ぽん（天然お転婆OL、20代前半）
- 外見: ショートボブの黒髪、少しアホ毛あり、くりっとした茶色の目
- 服装: 淡いブルーのシャツ、ダークネイビーのスラックス（OL服）
- 性格: 天然でちょっと抜けてる、ラーメン大好き、表情豊か
- 画風: 水彩風アニメイラスト、温かみのある淡い色調、漫画コマ枠あり
"""

SYSTEM_PROMPT = """あなたは四コマ漫画のストーリーライターです。
ラーメン好きOL「ぽん」を主人公にした、クスッと笑えるあるある系四コマを考えます。
必ず日本語で回答してください。"""

def generate(theme: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    today = datetime.date.today()

    user_prompt = f"""
今日（{today}）公開する四コマ漫画を1本作ってください。
テーマヒント: {theme if theme else "ラーメンあるある（自由）"}

## 出力形式（JSON）

```json
{{
  "episode_title": "コマタイトル（10文字以内）",
  "story_summary": "4コマのあらすじ（1〜2文）",
  "panels": [
    {{
      "panel": 1,
      "scene": "シーン説明（日本語）",
      "pon_expression": "ぽんの表情・ポーズ（例: 驚き、手を合わせて期待、うなだれる）",
      "dialogue": "セリフまたはナレーション（吹き出しに入るテキスト）",
      "chatgpt_prompt": "ChatGPTへの英語プロンプト（後述の形式で）"
    }},
    ... (4コマ分)
  ]
}}
```

## chatgpt_promptの形式
各コマのchatgpt_promptは以下を必ず含めてください:
- 画風指定: "watercolor anime style, soft warm colors, manga panel border, clean line art"
- ぽんの外見: "Japanese office lady in her early 20s, short black bob hair with a small ahoge, big brown eyes, light blue button-up shirt, dark navy slacks"
- そのコマの具体的な状況・表情・背景
- 「4-panel manga, panel [番号] of 4」を末尾に

簡潔で笑えるオチがつくように工夫してください。
"""

    print("ストーリーを考案中...\n")
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        system=SYSTEM_PROMPT
    )

    raw = message.content[0].text

    # JSONを抽出
    import re
    match = re.search(r'```json\s*([\s\S]+?)\s*```', raw)
    if match:
        data = json.loads(match.group(1))
    else:
        # コードブロックなしの場合
        data = json.loads(raw)

    data["pub_date"] = today.isoformat()
    data["slug"] = f"4koma-{today.isoformat()}"
    data["output"] = f"4koma-{today.isoformat()}.png"

    return data


def print_instructions(data: dict, out_path: Path):
    title = data["episode_title"]
    summary = data["story_summary"]
    panels = data["panels"]

    print("=" * 60)
    print(f"  四コマ: {title}")
    print(f"  あらすじ: {summary}")
    print("=" * 60)
    print()
    print("【ChatGPTへの手順】")
    print("─" * 60)
    print("以下のプロンプトを1枚ずつChatGPTに貼り付けて画像を生成し、")
    print(f"  {STAGING_DIR}/")
    print("  に panel1.png, panel2.png, panel3.png, panel4.png として保存してください。")
    print()

    for p in panels:
        n = p["panel"]
        print(f"【コマ{n}】 {p['scene']}")
        print(f"  セリフ: {p['dialogue']}")
        print(f"  表情: {p['pon_expression']}")
        print()
        print(f"  ▼ ChatGPTプロンプト（コピーして使用）:")
        print(f"  {p['chatgpt_prompt']}")
        print()
        print("─" * 60)

    print()
    print("4枚保存後、以下を実行して公開:")
    print(f"  python scripts/4koma_publish.py")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", default="", help="今日のテーマヒント（例: '月曜あるある'）")
    args = parser.parse_args()

    data = generate(args.theme)

    # ステージングフォルダに保存
    out_path = STAGING_DIR / "current_episode.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print_instructions(data, out_path)
    print(f"✅ プロンプト保存済み: {out_path}")


if __name__ == "__main__":
    main()
