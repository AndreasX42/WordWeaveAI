package handlers

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/utils"
	jwt "github.com/appleboy/gin-jwt/v2"
	"github.com/gin-gonic/gin"
	"golang.org/x/oauth2"
)

const (
	defaultFrontendOrigin = "http://localhost:4200"
	defaultProdOrigin     = "https://wordweave.xyz"

	googleUserInfoURL = "https://www.googleapis.com/oauth2/v2/userinfo"
	googleAPITimeout  = 3 * time.Second

	cookiePath          = "/"
	oauthStateCookie    = "oauthstate"
	jwtCookie           = "jwt"
	stateCookieMaxAge   = 120 // seconds; survives the OAuth round-trip only
	jwtCookieMaxAge     = 120 // seconds; long enough for the frontend to read and store the token
	frontendCallbackPath = "/auth/callback"
)

var defaultAllowedOrigins = []string{defaultFrontendOrigin, defaultProdOrigin}

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
	authMiddleware    *jwt.GinJWTMiddleware
	httpClient        *http.Client
}

func NewOAuthHandler(userService *services.UserService, googleOAuthConfig *oauth2.Config, authMiddleware *jwt.GinJWTMiddleware) *OAuthHandler {
	return &OAuthHandler{
		userService:       userService,
		googleOAuthConfig: googleOAuthConfig,
		authMiddleware:    authMiddleware,
		httpClient:        &http.Client{Timeout: googleAPITimeout},
	}
}

// isHTTPS reports whether the Secure cookie flag should be set (production only).
func isHTTPS() bool {
	return os.Getenv("GIN_MODE") == "release"
}

// setCookie sets an HttpOnly cookie with SameSite=Lax and Secure flag derived from the runtime mode.
func (h *OAuthHandler) setCookie(c *gin.Context, name, value string, maxAgeSecs int) {
	c.SetSameSite(http.SameSiteLaxMode)
	c.SetCookie(name, value, maxAgeSecs, cookiePath, "", isHTTPS(), true)
}

// allowedFrontendOrigins returns the set of whitelisted redirect targets from env or built-in defaults.
func allowedFrontendOrigins() []string {
	return utils.ParseCommaSeparatedList(os.Getenv("FRONTEND_ALLOWED_URLS"), defaultAllowedOrigins)
}

// safeRedirectOrigin returns FRONTEND_URL if it is in the allowed list; otherwise the first allowed entry.
// This prevents open-redirect attacks by never redirecting to an arbitrary caller-supplied URL.
func safeRedirectOrigin() string {
	want := utils.GetEnvWithDefault("FRONTEND_URL", defaultFrontendOrigin)
	allowed := allowedFrontendOrigins()
	for _, a := range allowed {
		if want == a {
			return want
		}
	}
	if len(allowed) > 0 {
		return allowed[0]
	}
	return defaultFrontendOrigin
}

// callbackURL builds an absolute frontend callback URL.
func callbackURL(base string, params url.Values) string {
	u := fmt.Sprintf("%s%s", strings.TrimSuffix(base, "/"), frontendCallbackPath)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	return u
}

func generateOAuthState() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return base64.URLEncoding.EncodeToString(b)
}

// GoogleLogin initiates the Google OAuth 2.0 flow.
func (h *OAuthHandler) GoogleLogin(c *gin.Context) {
	state := generateOAuthState()
	h.setCookie(c, oauthStateCookie, state, stateCookieMaxAge)
	c.Redirect(http.StatusFound, h.googleOAuthConfig.AuthCodeURL(state))
}

// GoogleCallback completes the OAuth flow: validates state, exchanges the code,
// fetches user info, upserts the user, and issues a short-lived JWT handoff cookie.
func (h *OAuthHandler) GoogleCallback(c *gin.Context) {
	storedState, err := c.Cookie(oauthStateCookie)
	if err != nil {
		h.redirectError(c, "invalid_state", "OAuth state parameter missing or invalid")
		return
	}
	if c.Query("state") != storedState {
		h.redirectError(c, "invalid_state", "OAuth state parameter mismatch")
		return
	}
	if oauthErr := c.Query("error"); oauthErr != "" {
		desc := c.Query("error_description")
		if desc == "" {
			desc = "OAuth authorization failed"
		}
		h.redirectError(c, oauthErr, desc)
		return
	}

	code := c.Query("code")
	if code == "" {
		h.redirectError(c, "missing_code", "Authorization code not found")
		return
	}

	token, err := h.googleOAuthConfig.Exchange(c.Request.Context(), code)
	if err != nil {
		h.redirectError(c, "token_exchange_failed", "Failed to exchange authorization code")
		return
	}

	userInfo, err := h.fetchGoogleUserInfo(c.Request.Context(), token.AccessToken)
	if err != nil {
		h.redirectError(c, "user_info_failed", "Failed to fetch user information")
		return
	}

	// TODO: sync profile image updates on repeat logins
	user, err := h.userService.CreateOrLoginOAuthUser(c.Request.Context(), services.OAuthUserRequest{
		GoogleID:     userInfo.ID,
		Email:        userInfo.Email,
		Name:         userInfo.Name,
		Username:     userInfo.GivenName,
		ProfileImage: userInfo.Picture,
	})
	if err != nil {
		h.redirectError(c, "user_creation_failed", "Failed to create or login user")
		return
	}

	jwtToken, _, err := h.authMiddleware.TokenGenerator(user)
	if err != nil {
		h.redirectError(c, "token_generation_failed", "Could not generate authentication token")
		return
	}

	h.setCookie(c, oauthStateCookie, "", -1) // clear state cookie
	h.setCookie(c, jwtCookie, jwtToken, jwtCookieMaxAge)

	// Redirect with a minimal success signal; the frontend calls /api/auth/me to get user data.
	c.Redirect(http.StatusFound, callbackURL(safeRedirectOrigin(), url.Values{"success": {"true"}}))
}

func (h *OAuthHandler) fetchGoogleUserInfo(ctx context.Context, accessToken string) (*GoogleUserInfo, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, googleUserInfoURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+accessToken)

	resp, err := h.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("google userinfo returned %s", resp.Status)
	}

	var userInfo GoogleUserInfo
	if err := json.NewDecoder(resp.Body).Decode(&userInfo); err != nil {
		return nil, fmt.Errorf("decoding google userinfo: %w", err)
	}
	return &userInfo, nil
}

func (h *OAuthHandler) redirectError(c *gin.Context, code, description string) {
	params := url.Values{}
	params.Set("error", code)
	params.Set("error_description", description)
	c.Redirect(http.StatusFound, callbackURL(safeRedirectOrigin(), params))
}
