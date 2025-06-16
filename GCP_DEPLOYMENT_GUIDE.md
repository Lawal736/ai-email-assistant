# 🚀 Google Cloud Platform (GCP) Deployment Guide
# AI Email Assistant - Step by Step Deployment

## Prerequisites
- ✅ Google Cloud Platform account
- ✅ Google Cloud CLI (gcloud) installed
- ✅ Git repository of your AI Email Assistant
- ✅ All API keys and credentials ready

---

## Step 1: Set Up Google Cloud Project

### 1.1 Create a New Project
```bash
# Open Google Cloud Console
# Go to: https://console.cloud.google.com/

# Create new project or select existing
# Project Name: ai-email-assistant
# Project ID: ai-email-assistant-[your-unique-id]
```

### 1.2 Enable Required APIs
```bash
# Enable these APIs in Google Cloud Console:
# - Cloud Run API
# - Cloud Build API
# - Container Registry API
# - Cloud SQL Admin API (if using Cloud SQL)
# - Secret Manager API
```

### 1.3 Install and Configure gcloud CLI
```bash
# Download and install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate with your account
gcloud auth login

# Set your project
gcloud config set project ai-email-assistant-[your-unique-id]

# Verify setup
gcloud config list
```

---

## Step 2: Prepare Your Application

### 2.1 Update Environment Configuration
```bash
# Copy your .env file to production settings
cp .env .env.production

# Edit .env.production with production values:
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=your-production-secret-key
```

### 2.2 Create Cloud Run Configuration
Create `cloudbuild.yaml`:
```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ai-email-assistant', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ai-email-assistant']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'ai-email-assistant'
      - '--image'
      - 'gcr.io/$PROJECT_ID/ai-email-assistant'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '2'
      - '--timeout'
      - '300'
      - '--concurrency'
      - '80'
      - '--max-instances'
      - '10'

images:
  - 'gcr.io/$PROJECT_ID/ai-email-assistant'
```

### 2.3 Update Dockerfile for GCP
```dockerfile
# Use the official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8080

# Run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

---

## Step 3: Set Up Secrets Management

### 3.1 Create Secrets in Secret Manager
```bash
# Create secrets for sensitive data
echo "your-anthropic-api-key" | gcloud secrets create anthropic-api-key --data-file=-
echo "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
echo "your-paystack-secret-key" | gcloud secrets create paystack-secret-key --data-file=-
echo "your-paystack-public-key" | gcloud secrets create paystack-public-key --data-file=-
echo "your-stripe-secret-key" | gcloud secrets create stripe-secret-key --data-file=-
echo "your-stripe-public-key" | gcloud secrets create stripe-public-key --data-file=-
echo "your-flask-secret-key" | gcloud secrets create flask-secret-key --data-file=-
```

### 3.2 Grant Access to Secrets
```bash
# Get your Cloud Run service account
gcloud run services describe ai-email-assistant --region=us-central1 --format="value(spec.template.spec.serviceAccountName)"

# Grant access to secrets (replace with your service account)
gcloud secrets add-iam-policy-binding anthropic-api-key \
    --member="serviceAccount:ai-email-assistant@ai-email-assistant-[your-unique-id].iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

---

## Step 4: Set Up Database (Cloud SQL)

### 4.1 Create Cloud SQL Instance
```bash
# Create PostgreSQL instance
gcloud sql instances create ai-email-assistant-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04

# Create database
gcloud sql databases create ai_email_assistant --instance=ai-email-assistant-db

# Create user
gcloud sql users create ai-app-user \
    --instance=ai-email-assistant-db \
    --password=your-secure-password
```

### 4.2 Get Database Connection Info
```bash
# Get connection info
gcloud sql instances describe ai-email-assistant-db --format="value(connectionName)"

# Save connection name for later use
# Format: ai-email-assistant-[your-unique-id]:us-central1:ai-email-assistant-db
```

---

## Step 5: Deploy to Cloud Run

### 5.1 Build and Deploy
```bash
# Submit build to Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Or deploy manually:
# 1. Build image
docker build -t gcr.io/ai-email-assistant-[your-unique-id]/ai-email-assistant .

# 2. Push to Container Registry
docker push gcr.io/ai-email-assistant-[your-unique-id]/ai-email-assistant

# 3. Deploy to Cloud Run
gcloud run deploy ai-email-assistant \
    --image gcr.io/ai-email-assistant-[your-unique-id]/ai-email-assistant \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 80 \
    --max-instances 10 \
    --set-env-vars "FLASK_ENV=production" \
    --set-env-vars "DATABASE_URL=postgresql://ai-app-user:your-secure-password@/ai_email_assistant?host=/cloudsql/ai-email-assistant-[your-unique-id]:us-central1:ai-email-assistant-db" \
    --add-cloudsql-instances ai-email-assistant-[your-unique-id]:us-central1:ai-email-assistant-db
```

### 5.2 Set Environment Variables
```bash
# Set environment variables for Cloud Run service
gcloud run services update ai-email-assistant \
    --region=us-central1 \
    --set-env-vars="ANTHROPIC_API_KEY=projects/ai-email-assistant-[your-unique-id]/secrets/anthropic-api-key/versions/latest" \
    --set-env-vars="OPENAI_API_KEY=projects/ai-email-assistant-[your-unique-id]/secrets/openai-api-key/versions/latest" \
    --set-env-vars="PAYSTACK_SECRET_KEY=projects/ai-email-assistant-[your-unique-id]/secrets/paystack-secret-key/versions/latest" \
    --set-env-vars="PAYSTACK_PUBLIC_KEY=projects/ai-email-assistant-[your-unique-id]/secrets/paystack-public-key/versions/latest" \
    --set-env-vars="STRIPE_SECRET_KEY=projects/ai-email-assistant-[your-unique-id]/secrets/stripe-secret-key/versions/latest" \
    --set-env-vars="STRIPE_PUBLIC_KEY=projects/ai-email-assistant-[your-unique-id]/secrets/stripe-public-key/versions/latest" \
    --set-env-vars="SECRET_KEY=projects/ai-email-assistant-[your-unique-id]/secrets/flask-secret-key/versions/latest"
```

---

## Step 6: Set Up Custom Domain (Optional)

### 6.1 Map Custom Domain
```bash
# Map custom domain to Cloud Run service
gcloud run domain-mappings create \
    --service ai-email-assistant \
    --domain your-domain.com \
    --region us-central1
```

### 6.2 Update DNS Records
```bash
# Get the IP address for your domain mapping
gcloud run domain-mappings describe \
    --domain your-domain.com \
    --region us-central1

# Add CNAME record in your DNS provider:
# your-domain.com -> ghs.googlehosted.com
```

---

## Step 7: Set Up Monitoring and Logging

### 7.1 Enable Cloud Monitoring
```bash
# Enable monitoring APIs
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com
```

### 7.2 Create Monitoring Dashboard
```bash
# Create basic monitoring dashboard
gcloud monitoring dashboards create --config-from-file=dashboard-config.json
```

### 7.3 Set Up Alerts
```bash
# Create alert policy for high error rates
gcloud alpha monitoring policies create --policy-from-file=alert-policy.json
```

---

## Step 8: Set Up CI/CD Pipeline

### 8.1 Create Cloud Build Trigger
```bash
# Connect your GitHub repository
# Go to Cloud Build > Triggers
# Create trigger for automatic deployment on push to main branch
```

### 8.2 Create GitHub Actions Workflow (Alternative)
Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Google Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Google Cloud CLI
      uses: google-github-actions/setup-gcloud@v0
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ai-email-assistant-[your-unique-id]
    
    - name: Build and Deploy
      run: |
        gcloud builds submit --config cloudbuild.yaml
```

---

## Step 9: Final Configuration

### 9.1 Update Google OAuth Redirect URIs
```bash
# Go to Google Cloud Console > APIs & Services > Credentials
# Update OAuth 2.0 Client ID redirect URIs:
# - https://your-domain.com/oauth2callback
# - https://ai-email-assistant-[hash]-uc.a.run.app/oauth2callback
```

### 9.2 Test the Deployment
```bash
# Get your service URL
gcloud run services describe ai-email-assistant \
    --region=us-central1 \
    --format="value(status.url)"

# Test the application
curl https://ai-email-assistant-[hash]-uc.a.run.app/
```

### 9.3 Set Up SSL Certificate
```bash
# SSL is automatically handled by Cloud Run
# No additional configuration needed
```

---

## Step 10: Cost Optimization

### 10.1 Set Up Budget Alerts
```bash
# Create budget alert
gcloud billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT_ID \
    --display-name="AI Email Assistant Budget" \
    --budget-amount=100 \
    --budget-amount-currency=USD \
    --threshold-rules=threshold=0.5,basis=current_spend \
    --threshold-rules=threshold=1.0,basis=current_spend
```

### 10.2 Optimize Resource Usage
```bash
# Adjust Cloud Run settings for cost optimization
gcloud run services update ai-email-assistant \
    --region=us-central1 \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 5 \
    --concurrency 40
```

---

## Estimated Costs (Monthly)

### Cloud Run
- **2 vCPU, 2GB RAM**: ~$30-50/month
- **1 vCPU, 1GB RAM**: ~$15-25/month

### Cloud SQL
- **db-f1-micro**: ~$7/month
- **db-g1-small**: ~$25/month

### Other Services
- **Container Registry**: ~$5-10/month
- **Cloud Build**: ~$5-15/month
- **Secret Manager**: ~$1-5/month

**Total Estimated Cost**: $30-80/month depending on usage

---

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
```bash
# Check Cloud SQL connection
gcloud sql connect ai-email-assistant-db --user=ai-app-user
```

2. **Secret Access Issues**
```bash
# Verify secret access
gcloud secrets versions access latest --secret="anthropic-api-key"
```

3. **Build Failures**
```bash
# Check build logs
gcloud builds log [BUILD_ID]
```

4. **Service Not Starting**
```bash
# Check service logs
gcloud run services logs read ai-email-assistant --region=us-central1
```

---

## Security Best Practices

1. **Use Secret Manager** for all sensitive data
2. **Enable Cloud Armor** for DDoS protection
3. **Set up VPC** for network isolation
4. **Use IAM** for fine-grained access control
5. **Enable audit logging** for compliance

---

## Next Steps

1. ✅ Deploy your application
2. ✅ Set up monitoring and alerts
3. ✅ Configure custom domain
4. ✅ Set up CI/CD pipeline
5. ✅ Monitor costs and optimize
6. ✅ Set up backup and disaster recovery

Your AI Email Assistant is now deployed on Google Cloud Platform! 🎉 