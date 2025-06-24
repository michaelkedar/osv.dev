# The OSV API on Cloud Run
# Adapted from https://github.com/hashicorp/terraform-provider-google/issues/5528#issuecomment-1136040976

resource "google_cloud_run_service" "api_backend2" {
  project  = "michaelkedar-test"
  name     = "osv-grpc-backend-new"
  location = "us-central1"

  template {
    spec {
      containers {
        image = "gcr.io/michaelkedar-test/osv-server:original"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  lifecycle {
    ignore_changes = [
      # To be managed by Cloud Deploy.
      template,
      traffic,
    ]
    prevent_destroy = true
  }
}

variable "_api_descriptor_file" {
  # This isn't actually sensitive, but it's outputted as a massive base64 string which really floods the plan output.
  sensitive = true
  type      = string
  default   = "api/api_descriptor.pb"
}

resource "google_endpoints_service" "grpc_service2" {
  project      = "michaelkedar-test"
  service_name = "osv-grpc-v1-new-784002525137.us-central1.run.app"
  grpc_config = templatefile(
    "api/api_config.tftpl",
    {
      service_name      = "osv-grpc-v1-new-784002525137.us-central1.run.app",
      backend_url       = replace(google_cloud_run_service.api_backend2.status[0].url, "https://", "grpcs://")
      # backend_batch_url = replace(google_cloud_run_v2_service.api_backend_batch.uri, "https://", "grpcs://")
  })
  protoc_output_base64 = filebase64(var._api_descriptor_file)
}

resource "google_project_service" "grpc_service_api2" {
  project = "michaelkedar-test"
  service = google_endpoints_service.grpc_service2.service_name
}


data "external" "esp_version" {
  program = ["bash", "${path.module}/../../modules/osv/scripts/esp_full_version", "2.51.0"]
}

resource "null_resource" "grpc_proxy_image2" {
  triggers = {
    # Update this when the config changes or there is a new ESP image
    config_id   = google_endpoints_service.grpc_service2.config_id
    esp_version = data.external.esp_version.result.esp_full_version
  }

  # Script obtained from:
  # https://github.com/GoogleCloudPlatform/esp-v2/blob/master/docker/serverless/gcloud_build_image
  provisioner "local-exec" {
    command = <<EOS
      bash ${path.module}/../../modules/osv/scripts/gcloud_build_image \
        -s osv-grpc-v1-new-784002525137.us-central1.run.app \
        -c ${google_endpoints_service.grpc_service2.config_id} \
        -p michaelkedar-test \
        -v 2.51.0
    EOS
  }
}

data "google_container_registry_image" "api2" {
  project = "michaelkedar-test"
  name    = "endpoints-runtime-serverless"
  tag = format(
    "%s-%s-%s",
    data.external.esp_version.result.esp_full_version,
    "osv-grpc-v1-new-784002525137.us-central1.run.app",
    google_endpoints_service.grpc_service2.config_id
  )
  depends_on = [null_resource.grpc_proxy_image2]
}


resource "google_cloud_run_service" "api2" {
  project  = "michaelkedar-test"
  name     = "osv-grpc-v1-new"
  location = "us-central1"

  template {
    spec {
      containers {
        image = data.google_container_registry_image.api2.image_url
        env {
          name  = "ESPv2_ARGS"
          value = "^++^--transcoding_preserve_proto_field_names++--envoy_connection_buffer_limit_bytes=104857600++--underscores_in_headers++--cors_preset=basic++--cors_allow_methods=GET,POST,OPTIONS"
        }
        resources {
          limits = {
            "cpu"    = "1000m"
            "memory" = "2Gi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  # lifecycle {
  #   prevent_destroy = true
  # }
}

# resource "google_cloud_run_domain_mapping" "api" {
#   project  = var.project_id
#   name     = var.api_url
#   location = google_cloud_run_service.api.location
#   metadata {
#     namespace = var.project_id
#   }
#   spec {
#     route_name = google_cloud_run_service.api.name
#   }
# }
