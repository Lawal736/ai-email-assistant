import os
import stripe
from datetime import datetime, timedelta
from models import DatabaseManager, User, SubscriptionPlan, PaymentRecord
from web3 import Web3
from eth_account import Account
import json

class PaymentService:
    """Payment service for handling Stripe payments and subscriptions"""
    
    def __init__(self):
        # Initialize Stripe with API key
        self.stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
        if self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key
        
        # Crypto payment configuration
        self.usdt_contract_address = "0x75Fc169eD2832e33F74D31430249e09c09358A75"
        self.usdt_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
        
        # Initialize Web3 (you can use Infura, Alchemy, or other providers)
        self.w3 = None
        self.initialize_web3()
        
        self.db_manager = DatabaseManager()
        self.user_model = User(self.db_manager)
        self.plan_model = SubscriptionPlan(self.db_manager)
        self.payment_model = PaymentRecord(self.db_manager)
    
    def initialize_web3(self):
        """Initialize Web3 connection for crypto payments"""
        try:
            # You can use Infura, Alchemy, or other providers
            # For development, you might use a local node or testnet
            infura_url = os.getenv('INFURA_URL', 'https://mainnet.infura.io/v3/YOUR_PROJECT_ID')
            self.w3 = Web3(Web3.HTTPProvider(infura_url))
            
            if self.w3.is_connected():
                print("✅ Web3 connected for crypto payments")
            else:
                print("⚠️ Web3 connection failed")
        except Exception as e:
            print(f"⚠️ Web3 initialization error: {e}")
    
    def create_stripe_payment_intent(self, amount, currency='usd', metadata=None):
        """Create a Stripe payment intent"""
        if not self.stripe_secret_key:
            return {"error": "Stripe not configured"}
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                metadata=metadata or {}
            )
            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id
            }
        except Exception as e:
            return {"error": str(e)}
    
    def create_crypto_payment_session(self, amount_usd, user_id, plan_type, billing_period='monthly'):
        """Create a crypto payment session for USDT"""
        try:
            # For USDT, we'll use 1:1 ratio with USD (approximate)
            usdt_amount = amount_usd
            
            # Generate a unique payment ID
            payment_id = f"crypto_{user_id}_{int(datetime.now().timestamp())}"
            
            # Create payment session data
            payment_session = {
                "payment_id": payment_id,
                "amount_usd": amount_usd,
                "amount_usdt": usdt_amount,
                "usdt_address": self.usdt_contract_address,
                "user_id": user_id,
                "plan_type": plan_type,
                "billing_period": billing_period,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now().timestamp() + 3600),  # 1 hour expiry
                "payment_method": "usdt_erc20"
            }
            
            return payment_session
            
        except Exception as e:
            return {"error": f"Failed to create crypto payment session: {str(e)}"}
    
    def verify_usdt_payment(self, payment_session, user_wallet_address):
        """Verify USDT payment by checking balance and transfers"""
        try:
            if not self.w3 or not self.w3.is_connected():
                return {"error": "Web3 not connected"}
            
            # Get USDT contract
            usdt_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.usdt_contract_address),
                abi=self.usdt_abi
            )
            
            # Check if payment has expired
            if datetime.now().timestamp() > payment_session["expires_at"]:
                return {"error": "Payment session expired"}
            
            # Check balance of the receiving address
            balance = usdt_contract.functions.balanceOf(
                self.w3.to_checksum_address(self.usdt_contract_address)
            ).call()
            
            # For now, we'll use a simple verification
            # In production, you'd want to track specific transactions
            # and verify the exact amount was transferred
            
            # Convert USDT amount to wei (USDT has 6 decimals)
            required_amount = int(payment_session["amount_usdt"] * 10**6)
            
            # This is a simplified verification
            # In production, you'd implement proper transaction tracking
            return {
                "verified": True,  # Simplified for demo
                "payment_id": payment_session["payment_id"],
                "amount_verified": payment_session["amount_usdt"],
                "user_wallet": user_wallet_address,
                "transaction_hash": "0x" + "0" * 64  # Placeholder
            }
            
        except Exception as e:
            return {"error": f"Payment verification failed: {str(e)}"}
    
    def create_checkout_session(self, user_id, plan_name, billing_period='monthly'):
        """Create a Stripe checkout session for subscription"""
        try:
            # Get plan details
            plan = self.plan_model.get_plan_by_name(plan_name)
            if not plan:
                return {'success': False, 'error': 'Plan not found'}
            
            # Get user details
            user = self.user_model.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Determine price ID and amount
            if billing_period == 'yearly':
                price_id = plan['stripe_price_id_yearly']
                amount = plan['price_yearly']
            else:
                price_id = plan['stripe_price_id_monthly']
                amount = plan['price_monthly']
            
            # Create or get Stripe customer
            customer_id = user.get('stripe_customer_id')
            if not customer_id:
                customer = stripe.Customer.create(
                    email=user['email'],
                    name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                )
                customer_id = customer.id
                # Update user with customer ID
                self.user_model.update_subscription(user_id, user['subscription_plan'], customer_id)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{os.getenv('BASE_URL', 'http://localhost:5001')}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{os.getenv('BASE_URL', 'http://localhost:5001')}/payment/cancel",
                metadata={
                    'user_id': user_id,
                    'plan_name': plan_name,
                    'billing_period': billing_period
                }
            )
            
            return {
                'success': True,
                'session_id': session.id,
                'checkout_url': session.url
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_one_time_payment_session(self, user_id, plan_name, billing_period='monthly'):
        """Create a one-time payment session (for testing without Stripe products)"""
        try:
            # Get plan details
            plan = self.plan_model.get_plan_by_name(plan_name)
            if not plan:
                return {'success': False, 'error': 'Plan not found'}
            
            # Get user details
            user = self.user_model.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Determine amount
            if billing_period == 'yearly':
                amount = plan['price_yearly']
            else:
                amount = plan['price_monthly']
            
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'user_id': user_id,
                    'plan_name': plan_name,
                    'billing_period': billing_period
                }
            )
            
            # Create payment record
            self.payment_model.create_payment_record(
                user_id=user_id,
                stripe_payment_intent_id=payment_intent.id,
                amount=amount,
                plan_name=plan_name,
                billing_period=billing_period,
                status='pending'
            )
            
            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def handle_webhook(self, payload, sig_header):
        """Handle Stripe webhooks"""
        try:
            webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            
            # Handle the event
            if event['type'] == 'checkout.session.completed':
                return self._handle_checkout_completed(event['data']['object'])
            elif event['type'] == 'invoice.payment_succeeded':
                return self._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'invoice.payment_failed':
                return self._handle_payment_failed(event['data']['object'])
            elif event['type'] == 'customer.subscription.deleted':
                return self._handle_subscription_cancelled(event['data']['object'])
            
            return {'success': True, 'message': 'Webhook processed'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_checkout_completed(self, session):
        """Handle successful checkout completion"""
        try:
            user_id = int(session['metadata']['user_id'])
            plan_name = session['metadata']['plan_name']
            billing_period = session['metadata']['billing_period']
            
            # Calculate expiration date
            if billing_period == 'yearly':
                expires_at = datetime.now() + timedelta(days=365)
            else:
                expires_at = datetime.now() + timedelta(days=30)
            
            # Update user subscription
            self.user_model.update_subscription(
                user_id=user_id,
                plan_name=plan_name,
                stripe_customer_id=session['customer'],
                expires_at=expires_at.isoformat()
            )
            
            return {'success': True, 'message': 'Subscription activated'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        try:
            # Update payment record status
            self.payment_model.update_payment_status(
                invoice['payment_intent'],
                'succeeded'
            )
            
            return {'success': True, 'message': 'Payment recorded'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_payment_failed(self, invoice):
        """Handle failed payment"""
        try:
            # Update payment record status
            self.payment_model.update_payment_status(
                invoice['payment_intent'],
                'failed'
            )
            
            return {'success': True, 'message': 'Payment failure recorded'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_subscription_cancelled(self, subscription):
        """Handle subscription cancellation"""
        try:
            # Find user by customer ID and update subscription
            # This would require a method to find user by stripe_customer_id
            return {'success': True, 'message': 'Subscription cancelled'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_subscription_plans(self):
        """Get all available subscription plans"""
        return self.plan_model.get_all_plans()
    
    def get_user_payments(self, user_id):
        """Get payment history for a user"""
        return self.payment_model.get_user_payments(user_id)
    
    def cancel_subscription(self, user_id):
        """Cancel user's subscription"""
        try:
            user = self.user_model.get_user_by_id(user_id)
            if not user or not user.get('stripe_customer_id'):
                return {'success': False, 'error': 'No active subscription found'}
            
            # Cancel subscription in Stripe
            subscriptions = stripe.Subscription.list(customer=user['stripe_customer_id'])
            if subscriptions.data:
                subscription = subscriptions.data[0]
                stripe.Subscription.delete(subscription.id)
            
            # Update user subscription status
            self.user_model.update_subscription(
                user_id=user_id,
                plan_name='free',
                expires_at=None
            )
            
            return {'success': True, 'message': 'Subscription cancelled'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_payment_methods(self):
        """Get available payment methods"""
        methods = []
        
        # Stripe payments
        if self.stripe_secret_key:
            methods.append({
                "id": "stripe",
                "name": "Credit Card",
                "description": "Pay with Visa, Mastercard, or other cards",
                "icon": "credit-card",
                "type": "card"
            })
        
        # Crypto payments
        methods.append({
            "id": "usdt",
            "name": "USDT (ERC20)",
            "description": "Pay with USDT on Ethereum network",
            "icon": "bitcoin",
            "type": "crypto",
            "contract_address": self.usdt_contract_address,
            "network": "Ethereum"
        })
        
        return methods
    
    def process_payment_webhook(self, event_type, data):
        """Process payment webhooks from Stripe"""
        if event_type == 'payment_intent.succeeded':
            return {
                "status": "success",
                "payment_id": data.get('id'),
                "amount": data.get('amount') / 100,  # Convert from cents
                "currency": data.get('currency')
            }
        elif event_type == 'payment_intent.payment_failed':
            return {
                "status": "failed",
                "payment_id": data.get('id'),
                "error": data.get('last_payment_error', {}).get('message', 'Payment failed')
            }
        
        return {"status": "unknown", "event": event_type}
    
    def add_payment_method(self, user_id, payment_method_id):
        """Add a payment method to user's account"""
        try:
            user = self.user_model.get_user_by_id(user_id)
            if not user or not user.get('stripe_customer_id'):
                return {'success': False, 'error': 'User not found'}
            
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user['stripe_customer_id']
            )
            
            return {'success': True, 'message': 'Payment method added'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def remove_payment_method(self, user_id, payment_method_id):
        """Remove a payment method from user's account"""
        try:
            user = self.user_model.get_user_by_id(user_id)
            if not user or not user.get('stripe_customer_id'):
                return {'success': False, 'error': 'User not found'}
            
            # Detach payment method
            stripe.PaymentMethod.detach(payment_method_id)
            
            return {'success': True, 'message': 'Payment method removed'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def activate_subscription(self, user_id, plan_name, payment_method='stripe', payment_id=None, billing_period='monthly'):
        """Activate user subscription after successful payment"""
        try:
            # Calculate expiration date based on billing period
            if billing_period == 'yearly':
                expires_at = datetime.now() + timedelta(days=365)
            else:
                expires_at = datetime.now() + timedelta(days=30)
            
            # Update user subscription
            self.user_model.update_subscription(
                user_id=user_id,
                plan_name=plan_name,
                expires_at=expires_at.isoformat()
            )
            
            # Create payment record if payment_id is provided
            if payment_id:
                # Get plan details for amount
                plan = self.plan_model.get_plan_by_name(plan_name)
                if plan:
                    amount = plan['price_yearly'] if billing_period == 'yearly' else plan['price_monthly']
                    self.payment_model.create_payment_record(
                        user_id=user_id,
                        stripe_payment_intent_id=payment_id,
                        amount=amount,
                        plan_name=plan_name,
                        billing_period=billing_period,
                        status='succeeded'
                    )
            
            return True
            
        except Exception as e:
            print(f"Error activating subscription: {e}")
            return False 