# 🐙 GitHub Setup Guide

This guide will help you connect your AI Email Assistant project to GitHub and prepare it for deployment.

## 📋 Prerequisites

- GitHub account
- Git installed on your computer
- Your AI Email Assistant project ready

## 🚀 Step-by-Step Setup

### 1. Create a GitHub Repository

1. **Go to GitHub.com** and sign in to your account
2. **Click the "+" icon** in the top right corner
3. **Select "New repository"**
4. **Fill in the repository details:**
   - Repository name: `ai-email-assistant` (or your preferred name)
   - Description: `AI-powered email management system with Gmail integration`
   - Make it **Public** or **Private** (your choice)
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
5. **Click "Create repository"**

### 2. Connect Your Local Repository to GitHub

After creating the repository, GitHub will show you commands. Use these:

```bash
# Add the remote repository (replace with your actual repository URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Rename the default branch to 'main' (if not already done)
git branch -M main

# Push your code to GitHub
git push -u origin main
```

### 3. Verify the Connection

```bash
# Check your remote repositories
git remote -v

# You should see something like:
# origin  https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git (fetch)
# origin  https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git (push)
```

## 🔧 Alternative: Use the Deployment Script

You can also use the provided deployment script:

```bash
# Make sure the script is executable
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

The script will guide you through the GitHub setup process.

## 🔒 Security Considerations

### Before Pushing to GitHub

1. **Check your .gitignore file** - Make sure sensitive files are excluded:
   - `credentials.json`
   - `.env`
   - `token.json`
   - Any other files with API keys

2. **Verify no sensitive data is in your code:**
   ```bash
   # Search for potential API keys in your code
   grep -r "sk-" .
   grep -r "AIza" .
   ```

3. **Use environment variables** for all sensitive data in production

## 📦 Repository Structure

Your GitHub repository should look like this:

```
ai-email-assistant/
├── README.md              # Project documentation
├── requirements.txt       # Python dependencies
├── app.py                # Main Flask application
├── gmail_service.py      # Gmail API integration
├── ai_service.py         # OpenAI API integration
├── email_processor.py    # Email processing logic
├── templates/           # HTML templates
├── static/             # CSS, JS, images
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose configuration
├── Procfile           # Heroku configuration
├── runtime.txt        # Python version specification
├── .gitignore         # Git ignore rules
├── deploy.sh          # Deployment script
└── env_example.txt    # Environment variables example
```

## 🚀 Next Steps After GitHub Setup

### 1. Set Up Environment Variables

Create a `.env` file locally (this won't be pushed to GitHub):

```bash
cp env_example.txt .env
# Edit .env with your actual API keys
```

### 2. Choose Your Deployment Platform

- **Heroku**: Easy deployment with git push
- **Docker**: Containerized deployment
- **VPS**: Manual server deployment
- **Railway**: Modern platform deployment

### 3. Set Up CI/CD (Optional)

Consider setting up GitHub Actions for automated testing and deployment:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
        heroku_app_name: ${{ secrets.HEROKU_APP_NAME }}
        heroku_email: ${{ secrets.HEROKU_EMAIL }}
```

## 🔄 Regular Workflow

After setting up GitHub, your regular workflow will be:

```bash
# Make changes to your code
# Add changes to git
git add .

# Commit changes
git commit -m "Description of your changes"

# Push to GitHub
git push origin main

# Deploy (if using Heroku)
git push heroku main
```

## 🆘 Troubleshooting

### Common Issues

1. **Authentication Error**
   ```bash
   # Set up GitHub CLI or use personal access token
   git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO.git
   ```

2. **Large File Error**
   ```bash
   # Check for large files
   git ls-files | xargs ls -la | sort -k5 -nr | head -10
   ```

3. **Branch Issues**
   ```bash
   # Check current branch
   git branch
   
   # Switch to main branch
   git checkout main
   ```

## 📞 Support

If you encounter issues:

1. Check the [GitHub documentation](https://docs.github.com/)
2. Review your `.gitignore` file
3. Ensure no sensitive data is being committed
4. Check the repository structure matches the expected layout

---

**🎉 Congratulations! Your AI Email Assistant is now ready for deployment!** 