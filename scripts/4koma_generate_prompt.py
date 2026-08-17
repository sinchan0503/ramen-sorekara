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

SYSTEM_PROMPT = """あなたは百戦錬磨のギャグ漫画原作者です。
ラーメン好きOL「ぽん」を主人公にした四コマを考えますが、
「ほっこりオチ」で満足せず、毎回もっと面白くする気概で書いてください。
テンプレ通りの型をなぞるだけの予定調和な結末は却下し、
読者の予想を一段超える意外性・毒っ気・言葉のセンスを狙います。
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

## ギャグセンスを高めるための必須チェック（2026-08-17〜強化）
- 「意地で完食したら実は隣の注文だった」レベルの、前提そのものをひっくり返す裏切りを最低ラインとする
- そのオチ、他の四コマ漫画で見たことないか自問する。既視感のある展開（気づいたら〆のセリフで終わる、単に驚くだけ等）は捨てて書き直す
- オチの一文はできるだけ短く、韻や語感の良さ・言葉のダブルミーニングも狙えないか検討する
- 最後にダメ押し（二段オチ）を必ず1つ足す。ただの追加情報ではなく、オチをさらに一段ひっくり返す・強める一言にする
- ぽんの天然さは「無自覚に的確なボケをかます」方向で使う。ただのおっとりでは終わらせない

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
      "dialogue": "セリフまたはナレーション（吹き出しに入るテキスト。「ぽん：」「同僚：」「ナレーション：」等の話者名ラベルは絶対に含めない。誰の発言かは絵（表情・位置）で伝えるので、セリフの中身だけを書く）",
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
- 話者名ラベル厳禁: セリフは吹き出しに直接入る言葉のみ。"Pon:" や "Coworker:" のような話者表記を吹き出しテキストに含めない

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

    for p in data["panels"]:
        p["dialogue"] = strip_speaker_labels(p["dialogue"])

    data["pub_date"] = today.isoformat()
    data["slug"] = f"4koma-{today.isoformat()}"
    data["output"] = f"4koma-{today.isoformat()}.png"
    data["combined_prompt"] = build_combined_prompt(data)

    return data


# プロンプトで指示しても稀にAIが話者名ラベルを付けてくることがあるための保険（コード側で強制除去）
SPEAKER_LABELS = ["ぽん", "同僚", "店員", "店主", "友人", "上司", "先輩", "後輩", "客", "ナレーション"]

def strip_speaker_labels(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        for label in SPEAKER_LABELS:
            if line.startswith(f"{label}「"):
                line = line[len(label) + 1:]
                if line.endswith("」"):
                    line = line[:-1]
                break
            if line.startswith(f"{label}：") or line.startswith(f"{label}:"):
                line = line[len(label) + 1:].strip()
                break
        cleaned.append(line)
    return "\n".join(cleaned)


def build_combined_prompt(data: dict) -> str:
    """4コマ分のプロンプトを1枚の統合画像用プロンプトにまとめる"""
    panel_lines = []
    for p in data["panels"]:
        panel_lines.append(
            f"Panel {p['panel']}: {p['chatgpt_prompt']} "
            f"Speech bubble text (exact Japanese, keep as-is): \"{p['dialogue']}\""
        )
    panels_block = "\n".join(panel_lines)

    return (
        "Create ONE single vertical image containing a 4-panel manga comic "
        "(4 panels stacked top to bottom, each panel separated by a thin border, "
        "no panel numbers or labels drawn on the image). "
        "watercolor anime style, soft warm colors, clean line art, consistent character design "
        "across all 4 panels: Japanese office lady \"Pon\", early 20s, short black bob hair with "
        "a small ahoge, big brown eyes, light blue button-up shirt, dark navy slacks. "
        "Add a speech bubble with the exact Japanese text shown for each panel. "
        "Do NOT add any speaker name/label (e.g. do not write \"Pon:\" or a Japanese name) "
        "inside or above any speech bubble — write ONLY the quoted line itself, nothing else. "
        f"{panels_block} "
        "Final panel (bottom) is the punchline — make sure the character's expression there is "
        "exaggerated/comically deformed (e.g. wide eyes, flustered face) to sell the twist."
    )


def print_instructions(data: dict, out_path: Path):
    title = data["episode_title"]
    summary = data["story_summary"]
    panels = data["panels"]

    print("=" * 60)
    print(f"  四コマ: {title}")
    print(f"  あらすじ: {summary}")
    print("=" * 60)
    print()
    for p in panels:
        print(f"【コマ{p['panel']}】 {p['scene']}")
        print(f"  セリフ: {p['dialogue']}")
    print()
    print("【ChatGPTへの手順】")
    print("─" * 60)
    print("以下の統合プロンプトを1回だけChatGPTに貼り付けて、")
    print("4コマがまとまった画像を1枚だけ生成してください（バラバラに4回生成しない）。")
    print(f"  {STAGING_DIR}/combined.png")
    print("として保存してください。")
    print()
    print("▼ ChatGPTプロンプト（コピーして使用・これ1本のみ）:")
    print(f"  {data['combined_prompt']}")
    print()
    print("─" * 60)
    print()
    print("保存後、以下を実行して公開:")
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
