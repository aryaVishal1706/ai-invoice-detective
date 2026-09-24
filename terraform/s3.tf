# ── S3: Lambda deployment zip ──────────────────────────────────────────────
resource "aws_s3_bucket" "lambda_bucket" {
  bucket        = "${var.project}-lambda-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

# ── S3: ML model storage ────────────────────────────────────────────────────
resource "aws_s3_bucket" "model_bucket" {
  bucket        = "${var.project}-models-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

# ── S3: React frontend static website ──────────────────────────────────────
resource "aws_s3_bucket" "frontend_bucket" {
  bucket        = "${var.project}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend_bucket.id
  index_document { suffix = "index.html" }
  error_document { key    = "index.html" }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend_bucket.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend_public" {
  bucket = aws_s3_bucket.frontend_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend_bucket.arn}/*"
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# ── S3: CodePipeline artifacts — REMOVED (no pipeline)


output "frontend_url" {
  value = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "lambda_bucket_name" {
  value = aws_s3_bucket.lambda_bucket.id
}

output "model_bucket_name" {
  value = aws_s3_bucket.model_bucket.id
}

output "frontend_bucket_name" {
  value = aws_s3_bucket.frontend_bucket.id
}
