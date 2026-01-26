variable "region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Unique name for the S3 bucket"
  type        = string
}

variable "environment" {
  description = "Environment name"
  default     = "dev"
}
