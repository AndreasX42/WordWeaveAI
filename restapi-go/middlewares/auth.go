package middlewares

import (
	"net/http"
	"strings"

	"github.com/AndreasX42/wordweave-go/domain/services"
	"github.com/AndreasX42/wordweave-go/utils"
	"github.com/gin-gonic/gin"
)

func Authentication(userService *services.UserService) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.Request.Header.Get("Authorization")

		if authHeader == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized", "details": gin.H{"error": "No bearer token provided"}})
			return
		}

		parts := strings.Split(authHeader, " ")

		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" || parts[1] == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized", "details": gin.H{"error": "Invalid bearer token format"}})
			return
		}

		token := parts[1]

		userId, err := utils.VerifyJWT(token)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized", "details": gin.H{"error": "Invalid token"}})
			return
		}

		user, err := userService.GetUserByID(c.Request.Context(), userId)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized", "details": gin.H{"error": "User not found"}})
			return
		}

		if err := user.IsEligibleForLogin(); err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized", "details": gin.H{"error": err.Error()}})
			return
		}

		c.Set("principal", user)
		c.Next()
	}
}
