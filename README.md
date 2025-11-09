# AWS News Notifier

AWS What's New の最新情報を自動的に取得してSlackに通知するシステムです。
EventBridgeで毎日定時に実行され、過去24時間に公開されたAWSの新機能やアップデート情報をRSSフィードから収集し、Slackに通知します。

## 機能

- 📰 AWS What's New のRSSフィードから24時間以内の記事を取得
- ⏰ EventBridgeで毎日JST 9:00に自動実行
- 💬 Slackへリアルタイム通知（ニュースが0件の場合も通知）
- 🏷️ タイトル、リンク、公開日時、カテゴリを構造化して返却
- 📊 CloudWatch Logsに詳細なログを出力

## 前提条件

- Terraform >= 1.0
- AWS CLI（認証情報が設定済み）
- Python 3.12
- jq（JSON整形用、オプション）
- S3バケット（Lambda コードの保存先）

## ファイル構成

```
.
├── Makefile                  # デプロイ自動化
├── provider.tf                # AWSプロバイダー設定
├── variables.tf               # 変数定義
├── iam.tf                    # IAMロール・ポリシー定義
├── main.tf                   # Lambda関数リソース定義
├── eventbridge.tf            # EventBridge定期実行設定
├── outputs.tf                # 出力定義
├── notifier.py               # Lambda関数のソースコード
├── requirements.txt          # Python依存ライブラリ
├── terraform.tfvars          # 機密情報（Git管理対象外）
├── terraform.tfvars.example  # 設定テンプレート
└── .gitignore               # Git除外設定
```

## セットアップ手順（手動）

### 1. 設定ファイルの作成

`terraform.tfvars.example` をコピーして `terraform.tfvars` を作成し、実際の値を設定します：

```bash
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を編集：

```hcl
# S3バケット名（Lambda コードの保存先）
s3_bucket = "your-bucket-name"

# S3キー（Lambda デプロイパッケージのパス）
s3_key = "notifier.zip"

# Lambda関数名
lambda_function_name = "aws-news-notifier"

# AWSリージョン
aws_region = "ap-northeast-1"

# Slack Webhook URL（通知の送信先）
slack_webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

⚠️ **注意**: `terraform.tfvars` は機密情報（Slack Webhook URLなど）を含むため、`.gitignore` で除外されています。

### Slack Webhook URLの取得方法

1. Slackワークスペースで [Incoming Webhooks](https://api.slack.com/messaging/webhooks) を設定
2. 通知を送信したいチャンネルを選択
3. 生成されたWebhook URLをコピー
4. `terraform.tfvars` の `slack_webhook_url` に設定

### 2. デプロイパッケージの作成

依存ライブラリを含めたZIPファイルを作成します：

```bash
# 依存ライブラリをインストール
pip install -r requirements.txt -t package/

# Lambda関数のコードをコピー
cp notifier.py package/

# ZIPファイルを作成
cd package
zip -r ../notifier.zip .
cd ..

# 不要なディレクトリを削除
rm -rf package/
```

### 3. S3へのアップロード

Lambda関数のコードをS3にアップロードします：

```bash
# terraform.tfvars で設定したバケット名を使用
aws s3 cp notifier.zip s3://your-bucket-name/notifier.zip
```

### 4. Terraformでデプロイ

Terraformを使ってLambda関数をデプロイします：

```bash
# 初期化（初回のみ）
terraform init

# デプロイ内容の確認
terraform plan

# デプロイの実行
terraform apply
```

## Lambda関数の実行

### AWS CLIで実行

```bash
aws lambda invoke \
  --function-name aws-news-notifier \
  --log-type Tail \
  response.json

# レスポンスを確認
cat response.json | jq .
```

### AWS マネジメントコンソールで実行

1. Lambda コンソールを開く
2. 関数 `aws-news-notifier` を選択
3. 「テスト」タブをクリック
4. 「テスト」ボタンをクリック

### レスポンス形式

```json
{
  "statusCode": 200,
  "body": {
    "message": "24時間以内のAWS最新情報を15件取得しました",
    "time_threshold": "2025-11-08 10:00:00",
    "count": 15,
    "slack_notifications": {
      "success": 15,
      "failure": 0
    },
    "items": [
      {
        "title": "AWS Advanced .NET Data Provider Driver is Generally Available",
        "link": "https://aws.amazon.com/about-aws/whats-new/2025/11/aws-net-data-provider-driver/",
        "published": "2025-11-07 10:30:00",
        "description": "AWS Advanced .NET Data Provider Driver...",
        "categories": ["Database", "RDS"]
      }
    ]
  }
}
```

### CloudWatch Logs の確認

```bash
# ログを確認
aws logs tail /aws/lambda/aws-news-notifier --follow
```

ログには以下の情報が出力されます：
- RSSフィード取得開始
- 取得対象期間（24時間前の日時）
- 取得した記事数
- 各記事のタイトルと公開日時
- Slack通知の成功/失敗状況

## Lambda関数の更新

コードを変更した場合の更新手順：

### 方法1: Terraform経由で更新（推奨）

```bash
# 1. コードを修正
vim notifier.py

# 2. デプロイパッケージを再作成
pip install -r requirements.txt -t package/
cp notifier.py package/
cd package && zip -r ../notifier.zip . && cd ..
rm -rf package/

# 3. S3にアップロード
aws s3 cp notifier.zip s3://your-bucket-name/notifier.zip

# 4. Terraformで更新（S3のETagが変わると自動的に検出）
terraform apply
```

### 方法2: AWS CLI で直接更新

```bash
# S3にアップロード後、直接Lambda関数を更新
aws lambda update-function-code \
  --function-name aws-news-notifier \
  --s3-bucket your-bucket-name \
  --s3-key notifier.zip
```

## トラブルシューティング

### フィードが取得できない

- Lambda関数にインターネットアクセス権限があるか確認
- CloudWatch Logsでエラーメッセージを確認

### 依存ライブラリのエラー

```bash
# Lambda互換のライブラリをインストール
pip install -r requirements.txt -t package/ --platform manylinux2014_x86_64 --only-binary=:all:
```

### タイムアウトエラー

`main.tf:24` でタイムアウトを延長：

```hcl
timeout = 60  # 30秒 → 60秒に変更
```

## インフラストラクチャの削除

全てのリソースを削除する場合：

```bash
terraform destroy
```

⚠️ **注意**: S3バケット内のZIPファイルは手動で削除する必要があります。

## 定期実行の設定

EventBridgeにより、Lambda関数は以下のスケジュールで自動実行されます：

- **実行時刻**: 毎日JST 9:00（UTC 0:00）
- **実行内容**: 過去24時間のAWSニュースを取得してSlackに通知
- **設定ファイル**: `eventbridge.tf:5`

### スケジュールの変更方法

`eventbridge.tf` の `schedule_expression` を変更してください：

```hcl
# 例: 毎日JST 18:00（UTC 9:00）に実行
schedule_expression = "cron(0 9 * * ? *)"

# 例: 12時間ごとに実行
schedule_expression = "rate(12 hours)"
```

変更後、`terraform apply` でデプロイしてください。

## 出力情報

`terraform apply` 実行後、以下の情報が表示されます：

- `lambda_function_arn`: Lambda関数のARN
- `lambda_function_name`: Lambda関数名（aws-news-notifier）
- `lambda_role_arn`: 実行ロールのARN
- `lambda_invoke_arn`: 呼び出しARN（API Gateway連携用）

## ライセンス

MIT License

## 参考リンク

- [AWS What's New](https://aws.amazon.com/about-aws/whats-new/)
- [AWS What's New RSS Feed](https://aws.amazon.com/about-aws/whats-new/recent/feed/)
- [Terraform AWS Lambda](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function)
