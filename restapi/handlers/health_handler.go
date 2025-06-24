package handlers

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/AndreasX42/restapi/utils"
	"github.com/gin-gonic/gin"
	"github.com/guregu/dynamo/v2"
)

type HealthHandler struct {
	dynamoDB *dynamo.DB
}

func NewHealthHandler(dynamoDB *dynamo.DB) *HealthHandler {
	return &HealthHandler{
		dynamoDB: dynamoDB,
	}
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status    string                 `json:"status"`
	Timestamp time.Time              `json:"timestamp"`
	Version   string                 `json:"version"`
	Services  map[string]ServiceInfo `json:"services"`
	Uptime    string                 `json:"uptime,omitempty"`
}

// ServiceInfo represents the status of individual services
type ServiceInfo struct {
	Status       string `json:"status"`
	ResponseTime string `json:"response_time,omitempty"`
	Error        string `json:"error,omitempty"`
}

var startTime = time.Now()

// HealthCheck performs comprehensive health check including DynamoDB
func (h *HealthHandler) HealthCheck(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	startCheck := time.Now()
	services := make(map[string]ServiceInfo)

	// Check DynamoDB connectivity
	dynamoStatus := h.checkDynamoDB(ctx)
	services["dynamodb"] = dynamoStatus

	// Determine overall status
	overallStatus := "healthy"
	for _, service := range services {
		if service.Status != "healthy" {
			overallStatus = "unhealthy"
			break
		}
	}

	response := HealthResponse{
		Status:    overallStatus,
		Timestamp: time.Now(),
		Version:   utils.GetEnvWithDefault("APP_VERSION", "1.0.0"),
		Services:  services,
		Uptime:    time.Since(startTime).String(),
	}

	// Set appropriate HTTP status code
	statusCode := http.StatusOK
	if overallStatus == "unhealthy" {
		statusCode = http.StatusServiceUnavailable
	}

	// Add response time
	responseTime := time.Since(startCheck)
	c.Header("X-Response-Time", responseTime.String())

	c.JSON(statusCode, response)
}

// checkDynamoDB tests DynamoDB connectivity by describing all application tables
func (h *HealthHandler) checkDynamoDB(ctx context.Context) ServiceInfo {
	startTime := time.Now()

	// Define all tables used by the application
	tables := map[string]string{
		"users":       utils.GetTableName(os.Getenv("DYNAMODB_USER_TABLE_NAME")),
		"vocab":       utils.GetTableName(os.Getenv("DYNAMODB_VOCAB_TABLE_NAME")),
		"vocab_lists": utils.GetTableName(os.Getenv("DYNAMODB_VOCAB_LIST_TABLE_NAME")),
	}

	var errors []string
	tableStatuses := make(map[string]string)

	// Check each table
	for tableName, fullTableName := range tables {
		table := h.dynamoDB.Table(fullTableName)

		// Try to describe the table to test connectivity and existence
		desc, err := table.Describe().Run(ctx)
		if err != nil {
			errors = append(errors, fmt.Sprintf("%s: %v", tableName, err))
			tableStatuses[tableName] = "error"
		} else {
			tableStatuses[tableName] = string(desc.Status)
		}
	}

	responseTime := time.Since(startTime)

	// Determine overall health
	if len(errors) > 0 {
		return ServiceInfo{
			Status:       "unhealthy",
			ResponseTime: responseTime.String(),
			Error: fmt.Sprintf("Table issues: %s. Statuses: %v",
				strings.Join(errors, "; "), tableStatuses),
		}
	}

	// Check if all tables are ACTIVE
	for tableName, status := range tableStatuses {
		if status != "ACTIVE" {
			return ServiceInfo{
				Status:       "degraded",
				ResponseTime: responseTime.String(),
				Error: fmt.Sprintf("Table %s is %s (not ACTIVE). All statuses: %v",
					tableName, status, tableStatuses),
			}
		}
	}

	return ServiceInfo{
		Status:       "healthy",
		ResponseTime: responseTime.String(),
		Error:        fmt.Sprintf("All tables ACTIVE: %v", tableStatuses),
	}
}
