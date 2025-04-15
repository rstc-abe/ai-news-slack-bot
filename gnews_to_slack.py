import requests
import datetime

import os
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY")

from datetime import datetime, timedelta


from datetime import datetime, timedelta, timezone

def get_ai_news():
    query = "AI OR 生成AI OR 人工知能 OR 機械学習 OR 深層学習 OR ChatGPT OR LLM OR Claude OR Gemini OR OpenAI"
    url = f"https://gnews.io/api/v4/search?q={query}&lang=ja&token={GNEWS_API_KEY}&max=10"
    res = requests.get(url)

    if res.status_code != 200:
        print("❗ ステータスコード:", res.status_code)
        print("📩 レスポンス内容:", res.text)
        return []

    articles = res.json().get("articles", [])

    # JSTでの前日日付
    jst = timezone(timedelta(hours=9))
    jst_now = datetime.now(jst)
    yesterday = (jst_now - timedelta(days=1)).strftime('%Y-%m-%d')

    # フィルター：publishedAtが前日の記事
    filtered_articles = [a for a in articles if a['publishedAt'].startswith(yesterday)]

    return filtered_articles

def get_yesterday_date():
    jst = timezone(timedelta(hours=9))
    jst_now = datetime.now(jst)
    return (jst_now - timedelta(days=1)).strftime('%Y-%m-%d')

def post_to_slack_blockkit(news_list):
    blocks = []

    # ヘッダー
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*📰 本日のAI関連ニュースまとめ*"
        }
    })
    blocks.append({"type": "divider"})

    # 各記事ブロック
    for article in news_list:
        title = article['title']
        url = article['url']
        published = article['publishedAt'][:10]
        description = article.get('description', '')
        content = article.get('content', '')

        keywords = ["新モデル", "新バージョン", "発表", "リリース", "GPT", "Claude", "Gemini", "Mixtral", "Anthropic"]
        is_new_model = any(kw in (description + content) for kw in keywords)
        detail_line = f"\n🆕 *新機能*: {description[:100]}..." if is_new_model else ""

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📌 *<{url}|{title}>*\n🗓 {published}{detail_line}"
            }
        })
        blocks.append({"type": "divider"})

    # Slackへ送信
    payload = {
        "blocks": blocks
    }
    requests.post(SLACK_WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    articles = get_ai_news()

    if not articles:
        post_to_slack_blockkit([{
            "title": f"📭 前日（{get_yesterday_date()}）のAI関連ニュースは見つかりませんでした。",
            "url": "",
            "publishedAt": "",
            "description": "",
            "content": ""
        }])
    else:
        post_to_slack_blockkit(articles)
