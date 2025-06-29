package handlers

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/utils"
	"github.com/gin-gonic/gin"
	"golang.org/x/oauth2"
)

// GoogleUserInfo represents the user information from Google
type GoogleUserInfo struct {
	ID            string `json:"id"`
	Email         string `json:"email"`
	VerifiedEmail bool   `json:"verified_email"`
	Name          string `json:"name"`
	GivenName     string `json:"given_name"`
	FamilyName    string `json:"family_name"`
	Picture       string `json:"picture"`
	Locale        string `json:"locale"`
}

type OAuthHandler struct {
	userService       *services.UserService
	googleOAuthConfig *oauth2.Config
	httpClient        *http.Client
}

func NewOAuthHandler(userService *services.UserService, googleOAuthConfig *oauth2.Config) *OAuthHandler {
	return &OAuthHandler{
		userService:       userService,
		googleOAuthConfig: googleOAuthConfig,
		httpClient: &http.Client{
			Timeout: time.Second * 10, // 10 second timeout for Google API calls
		},
	}
}

// generateStateOauthCookie generates a random state string for OAuth security
func generateStateOauthCookie() string {
	b := make([]byte, 16)
	rand.Read(b)
	return base64.URLEncoding.EncodeToString(b)
}

// GoogleLogin initiates the Google OAuth flow
func (h *OAuthHandler) GoogleLogin(c *gin.Context) {
	// Generate random state
	oauthState := generateStateOauthCookie()

	// Store state in cookie for verification with security flags
	isProduction := os.Getenv("GIN_MODE") == "release"
	c.SetSameSite(http.SameSiteLaxMode) // CSRF protection
	c.SetCookie("oauthstate", oauthState, 120, "/", "", isProduction, true)

	// Get OAuth URL
	url := h.googleOAuthConfig.AuthCodeURL(oauthState)

	// Direct redirect to Google OAuth
	c.Redirect(http.StatusFound, url)
}

// GoogleCallback handles the OAuth callback from Google
func (h *OAuthHandler) GoogleCallback(c *gin.Context) {
	// Verify state parameter
	oauthState, err := c.Cookie("oauthstate")
	if err != nil {
		h.redirectToFrontendWithError(c, "invalid_state", "OAuth state parameter missing or invalid")
		return
	}

	if c.Query("state") != oauthState {
		h.redirectToFrontendWithError(c, "invalid_state", "OAuth state parameter mismatch")
		return
	}

	// Check for OAuth errors (user denied permission, etc.)
	if oauthError := c.Query("error"); oauthError != "" {
		errorDescription := c.Query("error_description")
		if errorDescription == "" {
			errorDescription = "OAuth authorization failed"
		}
		h.redirectToFrontendWithError(c, oauthError, errorDescription)
		return
	}

	// Exchange code for token
	code := c.Query("code")
	if code == "" {
		h.redirectToFrontendWithError(c, "missing_code", "Authorization code not found")
		return
	}

	token, err := h.googleOAuthConfig.Exchange(c.Request.Context(), code)
	if err != nil {
		h.redirectToFrontendWithError(c, "token_exchange_failed", "Failed to exchange authorization code")
		return
	}

	// Get user info from Google
	userInfo, err := h.getUserInfoFromGoogle(c.Request.Context(), token.AccessToken)
	if err != nil {
		h.redirectToFrontendWithError(c, "user_info_failed", "Failed to fetch user information")
		return
	}

	// Create or login user
	oauthReq := services.OAuthUserRequest{
		GoogleID:     userInfo.ID,
		Email:        userInfo.Email,
		Name:         userInfo.Name,
		Username:     userInfo.GivenName,
		ProfileImage: userInfo.Picture,
	}

	// TODO: Update user info if needed (like profile image)
	user, err := h.userService.CreateOrLoginOAuthUser(c.Request.Context(), oauthReq)
	if err != nil {
		h.redirectToFrontendWithError(c, "user_creation_failed", "Failed to create or login user")
		return
	}

	// Generate JWT token
	jwtToken, err := utils.GenerateJWT(user.ID, user.Username)
	if err != nil {
		h.redirectToFrontendWithError(c, "token_generation_failed", "Could not generate authentication token")
		return
	}

	// Clear the OAuth state cookie
	isProduction := os.Getenv("GIN_MODE") == "release"
	c.SetSameSite(http.SameSiteLaxMode) // CSRF protection
	c.SetCookie("oauthstate", "", -1, "/", "", isProduction, true)

	// Store JWT token in secure HTTP-only cookie (most secure approach)
	c.SetCookie("jwt", jwtToken, 120, "/", "", isProduction, true)

	// Redirect to frontend with minimal success indicator - no user data in URL or cookies
	// Frontend will call /api/auth/me endpoint to get user info using the auth cookie
	redirectURL := fmt.Sprintf("%s/auth/callback?success=true", h.validateAndGetFrontendURL())

	// Redirect to frontend
	c.Redirect(http.StatusFound, redirectURL)
}

// getUserInfoFromGoogle fetches user information from Google using the access token
func (h *OAuthHandler) getUserInfoFromGoogle(ctx context.Context, accessToken string) (*GoogleUserInfo, error) {
	// Create HTTP request to Google's userinfo endpoint with context
	req, err := http.NewRequestWithContext(ctx, "GET", "https://www.googleapis.com/oauth2/v2/userinfo", nil)
	if err != nil {
		return nil, err
	}

	// Add authorization header
	req.Header.Add("Authorization", "Bearer "+accessToken)

	// Make the request using reusable HTTP client
	resp, err := h.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to get user info: %s", resp.Status)
	}

	// Read and parse response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var userInfo GoogleUserInfo
	if err := json.Unmarshal(body, &userInfo); err != nil {
		return nil, err
	}

	return &userInfo, nil
}

// getFrontendURL returns the frontend URL from environment or default
func (h *OAuthHandler) getFrontendURL() string {
	frontendURL := os.Getenv("FRONTEND_URL")
	if frontendURL == "" {
		frontendURL = "http://localhost:4200"
	}
	return frontendURL
}

// validateAndGetFrontendURL validates frontend URL against allowed list to prevent open redirects
func (h *OAuthHandler) validateAndGetFrontendURL() string {
	frontendURL := h.getFrontendURL()

	// Define allowed frontend URLs (prevent open redirect attacks)
	allowedURLs := []string{
		"http://localhost:4200",
	}

	// Validate against allowed list
	for _, allowed := range allowedURLs {
		if frontendURL == allowed {
			return frontendURL
		}
	}

	// If not in allowed list, use safe default
	return "http://localhost:4200"
}

// redirectToFrontendWithError redirects to frontend with error parameters
func (h *OAuthHandler) redirectToFrontendWithError(c *gin.Context, errorType, errorDescription string) {
	baseURL := h.validateAndGetFrontendURL()
	params := url.Values{}
	params.Add("error", errorType)
	params.Add("error_description", errorDescription)

	redirectURL := fmt.Sprintf("%s/auth/callback?%s", baseURL, params.Encode())
	c.Redirect(http.StatusFound, redirectURL)
}
