#!/bin/bash

# AI Email Assistant Deployment Script
# This script helps you set up GitHub and deploy your application

set -e

echo "🚀 AI Email Assistant Deployment Script"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed. Please install git first."
    exit 1
fi

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_status "Initializing git repository..."
    git init
fi

# Add all files to git
print_status "Adding files to git..."
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    print_warning "No changes to commit. All files are already tracked."
else
    print_status "Committing changes..."
    git commit -m "Initial commit: AI Email Assistant with deployment configuration"
fi

# Check if remote origin exists
if ! git remote get-url origin &> /dev/null; then
    print_header "GitHub Repository Setup"
    echo "To connect to GitHub, you need to:"
    echo "1. Create a new repository on GitHub"
    echo "2. Run the following commands:"
    echo ""
    echo "git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git"
    echo "git branch -M main"
    echo "git push -u origin main"
    echo ""
    read -p "Have you created a GitHub repository? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your GitHub repository URL: " repo_url
        if [ ! -z "$repo_url" ]; then
            git remote add origin "$repo_url"
            git branch -M main
            print_status "Pushing to GitHub..."
            git push -u origin main
            print_status "✅ Successfully pushed to GitHub!"
        fi
    fi
else
    print_status "Remote origin already exists. Pushing changes..."
    git push origin main
fi

print_header "Deployment Options"
echo ""
echo "Your application is now ready for deployment. Choose an option:"
echo ""
echo "1. Heroku Deployment"
echo "2. Docker Deployment"
echo "3. Manual Deployment"
echo "4. Exit"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        print_header "Heroku Deployment"
        echo ""
        echo "To deploy to Heroku:"
        echo "1. Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli"
        echo "2. Login to Heroku: heroku login"
        echo "3. Create app: heroku create your-app-name"
        echo "4. Set environment variables:"
        echo "   heroku config:set OPENAI_API_KEY=your_key"
        echo "   heroku config:set FLASK_SECRET_KEY=your_secret"
        echo "   heroku config:set GOOGLE_CREDENTIALS=\"\$(cat credentials.json)\""
        echo "5. Deploy: git push heroku main"
        echo ""
        ;;
    2)
        print_header "Docker Deployment"
        echo ""
        echo "To deploy with Docker:"
        echo "1. Build image: docker build -t ai-email-assistant ."
        echo "2. Run container: docker run -p 5001:5001 ai-email-assistant"
        echo "3. Or use docker-compose: docker-compose up -d"
        echo ""
        ;;
    3)
        print_header "Manual Deployment"
        echo ""
        echo "For manual deployment:"
        echo "1. Ensure all dependencies are installed: pip install -r requirements.txt"
        echo "2. Set up environment variables in .env file"
        echo "3. Place credentials.json in project root"
        echo "4. Run: python app.py"
        echo ""
        ;;
    4)
        print_status "Exiting..."
        exit 0
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

print_status "✅ Deployment setup complete!"
echo ""
echo "Next steps:"
echo "1. Set up your environment variables in .env file"
echo "2. Place your credentials.json file in the project root"
echo "3. Test your application locally: python app.py"
echo "4. Deploy using your chosen method"
echo ""
echo "For more information, see README.md" 