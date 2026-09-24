# ── DynamoDB: invoice reports ───────────────────────────────────────────────
resource "aws_dynamodb_table" "reports" {
  name         = "${var.project}-reports"
  billing_mode = "PAY_PER_REQUEST"   # serverless — pay only when used
  hash_key     = "invoice_id"

  attribute {
    name = "invoice_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

output "dynamodb_table" {
  value = aws_dynamodb_table.reports.name
}
