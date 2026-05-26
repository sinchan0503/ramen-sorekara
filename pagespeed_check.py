#!/usr/bin/env python3
"""
PageSpeed Insights 定期チェックスクリプト
ramen-sorekara.com のモバイル・デスクトップスコアを計測してレポート保存
"""

import urllib.request
import json
import os
from datetime import datetime

URL = "https://ramen-sorekara.com"
API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
REPORT_DIR = os.path.join(os.path.dirname(__file__), "analytics_reports")

def fetch_score(strategy):
    endpoint = f"{API}?url={URL}&strategy={strategy}&category=performance&category=seo&category=accessibility&category=best-practices"
    with urllib.request.urlopen(endpoint, timeout=60) as res:
        return json.loads(res.read())

def extract(data, strategy):
    cats = data.get("lighthouseResult", {}).get("categories", {})
    audits = data.get("lighthouseResult", {}).get("audits", {})

    def score(key):
        val = cats.get(key, {}).get("score")
        return int(val * 100) if val is not None else "N/A"

    def metric(key):
        val = audits.get(key, {}).get("displayValue", "N/A")
        return val

    return {
        "strategy": strategy,
        "performance": score("performance"),
        "seo": score("seo"),
        "accessibility": score("accessibility"),
        "best_practices": score("best-practices"),
        "fcp": metric("first-contentful-paint"),
        "lcp": metric("largest-contentful-paint"),
        "tbt": metric("total-blocking-time"),
        "cls": metric("cumulative-layout-shift"),
        "si": metric("speed-index"),
    }

def score_emoji(score):
    if score == "N/A":
        return "❓"
    if score >= 90:
        return "🟢"
    if score >= 50:
        return "🟡"
    return "🔴"

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"📊 PageSpeed計測中: {URL}")

    results = []
    for strategy in ["mobile", "desktop"]:
        print(f"  → {strategy} 計測中...")
        try:
            data = fetch_score(strategy)
            results.append(extract(data, strategy))
            print(f"  ✅ {strategy} 完了")
        except Exception as e:
            print(f"  ❌ {strategy} エラー: {e}")

    if not results:
        print("全て失敗しました")
        return

    # レポート生成
    lines = [
        f"# PageSpeed レポート {today}",
        "",
        f"対象: {URL}",
        "",
        "## スコア",
        "",
        "| 計測環境 | パフォーマンス | SEO | ユーザー補助 | おすすめの方法 |",
        "|---------|-------------|-----|-----------|-------------|",
    ]

    for r in results:
        label = "モバイル" if r["strategy"] == "mobile" else "デスクトップ"
        lines.append(
            f"| {label} "
            f"| {score_emoji(r['performance'])} {r['performance']} "
            f"| {score_emoji(r['seo'])} {r['seo']} "
            f"| {score_emoji(r['accessibility'])} {r['accessibility']} "
            f"| {score_emoji(r['best_practices'])} {r['best_practices']} |"
        )

    lines += ["", "## Core Web Vitals", ""]
    for r in results:
        label = "モバイル" if r["strategy"] == "mobile" else "デスクトップ"
        lines += [
            f"### {label}",
            "",
            f"| 指標 | 値 |",
            f"|------|-----|",
            f"| First Contentful Paint | {r['fcp']} |",
            f"| Largest Contentful Paint | {r['lcp']} |",
            f"| Total Blocking Time | {r['tbt']} |",
            f"| Cumulative Layout Shift | {r['cls']} |",
            f"| Speed Index | {r['si']} |",
            "",
        ]

    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f"{today}-pagespeed.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))

    print(f"\n✅ レポート保存: {path}")

    # サマリー表示
    for r in results:
        label = "モバイル" if r["strategy"] == "mobile" else "デスクトップ"
        print(f"  {label}: パフォーマンス {r['performance']} / SEO {r['seo']}")

if __name__ == "__main__":
    main()
