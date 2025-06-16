# 🚀 GCP Quick Start Guide
# Deploy AI Email Assistant in 10 Minutes

## Prerequisites
- Google Cloud Platform account
- gcloud CLI installed
- All API keys ready

## Quick Deployment (Automated)

### Option 1: Use the Deployment Script
```bash
# Make script executable
chmod +x gcp-deploy.sh

# Run the deployment script
./gcp-deploy.sh
```

### Option 2: Manual Deployment

#### 1. Set up Project
```bash
# Create new project
gcloud projects create ai-email-assistant-$(date +%s)
gcloud config set project ai-email-assistant-$(date +%s)

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

#### 2. Create Secrets
```bash
# Create secrets (replace with your actual keys)
echo "your-anthropic-key" | gcloud secrets create anthropic-api-key --data-file=-
echo "your-openai-key" | gcloud secrets create openai-api-key --data-file=-
echo "your-paystack-secret" | gcloud secrets create paystack-secret-key --data-file=-
echo "your-paystack-public" | gcloud secrets create paystack-public-key --data-file=-
echo "$(openssl rand -hex 32)" | gcloud secrets create flask-secret-key --data-file=-
```

#### 3. Deploy
```bash
# Deploy to Cloud Run
gcloud builds submit --config cloudbuild.yaml
```

#### 4. Get Your URL
```bash
# Get service URL
gcloud run services describe ai-email-assistant --region=us-central1 --format="value(status.url)"
```

## Environment Variables Needed

Make sure you have these API keys ready:
- **Anthropic API Key**: https://console.anthropic.com/
- **OpenAI API Key**: https://platform.openai.com/api-keys
- **Paystack Secret Key**: https://dashboard.paystack.com/#/settings/developer
- **Paystack Public Key**: https://dashboard.paystack.com/#/settings/developer
- **Google OAuth**: Already configured in your app

## Cost Breakdown
- **Cloud Run**: $15-50/month
- **Cloud SQL**: $7-25/month  
- **Other services**: $5-15/month
- **Total**: ~$30-80/month

## Next Steps
1. Update Google OAuth redirect URIs
2. Test the application
3. Set up custom domain (optional)
4. Configure monitoring

Your app will be live in minutes! 🎉 