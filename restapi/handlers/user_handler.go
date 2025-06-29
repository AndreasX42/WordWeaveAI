package handlers

import (
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/utils"
	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
)

type UserHandler struct {
	userService *services.UserService
}

func NewUserHandler(userService *services.UserService) *UserHandler {
	return &UserHandler{
		userService: userService,
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

func (h *UserHandler) handleValidationError(c *gin.Context, err error) {
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

func (h *UserHandler) Register(c *gin.Context) {
	var req RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		h.handleValidationError(c, err)
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
		h.handleValidationError(c, err)
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

	token, err := utils.GenerateJWT(user.ID, user.Username)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not generate token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Login successful",
		"details": gin.H{
			"token":          token,
			"user_id":        user.ID,
			"username":       user.Username,
			"email":          user.Email,
			"confirmedEmail": user.ConfirmedEmail,
			"isAdmin":        user.IsAdmin,
		},
	})
}

func (h *UserHandler) GetCurrentUser(c *gin.Context) {
	user, err := h.getPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Not authenticated"})
		return
	}

	// Generate a fresh JWT token (like login endpoint)
	jwtToken, err := utils.GenerateJWT(user.ID, user.Username)
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
	user, err := h.getPrincipal(c)
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
		h.handleValidationError(c, err)
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
		h.handleValidationError(c, err)
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
		h.handleValidationError(c, err)
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
		h.handleValidationError(c, err)
		return
	}

	user, err := h.getPrincipal(c)
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

func (h *UserHandler) getPrincipal(c *gin.Context) (*entities.User, error) {
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
