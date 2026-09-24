# ── IAM Role for Lambda ─────────────────────────────────────────────────────
resource "aws_iam_role" "lambda_role" {
  name = "${var.project}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Scan"]
        Resource = aws_dynamodb_table.reports.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.model_bucket.arn}/*"
      }
    ]
  })
}

# ── Lambda Function ──────────────────────────────────────────────────────────
resource "aws_lambda_function" "api" {
  function_name = "${var.project}-api"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_handler.handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 512

  # Placeholder zip — CodePipeline will update this on first deploy
  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = "lambda.zip"

  environment {
    variables = {
      GROQ_API_KEY         = var.groq_api_key
      DYNAMODB_TABLE       = aws_dynamodb_table.reports.name
      MODEL_BUCKET         = aws_s3_bucket.model_bucket.id
      MODEL_KEY            = "isolation_forest.pkl"
      DATASET_PATH         = "/tmp/invoice_dataset.csv"
      ML_LAMBDA_FUNCTION   = "${var.project}-ml"
    }
  }

  depends_on = [aws_iam_role_policy.lambda_policy]
}

output "lambda_function_name" {
  value = aws_lambda_function.api.function_name
}

# ── ML Lambda — IsolationForest scoring (separate function, heavy deps) ──────
resource "aws_lambda_function" "ml" {
  function_name = "${var.project}-ml"
  role          = aws_iam_role.lambda_role.arn
  handler       = "ml_lambda_handler.handler"
  runtime       = "python3.11"
  timeout       = 120
  memory_size   = 1024           # needs more memory for scikit-learn

  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = "ml_lambda.zip"

  environment {
    variables = {
      MODEL_BUCKET = aws_s3_bucket.model_bucket.id
      MODEL_KEY    = "isolation_forest.pkl"
      STATS_KEY    = "vendor_stats.json"
    }
  }

  depends_on = [aws_iam_role_policy.lambda_policy]
}

# Allow main Lambda to invoke ML Lambda
resource "aws_iam_role_policy" "invoke_ml_lambda" {
  role = aws_iam_role.lambda_role.id
  name = "invoke-ml-lambda"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.ml.arn
    }]
  })
}

output "ml_lambda_function_name" {
  value = aws_lambda_function.ml.function_name
}
