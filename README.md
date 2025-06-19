# AI-Powered Email Assistant Web App

A comprehensive email management platform that integrates Gmail API, AI analysis, and payment processing to help users efficiently manage their email communications.

## 🚀 Features

### Core Email Management
- **Gmail Integration**: Seamless OAuth2 authentication with Gmail API
- **Email Analysis**: AI-powered analysis of email content, sentiment, and priority
- **Smart Filtering**: Automatic filtering of social media, automated, and promotional emails
- **Email Threading**: Intelligent grouping of related emails into conversation threads
- **Daily Summaries**: Automated daily email summaries with key insights

### AI-Powered Features
- **Advanced AI Analysis**: Deep analysis of email content using GPT-4 and Claude models
- **Action Item Extraction**: Automatic identification and extraction of action items from emails
- **Response Recommendations**: AI-generated response suggestions for emails
- **Custom Insights**: Pro users can create custom analysis criteria for specific email patterns
- **Document Processing**: AI-powered analysis of email attachments (PDFs, Excel files, etc.)

### Subscription Management
- **Multi-Tier Plans**: Free, Pro, and Enterprise subscription levels
- **Flexible Billing**: Monthly and annual billing options
- **Payment Processing**: Integrated Paystack payment gateway with multi-currency support
- **Subscription Features**: Feature gating based on subscription levels
- **Billing History**: Complete payment and subscription history tracking

### User Experience
- **Modern UI**: Clean, responsive design with Bootstrap 5
- **Real-time Updates**: Live email processing and analysis
- **Account Management**: Comprehensive user profile and settings management
- **Gmail Account Linking**: Easy connection and disconnection of Gmail accounts
- **Currency Support**: Multi-currency support with automatic exchange rate updates

## 🛠️ Technical Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **AI Services**: OpenAI GPT-4, Anthropic Claude (Sonnet, Haiku)
- **Email API**: Gmail API v1
- **Payment**: Paystack integration
- **Authentication**: Session-based with OAuth2 for Gmail

### Frontend
- **Framework**: Bootstrap 5
- **JavaScript**: Vanilla JS with AJAX
- **Templates**: Jinja2 templating engine
- **Styling**: Custom CSS with responsive design

### External Services
- **Gmail API**: Email access and management
- **OpenAI API**: GPT-4 for advanced analysis
- **Anthropic API**: Claude models for efficient processing
- **Paystack**: Payment processing and webhooks
- **Exchange Rate API**: Real-time currency conversion

## 📋 Recent Updates & Improvements

### Gmail Integration Enhancements
- ✅ Fixed Gmail account switching issues
- ✅ Added proper Gmail email address tracking
- ✅ Implemented Gmail account disconnection functionality
- ✅ Enhanced OAuth2 flow with proper error handling
- ✅ Added Gmail profile information display

### Payment System Improvements
- ✅ Multi-currency support (USD, NGN, EUR, etc.)
- ✅ Real-time exchange rate updates
- ✅ Enhanced Paystack integration
- ✅ Improved billing history display
- ✅ Fixed subscription activation issues
- ✅ Added payment method tracking

### User Experience Enhancements
- ✅ Added member since and last login tracking
- ✅ Enhanced account page with detailed user information
- ✅ Improved subscription status display
- ✅ Added features page with plan comparison
- ✅ Enhanced dashboard with better email insights
- ✅ Added tooltips for pricing plans

### AI Features
- ✅ Hybrid AI service with multiple model support
- ✅ Custom insights for Pro users
- ✅ Enhanced email analysis with action items
- ✅ Document processing capabilities
- ✅ Improved response recommendations

## 🏗️ Project Structure

```
├── app.py                      # Main Flask application
├── models.py                   # Database models and user management
├── gmail_service.py           # Gmail API integration
├── ai_service.py              # AI analysis services
├── payment_service.py         # Payment processing
├── currency_service.py        # Currency conversion
├── email_processor.py         # Email processing logic
├── document_processor.py      # Document analysis
├── templates/                 # HTML templates
│   ├── base.html             # Base template
│   ├── dashboard.html        # Main dashboard
│   ├── account.html          # User account page
│   ├── features.html         # Features page
│   ├── pricing.html          # Pricing page
│   └── payment/              # Payment templates
├── static/                   # Static assets
└── users.db                  # SQLite database
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Gmail account
- OpenAI API key
- Anthropic API key
- Paystack account (for payments)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-email-assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   export OPENAI_API_KEY="your-openai-key"
   export ANTHROPIC_API_KEY="your-anthropic-key"
   export PAYSTACK_SECRET_KEY="your-paystack-key"
   ```

4. **Set up Gmail API**
   - Create a project in Google Cloud Console
   - Enable Gmail API
   - Download credentials.json
   - Place in project root

5. **Initialize database**
   ```bash
   python -c "from models import *; init_db()"
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

## 💳 Subscription Plans

### Free Plan
- Basic email analysis
- Limited AI features
- Standard email filtering
- Basic dashboard

### Pro Plan ($9.99/month)
- Advanced AI analysis
- Custom insights
- Document processing
- Priority support
- Enhanced email insights

### Enterprise Plan ($29.99/month)
- All Pro features
- Custom integrations
- Advanced analytics
- Dedicated support
- API access

## 🔧 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
PAYSTACK_SECRET_KEY=your-paystack-secret-key
PAYSTACK_PUBLIC_KEY=your-paystack-public-key
FLASK_SECRET_KEY=your-flask-secret-key
```

### Database Configuration
The app uses SQLite by default. For production, consider using PostgreSQL or MySQL.

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 📊 API Endpoints

### Authentication
- `POST /login` - User login
- `POST /register` - User registration
- `GET /logout` - User logout

### Gmail Integration
- `GET /connect-gmail` - Gmail connection page
- `GET /start-gmail-auth` - Start OAuth flow
- `GET /oauth2callback` - OAuth callback
- `POST /api/disconnect-gmail` - Disconnect Gmail

### Email Analysis
- `GET /api/emails` - Get user emails
- `GET /api/summary` - Get daily summary
- `POST /api/analyze-email` - Analyze specific email
- `POST /api/custom-insights` - Custom email analysis

### Payment & Subscription
- `GET /pricing` - Pricing page
- `POST /payment/process` - Process payment
- `GET /payment/success` - Payment success
- `GET /payment/cancel` - Payment cancellation

## 🔒 Security Features

- OAuth2 authentication for Gmail
- Session-based user authentication
- Secure payment processing
- API key encryption
- Input validation and sanitization

## 🌐 Deployment

### Production Setup
1. Use a production WSGI server (Gunicorn)
2. Set up HTTPS with SSL certificates
3. Configure environment variables
4. Set up database backups
5. Configure monitoring and logging

### Docker Deployment
```bash
docker build -t ai-email-assistant .
docker run -p 5000:5000 ai-email-assistant
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Contact the development team

## 🔄 Version History

### v2.0.0 (Current)
- Enhanced Gmail integration with account switching
- Multi-currency support with real-time exchange rates
- Improved AI analysis with hybrid model support
- Better user experience with member tracking
- Comprehensive payment system with Paystack
- Document processing capabilities
- Custom insights for Pro users
- Enhanced dashboard and account management

### v1.0.0
- Initial release
- Basic email analysis
- Gmail integration
- Payment processing

## 🎯 Key Achievements

### Technical Milestones
- ✅ Seamless Gmail account switching and management
- ✅ Multi-currency payment processing with Paystack
- ✅ Hybrid AI service with OpenAI and Anthropic integration
- ✅ Real-time email analysis and processing
- ✅ Comprehensive user account management
- ✅ Advanced subscription and billing system

### User Experience
- ✅ Modern, responsive UI with Bootstrap 5
- ✅ Intuitive email management interface
- ✅ Clear subscription plan comparison
- ✅ Detailed billing and payment history
- ✅ Easy Gmail account connection/disconnection
- ✅ Real-time currency conversion

### Business Features
- ✅ Three-tier subscription model (Free, Pro, Enterprise)
- ✅ Flexible billing options (monthly/annual)
- ✅ Multi-currency support for global users
- ✅ Feature gating based on subscription levels
- ✅ Comprehensive payment tracking and history

## AI Providers Support

This application supports multiple AI providers for intelligent email analysis and processing:

### Supported Providers

1. **DeepSeek** (Primary)
   - Models: DeepSeek Chat, DeepSeek Coder
   - Best for: Technical emails, coding-related content, cost-effective analysis
   - Environment variable: `DEEPSEEK_API_KEY`

2. **Google Gemini** (Secondary)
   - Models: Gemini 1.5 Pro, Gemini 1.5 Flash
   - Best for: Fast processing, cost-effective analysis, business emails
   - Environment variable: `GEMINI_API_KEY`

3. **Anthropic Claude** (Tertiary)
   - Models: Claude 3.5 Sonnet, Claude 3 Haiku
   - Best for: Complex analysis, nuanced understanding, high-quality responses
   - Environment variable: `ANTHROPIC_API_KEY`

4. **OpenAI GPT** (Fallback)
   - Models: GPT-3.5 Turbo
   - Best for: Reliable fallback option
   - Environment variable: `OPENAI_API_KEY`

### Setup Instructions

1. **Get API Keys:**
   - [DeepSeek](https://platform.deepseek.com/)
   - [Google Gemini](https://makersuite.google.com/app/apikey)
   - [Anthropic Claude](https://console.anthropic.com/)
   - [OpenAI](https://platform.openai.com/api-keys)

2. **Configure Environment Variables:**
   ```bash
   # Copy the example file
   cp env_example.txt .env
   
   # Edit .env and add your API keys
   DEEPSEEK_API_KEY=your_deepseek_key
   GEMINI_API_KEY=your_gemini_key
   ANTHROPIC_API_KEY=your_anthropic_key
   OPENAI_API_KEY=your_openai_key
   ```

3. **Provider Selection Logic:**
   - **Complex emails**: DeepSeek Chat → Gemini Pro → Claude Sonnet
   - **Simple emails**: DeepSeek Chat → Gemini Flash → Claude Haiku
   - **Coding tasks**: DeepSeek Coder (automatically selected)
   - **Fallback**: Automatic fallback to available providers in priority order

### Benefits of Multiple Providers

- **Cost Optimization**: Use cheaper models for simple tasks
- **Reliability**: Automatic fallback if one provider fails
- **Performance**: Choose the best model for each task type
- **Flexibility**: Mix and match providers based on your needs

---

**Built with ❤️ using Flask, Gmail API, and AI services**

*Last updated: June 2025*

## Deployment (Digital Ocean)

This project is now deployed and maintained on Digital Ocean App Platform.

### Quick Start for Digital Ocean

1. **Clone the repository:**
   ```sh
   git clone https://github.com/Lawal736/ai-email-assistant.git
   cd ai-email-assistant
   ```
2. **Set up your `.env` file:**
   - Copy `env_example.txt` to `.env` and fill in your secrets and API keys.
3. **Build and run locally (optional):**
   ```sh
   docker-compose up --build
   ```
4. **Deploy to Digital Ocean:**
   - Push your changes to GitHub.
   - Connect your repo to Digital Ocean App Platform.
   - Set environment variables in the Digital Ocean dashboard.
   - The platform will build and deploy automatically using the `Dockerfile`.

### Environment Variables
See `env_example.txt` for all required variables.

### Notes
- All GCP-specific scripts and configs have been removed.
- For local development, you can use Docker Compose or run with Python directly.
- For production, use Digital Ocean App Platform with the provided Dockerfile. 