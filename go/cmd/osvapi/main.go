package main

import (
	"context"
	"errors"
	"log"
	"net"
	"os"

	"cloud.google.com/go/compute/metadata"
	"cloud.google.com/go/datastore"
	"google.golang.org/grpc"

	"github.com/google/osv.dev/go/internal/server"
	v1 "github.com/google/osv.dev/go/pkg/api/osv/v1"
)

const (
	port = ":8000"
)

func main() {
	log.Printf("Starting OSV API server on port %s", port)

	ctx := context.Background()
	proj := os.Getenv("GOOGLE_CLOUD_PROJECT")
	if proj == "" {
		err := errors.New("GOOGLE_CLOUD_PROJECT environment variable must be set")
		if metadata.OnGCE() {
			proj, err = metadata.ProjectIDWithContext(ctx)
		}
		if err != nil {
			log.Fatalf("Failed to get project ID: %v", err)
		}
	}

	dsClient, err := datastore.NewClient(ctx, proj)
	if err != nil {
		log.Fatalf("Failed to create datastore client: %v", err)
	}
	defer dsClient.Close()

	lis, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	s := grpc.NewServer()
	v1.RegisterOSVServer(s, server.NewServer(dsClient))

	log.Printf("Server listening at %v", lis.Addr())
	if err := s.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
