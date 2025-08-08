package handlers

import (
	"net/http"
	"time"

	"github.com/AndreasX42/restapi/domain/services"
	jwt "github.com/appleboy/gin-jwt/v2"
	"github.com/gin-gonic/gin"
)

type UserHandler struct {
	userService    *services.UserService
	authMiddleware *jwt.GinJWTMiddleware
}

func NewUserHandler(userService *services.UserService, authMiddleware *jwt.GinJWTMiddleware) *UserHandler {
	return &UserHandler{
		userService:    userService,
		authMiddleware: authMiddleware,
	}
}

type RegisterRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Username string `json:"username" binding:"required,min=3"`
	Password string `json:"password" binding:"required,min=8"`
}

type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required,min=8"`
}

type ConfirmEmailRequest struct {
	Email string `json:"email" binding:"required,email"`
	Code  string `json:"code" binding:"required,min=6"`
}

type ResetPasswordRequest struct {
	Email string `json:"email" binding:"required,email"`
}

type ResendConfirmationRequest struct {
	Email string `json:"email" binding:"required,email"`
}

type UpdateRequest struct {
	Username string `json:"username" binding:"required,min=3"`
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"omitempty,min=8"`
}

func (h *UserHandler) Register(c *gin.Context) {
	var req RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	serviceReq := services.RegisterUserRequest{
		Email:    req.Email,
		Username: req.Username,
		Password: req.Password,
	}

	user, err := h.userService.RegisterUser(c.Request.Context(), serviceReq)
	if err != nil {
		statusCode := getErrorStatusCode(err)
		c.JSON(statusCode, gin.H{"message": "Registration failed", "details": gin.H{"error": err.Error()}})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Registration successful. Check your email for the confirmation code",
		"details": gin.H{
			"user_id":  user.ID,
			"username": user.Username,
			"email":    user.Email,
		},
	})
}

func (h *UserHandler) Login(c *gin.Context) {
	var req LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	serviceReq := services.LoginUserRequest{
		Email:    req.Email,
		Password: req.Password,
	}

	user, err := h.userService.LoginUser(c.Request.Context(), serviceReq)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Login failed", "details": gin.H{"error": err.Error()}})
		return
	}

	// Set user in context for gin-jwt
	c.Set("user", user)

	// Generate JWT token using gin-jwt's token generator for consistency
	jwtToken, _, err := h.authMiddleware.TokenGenerator(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not generate token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"user": gin.H{
			"id":             user.ID,
			"username":       user.Username,
			"email":          user.Email,
			"confirmedEmail": user.ConfirmedEmail,
			"isAdmin":        user.IsAdmin,
			"profileImage":   user.ProfileImage,
			"createdAt":      user.CreatedAt.Format(time.RFC3339),
		},
		"token": jwtToken,
	})
}

func (h *UserHandler) GetCurrentUser(c *gin.Context) {
	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Not authenticated"})
		return
	}

	// Set user in context for gin-jwt
	c.Set("user", user)

	// Generate JWT token using gin-jwt's token generator
	jwtToken, _, err := h.authMiddleware.TokenGenerator(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not generate token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"user": gin.H{
			"id":             user.ID,
			"username":       user.Username,
			"email":          user.Email,
			"confirmedEmail": user.ConfirmedEmail,
			"isAdmin":        user.IsAdmin,
			"profileImage":   user.ProfileImage,
			"createdAt":      user.CreatedAt.Format(time.RFC3339),
		},
		"token": jwtToken,
	})
}

func (h *UserHandler) Delete(c *gin.Context) {
	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	err = h.userService.DeleteUser(c.Request.Context(), user.ID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not delete user", "details": gin.H{"error": err.Error()}})
		return
	}

	c.JSON(http.StatusNoContent, gin.H{"message": "User deleted successfully"})
}

func (h *UserHandler) ConfirmEmail(c *gin.Context) {
	var req ConfirmEmailRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	serviceReq := services.ConfirmEmailRequest{
		Email: req.Email,
		Code:  req.Code,
	}

	err := h.userService.ConfirmEmail(c.Request.Context(), serviceReq)
	if err != nil {
		statusCode := getErrorStatusCode(err)
		c.JSON(statusCode, gin.H{"message": "Email confirmation failed", "details": gin.H{"error": err.Error()}})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Email confirmed successfully"})
}

func (h *UserHandler) ResendConfirmationCode(c *gin.Context) {
	var req ResendConfirmationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	err := h.userService.ResendConfirmationCode(c.Request.Context(), req.Email)
	if err != nil {
		statusCode := getErrorStatusCode(err)
		c.JSON(statusCode, gin.H{"message": "Failed to resend confirmation code", "details": gin.H{"error": err.Error()}})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Confirmation code sent successfully. Check your email"})
}

func (h *UserHandler) ResetPassword(c *gin.Context) {
	var req ResetPasswordRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	serviceReq := services.ResetPasswordRequest{
		Email: req.Email,
	}

	err := h.userService.ResetPassword(c.Request.Context(), serviceReq)
	if err != nil {
		statusCode := getErrorStatusCode(err)
		c.JSON(statusCode, gin.H{"message": "Could not reset password", "details": gin.H{"error": err.Error()}})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Password reset email sent successfully"})
}

func (h *UserHandler) Update(c *gin.Context) {
	var req UpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	serviceReq := services.UpdateUserRequest{
		User:     user,
		Username: req.Username,
		Email:    req.Email,
		Password: req.Password,
	}

	err = h.userService.UpdateUser(c.Request.Context(), serviceReq)
	if err != nil {
		statusCode := getErrorStatusCode(err)
		c.JSON(statusCode, gin.H{"message": "Could not update user", "details": gin.H{"error": err.Error()}})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "User updated successfully"})
}

func getErrorStatusCode(err error) int {
	switch err.Error() {
	case "invalid email format", "username must be at least 3 characters", "password must be at least 8 characters", "invalid confirmation code format", "invalid confirmation code":
		return http.StatusBadRequest
	case "email already exists", "username already exists":
		return http.StatusConflict
	case "invalid credentials", "email not confirmed", "user not active":
		return http.StatusUnauthorized
	case "user not found":
		return http.StatusNotFound
	default:
		return http.StatusInternalServerError
	}
}
