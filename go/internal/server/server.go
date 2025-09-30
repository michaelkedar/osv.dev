package server

import (
	"context"
	"errors"
	"strings"

	"cloud.google.com/go/datastore"
	"cloud.google.com/go/storage"
	"github.com/google/osv.dev/go/internal/gcs"
	"github.com/google/osv.dev/go/internal/models"
	"github.com/google/osv.dev/go/logger"
	v1 "github.com/google/osv.dev/go/pkg/api/osv/v1"
	"github.com/ossf/osv-schema/bindings/go/osvschema"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

// Server implements the OSV gRPC service.
type Server struct {
	v1.UnimplementedOSVServer
	dsClient *datastore.Client
}

// NewServer creates a new Server instance.
func NewServer(dsClient *datastore.Client) *Server {
	return &Server{dsClient: dsClient}
}

// GetVulnById implements the GetVulnById RPC method.
func (s *Server) GetVulnById(ctx context.Context, req *v1.GetVulnByIdParameters) (*osvschema.Vulnerability, error) {
	logger.Info("GetVulnById called", "id", req.Id)
	if len(req.Id) > 100 {
		return nil, status.Error(codes.InvalidArgument, "ID too long")
	}

	vuln, err := gcs.GetByID(ctx, req.Id)
	if err != nil {
		if errors.Is(err, storage.ErrObjectNotExist) {
			// Check for aliases.
			query := datastore.NewQuery("AliasGroup").FilterField("bug_ids", "=", req.Id).Limit(1)
			var aliasGroups []*models.AliasGroup
			_, err := s.dsClient.GetAll(ctx, query, &aliasGroups)
			if err != nil {
				logger.Error("datastore.GetAll AliasGroup failed", "err", err)
			}
			if err == nil && len(aliasGroups) > 0 {
				aliases := []string{}
				for _, alias := range aliasGroups[0].BugIDs {
					if alias != req.Id {
						aliases = append(aliases, alias)
					}
				}
				aliasString := strings.Join(aliases, " ")
				return nil, status.Errorf(codes.NotFound, "Vulnerability not found, but the following aliases were: %s", aliasString)
			}

			return nil, status.Error(codes.NotFound, "Vulnerability not found")
		}
		logger.Error("gcs.GetByID failed", "err", err)
		return nil, status.Error(codes.Internal, "failed to get vulnerability")
	}

	return vuln, nil
}

// // QueryAffected implements the QueryAffected RPC method.
// func (s *Server) QueryAffected(ctx context.Context, req *v1.QueryAffectedParameters) (*v1.VulnerabilityList, error) {
// 	logger.Info("QueryAffected called", "query", req.Query)
// 	// In a real implementation, you would query for vulnerabilities.
// 	// For a stub, we return an empty list.
// 	return &v1.VulnerabilityList{}, nil
// }

// // QueryAffectedBatch implements the QueryAffectedBatch RPC method.
// func (s *Server) QueryAffectedBatch(ctx context.Context, req *v1.QueryAffectedBatchParameters) (*v1.BatchVulnerabilityList, error) {
// 	logger.Info("QueryAffectedBatch called", "num_queries", len(req.Query.Queries))
// 	// In a real implementation, you would perform a batch query.
// 	// For a stub, we return an empty list.
// 	return &v1.BatchVulnerabilityList{}, nil
// }
