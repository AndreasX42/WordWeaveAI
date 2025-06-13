package middlewares

import (
	"log"
	"os"
	"strconv"
	"time"

	"github.com/AndreasX42/wordweave-go/domain/entities"
	"github.com/AndreasX42/wordweave-go/domain/services"
	jwt "github.com/appleboy/gin-jwt/v2"
	"github.com/gin-gonic/gin"
)

var identityKey = "user_id"

// JWTMiddleware creates a new JWT middleware with the UserService
func JWTMiddleware(userService *services.UserService) (*jwt.GinJWTMiddleware, error) {
	// Get JWT configuration from environment
	secretKey := os.Getenv("JWT_SECRET_KEY")
	if secretKey == "" {
		log.Fatal("JWT_SECRET_KEY environment variable is required")
	}

	expirationMinutes, err := strconv.ParseInt(os.Getenv("JWT_EXPIRATION_TIME"), 10, 64)
	if err != nil || expirationMinutes < 0 {
		log.Fatal("JWT_EXPIRATION_TIME environment variable is required")
	}

	authMiddleware, err := jwt.New(&jwt.GinJWTMiddleware{
		Realm:       "wordweave",
		Key:         []byte(secretKey),
		Timeout:     time.Duration(expirationMinutes) * time.Minute,
		MaxRefresh:  time.Duration(12) * time.Hour,
		IdentityKey: identityKey,

		Authenticator: func(c *gin.Context) (interface{}, error) {
			var loginVals struct {
				Email    string `json:"email" binding:"required,email"`
				Password string `json:"password" binding:"required,min=8"`
			}
			if err := c.ShouldBindJSON(&loginVals); err != nil {
				return nil, jwt.ErrMissingLoginValues
			}

			// Use existing UserService to authenticate
			loginReq := services.LoginUserRequest{
				Email:    loginVals.Email,
				Password: loginVals.Password,
			}

			user, err := userService.LoginUser(c.Request.Context(), loginReq)
			if err != nil {
				return nil, err
			}

			return user, nil
		},

		Authorizator: func(data interface{}, c *gin.Context) bool {
			if user, ok := data.(*entities.User); ok {
				// Set the user object in the context for handlers to use
				c.Set("principal", user)
				return true
			}
			return false
		},

		PayloadFunc: func(data interface{}) jwt.MapClaims {
			if user, ok := data.(*entities.User); ok {
				return jwt.MapClaims{
					identityKey: user.ID,
				}
			}
			return jwt.MapClaims{}
		},

		IdentityHandler: func(c *gin.Context) interface{} {
			claims := jwt.ExtractClaims(c)
			userID := claims[identityKey].(string)
			user, err := userService.GetUserByID(c.Request.Context(), userID)
			if err != nil {
				return nil
			}
			return user
		},

		Unauthorized: func(c *gin.Context, code int, message string) {
			c.JSON(code, gin.H{"message": "Unauthorized", "details": gin.H{"error": message}})
		},

		TokenLookup:   "header: Authorization, query: token, cookie: jwt",
		TokenHeadName: "Bearer",
		TimeFunc:      time.Now,
	})

	if err != nil {
		return nil, err
	}

	return authMiddleware, nil
}
