package services

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/AndreasX42/wordweave-go/domain/repositories"
	"github.com/AndreasX42/wordweave-go/utils"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/ses"
	"github.com/aws/aws-sdk-go-v2/service/ses/types"
)

// SESEmailService implements EmailService using AWS SES
type SESEmailService struct {
	client *ses.Client
	config EmailConfig
}

type EmailConfig struct {
	FromEmail    string
	FromName     string
	TemplateType string
}

// NewSESEmailService creates a new SES email service
func NewSESEmailService(client *ses.Client) repositories.EmailService {
	config := EmailConfig{
		FromEmail:    utils.GetEnvWithDefault("SES_FROM_EMAIL", ""),
		FromName:     utils.GetEnvWithDefault("SES_FROM_NAME", ""),
		TemplateType: utils.GetEnvWithDefault("EMAIL_TEMPLATE_TYPE", "html"),
	}

	return &SESEmailService{
		client: client,
		config: config,
	}
}

func (s *SESEmailService) SendConfirmationEmail(email, code string) error {
	htmlBody := s.createHTMLEmailBody(code)
	textBody := s.createTextEmailBody(code)

	input := &ses.SendEmailInput{
		Source: aws.String(fmt.Sprintf("%s <%s>", s.config.FromName, s.config.FromEmail)),
		Destination: &types.Destination{
			ToAddresses: []string{email},
		},
		Message: &types.Message{
			Subject: &types.Content{
				Data:    aws.String("Confirm Your Email Address"),
				Charset: aws.String("UTF-8"),
			},
			Body: &types.Body{
				Html: &types.Content{
					Data:    aws.String(htmlBody),
					Charset: aws.String("UTF-8"),
				},
				Text: &types.Content{
					Data:    aws.String(textBody),
					Charset: aws.String("UTF-8"),
				},
			},
		},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	result, err := s.client.SendEmail(ctx, input)
	if err != nil {
		log.Printf("failed to send email to %s: %v", email, err)
		return err
	}

	log.Printf("Email sent successfully to %s. Message ID: %s", email, *result.MessageId)
	return nil
}

func (s *SESEmailService) SendResetPasswordEmail(email, password string) error {
	htmlBody := s.createPasswordResetHTMLBody(password)
	textBody := s.createPasswordResetTextBody(password)

	input := &ses.SendEmailInput{
		Source: aws.String(fmt.Sprintf("%s <%s>", s.config.FromName, s.config.FromEmail)),
		Destination: &types.Destination{
			ToAddresses: []string{email},
		},
		Message: &types.Message{
			Subject: &types.Content{
				Data:    aws.String("Password Reset"),
				Charset: aws.String("UTF-8"),
			},
			Body: &types.Body{
				Html: &types.Content{
					Data:    aws.String(htmlBody),
					Charset: aws.String("UTF-8"),
				},
				Text: &types.Content{
					Data:    aws.String(textBody),
					Charset: aws.String("UTF-8"),
				},
			},
		},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	result, err := s.client.SendEmail(ctx, input)
	if err != nil {
		log.Printf("failed to send password reset email to %s: %v", email, err)
		return err
	}

	log.Printf("Password reset email sent successfully to %s. Message ID: %s", email, *result.MessageId)
	return nil
}

func (s *SESEmailService) createHTMLEmailBody(code string) string {
	return fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Confirm Your Email</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #000; }
        h1, h2, h3, h4, h5, h6 { color: #000; }
        p { color: #000; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
        .header h1 { color: white; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .content h2 { color: #000; }
        .content p { color: #000; }
        .code { font-size: 24px; font-weight: bold; color: #4CAF50; background-color: #f0f0f0; padding: 10px; text-align: center; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        .footer p { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to %s!</h1>
        </div>
        <div class="content">
            <h2>Confirm Your Email Address</h2>
            <p>Thank you for registering with %s. To complete your registration, please use the confirmation code below:</p>
            <div class="code">%s</div>
            <p>This code will expire in 24 hours for security reasons.</p>
            <p>If you didn't create an account with us, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Sent by %s.</p>
        </div>
    </div>
</body>
</html>`, s.config.FromName, s.config.FromName, code, s.config.FromName)
}

func (s *SESEmailService) createTextEmailBody(code string) string {
	return fmt.Sprintf(`
Welcome to %s!

Please confirm your email address by using the following confirmation code:

%s

If you didn't create an account with us, please ignore this email.

Best regards,
The %s Team
`, s.config.FromName, code, s.config.FromName)
}

func (s *SESEmailService) createPasswordResetHTMLBody(password string) string {
	return fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Password Reset</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #000; }
        h1, h2, h3, h4, h5, h6 { color: #000; }
        p { color: #000; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e93030; color: white; padding: 20px; text-align: center; }
        .header h1 { color: white; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .content h2 { color: #000; }
        .content p { color: #000; }
        .password { font-size: 24px; font-weight: bold; color: #e93030; background-color: #f0f0f0; padding: 10px; text-align: center; border-radius: 5px; margin: 20px 0; }
        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .warning p { color: #000; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        .footer p { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset - %s</h1>
        </div>
        <div class="content">
            <h2>Your Password Has Been Reset</h2>
            <p>Your password has been successfully reset. Here is your new temporary password:</p>
            <div class="password">%s</div>
            <div class="warning">
                <p><strong>⚠️ Important Security Notice:</strong></p>
                <p>Please log in with this temporary password and change it immediately for security reasons. This temporary password should only be used once.</p>
            </div>
            <p>If you didn't request a password reset, please contact our support team immediately.</p>
        </div>
        <div class="footer">
            <p>Sent by %s.</p>
        </div>
    </div>
</body>
</html>`, s.config.FromName, password, s.config.FromName)
}

func (s *SESEmailService) createPasswordResetTextBody(password string) string {
	return fmt.Sprintf(`
Password Reset - %s

Your password has been reset. Here is your new temporary password:

%s

IMPORTANT: Please log in with this temporary password and change it immediately for security reasons.

If you didn't request a password reset, please contact our support team immediately.

Best regards,
The %s Team
`, s.config.FromName, password, s.config.FromName)
}
