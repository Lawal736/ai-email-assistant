# 🚀 Deployment Guide for AI Email Assistant

## Quick Deploy Options

### Option 1: Deploy to Railway (Recommended - Easiest)

1. **Sign up for Railway** (railway.app)
2. **Connect your GitHub repository**
3. **Set environment variables** in Railway dashboard:
   ```
   FLASK_ENV=production
   SECRET_KEY=your-secret-key
   OPENAI_API_KEY=your-openai-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   PAYSTACK_SECRET_KEY=your-paystack-key
   STRIPE_SECRET_KEY=your-stripe-key
   ANTHROPIC_API_KEY=your-anthropic-key
   ```
4. **Deploy** - Railway will automatically detect your Flask app

### Option 2: Deploy to Heroku

1. **Install Heroku CLI**
2. **Login to Heroku**:
   ```bash
   heroku login
   ```
3. **Create Heroku app**:
   ```bash
   heroku create your-app-name
   ```
4. **Set environment variables**:
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set OPENAI_API_KEY=your-openai-key
   heroku config:set GOOGLE_CLIENT_ID=your-google-client-id
   heroku config:set GOOGLE_CLIENT_SECRET=your-google-client-secret
   heroku config:set PAYSTACK_SECRET_KEY=your-paystack-key
   heroku config:set STRIPE_SECRET_KEY=your-stripe-key
   heroku config:set ANTHROPIC_API_KEY=your-anthropic-key
   ```
5. **Deploy**:
   ```bash
   git push heroku main
   ```

### Option 3: Deploy to DigitalOcean App Platform

1. **Sign up for DigitalOcean**
2. **Create new app** in App Platform
3. **Connect your GitHub repository**
4. **Configure environment variables** in the dashboard
5. **Deploy**

## Required Environment Variables

### Essential Variables
- `SECRET_KEY`: Flask secret key (generate with `python -c "import secrets; print(secrets.token_hex(16))"`)
- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key

### Google OAuth (Required for Gmail integration)
- `GOOGLE_CLIENT_ID`: From Google Cloud Console
- `GOOGLE_CLIENT_SECRET`: From Google Cloud Console

### Payment Processing
- `PAYSTACK_SECRET_KEY`: Your Paystack secret key
- `STRIPE_SECRET_KEY`: Your Stripe secret key

### Optional
- `FLASK_ENV`: Set to "production" for deployment

## Pre-Deployment Checklist

### 1. Update Google OAuth Redirect URIs
In your Google Cloud Console:
- Add your production domain to authorized redirect URIs
- Example: `https://your-app.railway.app/oauth2callback`

### 2. Update Payment Webhooks
In Paystack/Stripe dashboard:
- Update webhook URLs to your production domain
- Example: `https://your-app.railway.app/webhook/paystack`

### 3. Database Setup
Your app uses SQLite locally. For production:
- Consider using PostgreSQL (add `psycopg2-binary` to requirements.txt)
- Or keep SQLite for simple deployments

### 4. File Storage
- Gmail credentials and tokens are stored locally
- Consider using cloud storage for production

## Deployment Commands

### From Cursor Terminal:

```bash
# 1. Commit all changes
git add .
git commit -m "Prepare for deployment"

# 2. Push to GitHub
git push origin main

# 3. Deploy to Railway (if using Railway)
# Just connect your repo in Railway dashboard

# 4. Deploy to Heroku (if using Heroku)
heroku login
heroku create your-app-name
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(16))")
heroku config:set OPENAI_API_KEY=your-openai-key
heroku config:set GOOGLE_CLIENT_ID=your-google-client-id
heroku config:set GOOGLE_CLIENT_SECRET=your-google-client-secret
heroku config:set PAYSTACK_SECRET_KEY=your-paystack-key
heroku config:set STRIPE_SECRET_KEY=your-stripe-key
heroku config:set ANTHROPIC_API_KEY=your-anthropic-key
git push heroku main
```

## Post-Deployment

### 1. Test Your App
- Visit your deployed URL
- Test user registration/login
- Test Gmail OAuth flow
- Test payment processing

### 2. Monitor Logs
- Railway: View logs in dashboard
- Heroku: `heroku logs --tail`
- DigitalOcean: View logs in App Platform dashboard

### 3. Set Up Custom Domain (Optional)
- Configure custom domain in your deployment platform
- Update DNS records
- Update Google OAuth redirect URIs

## Troubleshooting

### Common Issues:
1. **Port binding**: Your app should use `os.environ.get('PORT', 5001)`
2. **Environment variables**: Ensure all required variables are set
3. **Google OAuth**: Check redirect URIs match your production domain
4. **Database**: SQLite files may not persist on some platforms

### Debug Commands:
```bash
# Check app status
heroku ps

# View logs
heroku logs --tail

# Run app locally with production settings
FLASK_ENV=production python app.py
```

## Security Considerations

1. **Never commit API keys** to version control
2. **Use environment variables** for all secrets
3. **Enable HTTPS** (automatic on most platforms)
4. **Regular security updates** for dependencies
5. **Monitor for suspicious activity**

## Cost Considerations

- **Railway**: Free tier available, then pay-as-you-go
- **Heroku**: Free tier discontinued, starts at $7/month
- **DigitalOcean**: Starts at $5/month
- **API costs**: OpenAI, Anthropic, and payment processing fees

## Support

If you encounter issues:
1. Check the logs in your deployment platform
2. Verify all environment variables are set
3. Test locally with production settings
4. Check platform-specific documentation 