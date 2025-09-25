# V1 API server

The API server runs on Cloud Run with Cloud Endpoints.

# GRPC and service configuration

The canonical Protobuf API definition is located at `api/proto/osv/v1/osv_service_v1.proto`.

To generate the Python gRPC stubs from the API definition, run the `build-protos` target from the top-level `Makefile` in the root of the repository:

```sh
make build-protos
```

## Deploy service proxy

Deployment is handled through terraform.

`api_descriptor.pb` is symlinked to inside `deployment/terraform/environments/oss-vdb[-test]/api/`,
Make any desired changes to `api_config.tftpl` in same folder.

`terraform plan` and `terraform apply` are automatically run on `oss-vdb-test` on pushes to the master branch.

For `oss-vdb`, terraform is run as part of the weekly release process.

## Deploy endpoints configuration for integration tests

The Cloud Endpoints service that is required for the unit tests to run is **not** automatically deployed (to allow for testing of proto changes). The testing service is `api-test.osv.dev` on the `oss-vdb` project.

The configuration for this service is located in this directory `api_config_test.yaml`. To deploy changes, use the following command:

```sh
gcloud endpoints services deploy api_descriptor.pb api_config_test.yaml --project=oss-vdb
```
