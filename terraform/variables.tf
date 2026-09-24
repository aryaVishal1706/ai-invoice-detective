variable "region"       { default = "ap-south-1" }
variable "project"      { default = "ai-invoice-detective" }
variable "github_owner" { default = "aryaVishal1706" }
variable "github_repo"  { default = "ai-invoice-detective" }
variable "github_branch"{ default = "main" }
variable "groq_api_key" {
  description = "Groq API key — set via: terraform apply -var='groq_api_key=YOUR_KEY'"
  sensitive   = true
}
