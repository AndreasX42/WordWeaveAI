package middlewares

import (
	"log"
	"os"
	"time"

	"github.com/AndreasX42/restapi/utils"
	"github.com/gin-contrib/cors"
)

var (
	corsDefaultOrigins = []string{
		"http://localhost:4200",
		"http://127.0.0.1:4200",
	}
	corsAllowedMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	corsAllowedHeaders = []string{"Content-Type", "Accept", "Authorization"}
	corsExposedHeaders = []string{"Content-Length", "Authorization", "Content-Type"}
)

// GetCORSConfig builds the CORS policy from environment variables.
// CORS_ALLOWED_ORIGINS is required in production (GIN_MODE=release).
func GetCORSConfig() cors.Config {
	origins := utils.ParseCommaSeparatedList(os.Getenv("CORS_ALLOWED_ORIGINS"), corsDefaultOrigins)

	if len(origins) == 0 || (os.Getenv("GIN_MODE") == "release" && os.Getenv("CORS_ALLOWED_ORIGINS") == "") {
		log.Fatal("CORS_ALLOWED_ORIGINS must be set in production")
	}

	return cors.Config{
		AllowAllOrigins:  false,
		AllowOrigins:     origins,
		AllowMethods:     corsAllowedMethods,
		AllowHeaders:     corsAllowedHeaders,
		ExposeHeaders:    corsExposedHeaders,
		AllowCredentials: true,
		MaxAge:           time.Duration(utils.EnvPositiveInt("CORS_MAX_AGE_HOURS", 12)) * time.Hour,
	}
}
