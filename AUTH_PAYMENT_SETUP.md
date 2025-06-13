# AI Email Assistant - Authentication & Payment Setup Guide

This guide will help you set up the AI Email Assistant with user authentication, subscription management, and payment processing (both Stripe and crypto payments).

## 🚀 Quick Start

1. **Run the setup script:**
   ```bash
   python setup_auth_payment.py
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your environment variables in `.env**

4. **Start the application:**
   ```bash
   python app.py
   ```

## 📋 Features

### Authentication System
- ✅ User registration and login
- ✅ Password hashing with bcrypt
- ✅ Session management
- ✅ Password reset functionality
- ✅ Email verification (optional)

### Payment System
- ✅ **Stripe Integration** - Credit card payments
- ✅ **Crypto Payments** - USDT (ERC20) on Ethereum
- ✅ Subscription management
- ✅ Usage tracking
- ✅ Billing history
- ✅ Payment webhooks

### Subscription Plans
- **Free Plan**: 50 emails/month, basic features
- **Pro Plan**: $19.99/month, 1,000 emails/month
- **Enterprise Plan**: $49.99/month, 10,000 emails/month

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DEBUG=True
PORT=5001

# Database
DATABASE_URL=sqlite:///ai_email_assistant.db

# Gmail API
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret

# AI APIs
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Stripe Payment
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Crypto Payment (Web3)
INFURA_URL=https://mainnet.infura.io/v3/your_project_id
USDT_CONTRACT_ADDRESS=0x75Fc169eD2832e33F74D31430249e09c09358A75
```

## 🔗 API Setup

### Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client IDs**
5. Set application type to **Web application**
6. Add authorized redirect URIs:
   - Development: `http://localhost:5001/oauth2callback`
   - Production: `https://yourdomain.com/oauth2callback`
7. Copy Client ID and Client Secret to `.env`

### AI API Setup

#### OpenAI API
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy to `OPENAI_API_KEY` in `.env`

#### Anthropic API (Claude)
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create account and get API key
3. Copy to `ANTHROPIC_API_KEY` in `.env`

## 💳 Payment Setup

### Stripe Setup

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Create account or sign in
3. Go to **Developers** → **API keys**
4. Copy Publishable key and Secret key
5. Update `.env` with your keys
6. For webhooks:
   - Go to **Developers** → **Webhooks**
   - Add endpoint: `https://yourdomain.com/payment/webhook`
   - Copy webhook secret to `.env`

### Crypto Payment Setup (USDT)

#### Web3 Provider Setup

Choose one of these providers:

**Infura (Recommended):**
1. Go to [Infura](https://infura.io/)
2. Create account and new project
3. Copy Ethereum mainnet endpoint
4. Update `INFURA_URL` in `.env`

**Alchemy:**
1. Go to [Alchemy](https://alchemy.com/)
2. Create account and app
3. Copy HTTP endpoint
4. Update `ALCHEMY_URL` in `.env`

**QuickNode:**
1. Go to [QuickNode](https://quicknode.com/)
2. Create account and endpoint
3. Copy HTTP endpoint
4. Update `QUICKNODE_URL` in `.env`

#### USDT Configuration

The USDT contract address is pre-configured:
- **Contract**: `0x75Fc169eD2832e33F74D31430249e09c09358A75`
- **Network**: Ethereum Mainnet
- **Token**: USDT (ERC20)
- **Decimals**: 6

## 🗄️ Database Setup

The application uses SQLite by default. The database will be created automatically with the following tables:

- `users` - User accounts and authentication
- `subscription_plans` - Available subscription plans
- `payment_records` - Payment history and billing
- `usage_tracking` - API usage monitoring

Default plans are created automatically:
- Free Plan (0 emails/month)
- Pro Plan ($19.99/month, 1,000 emails/month)
- Enterprise Plan ($49.99/month, 10,000 emails/month)

## 🔐 Security Features

### Authentication Security
- Password hashing with bcrypt
- Session-based authentication
- CSRF protection
- Secure cookie settings

### Payment Security
- Stripe PCI compliance
- Webhook signature verification
- Crypto payment verification
- Transaction logging

### Data Security
- Environment variable protection
- SQL injection prevention
- XSS protection
- Secure headers

## 🚀 Production Deployment

### Environment Setup
```env
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-production-secret-key
```

### Web Server Setup
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

### SSL Configuration
- Set up SSL certificates (Let's Encrypt recommended)
- Configure HTTPS redirects
- Update OAuth redirect URIs

### Database Setup
For production, consider using PostgreSQL:
```env
DATABASE_URL=postgresql://user:password@localhost/ai_email_assistant
```

## 📊 Usage Tracking

The system tracks:
- Email processing usage
- AI API calls
- Payment transactions
- User activity

Usage limits are enforced per subscription plan.

## 🔄 Payment Flow

### Stripe Payment Flow
1. User selects plan and payment method
2. Stripe checkout session created
3. User completes payment
4. Webhook processes successful payment
5. Subscription activated

### Crypto Payment Flow
1. User selects crypto payment
2. Payment session created with USDT amount
3. User sends USDT to specified address
4. Payment verification checks blockchain
5. Subscription activated upon verification

## 🛠️ Troubleshooting

### Common Issues

**Gmail Authentication:**
- Check OAuth redirect URIs
- Verify client ID/secret
- Ensure Gmail API is enabled

**Payment Issues:**
- Verify Stripe keys
- Check webhook configuration
- Ensure crypto provider is accessible

**Database Issues:**
- Check file permissions
- Verify SQLite installation
- Check database path

### Logs and Debugging

Enable debug mode for detailed logs:
```env
DEBUG=True
FLASK_ENV=development
```

Check application logs for error details.

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review application logs
- Contact support with error details

## 🔄 Updates

To update the application:
1. Backup your database
2. Pull latest changes
3. Run `pip install -r requirements.txt`
4. Restart the application

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

---

**Note**: This is a development setup. For production use, ensure all security best practices are followed and proper SSL certificates are configured. 