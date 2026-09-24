variable "region" {
  default     = "ap-south-1"
  description = "AWS region — Mumbai"
}

variable "project" {
  default     = "ai-invoice-detective"
  description = "Project name — used as prefix for all AWS resources"
}

variable "groq_api_key" {
  description = "Groq API key — passed via GitHub Secret GROQ_API_KEY"
  sensitive   = true
}
