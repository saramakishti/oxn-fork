# Set the provider
provider "google" {
  credentials = file(var.path_to_json_service_account)
  project     = var.project_id
  region      = var.region
}

resource "random_uuid" "bucket_id" {}

# Create a Google Cloud Storage bucket
resource "google_storage_bucket" "data_bucket" {
  name          = "${random_uuid.bucket_id.result}-${var.storage_name}"
  location      = "EU"
  storage_class = "STANDARD"
}
