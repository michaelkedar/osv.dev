package gcs

import (
	"context"
	"fmt"
	"io"
	"log"
	"os"
	"path"

	"cloud.google.com/go/storage"
	"google.golang.org/protobuf/proto"

	osvschema "github.com/ossf/osv-schema/bindings/go/osvschema"
)

const (
	vulnPBPath = "all/pb/"
)

var (
	storageClient *storage.Client
)

func init() {
	var err error
	storageClient, err = storage.NewClient(context.Background())
	if err != nil {
		log.Fatalf("Failed to create storage client: %v", err)
	}
}

// getOSVBucket returns a handle to the GCS bucket where OSV vulnerabilities are stored.
func getOSVBucket() (*storage.BucketHandle, error) {
	bucketName := os.Getenv("OSV_VULNERABILITIES_BUCKET")
	if bucketName == "" {
		return nil, fmt.Errorf("OSV_VULNERABILITIES_BUCKET environment variable not set")
	}
	return storageClient.Bucket(bucketName), nil
}

// GetByID fetches an OSV record from the GCS bucket by its ID.
func GetByID(ctx context.Context, vulnID string) (*osvschema.Vulnerability, error) {
	bucket, err := getOSVBucket()
	if err != nil {
		return nil, fmt.Errorf("failed to get OSV bucket: %w", err)
	}

	objPath := path.Join(vulnPBPath, vulnID+".pb")
	reader, err := bucket.Object(objPath).NewReader(ctx)
	if err != nil {
		if err == storage.ErrObjectNotExist {
			log.Printf("Vulnerability %s not found in GCS", vulnID)
			return nil, err // Return the original error to be handled by the caller.
		}
		return nil, fmt.Errorf("failed to create reader for GCS object %s: %w", objPath, err)
	}
	defer reader.Close()

	data, err := io.ReadAll(reader)
	if err != nil {
		return nil, fmt.Errorf("failed to read GCS object %s: %w", objPath, err)
	}

	var vuln osvschema.Vulnerability
	if err := proto.Unmarshal(data, &vuln); err != nil {
		return nil, fmt.Errorf("failed to unmarshal vulnerability protobuf for %s: %w", vulnID, err)
	}

	return &vuln, nil
}
