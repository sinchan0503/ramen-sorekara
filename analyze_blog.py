"""
ラーメンブログ アナリティクス分析スクリプト
GA4 + Search Console のデータを取得してMarkdownレポートを生成する
"""
import json
import datetime
import urllib.request
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest
)

BASE_DIR = Path(__file__).parent
TOKEN_FILE = BASE_DIR / "blog_token.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
REPORTS_DIR = BASE_DIR / "analytics_reports"

GA4_PROPERTY_ID = "535135265"
GSC_SITE_URL = "sc-domain:ramen-sorekara.com"

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]


def get_credentials() -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def fetch_ga4_data(creds: Credentials) -> dict:
    """GA4からページ別アクセス数を取得"""
    print("  GA4データ取得中...")
    try:
        client = BetaAnalyticsDataClient(credentials=creds)
        end_date = datetime.date.today() - datetime.timedelta(days=1)
        start_date = end_date - datetime.timedelta(days=27)  # 28日分

        request = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(
                start_date=str(start_date),
                end_date=str(end_date)
            )],
            dimensions=[Dimension(name="pagePath"), Dimension(name="pageTitle")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
            ],
            order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}],
            limit=20,
        )
        response = client.run_report(request)

        pages = []
        total_sessions = 0
        for row in response.rows:
            sessions = int(row.metric_values[0].value)
            total_sessions += sessions
            pages.append({
                "path": row.dimension_values[0].value,
                "title": row.dimension_values[1].value[:40],
                "sessions": sessions,
                "pageviews": int(row.metric_values[1].value),
                "bounce_rate": round(float(row.metric_values[2].value) * 100, 1),
                "avg_duration": round(float(row.metric_values[3].value), 1),
            })

        print(f"  GA4: {len(pages)}ページ取得 / 合計セッション: {total_sessions}")
        return {"pages": pages, "total_sessions": total_sessions, "period_days": 28}
    except Exception as e:
        print(f"  WARNING: GA4取得失敗: {e}")
        return {"pages": [], "total_sessions": 0, "period_days": 28}


def fetch_search_console_data(creds: Credentials) -> dict:
    """Search Consoleから検索キーワードとページを取得"""
    print("  Search Consoleデータ取得中...")
    try:
        service = build("webmasters", "v3", credentials=creds)
        end_date = datetime.date.today() - datetime.timedelta(days=3)  # 3日前まで（反映ラグ）
        start_date = end_date - datetime.timedelta(days=27)  # 28日分

        # キーワード別
        keyword_response = service.searchanalytics().query(
            siteUrl=GSC_SITE_URL,
            body={
                "startDate": str(start_date),
                "endDate": str(end_date),
                "dimensions": ["query"],
                "rowLimit": 20,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            }
        ).execute()

        keywords = []
        for row in keyword_response.get("rows", []):
            keywords.append({
                "query": row["keys"][0],
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": round(row["ctr"] * 100, 1),
                "position": round(row["position"], 1),
            })

        # ページ別
        page_response = service.searchanalytics().query(
            siteUrl=GSC_SITE_URL,
            body={
                "startDate": str(start_date),
                "endDate": str(end_date),
                "dimensions": ["page"],
                "rowLimit": 10,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            }
        ).execute()

        pages = []
        total_clicks = 0
        total_impressions = 0
        for row in page_response.get("rows", []):
            total_clicks += row["clicks"]
            total_impressions += row["impressions"]
            pages.append({
                "page": row["keys"][0].replace("https://ramen-sorekara.com", ""),
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": round(row["ctr"] * 100, 1),
                "position": round(row["position"], 1),
            })

        print(f"  Search Console: クリック合計{total_clicks} / 表示合計{total_impressions}")
        return {
            "keywords": keywords,
            "pages": pages,
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
        }
    except Exception as e:
        print(f"  WARNING: Search Console取得失敗: {e}")
        return {"keywords": [], "pages": [], "total_clicks": 0, "total_impressions": 0}


def save_report(ga4: dict, gsc: dict):
    """Markdownレポートを保存"""
    REPORTS_DIR.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()
    report_path = REPORTS_DIR / f"{today}.md"

    lines = [
        f"# ラーメンブログ アナリティクスレポート — {today}",
        f"（過去28日間）\n",
        "## サマリー",
        f"| 指標 | 数値 |",
        f"|------|------|",
        f"| セッション数（GA4） | {ga4['total_sessions']:,} |",
        f"| 検索クリック数（GSC） | {gsc['total_clicks']:,} |",
        f"| 検索表示回数（GSC） | {gsc['total_impressions']:,} |",
        "",
        "## 検索キーワード TOP20（Search Console）",
        "| キーワード | クリック | 表示 | CTR | 平均順位 |",
        "|-----------|---------|------|-----|---------|",
    ]

    for kw in gsc["keywords"]:
        lines.append(
            f"| {kw['query']} | {kw['clicks']} | {kw['impressions']} | {kw['ctr']}% | {kw['position']} |"
        )

    lines += [
        "",
        "## ページ別検索流入 TOP10（Search Console）",
        "| ページ | クリック | 表示 | CTR | 平均順位 |",
        "|--------|---------|------|-----|---------|",
    ]
    for p in gsc["pages"]:
        lines.append(
            f"| {p['page']} | {p['clicks']} | {p['impressions']} | {p['ctr']}% | {p['position']} |"
        )

    lines += [
        "",
        "## ページ別アクセス TOP20（GA4）",
        "| ページ | セッション | PV | 直帰率 | 平均滞在 |",
        "|--------|-----------|-----|-------|---------|",
    ]
    for p in ga4["pages"]:
        lines.append(
            f"| {p['path']} | {p['sessions']:,} | {p['pageviews']:,} | {p['bounce_rate']}% | {p['avg_duration']}s |"
        )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n✅ レポート保存: {report_path}")
    return report_path


COMPANY_DIR = Path.home() / "cc-company" / ".company"


def generate_actions(ga4: dict, gsc: dict) -> dict:
    """アナリティクスデータから具体的アクションを分類して生成"""
    article_ideas = []   # 次回以降の記事ネタ
    seo_fixes = []       # 既存記事のSEO修正
    design_fixes = []    # サイトデザイン改善

    # 滞在時間が長いカテゴリ → 類似記事を増やす
    top_dwell = sorted(ga4["pages"], key=lambda x: x["avg_duration"], reverse=True)[:5]
    for p in top_dwell:
        if p["avg_duration"] >= 300 and p["sessions"] >= 3:
            if "4koma" in p["path"]:
                article_ideas.append(f"四コマ継続強化（滞在{p['avg_duration']}秒・人気）→ 週複数本に増やすことを検討")
            elif "/blog/" in p["path"] and "4koma" not in p["path"]:
                slug = p["path"].replace("/blog/", "").strip("/")
                article_ideas.append(f"「{slug}」系の記事が人気（滞在{p['avg_duration']}秒）→ 同エリア・同ジャンルの記事を追加")

    # /game ページが滞在長い → 関連コンテンツへの導線
    for p in ga4["pages"]:
        if p["path"] == "/game" and p["avg_duration"] >= 300:
            design_fixes.append(f"/game ページ滞在{p['avg_duration']}秒と長い → ゲーム後にブログ記事へ誘導するリンクを追加")

    # 直帰率高いページ → コンテンツ・デザイン改善
    for p in ga4["pages"]:
        if p["sessions"] >= 5 and p["bounce_rate"] >= 60:
            slug = p["path"].strip("/")
            design_fixes.append(f"「{slug}」直帰率{p['bounce_rate']}% → 記事末尾の関連記事リンクを強化")

    # 表示多いのにCTR低いキーワード → 次回記事のタイトル参考に
    for p in gsc["pages"]:
        if p["impressions"] >= 10 and p["ctr"] < 5.0:
            slug = p["page"].replace("https://www.ramen-sorekara.com", "").replace("https://ramen-sorekara.com", "").strip("/")
            seo_fixes.append(f"「{slug or 'トップ'}」表示{p['impressions']}回・CTR{p['ctr']}% → 次回同ジャンル記事はタイトルにクリックされる言葉を入れる")

    # 検索順位11-20位のキーワード → 次回記事でそのキーワードを意識する
    for kw in gsc["keywords"]:
        if 10 < kw["position"] <= 20 and kw["impressions"] >= 5:
            seo_fixes.append(f"キーワード「{kw['query']}」順位{kw['position']} → 次回関連記事を書く際にこのキーワードを意識する")

    return {
        "article_ideas": article_ideas[:3],
        "seo_fixes": seo_fixes[:3],
        "design_fixes": design_fixes[:3],
    }


def save_actions(actions: dict, ga4: dict, gsc: dict):
    """アクションを各部署ファイルに書き込む"""
    today = datetime.date.today().isoformat()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. PM: 週次レビューをプロジェクトファイルに追記
    pm_path = COMPANY_DIR / "pm" / "projects" / "ramen-blog-growth.md"
    pm_entry = f"\n\n## {timestamp} 週次レビュー\n\n"
    pm_entry += f"**指標**: セッション {ga4['total_sessions']:,} / 検索クリック {gsc['total_clicks']:,} / 表示 {gsc['total_impressions']:,}\n\n"
    if actions["article_ideas"]:
        pm_entry += "**記事アクション**\n"
        for a in actions["article_ideas"]:
            pm_entry += f"- [ ] {a}\n"
    if actions["seo_fixes"]:
        pm_entry += "\n**次回記事への参考（SEO傾向）**\n"
        for a in actions["seo_fixes"]:
            pm_entry += f"- {a}\n"
    if actions["design_fixes"]:
        pm_entry += "\n**デザイン改善**\n"
        for a in actions["design_fixes"]:
            pm_entry += f"- [ ] {a}\n"
    with open(pm_path, "a", encoding="utf-8") as f:
        f.write(pm_entry)
    print(f"✅ PMプロジェクト追記: {pm_path}")

    # 2. マーケティング: 記事ネタ＋SEO傾向をコンテンツ計画に追記
    mkt_path = COMPANY_DIR / "marketing" / "content-plan" / "blog-4koma.md"
    mkt_entry = f"\n\n## アナリティクス由来のヒント（{today}）\n\n"
    if actions["article_ideas"]:
        mkt_entry += "**次回記事ネタ**\n"
        for a in actions["article_ideas"]:
            mkt_entry += f"- [ ] {a}\n"
    if actions["seo_fixes"]:
        mkt_entry += "\n**記事タイトル・構成の参考**\n"
        for a in actions["seo_fixes"]:
            mkt_entry += f"- {a}\n"
    with open(mkt_path, "a", encoding="utf-8") as f:
        f.write(mkt_entry)
    print(f"✅ マーケティング記事ネタ追記: {mkt_path}")

    # 3. 秘書TODO: デザイン改善のみ追記（既存記事変更はしない）
    todo_path = COMPANY_DIR / "secretary" / "todos" / f"{today}.md"
    todo_entry = f"\n\n## ラーメンブログ 週次アクション（アナリティクス由来）\n\n"
    all_actions = actions["design_fixes"]
    for a in all_actions:
        todo_entry += f"- [ ] {a} | 優先度: 通常\n"
    if todo_path.exists():
        with open(todo_path, "a", encoding="utf-8") as f:
            f.write(todo_entry)
    else:
        with open(todo_path, "w", encoding="utf-8") as f:
            f.write(f"# TODO {today}\n{todo_entry}")
    print(f"✅ 秘書TODO追記: {todo_path}")


def notify_slack(ga4: dict, gsc: dict, suggestions: list[str]):
    """Slack通知"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return

    today = datetime.date.today().isoformat()
    text = f"*🍜 ラーメンブログ 週次レポート ({today})*\n"
    text += f"> セッション: *{ga4['total_sessions']:,}* | 検索クリック: *{gsc['total_clicks']:,}* | 表示: *{gsc['total_impressions']:,}*\n\n"

    if suggestions:
        text += "*今週の改善アクション*\n"
        for s in suggestions[:3]:
            text += f"• {s}\n"

    payload = {"text": text}
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req)
        print("✅ Slack通知送信完了")
    except Exception as e:
        print(f"  WARNING: Slack通知失敗: {e}")


def main():
    print("\n🍜 ラーメンブログ アナリティクス分析開始...\n")

    creds = get_credentials()
    ga4_data = fetch_ga4_data(creds)
    gsc_data = fetch_search_console_data(creds)
    report_path = save_report(ga4_data, gsc_data)

    print("\n📊 サマリー")
    print(f"  セッション数: {ga4_data['total_sessions']:,}")
    print(f"  検索クリック: {gsc_data['total_clicks']:,}")
    print(f"  検索表示回数: {gsc_data['total_impressions']:,}")

    if gsc_data["keywords"]:
        print("\n🔍 検索キーワード TOP5")
        for kw in gsc_data["keywords"][:5]:
            print(f"  {kw['query']}: {kw['clicks']}クリック（順位{kw['position']}）")

    actions = generate_actions(ga4_data, gsc_data)
    all_suggestions = actions["article_ideas"] + actions["seo_fixes"] + actions["design_fixes"]
    if all_suggestions:
        print("\n💡 アクション")
        if actions["article_ideas"]:
            print("  📝 記事ネタ:")
            for a in actions["article_ideas"]:
                print(f"    • {a}")
        if actions["seo_fixes"]:
            print("  🔍 SEO修正:")
            for a in actions["seo_fixes"]:
                print(f"    • {a}")
        if actions["design_fixes"]:
            print("  🎨 デザイン改善:")
            for a in actions["design_fixes"]:
                print(f"    • {a}")
    save_actions(actions, ga4_data, gsc_data)
    notify_slack(ga4_data, gsc_data, all_suggestions)


if __name__ == "__main__":
    main()
