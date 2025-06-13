# �� AI Email Assistant Pro

A comprehensive AI-powered email management system with user authentication, subscription plans, and advanced email analysis capabilities.

## ✨ Features

### 🔐 User Management
- **User Registration & Authentication**: Secure signup/login with password reset
- **Profile Management**: User profiles with subscription tracking
- **Session Management**: Secure session handling with login required decorators

### 💳 Subscription & Payment System
- **Multiple Payment Methods**: Stripe (credit cards) and USDT (crypto) payments
- **Subscription Plans**: Free, Pro, and Enterprise tiers with different limits
- **Usage Tracking**: Monitor API usage and enforce plan limits
- **Billing Management**: Complete billing history and subscription management

### 📧 Advanced Email Processing
- **Gmail Integration**: Secure OAuth2 authentication with Gmail API
- **Email Threading**: Intelligent email conversation grouping
- **Attachment Processing**: Support for PDF, Excel, Word, and image files
- **Smart Filtering**: Automated filtering of newsletters and promotional emails

### 🤖 Hybrid AI Analysis
- **Multi-Model Support**: OpenAI GPT-4, Claude Sonnet, and Claude Haiku
- **Intelligent Model Selection**: Automatic model selection based on task complexity
- **Email Summaries**: AI-generated daily email summaries
- **Action Items**: Extract actionable tasks from emails
- **Response Recommendations**: AI-suggested email responses
- **Document Analysis**: AI-powered analysis of email attachments

### 📊 Dashboard & Analytics
- **Real-time Dashboard**: Live email processing and analysis
- **Email Threads**: Organized conversation view
- **Usage Analytics**: Track API usage and plan limits
- **Modern UI**: Beautiful, responsive web interface with Bootstrap 5

### 🔒 Security & Privacy
- **Secure Authentication**: Password hashing and secure session management
- **API Key Protection**: Environment-based configuration
- **Data Privacy**: No permanent email storage, in-memory processing only
- **HTTPS Ready**: Production-ready security configurations

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Gmail account
- OpenAI API key
- Google Cloud Console project
- Stripe account (for payments)
- Optional: Web3 provider (for crypto payments)

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
   # Edit .env with your API keys and configuration
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

6. **Configure Stripe (for payments)**
   - Create a Stripe account
   - Get your API keys from Stripe Dashboard
   - Add them to your `.env` file

7. **Initialize the database**
   ```bash
   python setup_auth_payment.py
   ```

8. **Run the application**
   ```bash
   python app.py
   ```

9. **Access the app**
   - Open http://localhost:5001
   - Sign up for an account
   - Connect your Gmail account
   - Choose a subscription plan
   - Start managing your emails with AI!

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Configuration (for Claude models)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Stripe Configuration
STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Web3 Configuration (for crypto payments)
INFURA_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Gmail API Configuration
# credentials.json should be placed in project root
```

### Database Setup

The application uses SQLite for development. Run the setup script to initialize:

```bash
python setup_auth_payment.py
```

This will:
- Create the database with all required tables
- Set up subscription plans
- Initialize payment configurations

## 📁 Project Structure

```
ai-email-assistant/
├── app.py                    # Main Flask application
├── models.py                 # Database models and ORM
├── payment_service.py        # Payment processing (Stripe + Crypto)
├── gmail_service.py          # Gmail API integration
├── ai_service.py             # AI service with hybrid model support
├── email_processor.py        # Email processing and threading
├── document_processor.py     # Attachment processing
├── requirements.txt          # Python dependencies
├── templates/               # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── auth/
│   ├── payment/
│   └── account/
├── static/                  # CSS, JS, images
├── credentials.json         # Gmail API credentials (not in repo)
├── .env                     # Environment variables (not in repo)
├── users.db                 # SQLite database (not in repo)
├── setup_auth_payment.py    # Database initialization
├── deploy.sh                # Deployment script
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Docker compose
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

# Test payment system
python test_crypto_payment.py

# Test document processing
python test_document_processing.py

# Test hybrid AI
python test_hybrid_ai.py

# Setup environment
python setup_env.py
```

### Database Management

```bash
# Initialize database
python setup_auth_payment.py

# Reset database
rm users.db
python setup_auth_payment.py
```

## 💳 Payment System

### Supported Payment Methods

1. **Stripe (Credit/Debit Cards)**
   - Visa, Mastercard, American Express
   - Secure payment processing
   - Automatic subscription management

2. **USDT (Cryptocurrency)**
   - ERC20 USDT on Ethereum network
   - Manual payment verification
   - Wallet address-based tracking

### Subscription Plans

- **Free**: 50 emails/month, basic features
- **Pro**: 500 emails/month, advanced AI analysis
- **Enterprise**: Unlimited emails, priority support

## 🤖 AI Features

### Hybrid AI System

The application uses multiple AI models for optimal performance:

- **Claude Sonnet**: Complex analysis and summaries
- **Claude Haiku**: Quick tasks and simple analysis
- **OpenAI GPT-4**: Fallback for advanced features

### Email Analysis Features

- **Daily Summaries**: AI-generated overview of daily emails
- **Action Items**: Extract actionable tasks from emails
- **Response Recommendations**: AI-suggested email responses
- **Document Analysis**: Process and analyze email attachments
- **Email Threading**: Group related emails into conversations

## 🚀 Deployment

### Heroku Deployment

1. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables**
   ```bash
   heroku config:set OPENAI_API_KEY=your_key
   heroku config:set ANTHROPIC_API_KEY=your_key
   heroku config:set STRIPE_PUBLIC_KEY=your_key
   heroku config:set STRIPE_SECRET_KEY=your_key
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

3. **Using Docker Compose**
   ```bash
   docker-compose up -d
   ```

### Production Deployment

Use the provided deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

## 🔒 Security

- **API Keys**: Never commit API keys to version control
- **OAuth Tokens**: Stored securely in session and temporary files
- **Email Data**: Processed in memory, not stored permanently
- **HTTPS**: Use HTTPS in production for secure data transmission
- **Password Security**: Bcrypt hashing for user passwords
- **Session Security**: Secure session management with timeouts

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

3. **Payment Processing Errors**
   - Verify Stripe API keys are correct
   - Check webhook configuration
   - Ensure proper SSL in production

4. **OAuth Redirect URI Mismatch**
   - Ensure redirect URI in Google Cloud Console matches your app URL
   - For local development: `http://localhost:5001/oauth2callback`

5. **Database Issues**
   - Run `python setup_auth_payment.py` to reinitialize
   - Check file permissions for `users.db`

6. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 📞 Support

If you encounter any issues:

1. Check the troubleshooting section above
2. Review the logs in your terminal
3. Ensure all API keys and credentials are properly configured
4. Check the documentation files in the project
5. Create an issue on GitHub with detailed error information

## 📚 Documentation

Additional documentation files:

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup instructions
- [AUTH_PAYMENT_SETUP.md](AUTH_PAYMENT_SETUP.md) - Authentication and payment setup
- [HYBRID_AI_GUIDE.md](HYBRID_AI_GUIDE.md) - AI system configuration
- [USER_EXPERIENCE_IMPROVEMENTS.md](USER_EXPERIENCE_IMPROVEMENTS.md) - UX features
- [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) - Deployment guide
- [GITHUB_SETUP.md](GITHUB_SETUP.md) - GitHub repository setup

## 🎯 Roadmap

- [x] User authentication and registration
- [x] Subscription and payment system
- [x] Hybrid AI with multiple models
- [x] Document processing and analysis
- [x] Email threading and organization
- [ ] Email scheduling and automation
- [ ] Advanced email filtering rules
- [ ] Multi-language support
- [ ] Mobile app
- [ ] Team collaboration features
- [ ] Advanced analytics dashboard
- [ ] API rate limiting and optimization
- [ ] Email backup and export features

## 🏆 Features Completed

✅ **Core Email Management**
- Gmail OAuth integration
- Email fetching and processing
- Real-time dashboard

✅ **AI-Powered Analysis**
- Daily email summaries
- Action item extraction
- Response recommendations
- Document analysis

✅ **User Management**
- User registration and login
- Password reset functionality
- Profile management
- Session handling

✅ **Subscription System**
- Multiple subscription tiers
- Usage tracking and limits
- Payment processing (Stripe + Crypto)
- Billing management

✅ **Advanced Features**
- Email threading
- Attachment processing
- Hybrid AI model selection
- Modern responsive UI

---

**Made with ❤️ for better email management**

*Transform your email workflow with AI-powered insights and automation.* 