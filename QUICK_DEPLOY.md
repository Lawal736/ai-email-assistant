# 🚀 Quick Deployment Guide for AI Email Assistant

## Prerequisites

Before deploying, make sure you have:

1. **API Keys**:
   - [Anthropic API Key](https://console.anthropic.com/) (Claude)
   - [OpenAI API Key](https://platform.openai.com/api-keys) (GPT-4)
   - [Google OAuth Credentials](https://console.cloud.google.com/apis/credentials)

2. **Payment Processing**:
   - [Paystack Account](https://paystack.com/) (Primary)
   - [Stripe Account](https://stripe.com/) (Optional)

3. **Deployment Platform Account**:
   - [Railway](https://railway.app/) (Recommended)
   - [Heroku](https://heroku.com/)
   - [DigitalOcean](https://digitalocean.com/)

## Step 1: Set Up Environment Variables

### Option A: Use the Setup Script (Recommended)
```bash
python3 setup_deployment_env.py
```

### Option B: Manual Setup
1. Copy `env_template.txt` to `.env`
2. Fill in your actual values
3. **DO NOT commit .env to git**

## Step 2: Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `https://your-app-domain.com/oauth2callback`
   - `http://localhost:5001/oauth2callback` (for local testing)
6. Download `credentials.json` and add to deployment

## Step 3: Deploy to Railway (Recommended)

### Quick Deploy
1. **Sign up** at [railway.app](https://railway.app/)
2. **Connect your GitHub repository**
3. **Add environment variables** in Railway dashboard:
   - Copy all variables from your `.env` file
4. **Deploy** - Railway auto-detects Flask app

### Manual Deploy
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Add environment variables
railway variables set FLASK_ENV=production
railway variables set SECRET_KEY=your-secret-key
# ... add all other variables

# Deploy
railway up
```

## Step 4: Deploy to Heroku

```bash
# Install Heroku CLI
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key
heroku config:set ANTHROPIC_API_KEY=your-anthropic-key
heroku config:set OPENAI_API_KEY=your-openai-key
heroku config:set GOOGLE_CLIENT_ID=your-google-client-id
heroku config:set GOOGLE_CLIENT_SECRET=your-google-client-secret
heroku config:set PAYSTACK_SECRET_KEY=your-paystack-key
heroku config:set PAYSTACK_PUBLIC_KEY=your-paystack-public-key

# Deploy
git push heroku main
```

## Step 5: Deploy to DigitalOcean

1. **Sign up** at [digitalocean.com](https://digitalocean.com/)
2. **Create App Platform** app
3. **Connect your GitHub repository**
4. **Configure environment variables**:
   - Add all variables from your `.env` file
5. **Deploy** - DigitalOcean auto-detects Flask app

## Step 6: Post-Deployment Setup

### 1. Update Google OAuth Redirect URIs
- Go to Google Cloud Console
- Add your deployment URL: `https://your-app-domain.com/oauth2callback`

### 2. Test Your Deployment
- Visit your app URL
- Test user registration/login
- Test Gmail connection
- Test payment processing

### 3. Set Up Webhooks (Optional)
- Configure Paystack webhooks for payment notifications
- Configure Stripe webhooks (if using Stripe)

## Environment Variables Reference

### Required Variables
```bash
# Flask
FLASK_ENV=production
SECRET_KEY=your-secret-key
PORT=5001

# AI APIs
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Payment Processing
PAYSTACK_SECRET_KEY=your-paystack-secret-key
PAYSTACK_PUBLIC_KEY=your-paystack-public-key
```

### Optional Variables
```bash
# Alternative Payment
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_PUBLIC_KEY=your-stripe-public-key

# Cryptocurrency
INFURA_URL=your-infura-url

# Deployment
BASE_URL=https://your-app-domain.com
```

## Troubleshooting

### Common Issues

1. **Port Binding Error**
   - Ensure your app uses `os.environ.get('PORT', 5001)`
   - ✅ Already configured in your app

2. **Google OAuth Error**
   - Check redirect URIs in Google Cloud Console
   - Ensure `credentials.json` is properly configured

3. **Payment Processing Error**
   - Verify API keys are correct
   - Check webhook configurations

4. **Database Issues**
   - SQLite works for small deployments
   - Consider PostgreSQL for production

### Support

- Check the logs in your deployment platform
- Review the `deploy-guide.md` for detailed instructions
- Test locally first with `python3 app.py`

## Cost Optimization

### Railway
- Free tier: $5/month credit
- Pro tier: Pay per usage

### Heroku
- Free tier: Discontinued
- Basic dyno: $7/month

### DigitalOcean
- Basic app: $5/month
- Pro app: $12/month

## Security Checklist

- ✅ Use strong SECRET_KEY
- ✅ Set FLASK_ENV=production
- ✅ Use HTTPS in production
- ✅ Secure API keys
- ✅ Configure CORS properly
- ✅ Set up proper logging

---

**🎉 Your AI Email Assistant is now ready for deployment!** 