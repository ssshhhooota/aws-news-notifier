# EventBridge Rule - 毎日JST 9:00（UTC 0:00）に実行
resource "aws_cloudwatch_event_rule" "daily_schedule" {
  name                = "${var.lambda_function_name}-daily-trigger"
  description         = "Trigger Lambda function daily at 9:00 JST (0:00 UTC)"
  schedule_expression = "cron(0 0 * * ? *)"

  tags = {
    Name = "${var.lambda_function_name}-daily-trigger"
  }
}

# EventBridge Target - Lambda関数を指定
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_schedule.name
  target_id = "lambda"
  arn       = aws_lambda_function.notifier.arn
}

# Lambda Permission - EventBridgeからの呼び出しを許可
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notifier.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_schedule.arn
}
