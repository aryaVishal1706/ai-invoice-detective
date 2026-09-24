terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Store Terraform state in S3 so it persists between GitHub Actions runs
  backend "s3" {
    bucket = "ai-invoice-detective-tfstate-723146859876"
    key    = "terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}
