variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "s3_bucket" {
  description = "S3 bucket name where the Lambda code is stored"
  type        = string
  # デフォルト値なし - terraform.tfvars で指定必須
}

variable "s3_key" {
  description = "S3 key (path) to the Lambda deployment package"
  type        = string
  default     = "notifier.zip"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "aws-news-notifier"
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_handler" {
  description = "Lambda handler"
  type        = string
  default     = "notifier.lambda_handler"
}

variable "slack_webhook_url" {
  description = "Slack Webhook URL for notifications"
  type        = string
  sensitive   = true
  # デフォルト値なし - terraform.tfvars で指定必須
}
