# Set the provider
provider "google" {
  credentials = file("<path-to-your-service-account-json>")
  project     = "<your-project-id>"
  region      = "us-central1" # Adjust as needed
}

# Create a Google Cloud Storage bucket
resource "google_storage_bucket" "my_bucket" {
  name          = ""
  location      = "US"
  storage_class = "STANDARD"
}

# Assign permissions to the service account
resource "google_storage_bucket_iam_member" "bucket_access" {
  bucket = google_storage_bucket.my_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:<your-service-account-email>"
}