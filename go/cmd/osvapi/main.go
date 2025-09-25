package main

import (
	"log"
	"net"

	"google.golang.org/grpc"

	"github.com/google/osv.dev/go/internal/server"
	v1 "github.com/google/osv.dev/go/pkg/api/osv/v1"
)

const (
	port = ":8080"
)

func main() {
	log.Printf("Starting OSV API server on port %s", port)

	lis, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	s := grpc.NewServer()
	v1.RegisterOSVServer(s, &server.Server{})

	log.Printf("Server listening at %v", lis.Addr())
	if err := s.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
