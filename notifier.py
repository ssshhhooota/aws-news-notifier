import logging
from datetime import datetime, timedelta, timezone
import feedparser
import json
import os
from urllib import request, error

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# RSS フィードURL（グローバルスコープで定義）
RSS_FEED_URL = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"

# Slack Webhook URL（環境変数から取得）
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# JSTタイムゾーン（UTC+9）
JST = timezone(timedelta(hours=9))


def utc_to_jst(utc_dt):
    """UTC日時をJST日時に変換"""
    # UTCとして設定
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    # JSTに変換
    return utc_dt.astimezone(JST)


def get_24_hours_ago():
    """24時間前の日時を取得"""
    now = datetime.now()
    return now - timedelta(hours=24)


def get_recent_news():
    """AWS What's New から24時間以内のニュースを取得"""
    logger.info(f"RSSフィードを取得中: {RSS_FEED_URL}")

    # RSSフィードをパース
    feed = feedparser.parse(RSS_FEED_URL)

    if feed.bozo:
        logger.error(f"RSSフィードのパースエラー: {feed.bozo_exception}")
        return []

    # 24時間前の日時を取得
    time_threshold = get_24_hours_ago()
    logger.info(f"取得対象期間: {time_threshold.strftime('%Y-%m-%d %H:%M:%S')} 以降")

    recent_items = []

    for entry in feed.entries:
        try:
            # 公開日時をパース（RSSのpubDateフィールドはUTC）
            pub_date_utc = datetime(*entry.published_parsed[:6])

            # UTCからJSTに変換
            pub_date_jst = utc_to_jst(pub_date_utc)

            # 24時間以内の記事かチェック
            if pub_date_utc >= time_threshold:
                recent_items.append({
                    'title': entry.title,
                    'link': entry.link,
                    'published': pub_date_jst.strftime('%Y-%m-%d %H:%M:%S JST'),
                    'description': entry.get('description', ''),
                    'categories': [tag.term for tag in entry.get('tags', [])]
                })

        except Exception as e:
            logger.warning(f"記事のパース中にエラー: {e}")
            continue

    logger.info(f"24時間以内の記事数: {len(recent_items)}")
    return recent_items


def send_slack_notification(news_item):
    """Slackに1件のニュースを通知"""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URLが設定されていません")
        return False

    try:
        # Slackメッセージのフォーマット
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🆕 AWS最新情報",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{news_item['title']}*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*公開日時:*\n{news_item['published']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*カテゴリ:*\n{', '.join(news_item['categories'][:3]) if news_item['categories'] else 'なし'}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<{news_item['link']}|詳細を見る>"
                    }
                },
                {
                    "type": "divider"
                }
            ]
        }

        # HTTPリクエストを作成
        req = request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        # リクエストを送信
        with request.urlopen(req) as response:
            if response.status == 200:
                logger.info(f"Slack通知成功: {news_item['title']}")
                return True
            else:
                logger.error(f"Slack通知失敗 (status {response.status}): {news_item['title']}")
                return False

    except error.HTTPError as e:
        logger.error(f"HTTP Error: {e.code} - {e.reason}")
        return False
    except error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        return False
    except Exception as e:
        logger.error(f"Slack通知でエラーが発生: {str(e)}", exc_info=True)
        return False


def send_no_news_notification(time_threshold):
    """ニュースが0件の場合の通知"""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URLが設定されていません")
        return False

    try:
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 AWS最新情報",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "本日は新しいAWSニュースはありませんでした。"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*確認期間:*\n{time_threshold} 以降"
                        }
                    ]
                }
            ]
        }

        req = request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with request.urlopen(req) as response:
            if response.status == 200:
                logger.info("Slack通知成功: ニュース0件")
                return True
            else:
                logger.error(f"Slack通知失敗 (status {response.status})")
                return False

    except error.HTTPError as e:
        logger.error(f"HTTP Error: {e.code} - {e.reason}")
        return False
    except error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        return False
    except Exception as e:
        logger.error(f"Slack通知でエラーが発生: {str(e)}", exc_info=True)
        return False


def lambda_handler(event, context):
    """Lambda関数のエントリーポイント"""
    logger.info("Lambda function invoked")

    try:
        # 24時間以内のニュースを取得
        recent_news = get_recent_news()

        # 結果をログ出力
        logger.info(f"取得した記事数: {len(recent_news)}")

        # Slackに通知
        success_count = 0
        failure_count = 0

        if len(recent_news) == 0:
            # 0件の場合の通知（JSTに変換）
            time_threshold_utc = get_24_hours_ago()
            time_threshold_jst = utc_to_jst(time_threshold_utc)
            time_threshold_str = time_threshold_jst.strftime('%Y-%m-%d %H:%M:%S JST')
            if send_no_news_notification(time_threshold_str):
                success_count = 1
            else:
                failure_count = 1
        else:
            # 1件ずつ通知
            for i, item in enumerate(recent_news, 1):
                logger.info(f"{i}. {item['title']} ({item['published']})")

                # Slack通知を送信
                if send_slack_notification(item):
                    success_count += 1
                else:
                    failure_count += 1

        logger.info(f"Slack通知完了 - 成功: {success_count}件, 失敗: {failure_count}件")

        # レスポンスのtime_thresholdもJSTに変換
        response_threshold_utc = get_24_hours_ago()
        response_threshold_jst = utc_to_jst(response_threshold_utc)

        return {
            'statusCode': 200,
            'body': {
                'message': f'24時間以内のAWS最新情報を{len(recent_news)}件取得しました',
                'time_threshold': response_threshold_jst.strftime('%Y-%m-%d %H:%M:%S JST'),
                'count': len(recent_news),
                'slack_notifications': {
                    'success': success_count,
                    'failure': failure_count
                },
                'items': recent_news
            }
        }

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {
                'error': str(e)
            }
        }

