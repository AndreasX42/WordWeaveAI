package routes

import (
	"errors"
	"net/http"

	"github.com/AndreasX42/wordweave-go/aws"
	"github.com/AndreasX42/wordweave-go/models"
	"github.com/AndreasX42/wordweave-go/utils"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type RegisterRequest struct {
	Email    string `json:"email" binding:"required"`
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type LoginRequest struct {
	Email    string `json:"email" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type DeleteRequest struct {
	UserId string `json:"user_id" binding:"required"`
}

type ConfirmEmailRequest struct {
	Email string `json:"email" binding:"required"`
	Code  string `json:"code" binding:"required"`
}

func getPrincipal(c *gin.Context) (*models.User, error) {
	userPtr, exists := c.Get("principal")
	if !exists {
		return nil, errors.New("principal not set")
	}

	user, ok := userPtr.(*models.User)
	if !ok {
		return nil, errors.New("principal invalid")
	}

	return user, nil
}

func register(c *gin.Context) {
	var req RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
		return
	}

	// Validation
	if !utils.IsValidEmail(req.Email) {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid email"})
		return
	}

	if len(req.Username) < 3 {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Username must be at least 3 characters"})
		return
	}

	if len(req.Password) < 8 {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Password must be at least 8 characters"})
		return
	}

	// Check if email already exists
	exists, err := models.CheckUsernameOrEmailExists(c.Request.Context(), req.Username, req.Email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not check username or email availability", "details": gin.H{"error": err.Error()}})
		return
	}

	if exists {
		c.JSON(http.StatusConflict, gin.H{"message": "Username or email already exist"})
		return
	}

	// Generate user data
	userId := uuid.New().String()
	confirmationCode := utils.GenerateConfirmationCode()
	hashedPassword, err := utils.HashPassword(req.Password)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Password hashing failed"})
		return
	}

	// Create user in DynamoDB
	err = models.CreateUser(c.Request.Context(), userId, req.Email, req.Username, hashedPassword, confirmationCode)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not save user", "details": gin.H{"error": err.Error()}})
		return
	}

	// Send confirmation email
	go aws.SendConfirmationEmailSES(req.Email, confirmationCode)

	c.JSON(http.StatusOK, gin.H{
		"message": "Registration successful. Check your email for the confirmation code",
		"details": gin.H{
			"user_id":  userId,
			"username": req.Username,
			"email":    req.Email,
		},
	})
}

func login(c *gin.Context) {
	var req LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
		return
	}

	if !utils.IsValidEmail(req.Email) || len(req.Password) < 8 {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid credentials"})
		return
	}

	user, err := models.ValidateCredentials(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Invalid credentials"})
		return
	}

	if !user.ConfirmedEmail {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "User not confirmed email"})
		return
	}

	if !user.IsActive {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "User not active"})
		return
	}

	token, err := utils.GenerateJWT(user.Id, user.Username)
	if err != nil {
		c.JSON(http.StatusInternalServerError,
			gin.H{"message": "Could not generate token",
				"details": gin.H{"message": err.Error()}})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Login successful", "details": gin.H{"token": token, "user_id": user.Id, "username": user.Username, "email": user.Email}})
}

func delete(c *gin.Context) {
	var req DeleteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
		return
	}

	user, err := getPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized", "details": gin.H{"error": err.Error()}})
		return
	}

	if user.Id != req.UserId {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized", "details": gin.H{"error": "User IDs mismatch"}})
		return
	}

	err = models.DeleteUser(c.Request.Context(), user.Id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not delete user", "details": gin.H{"error": err.Error()}})
		return
	}

	c.JSON(http.StatusNoContent, gin.H{"message": "User deleted successfully"})
}

func confirmEmail(c *gin.Context) {
	var req ConfirmEmailRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
		return
	}

	if !utils.IsValidEmail(req.Email) {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid email"})
		return
	}

	if len(req.Code) != 6 {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid confirmation code"})
		return
	}

	user, err := models.GetUserByEmail(c.Request.Context(), req.Email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not get user", "details": gin.H{"error": err.Error()}})
		return
	}

	if user.ConfirmationCode != req.Code {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Invalid confirmation code"})
		return
	}

	user.ConfirmedEmail = true
	user.IsActive = true
	user.ConfirmationCode = ""

	err = models.UpdateUser(c.Request.Context(), user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not update user", "details": gin.H{"error": err.Error()}})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Email confirmed successfully"})
}
