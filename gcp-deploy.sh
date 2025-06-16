#!/bin/bash

# GCP Deployment Script for AI Email Assistant
# This script automates the deployment process to Google Cloud Platform

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ai-email-assistant-$(date +%s)"
REGION="us-central1"
SERVICE_NAME="ai-email-assistant"
DB_INSTANCE_NAME="ai-email-assistant-db"

echo -e "${BLUE}🚀 AI Email Assistant - GCP Deployment Script${NC}"
echo "=================================================="

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_warning "You are not authenticated with gcloud. Please run:"
    echo "gcloud auth login"
    exit 1
fi

# Step 1: Create or select project
print_info "Step 1: Setting up Google Cloud Project"
echo "Current project: $(gcloud config get-value project 2>/dev/null || echo 'None')"

read -p "Do you want to create a new project? (y/N): " create_new
if [[ $create_new =~ ^[Yy]$ ]]; then
    read -p "Enter project name (or press Enter for default): " project_name
    if [ -z "$project_name" ]; then
        project_name="ai-email-assistant"
    fi
    
    gcloud projects create $PROJECT_ID --name="$project_name"
    gcloud config set project $PROJECT_ID
    print_status "Created new project: $PROJECT_ID"
else
    read -p "Enter existing project ID: " existing_project
    gcloud config set project $existing_project
    PROJECT_ID=$existing_project
    print_status "Using existing project: $PROJECT_ID"
fi

# Step 2: Enable required APIs
print_info "Step 2: Enabling required APIs"
apis=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "containerregistry.googleapis.com"
    "sqladmin.googleapis.com"
    "secretmanager.googleapis.com"
    "monitoring.googleapis.com"
    "logging.googleapis.com"
)

for api in "${apis[@]}"; do
    gcloud services enable $api
    print_status "Enabled $api"
done

# Step 3: Create secrets
print_info "Step 3: Setting up Secret Manager"
echo "You'll need to provide your API keys and secrets."

read -p "Enter your Anthropic API key: " anthropic_key
echo "$anthropic_key" | gcloud secrets create anthropic-api-key --data-file=-

read -p "Enter your OpenAI API key: " openai_key
echo "$openai_key" | gcloud secrets create openai-api-key --data-file=-

read -p "Enter your Paystack Secret key: " paystack_secret
echo "$paystack_secret" | gcloud secrets create paystack-secret-key --data-file=-

read -p "Enter your Paystack Public key: " paystack_public
echo "$paystack_public" | gcloud secrets create paystack-public-key --data-file=-

read -p "Enter your Stripe Secret key (or press Enter to skip): " stripe_secret
if [ ! -z "$stripe_secret" ]; then
    echo "$stripe_secret" | gcloud secrets create stripe-secret-key --data-file=-
fi

read -p "Enter your Stripe Public key (or press Enter to skip): " stripe_public
if [ ! -z "$stripe_public" ]; then
    echo "$stripe_public" | gcloud secrets create stripe-public-key --data-file=-
fi

# Generate Flask secret key
flask_secret=$(openssl rand -hex 32)
echo "$flask_secret" | gcloud secrets create flask-secret-key --data-file=-

print_status "All secrets created successfully"

# Step 4: Create Cloud SQL instance
print_info "Step 4: Setting up Cloud SQL Database"
read -p "Do you want to create a Cloud SQL instance? (Y/n): " create_db
if [[ ! $create_db =~ ^[Nn]$ ]]; then
    read -p "Enter database password: " db_password
    
    gcloud sql instances create $DB_INSTANCE_NAME \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=SSD \
        --storage-size=10GB \
        --backup-start-time=03:00 \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=04
    
    gcloud sql databases create ai_email_assistant --instance=$DB_INSTANCE_NAME
    gcloud sql users create ai-app-user --instance=$DB_INSTANCE_NAME --password=$db_password
    
    print_status "Cloud SQL instance created successfully"
else
    print_warning "Skipping Cloud SQL creation. Make sure you have a database configured."
fi

# Step 5: Build and deploy
print_info "Step 5: Building and deploying application"

# Check if Dockerfile exists, if not copy from Dockerfile.gcp
if [ ! -f "Dockerfile" ]; then
    if [ -f "Dockerfile.gcp" ]; then
        cp Dockerfile.gcp Dockerfile
        print_status "Using GCP-optimized Dockerfile"
    else
        print_error "No Dockerfile found. Please create one first."
        exit 1
    fi
fi

# Submit build to Cloud Build
print_info "Submitting build to Cloud Build..."
gcloud builds submit --config cloudbuild.yaml

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

print_status "Deployment completed successfully!"
echo "Your application is available at: $SERVICE_URL"

# Step 6: Set up monitoring
print_info "Step 6: Setting up monitoring"
read -p "Do you want to set up budget alerts? (Y/n): " setup_budget
if [[ ! $setup_budget =~ ^[Nn]$ ]]; then
    read -p "Enter monthly budget amount (USD): " budget_amount
    read -p "Enter billing account ID: " billing_account
    
    gcloud billing budgets create \
        --billing-account=$billing_account \
        --display-name="AI Email Assistant Budget" \
        --budget-amount=$budget_amount \
        --budget-amount-currency=USD \
        --threshold-rules=threshold=0.5,basis=current_spend \
        --threshold-rules=threshold=1.0,basis=current_spend
    
    print_status "Budget alerts configured"
fi

# Step 7: Final instructions
print_info "Step 7: Final Configuration"
echo ""
echo "🎉 Deployment completed! Here's what you need to do next:"
echo ""
echo "1. Update Google OAuth redirect URIs:"
echo "   - Go to Google Cloud Console > APIs & Services > Credentials"
echo "   - Add: $SERVICE_URL/oauth2callback"
echo ""
echo "2. Test your application:"
echo "   - Visit: $SERVICE_URL"
echo ""
echo "3. Monitor your application:"
echo "   - Cloud Run Console: https://console.cloud.google.com/run"
echo "   - Cloud Build Console: https://console.cloud.google.com/cloud-build"
echo ""
echo "4. Set up custom domain (optional):"
echo "   gcloud run domain-mappings create --service $SERVICE_NAME --domain your-domain.com --region $REGION"
echo ""
echo "Estimated monthly cost: $30-80 USD"
echo ""
print_status "Your AI Email Assistant is now live on Google Cloud Platform!" 