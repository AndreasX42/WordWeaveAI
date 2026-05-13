package handlers

import (
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/utils"
	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
)

// Common timeouts (configured via *_REQUEST_TIMEOUT_MS; defaults preserve prior constants).
var (
	DefaultRequestTimeout = 1 * time.Second
	SearchRequestTimeout  = 1500 * time.Millisecond
	HealthRequestTimeout  = 500 * time.Millisecond
)

func init() {
	DefaultRequestTimeout = utils.EnvMilliseconds("DEFAULT_REQUEST_TIMEOUT_MS", 1000)
	SearchRequestTimeout = utils.EnvMilliseconds("SEARCH_REQUEST_TIMEOUT_MS", 1500)
	HealthRequestTimeout = utils.EnvMilliseconds("HEALTH_REQUEST_TIMEOUT_MS", 500)
}

// HandleValidationError handles validation errors consistently across all handlers
func HandleValidationError(c *gin.Context, err error) {
	if errs, ok := err.(validator.ValidationErrors); ok {
		errMessages := make([]string, 0)
		for _, e := range errs {
			errMessages = append(errMessages, fmt.Sprintf("Field %s failed on the '%s' rule", e.Field(), e.Tag()))
		}
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Validation failed",
			"details": gin.H{
				"errors": errMessages,
			},
		})
		return
	}
	c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
}

// GetPrincipal extracts the authenticated user from the JWT context
func GetPrincipal(c *gin.Context) (*entities.User, error) {
	userPtr, exists := c.Get("principal")
	if !exists {
		return nil, errors.New("principal not set")
	}

	user, ok := userPtr.(*entities.User)
	if !ok {
		return nil, errors.New("principal invalid")
	}

	return user, nil
}
