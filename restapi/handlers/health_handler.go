package handlers

import (
	"context"
	"net/http"
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

// checkDynamoDB tests DynamoDB connectivity by describing the users table
func (h *HealthHandler) checkDynamoDB(ctx context.Context) ServiceInfo {
	startTime := time.Now()

	tableName := utils.GetTableName("users")
	table := h.dynamoDB.Table(tableName)

	// Try to describe the table to test connectivity
	_, err := table.Describe().Run(ctx)

	responseTime := time.Since(startTime)

	if err != nil {
		return ServiceInfo{
			Status:       "unhealthy",
			ResponseTime: responseTime.String(),
			Error:        err.Error(),
		}
	}

	return ServiceInfo{
		Status:       "healthy",
		ResponseTime: responseTime.String(),
	}

}
