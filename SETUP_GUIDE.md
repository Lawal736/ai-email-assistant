# AI Email Assistant - Setup Guide

This guide will walk you through setting up the AI Email Assistant step by step.

## Prerequisites

- Python 3.8 or higher
- Gmail account
- OpenAI API key
- Google Cloud Console account

## Step 1: Clone and Setup Project

1. **Clone or download the project files**
2. **Navigate to the project directory**
3. **Run the setup script:**
   ```bash
   python setup.py
   ```

## Step 2: Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to "API Keys" in your dashboard
4. Create a new API key
5. Copy the API key (it starts with `sk-`)

## Step 3: Configure Gmail API

### 3.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "AI Email Assistant")
4. Click "Create"

### 3.2 Enable Gmail API

1. In the Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for "Gmail API"
3. Click on "Gmail API"
4. Click "Enable"

### 3.3 Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. If prompted, configure the OAuth consent screen:
   - User Type: External
   - App name: "AI Email Assistant"
   - User support email: Your email
   - Developer contact information: Your email
4. Click "Save and Continue" through the remaining steps
5. Back in "Credentials", click "Create Credentials" → "OAuth 2.0 Client IDs"
6. Application type: "Desktop application"
7. Name: "AI Email Assistant Desktop"
8. Click "Create"
9. Download the JSON file and rename it to `credentials.json`
10. Place `credentials.json` in the project root directory

## Step 4: Configure Environment Variables

1. Open the `.env` file in the project directory
2. Replace `your_openai_api_key_here` with your actual OpenAI API key
3. Replace `your_flask_secret_key_here` with a random secret key (you can generate one with `python -c "import secrets; print(secrets.token_hex(16))"`)

Example `.env` file:
```env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
FLASK_SECRET_KEY=your-generated-secret-key-here
FLASK_ENV=development
```

## Step 5: Install Dependencies

If the setup script didn't install dependencies automatically:

```bash
pip install -r requirements.txt
```

## Step 6: Run the Application

1. **Start the application:**
   ```bash
   python app.py
   ```

2. **Open your browser and go to:**
   ```
   http://localhost:5000
   ```

3. **Connect your Gmail account:**
   - Click "Connect Gmail"
   - Follow the OAuth flow
   - Grant necessary permissions

## Step 7: Using the Application

### Dashboard Features

1. **Daily Summary**: AI-generated overview of your emails
2. **Action Items**: Extracted tasks and deadlines
3. **Response Recommendations**: AI-suggested responses
4. **Email List**: Recent emails with priority indicators

### Key Features

- **Email Prioritization**: Emails are automatically categorized by priority
- **Smart Summaries**: AI analyzes email content and provides insights
- **Action Extraction**: Identifies tasks, deadlines, and follow-ups
- **Response Suggestions**: Professional response recommendations
- **Secure Processing**: Emails are processed securely and not stored permanently

## Troubleshooting

### Common Issues

1. **"credentials.json not found"**
   - Make sure you downloaded the OAuth credentials from Google Cloud Console
   - Ensure the file is named `credentials.json` and is in the project root

2. **"OPENAI_API_KEY not found"**
   - Check that your `.env` file exists and contains the correct API key
   - Ensure the API key is valid and has sufficient credits

3. **Gmail authentication fails**
   - Make sure you've enabled the Gmail API in Google Cloud Console
   - Check that your OAuth consent screen is configured
   - Try clearing your browser cache and cookies

4. **Import errors**
   - Run `pip install -r requirements.txt` to install all dependencies
   - Make sure you're using Python 3.8 or higher

### Getting Help

If you encounter issues:

1. Check the console output for error messages
2. Verify all configuration files are in place
3. Ensure all dependencies are installed
4. Check that your API keys are valid and have sufficient credits

## Security Notes

- Never commit your `.env` file or `credentials.json` to version control
- Keep your API keys secure and don't share them
- The application processes emails temporarily and doesn't store them permanently
- All Gmail access is handled through secure OAuth2 authentication

## API Usage

The application uses:
- **OpenAI GPT-4**: For email analysis and response generation
- **Gmail API**: For reading and sending emails
- **Flask**: For the web interface

Monitor your API usage to avoid unexpected charges.

## Customization

You can customize the application by:
- Modifying the AI prompts in `ai_service.py`
- Adjusting email classification rules in `email_processor.py`
- Customizing the UI in the template files
- Adding new features to the Flask routes

## Support

For additional help or feature requests, please refer to the project documentation or create an issue in the project repository. 