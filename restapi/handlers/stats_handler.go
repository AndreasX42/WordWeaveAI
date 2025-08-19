package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/AndreasX42/restapi/domain/services"
	"github.com/gin-gonic/gin"
)

// StatsHandler handles system statistics endpoints
type StatsHandler struct {
	statsService *services.StatsService
}

// NewStatsHandler creates a new stats handler
func NewStatsHandler(statsService *services.StatsService) *StatsHandler {
	return &StatsHandler{
		statsService: statsService,
	}
}

// StatsResponse represents the API response for system statistics
type StatsResponse struct {
	Status string                `json:"status"`
	Data   *services.SystemStats `json:"data"`
}

// GetSystemStats returns app statistics
func (h *StatsHandler) GetSystemStats(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), DefaultRequestTimeout)
	defer cancel()

	startTime := time.Now()

	// Get system statistics
	stats, err := h.statsService.GetSystemStats(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  "error",
			"message": "Failed to retrieve system statistics",
			"error":   err.Error(),
		})
		return
	}

	// Add response time header
	responseTime := time.Since(startTime)
	c.Header("X-Response-Time", responseTime.String())

	// Return successful response
	c.JSON(http.StatusOK, StatsResponse{
		Status: "success",
		Data:   stats,
	})
}
