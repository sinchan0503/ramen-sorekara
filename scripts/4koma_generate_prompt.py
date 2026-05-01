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

WEEKDAY_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]

def get_season(month: int) -> str:
    if month in (3, 4, 5):   return "春（桜・新生活・GW）"
    if month in (6, 7, 8):   return "夏（猛暑・夏休み・花火）"
    if month in (9, 10, 11): return "秋（食欲の秋・紅葉・ハロウィン）"
    return "冬（寒い・鍋・年末年始）"

def get_date_context(today: datetime.date) -> str:
    weekday = WEEKDAY_JA[today.weekday()]
    season  = get_season(today.month)
    is_weekend = today.weekday() >= 5

    # 特別な日のチェック
    special = ""
    md = (today.month, today.day)
    if md == (1, 1):   special = "元日"
    elif md == (2, 14): special = "バレンタインデー"
    elif md == (3, 14): special = "ホワイトデー"
    elif md == (4, 1):  special = "エイプリルフール"
    elif md == (12, 24): special = "クリスマスイブ"
    elif md == (12, 31): special = "大晦日"
    elif today.month == 4 and 29 <= today.day <= 30: special = "GW直前"
    elif today.month == 5 and 1 <= today.day <= 5:   special = "ゴールデンウィーク"
    elif today.month == 5 and today.day == 6:         special = "GW明け初日"

    lines = [
        f"- 今日: {today} ({weekday})",
        f"- 季節: {season}",
        f"- 曜日の雰囲気: {'休日（のんびり・ラーメン遠征日和）' if is_weekend else weekday + 'らしい気分（仕事・平日あるある）'}",
    ]
    if special:
        lines.append(f"- 特別な日: {special}")

    return "\n".join(lines)


def generate(theme: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    today = datetime.date.today()
    date_context = get_date_context(today)

    user_prompt = f"""
今日公開する四コマ漫画を1本作ってください。

## 今日の日付・状況
{date_context}

## 重要: ストーリーを今日の状況に合わせること
- 曜日・季節・特別な日がストーリーや背景に自然に反映されていること
- 例: 金曜日なら「週末ラーメン計画」「花金気分」など
- 例: GWなら「ラーメン遠征」「人気店の行列」など
- 例: 春なら桜が背景に見える、夏ならセミや蝉の声など
- セリフや状況に違和感なく溶け込ませること（あからさまに説明しなくていい）

テーマヒント: {theme if theme else "（上記の日付・曜日・季節から自然に）"}

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
- ぽんの外見（毎回固定）: "Japanese office lady in her early 20s, short black bob hair with a small ahoge, big brown eyes, light blue button-up shirt, dark navy slacks"
- そのコマの具体的な状況・表情・背景
- 季節・曜日が伝わる背景描写（例: spring cherry blossoms, Friday evening glow, summer heat haze など）
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
