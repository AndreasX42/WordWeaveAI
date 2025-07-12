package handlers

import (
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
)

// Common timeout constants
const (
	DefaultRequestTimeout = 5 * time.Second
)

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
