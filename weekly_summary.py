import os
import openai
import feedparser
import requests
import re
from datetime import datetime, timedelta, timezone
from openai import OpenAI

# 環境変数からAPIキーとWebhookを取得（GitHub Secretsに設定してある想定）
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
openai.api_key = OPENAI_API_KEY
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 1週間以内のAIニュースをRSSから取得
def fetch_weekly_news_from_rss():
    rss_url = "https://news.google.com/rss/search?q=AI+OR+ChatGPT+OR+生成AI+OR+LLM&hl=ja&gl=JP&ceid=JP:ja"
    feed = feedparser.parse(rss_url)

    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    week_ago = now - timedelta(days=7)

    filtered_articles = []
    for entry in feed.entries:
        if hasattr(entry, 'published_parsed'):
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(jst)
            if published >= week_ago:
                filtered_articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": published.strftime('%Y-%m-%d')
                })

    return filtered_articles

# OpenAI APIでAI関連のニュースを要約
def summarize_ai_news(articles):
    if not articles:
        return "📭 過去1週間のAI関連ニュースは見つかりませんでした。"

    # ニュースを箇条書き形式で整形
    article_list = "\n".join([f"- {a['title']} ({a['link']})" for a in articles])

    prompt = f"""
以下は過去1週間の技術ニュースのタイトル一覧です。この中から「AI」「生成AI」「機械学習」「ChatGPT」「LLM」「Claude」などに関する重要なニュースだけを選び、日本語で3〜5件に要約してください。必要に応じてURLも添えてください。

{article_list}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたはニュースを要約するアシスタントです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )

        summary = response.choices[0].message.content
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ OpenAI APIで要約中にエラーが発生しました: {str(e)}"

def format_summary_for_slack(summary_text):
    lines = []
    current_title = None

    for line in summary_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # 番号付き or Markdown太字タイトルを抽出 → Slack太字に変換
        if re.match(r'^\d+\.\s+.*', line) or line.startswith('**') or line.startswith('・'):
            title = re.sub(r'^\d+\.\s*', '', line)  # 「1. タイトル」→「タイトル」
            title = title.strip('*')  # 「**タイトル**」→「タイトル」
            current_title = f"🔹 *{title}*"
            lines.append(current_title)
            continue

        # Markdownリンク形式 → Slack形式に変換
        if re.match(r'- \[.*?\]\((https?://.*?)\)', line):
            match = re.search(r'\[(.*?)\]\((https?://.*?)\)', line)
            if match:
                text = match.group(1)
                url = match.group(2)
                lines.append(f"➡️ <{url}|▶ {text}>")
            continue

        # 単純なURL行にも対応（「- 詳細はこちら: https://...」など）
        if re.match(r'^(https?://\S+)$', line) or 'http' in line:
            url_match = re.search(r'(https?://[^\s\)]+)', line)
            if url_match:
                url = url_match.group(1)
                lines.append(f"➡️ <{url}|▶ 詳細はこちら>")
            continue

        # その他の本文行
        lines.append(line)

    return "\n".join(lines)

# Slack投稿
def post_summary_to_slack(summary_text):
    formatted_text = format_summary_for_slack(summary_text)

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "*📰 今週のAIニュースまとめ*"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": formatted_text}},
        {"type": "divider"},
    ]
    payload = {"blocks": blocks}
    requests.post(SLACK_WEBHOOK_URL, json=payload)

# 実行処理
if __name__ == "__main__":
    articles = fetch_weekly_news_from_rss()
    summary = summarize_ai_news(articles)
    post_summary_to_slack(summary)
