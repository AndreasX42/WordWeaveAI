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
	Status       string            `json:"status"`
	ResponseTime string            `json:"response_time,omitempty"`
	Message      string            `json:"message,omitempty"`
	Error        string            `json:"error,omitempty"`
	Details      map[string]string `json:"details,omitempty"`
}

var startTime = time.Now()

// HealthCheck performs comprehensive health check including DynamoDB
func (h *HealthHandler) HealthCheck(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), HealthRequestTimeout)
	defer cancel()

	startCheck := time.Now()
	services := make(map[string]ServiceInfo)

	// Check DynamoDB connectivity
	dynamoStatus := h.checkDynamoDB(ctx)
	services["dynamodb"] = dynamoStatus

	// Determine overall status
	overallStatus := "healthy"
	for _, service := range services {
		if service.Status == "unhealthy" {
			overallStatus = "unhealthy"
			break
		}
		if service.Status != "healthy" {
			overallStatus = service.Status
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
	if overallStatus != "healthy" {
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
	tableConfigs := map[string]string{
		"users":          "DYNAMODB_USER_TABLE_NAME",
		"vocab":          "DYNAMODB_VOCAB_TABLE_NAME",
		"vocab_media":    "DYNAMODB_VOCAB_MEDIA_TABLE_NAME",
		"vocab_lists":    "DYNAMODB_VOCAB_LIST_TABLE_NAME",
		"ws_connections": "DYNAMODB_CONNECTIONS_TABLE_NAME",
	}

	tables := make(map[string]string, len(tableConfigs))
	var configErrors []string
	for tableName, envKey := range tableConfigs {
		baseName := os.Getenv(envKey)
		if baseName == "" {
			configErrors = append(configErrors, fmt.Sprintf("%s missing %s", tableName, envKey))
			continue
		}
		tables[tableName] = utils.GetTableName(baseName)
	}

	if len(configErrors) > 0 {
		return ServiceInfo{
			Status:       "unhealthy",
			ResponseTime: time.Since(startTime).String(),
			Error:        fmt.Sprintf("DynamoDB table configuration issues: %s", strings.Join(configErrors, "; ")),
		}
	}

	// Use channels to collect results from parallel checks
	type tableResult struct {
		name   string
		status string
		err    error
	}

	resultChan := make(chan tableResult, len(tables))

	// Launch parallel checks for each table
	for tableName, fullTableName := range tables {
		go func(name, fullName string) {
			table := h.dynamoDB.Table(fullName)
			desc, err := table.Describe().Run(ctx)

			result := tableResult{name: name, err: err}
			if err == nil {
				result.status = string(desc.Status)
			}

			resultChan <- result
		}(tableName, fullTableName)
	}

	// Collect results
	var errors []string
	tableStatuses := make(map[string]string)

	for i := 0; i < len(tables); i++ {
		result := <-resultChan
		if result.err != nil {
			errors = append(errors, fmt.Sprintf("%s: %v", result.name, result.err))
			tableStatuses[result.name] = "error"
		} else {
			tableStatuses[result.name] = result.status
		}
	}

	responseTime := time.Since(startTime)

	// Determine overall health
	if len(errors) > 0 {
		return ServiceInfo{
			Status:       "unhealthy",
			ResponseTime: responseTime.String(),
			Error:        fmt.Sprintf("Table issues: %s", strings.Join(errors, "; ")),
			Details:      tableStatuses,
		}
	}

	// Check if all tables are ACTIVE
	for tableName, status := range tableStatuses {
		if status != "ACTIVE" {
			return ServiceInfo{
				Status:       "degraded",
				ResponseTime: responseTime.String(),
				Message:      fmt.Sprintf("Table %s is %s (not ACTIVE)", tableName, status),
				Details:      tableStatuses,
			}
		}
	}

	return ServiceInfo{
		Status:       "healthy",
		ResponseTime: responseTime.String(),
		Message:      "All tables ACTIVE",
		Details:      tableStatuses,
	}
}
