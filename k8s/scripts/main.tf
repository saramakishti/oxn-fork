variable "project_id" {
  description = "GCP project ID"
  type        = string
}

# random suffix
resource "random_id" "bucket_suffix" {
  byte_length = 4
}


provider "google" {
  project = var.project_id
  region  = "europe-west1-b"       
}

# Create a GCS bucket for the kOps state store
resource "google_storage_bucket" "kops_state_store_oxn" {
  name     = "kops-state-store-${random_id.bucket_suffix.hex}"
  location = "EU"
  force_destroy = true                # allows bucket to be destroyed without emptying

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 2                          # auto-delete after 2 days
    }
  }
}

# output the bucket name for reference
output "kops_state_store_bucket_name" {
  value = google_storage_bucket.kops_state_store_oxn.name
}

