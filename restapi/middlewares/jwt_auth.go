package middlewares

import (
	"log"
	"os"
	"strconv"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/utils"
	jwt "github.com/appleboy/gin-jwt/v2"
	"github.com/gin-gonic/gin"
)

const identityKey = "user_id"

// JWTMiddleware creates a new JWT middleware with the UserService
func JWTMiddleware(userService *services.UserService) (*jwt.GinJWTMiddleware, error) {
	// Get JWT configuration from environment
	secretKey := os.Getenv("JWT_SECRET_KEY")
	if secretKey == "" || len(secretKey) < 32 {
		log.Fatal("JWT_SECRET_KEY environment variable is required and must be at least 32 characters long")
	}

	expirationMinutes, err := strconv.ParseInt(os.Getenv("JWT_EXPIRATION_TIME"), 10, 64)
	if err != nil || expirationMinutes <= 0 {
		log.Fatal("JWT_EXPIRATION_TIME environment variable is required")
	}

	maxRefreshHours := utils.EnvPositiveInt("JWT_MAX_REFRESH_HOURS", 24)
	authMiddleware, err := jwt.New(&jwt.GinJWTMiddleware{
		Realm:       "restapi",
		Key:         []byte(secretKey),
		Timeout:     time.Duration(expirationMinutes) * time.Minute,
		MaxRefresh:  time.Duration(maxRefreshHours) * time.Hour,
		IdentityKey: identityKey,

		Authenticator: func(c *gin.Context) (any, error) {
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

			// Store user in context for LoginResponse function
			c.Set("user", user)

			return user, nil
		},

		Authorizator: func(data any, c *gin.Context) bool {
			if user, ok := data.(*entities.User); ok {
				// Set the user object in the context for handlers to use
				c.Set("principal", user)
				return true
			}
			return false
		},

		PayloadFunc: func(data any) jwt.MapClaims {
			if user, ok := data.(*entities.User); ok {
				return jwt.MapClaims{
					identityKey: user.ID,
				}
			}
			return jwt.MapClaims{}
		},

		IdentityHandler: func(c *gin.Context) any {
			claims := jwt.ExtractClaims(c)
			userID, ok := claims[identityKey].(string)
			if !ok {
				return nil
			}

			user, err := userService.GetUserByID(c.Request.Context(), userID)
			if err != nil {
				return nil
			}

			return user
		},

		Unauthorized: func(c *gin.Context, code int, message string) {
			c.JSON(code, gin.H{"message": "Unauthorized", "details": gin.H{"error": message}})
		},

		LoginResponse: func(c *gin.Context, code int, token string, expire time.Time) {
			// Get the user from the context
			user, exists := c.Get("user")
			if !exists {
				c.JSON(code, gin.H{
					"code":   code,
					"token":  token,
					"expire": expire.Format(time.RFC3339),
				})
				return
			}

			// Cast to User entity
			userEntity, ok := user.(*entities.User)
			if !ok {
				c.JSON(code, gin.H{
					"code":   code,
					"token":  token,
					"expire": expire.Format(time.RFC3339),
				})
				return
			}

			// Return token along with user information
			c.JSON(code, gin.H{
				"user": gin.H{
					"id":             userEntity.ID,
					"username":       userEntity.Username,
					"email":          userEntity.Email,
					"confirmedEmail": userEntity.ConfirmedEmail,
					"isAdmin":        userEntity.IsAdmin,
					"profileImage":   userEntity.ProfileImage,
					"createdAt":      userEntity.CreatedAt.Format(time.RFC3339),
				},
				"token": token,
			})
		},

		TokenLookup:   "header: Authorization, cookie: jwt",
		TokenHeadName: "Bearer",
		TimeFunc:      time.Now,
	})

	if err != nil {
		return nil, err
	}

	return authMiddleware, nil
}
