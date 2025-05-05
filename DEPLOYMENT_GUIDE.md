# OpenManus Assistant Deployment Guide

## Fixing Deployment Issues

If you're experiencing issues with deployment, follow these steps to ensure proper configuration:

### 1. Update Deployment Settings in .replit file

In your Replit workspace, click on the "Tools" menu and select "Secrets". Add the following secrets:

- `SESSION_SECRET`: A secure random string for encrypting sessions
- `TELEGRAM_BOT_TOKEN_DONNAH`: Production Telegram bot token
- `OPENAI_API_KEY`: OpenAI API key for AI functionality 
- `DATABASE_URL`: PostgreSQL database connection string (automatically set by Replit)

### 2. Update Deployment Command

In your Replit workspace:
1. Click on the "..." menu in the files panel
2. Select "Show hidden files"
3. Find and open the `.replit` file
4. Update the deployment configuration to use these optimized settings:

```
[deployment]
deploymentTarget = "autoscale"
run = ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120", "main:app"]
```

## Explanation of Deployment Settings

- `--workers 3`: Creates 3 worker processes to handle requests in parallel
- `--timeout 120`: Increases the default timeout to 120 seconds for longer operations
- `--bind 0.0.0.0:5000`: Binds to all network interfaces on port 5000

## Verifying Environment Variables in Deployment

Make sure to check that all environment variables are correctly set in the deployment environment:

1. Go to your Replit dashboard
2. Click on your project
3. Go to the "Secrets" tab in the project settings
4. Verify that all required environment variables are set

## Deployment Process

1. Click on the "Deploy" button in your Replit workspace
2. Select your deployment settings
3. Click "Deploy" to start the deployment process
4. Once deployed, your application will be available at your deployment URL

## Troubleshooting

If you're still experiencing issues with deployment:

1. Check the deployment logs for any error messages
2. Verify that the Telegram webhook is correctly set up for your deployed application
3. Make sure the database connection is properly configured
4. If using the development bot in production, switch to the production bot token