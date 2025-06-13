# 🤖 AI Email Assistant

A smart email management system that uses AI to analyze, summarize, and provide recommendations for your Gmail inbox.

## ✨ Features

- **📧 Gmail Integration**: Secure OAuth2 authentication with Gmail API
- **🤖 AI-Powered Analysis**: OpenAI GPT integration for email insights
- **📊 Daily Summaries**: Automated daily email summaries and action items
- **🎯 Smart Recommendations**: AI-generated response recommendations
- **📱 Modern UI**: Beautiful, responsive web interface
- **🔄 Real-time Updates**: Live email processing and analysis
- **🛡️ Secure**: No email data stored permanently

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Gmail account
- OpenAI API key
- Google Cloud Console project

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ai-email-assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env_example.txt .env
   # Edit .env with your API keys
   ```

4. **Configure Gmail API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download `credentials.json` to project root

5. **Set up OpenAI API**
   - Get your API key from [OpenAI Platform](https://platform.openai.com/)
   - Add it to your `.env` file

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the app**
   - Open http://localhost:5001
   - Connect your Gmail account
   - Start managing your emails with AI!

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Gmail API Configuration
# credentials.json should be placed in project root
```

### Gmail API Setup

1. **Enable Gmail API**
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Select your project
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it

2. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application" for production or "Desktop application" for development
   - Add authorized redirect URIs: `http://localhost:5001/oauth2callback`
   - Download the credentials file as `credentials.json`

## 📁 Project Structure

```
ai-email-assistant/
├── app.py                 # Main Flask application
├── gmail_service.py       # Gmail API integration
├── ai_service.py          # OpenAI API integration
├── email_processor.py     # Email processing logic
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   └── ...
├── static/              # CSS, JS, images
├── credentials.json     # Gmail API credentials (not in repo)
├── .env                # Environment variables (not in repo)
└── README.md
```

## 🛠️ Development

### Running in Development Mode

```bash
python app.py
```

The app will run on http://localhost:5001 with debug mode enabled.

### Testing

```bash
# Test Gmail authentication
python test_gmail_auth.py

# Test OpenAI API
python check_openai_status.py

# Setup environment
python setup_env.py
```

## 🚀 Deployment

### Heroku Deployment

1. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables**
   ```bash
   heroku config:set OPENAI_API_KEY=your_key
   heroku config:set FLASK_SECRET_KEY=your_secret
   ```

3. **Add Gmail credentials**
   ```bash
   heroku config:set GOOGLE_CREDENTIALS="$(cat credentials.json)"
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

### Docker Deployment

1. **Build image**
   ```bash
   docker build -t ai-email-assistant .
   ```

2. **Run container**
   ```bash
   docker run -p 5001:5001 ai-email-assistant
   ```

## 🔒 Security

- **API Keys**: Never commit API keys to version control
- **OAuth Tokens**: Stored securely in session and temporary files
- **Email Data**: Processed in memory, not stored permanently
- **HTTPS**: Use HTTPS in production for secure data transmission

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Gmail API Quota Exceeded**
   - Check your Google Cloud Console quotas
   - Enable billing if required

2. **OpenAI API Quota Exceeded**
   - Check your OpenAI billing and usage
   - Upgrade your plan if needed

3. **OAuth Redirect URI Mismatch**
   - Ensure redirect URI in Google Cloud Console matches your app URL
   - For local development: `http://localhost:5001/oauth2callback`

4. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 📞 Support

If you encounter any issues:

1. Check the troubleshooting section above
2. Review the logs in your terminal
3. Ensure all API keys and credentials are properly configured
4. Create an issue on GitHub with detailed error information

## 🎯 Roadmap

- [ ] Email scheduling and automation
- [ ] Advanced email filtering
- [ ] Multi-language support
- [ ] Mobile app
- [ ] Team collaboration features
- [ ] Advanced analytics dashboard

---

**Made with ❤️ for better email management** 