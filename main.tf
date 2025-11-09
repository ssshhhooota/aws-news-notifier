# S3オブジェクトの情報を取得（ZIPファイルの変更検出用）
data "aws_s3_object" "lambda_zip" {
  bucket = var.s3_bucket
  key    = var.s3_key
}

# Lambda関数
resource "aws_lambda_function" "notifier" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_execution_role.arn

  # S3からコードを取得
  s3_bucket = var.s3_bucket
  s3_key    = var.s3_key

  # S3オブジェクトのETag（ハッシュ）を使用して変更を検出
  # ZIPファイルがS3で更新されると自動的にLambda関数も更新される
  source_code_hash = data.aws_s3_object.lambda_zip.etag

  handler = var.lambda_handler
  runtime = var.lambda_runtime

  # タイムアウト設定（秒）
  timeout = 30

  # メモリ設定（MB）
  memory_size = 128

  # 環境変数（必要に応じて追加）
  environment {
    variables = {
      ENVIRONMENT        = "production"
      SLACK_WEBHOOK_URL  = var.slack_webhook_url
    }
  }

  tags = {
    Name = var.lambda_function_name
  }
}

# CloudWatch Logsのロググループ
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 1

  tags = {
    Name = "${var.lambda_function_name}-logs"
  }
}
