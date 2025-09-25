package server

import (
	"context"
	"log"

	v1 "github.com/google/osv.dev/go/pkg/api/osv/v1"
	osvschema "github.com/ossf/osv-schema/bindings/go/osvschema"
)

// Server implements the OSV gRPC service.
type Server struct {
	v1.UnimplementedOSVServer
}

// GetVulnById implements the GetVulnById RPC method.
func (s *Server) GetVulnById(ctx context.Context, req *v1.GetVulnByIdParameters) (*osvschema.Vulnerability, error) {
	log.Printf("GetVulnById called with id: %s", req.Id)
	// In a real implementation, you would fetch and return a vulnerability.
	// For a stub, we return an empty one.
	return &osvschema.Vulnerability{}, nil
}

// QueryAffected implements the QueryAffected RPC method.
func (s *Server) QueryAffected(ctx context.Context, req *v1.QueryAffectedParameters) (*v1.VulnerabilityList, error) {
	log.Printf("QueryAffected called with query: %+v", req.Query)
	// In a real implementation, you would query for vulnerabilities.
	// For a stub, we return an empty list.
	return &v1.VulnerabilityList{}, nil
}

// QueryAffectedBatch implements the QueryAffectedBatch RPC method.
func (s *Server) QueryAffectedBatch(ctx context.Context, req *v1.QueryAffectedBatchParameters) (*v1.BatchVulnerabilityList, error) {
	log.Printf("QueryAffectedBatch called with %d queries", len(req.Query.Queries))
	// In a real implementation, you would perform a batch query.
	// For a stub, we return an empty list.
	return &v1.BatchVulnerabilityList{}, nil
}
