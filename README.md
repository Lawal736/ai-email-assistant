# AI Email Assistant

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-blue?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![DigitalOcean](https://img.shields.io/badge/Deploy-DigitalOcean-blueviolet?style=for-the-badge&logo=digitalocean)](https://www.digitalocean.com/products/app-platform)

A sophisticated, AI-powered email management platform designed to streamline your inbox. This application connects seamlessly with your Gmail account, provides intelligent email analysis, and offers a multi-tiered subscription model with secure payment processing.

## ✨ Core Features

### 👤 User & Account Management
- **Authentication**: Secure user signup, login, and password reset.
- **Google OAuth**: Seamlessly connect your Gmail account with a single click.
- **Account Dashboard**: A personal dashboard to view email summaries, manage settings, and track usage.
- **Subscription Tiers**: Multiple plans (e.g., Free, Pro, Enterprise) with feature gating.
- **Billing Portal**: View payment history and manage your subscription.

### 📧 Email Intelligence
- **AI-Powered Summaries**: Automatically generate concise summaries of long emails and threads.
- **Priority Detection**: Intelligent algorithms to identify and flag important emails.
- **Action Item Extraction**: Pulls out key tasks and deadlines from email content.
- **Document Analysis**: Process and analyze content from attached documents (PDFs, DOCX).
- **VIP Senders**: Automatically identify and manage emails from your most important contacts.

### 💳 Payments & Subscriptions
- **Multi-Gateway Support**: Integrated with **Paystack** for traditional payments and supports **Cryptocurrency** payments.
- **Multi-Currency**: Fetches real-time exchange rates and supports transactions in multiple currencies.
- **Secure Webhooks**: Robust webhook handling for reliable payment status updates.

### 🛡️ Admin Dashboard & Management
- **Analytics Dashboard**: At-a-glance view of key metrics: total users, active subscriptions, and database health.
- **User Management**: A comprehensive interface to **view, edit, delete, and search** for users, with full pagination.
- **Database Tools**: Interface for managing and monitoring the database.
- **System Logs**: View application logs directly from the admin panel.
- **Secure Access**: The admin panel is protected and accessible only to authorized administrators.

## 🛠️ Technology Stack

| Category      | Technology                                    |
|---------------|-----------------------------------------------|
| **Backend**   | Python, Flask, Gunicorn                       |
| **Database**  | PostgreSQL (Production), SQLite (Development) |
| **Frontend**  | HTML, CSS, JavaScript, Bootstrap 5, Jinja2    |
| **AI Services** | OpenAI, Anthropic (configurable)              |
| **Payments**  | Paystack, Web3 (for Crypto)                   |
| **APIs**      | Google (Gmail API), Exchange Rate APIs        |
| **Deployment**| Docker, DigitalOcean App Platform             |

## 🚀 Getting Started

Follow these instructions to set up the project for local development.

### 1. Prerequisites
- Python 3.11+
- Docker & Docker Compose
- A Google Cloud project with OAuth 2.0 credentials (`credentials.json`).
- API keys for OpenAI, Paystack, etc.

### 2. Clone the Repository
```bash
git clone https://github.com/Lawal736/ai-email-assistant.git
cd ai-email-assistant
```

### 3. Configure Environment Variables
Create a `.env` file by copying the example:
```bash
cp env_example.txt .env
```
Now, edit `.env` and fill in your credentials and API keys.

**Key Variables:**
- `FLASK_APP=app.py`
- `FLASK_ENV=development`
- `SECRET_KEY`: A strong, random secret key.
- `DATABASE_URL`: Your PostgreSQL connection string (for production/docker setup).
- `PAYSTACK_SECRET_KEY` & `PAYSTACK_PUBLIC_KEY`
- `GOOGLE_OAUTH_CLIENT_ID` & `GOOGLE_OAUTH_CLIENT_SECRET`
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

### 4. Set Up Google OAuth Credentials
- Go to the [Google Cloud Console](https://console.cloud.google.com/).
- Create a new project.
- Go to "APIs & Services" > "Credentials".
- Create an "OAuth 2.0 Client ID" for a "Web application".
- Add `http://127.0.0.1:5001/oauth2callback` to the "Authorized redirect URIs".
- Download the JSON file, rename it to `credentials.json`, and place it in the project root.

### 5. Running Locally

#### A) With SQLite (Simple)
This method is best for quick, simple local testing.

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run the App:**
    The application will automatically create and use a `users.db` SQLite file.
    ```bash
    flask run
    ```

#### B) With PostgreSQL (Using Docker)
This method mirrors the production environment and is recommended for most development work.

1.  **Build and Run with Docker Compose:**
    Ensure your `.env` file has the `DATABASE_URL` correctly configured to point to the `db` service.
    ```
    # Example DATABASE_URL for Docker Compose
    DATABASE_URL=postgresql://user:password@db:5432/mydatabase
    ```
    ```bash
    docker-compose up --build
    ```
This command will build the Flask application image, start a PostgreSQL container, and run the app, connecting it to the database.

## 🌐 Deployment

This application is configured for easy deployment on the **DigitalOcean App Platform**.

1.  **Push to GitHub**: Make sure your repository is up-to-date.
2.  **Create App on DigitalOcean**:
    - Select your GitHub repository.
    - DigitalOcean will auto-detect the `Dockerfile` and set up a web service.
3.  **Add a Database**:
    - In the "Resources" tab of your app, add a PostgreSQL managed database.
    - DigitalOcean will automatically provide the `DATABASE_URL` as an environment variable, which the application is configured to use.
4.  **Set Environment Variables**:
    - In the App Settings, add all the necessary environment variables from your `.env` file (`SECRET_KEY`, API keys, etc.).
    - Ensure you set `FLASK_ENV=production`.
5.  **Deploy**:
    - Trigger a manual deployment or push a new commit to your main branch. DigitalOcean will automatically build the Docker image and deploy the application.

## ⚙️ Project Structure
```
.
├── app.py                  # Main Flask application logic and routes
├── models.py               # SQLite models and database logic
├── models_postgresql.py    # PostgreSQL models and database logic
├── gmail_service.py        # Handles all Google API interactions
├── ai_service.py           # Logic for AI model interactions
├── payment_service.py      # Paystack and Crypto payment processing
├── Dockerfile              # Instructions to build the production Docker image
├── docker-compose.yml      # Defines services for local development (app + db)
├── requirements.txt        # Python package dependencies
├── deploy.sh               # Deployment script for DigitalOcean
├── templates/              # Jinja2 HTML templates
│   ├── admin/              # Templates for the Admin Dashboard
│   └── ...
└── static/                 # CSS, JavaScript, and image assets
```

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

<!-- Last updated: 2025-06-19 20:50 UTC - PostgreSQL models restored --> 