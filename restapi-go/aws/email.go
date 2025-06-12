package aws

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/AndreasX42/wordweave-go/utils"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/ses"
	"github.com/aws/aws-sdk-go-v2/service/ses/types"
)

var sesClient *ses.Client

// InitSES initializes the SES client
func InitSES() error {
	cfg, err := config.LoadDefaultConfig(context.TODO(), func(o *config.LoadOptions) error {
		if region := os.Getenv("AWS_SES_REGION"); region != "" {
			o.Region = region
		} else {
			o.Region = "us-east-1" // Default SES region
		}
		return nil
	})
	if err != nil {
		return fmt.Errorf("failed to load AWS config: %w", err)
	}

	sesClient = ses.NewFromConfig(cfg)
	return nil
}

// EmailConfig holds email configuration
type EmailConfig struct {
	FromEmail    string
	FromName     string
	Subject      string
	TemplateType string
}

// GetEmailConfig returns email configuration from environment
func GetEmailConfig() EmailConfig {
	return EmailConfig{
		FromEmail:    utils.GetEnvWithDefault("SES_FROM_EMAIL", ""),
		FromName:     utils.GetEnvWithDefault("SES_FROM_NAME", ""),
		Subject:      utils.GetEnvWithDefault("SES_SUBJECT", "Confirm Your Email Address"),
		TemplateType: utils.GetEnvWithDefault("EMAIL_TEMPLATE_TYPE", "html"),
	}
}

// SendConfirmationEmailSES sends an email confirmation using AWS SES
func SendConfirmationEmailSES(email, code string) {
	if sesClient == nil {
		log.Println("SES not initialized")
	}

	config := GetEmailConfig()

	// Create email content
	htmlBody := createHTMLEmailBody(code)
	textBody := createTextEmailBody(code)

	// Prepare the email input
	input := &ses.SendEmailInput{
		Source: aws.String(fmt.Sprintf("%s <%s>", config.FromName, config.FromEmail)),
		Destination: &types.Destination{
			ToAddresses: []string{email},
		},
		Message: &types.Message{
			Subject: &types.Content{
				Data:    aws.String(config.Subject),
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

	// Send the email
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	result, err := sesClient.SendEmail(ctx, input)
	if err != nil {
		log.Printf("failed to send email to %s: %v", email, err)
	}

	log.Printf("Email sent successfully to %s. Message ID: %s", email, *result.MessageId)
}

// createHTMLEmailBody creates an HTML email template
func createHTMLEmailBody(code string) string {
	return fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Confirm Your Email</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .code { font-size: 24px; font-weight: bold; color: #4CAF50; background-color: #f0f0f0; padding: 10px; text-align: center; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to WordWeave!</h1>
        </div>
        <div class="content">
            <h2>Confirm Your Email Address</h2>
            <p>Thank you for registering with WordWeave. To complete your registration, please use the confirmation code below:</p>
            <div class="code">%s</div>
            <p>This code will expire in 24 hours for security reasons.</p>
            <p>If you didn't create an account with us, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Sent by WordWeave.</p>
        </div>
    </div>
</body>
</html>`, code)
}

// createTextEmailBody creates a plain text email template
func createTextEmailBody(code string) string {
	return fmt.Sprintf(`
Welcome to WordWeave!

Thank you for registering with WordWeave. To complete your registration, please use the confirmation code below:

Confirmation Code: %s

This code will expire in 24 hours for security reasons.

If you didn't create an account with us, please ignore this email.

--
WordWeave Team

Sent by WordWeave.
`, code)
}
