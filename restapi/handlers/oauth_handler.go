package handlers

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

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
}

func NewOAuthHandler(userService *services.UserService, googleOAuthConfig *oauth2.Config) *OAuthHandler {
	return &OAuthHandler{
		userService:       userService,
		googleOAuthConfig: googleOAuthConfig,
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

	// Store state in cookie for verification
	c.SetCookie("oauthstate", oauthState, 3600, "/", "", false, true)

	// Get OAuth URL
	url := h.googleOAuthConfig.AuthCodeURL(oauthState)

	// TODO: Maybe redirect immediately to the auth url
	c.JSON(http.StatusOK, gin.H{
		"auth_url": url,
		"message":  "Redirect to this URL to authenticate with Google",
	})
}

// GoogleCallback handles the OAuth callback from Google
func (h *OAuthHandler) GoogleCallback(c *gin.Context) {
	// Verify state parameter
	// TODO: is state value validation secure here?
	oauthState, err := c.Cookie("oauthstate")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid state parameter"})
		return
	}

	if c.Query("state") != oauthState {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid OAuth state"})
		return
	}

	// Exchange code for token
	code := c.Query("code")
	if code == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Code not found"})
		return
	}

	token, err := h.googleOAuthConfig.Exchange(context.Background(), code)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Failed to exchange token"})
		return
	}

	// Get user info from Google
	userInfo, err := h.getUserInfoFromGoogle(token.AccessToken)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Failed to get user info"})
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
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Failed to create/login user", "details": gin.H{"error": err.Error()}})
		return
	}

	// Generate JWT token
	jwtToken, err := utils.GenerateJWT(user.ID, user.Username)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not generate token"})
		return
	}

	// Clear the OAuth state cookie
	c.SetCookie("oauthstate", "", -1, "/", "", false, true)

	c.JSON(http.StatusOK, gin.H{
		"message": "Google OAuth login successful",
		"details": gin.H{
			"token":         jwtToken,
			"user_id":       user.ID,
			"username":      user.Username,
			"email":         user.Email,
			"profile_image": user.ProfileImage,
		},
	})
}

// getUserInfoFromGoogle fetches user information from Google using the access token
func (h *OAuthHandler) getUserInfoFromGoogle(accessToken string) (*GoogleUserInfo, error) {
	// Create HTTP request to Google's userinfo endpoint
	req, err := http.NewRequest("GET", "https://www.googleapis.com/oauth2/v2/userinfo", nil)
	if err != nil {
		return nil, err
	}

	// Add authorization header
	req.Header.Add("Authorization", "Bearer "+accessToken)

	// Make the request
	client := &http.Client{}
	resp, err := client.Do(req)
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
