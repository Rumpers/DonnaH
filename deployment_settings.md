# Deployment Settings for OpenManus Assistant

## Recommended Gunicorn Settings

When deploying to Replit Deployments, update the `run` command in your `.replit` file to use these optimized settings:

```
run = ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120", "main:app"]
```

### Settings Explanation:

- `--workers 3`: Creates 3 worker processes to handle requests in parallel
- `--timeout 120`: Increases the default timeout to 120 seconds for longer operations
- `--bind 0.0.0.0:5000`: Binds to all network interfaces on port 5000

## Environment Variables Required for Production

Make sure to set these environment variables in the deployment environment:

- `SESSION_SECRET`: A secure random string for encrypting sessions
- `TELEGRAM_BOT_TOKEN_DONNAH`: Production Telegram bot token
- `OPENAI_API_KEY`: OpenAI API key for AI functionality
- `DATABASE_URL`: PostgreSQL database connection string (automatically set by Replit)

## Additional Security Considerations

- Turn off debugging in production (already handled by our config)
- Use HTTPS for all connections (automatically handled by Replit Deployments)
- Set up proper rate limiting for API endpoints
- Use secure password hashing (already implemented with werkzeug.security)
- Keep dependencies updated and monitor for vulnerabilities