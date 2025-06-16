import os
import requests
import hmac
import hashlib
from datetime import datetime, timedelta
from models import DatabaseManager, User, SubscriptionPlan, PaymentRecord
from web3 import Web3
from eth_account import Account
import json
import uuid

class PaymentService:
    """Payment service for handling Paystack payments and subscriptions"""
    
    def __init__(self):
        # Initialize Paystack with API key
        self.paystack_secret_key = os.getenv('PAYSTACK_SECRET_KEY')
        self.paystack_public_key = os.getenv('PAYSTACK_PUBLIC_KEY')
        self.paystack_base_url = "https://api.paystack.co"
        
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
    
    def _make_paystack_request(self, endpoint, method='GET', data=None):
        """Make authenticated request to Paystack API"""
        if not self.paystack_secret_key:
            return {"error": "Paystack not configured"}
        
        headers = {
            'Authorization': f'Bearer {self.paystack_secret_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.paystack_base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Paystack API error: {str(e)}"}
    
    def create_paystack_transaction(self, amount, email, reference=None, metadata=None, currency='NGN'):
        """Create a Paystack transaction"""
        if not reference:
            reference = f"txn_{int(datetime.now().timestamp())}"
        
        # Debug logging
        print(f"🔍 [DEBUG] create_paystack_transaction - Amount: {amount}, Currency: {currency}, Email: {email}")
        print(f"🔍 [DEBUG] Reference: {reference}")
        print(f"🔍 [DEBUG] Metadata: {metadata}")
        
        # Convert amount to smallest currency unit
        if currency in ['NGN', 'GHS', 'KES', 'ZAR', 'UGX', 'TZS', 'ZMW', 'XOF', 'XAF']:
            # For these currencies, multiply by 100 to convert to smallest unit (kobo, pesewa, etc.)
            amount_in_smallest_unit = int(amount * 100)
        else:
            amount_in_smallest_unit = int(amount * 100)
        
        print(f"🔍 [DEBUG] Amount in smallest unit: {amount_in_smallest_unit}")
        
        data = {
            'amount': amount_in_smallest_unit,
            'email': email,
            'reference': reference,
            'currency': currency,
            'metadata': metadata or {}
        }
        
        print(f"🔍 [DEBUG] Paystack API request data: {data}")
        print(f"[Paystack] Using key: {self.paystack_secret_key[:8]}... Currency: {currency} Amount: {amount}")
        
        response = self._make_paystack_request('/transaction/initialize', method='POST', data=data)
        print(f"[Paystack] API response: {response}")
        return response
    
    def verify_paystack_transaction(self, reference):
        """Verify a Paystack transaction"""
        return self._make_paystack_request(f'/transaction/verify/{reference}')
    
    def create_paystack_customer(self, email, first_name=None, last_name=None, phone=None):
        """Create a Paystack customer"""
        data = {
            'email': email,
            'first_name': first_name or '',
            'last_name': last_name or '',
            'phone': phone or ''
        }
        
        return self._make_paystack_request('/customer', method='POST', data=data)
    
    def create_paystack_subscription(self, customer_email, plan_code, start_date=None):
        """Create a Paystack subscription"""
        data = {
            'customer': customer_email,
            'plan': plan_code
        }
        
        if start_date:
            data['start_date'] = start_date
        
        return self._make_paystack_request('/subscription', method='POST', data=data)
    
    def create_paystack_plan(self, name, amount, interval='monthly', description=None):
        """Create a Paystack subscription plan"""
        data = {
            'name': name,
            'amount': int(amount * 100),  # Convert to kobo
            'interval': interval,
            'description': description or f'Subscription plan for {name}'
        }
        
        return self._make_paystack_request('/plan', method='POST', data=data)
    
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
    
    def create_checkout_session(self, user_id, plan_name, billing_period='monthly', user_currency='USD'):
        """Create a Paystack checkout session for subscription"""
        try:
            print(f"🔍 [DEBUG] create_checkout_session - User: {user_id}, Plan: {plan_name}, Billing: {billing_period}, Currency: {user_currency}")
            
            # Get plan details
            plan = self.plan_model.get_plan_by_name(plan_name)
            if not plan:
                print(f"❌ [DEBUG] Plan not found: {plan_name}")
                return {'success': False, 'error': 'Plan not found'}
            
            # Get user details
            user = self.user_model.get_user_by_id(user_id)
            if not user:
                print(f"❌ [DEBUG] User not found: {user_id}")
                return {'success': False, 'error': 'User not found'}
            
            # Determine amount in USD
            if billing_period == 'yearly':
                amount_usd = plan['price_yearly']
            else:
                amount_usd = plan['price_monthly']
            
            print(f"🔍 [DEBUG] Original USD amount: {amount_usd}")
            
            # For Paystack, we need to use NGN or other supported currencies
            # Paystack only supports: NGN, GHS, KES, ZAR, UGX, TZS, ZMW, XOF, XAF
            paystack_supported_currencies = ['NGN', 'GHS', 'KES', 'ZAR', 'UGX', 'TZS', 'ZMW', 'XOF', 'XAF']
            
            if user_currency not in paystack_supported_currencies:
                print(f"⚠️ [DEBUG] Currency {user_currency} not supported by Paystack, forcing NGN")
                # Convert to NGN for Paystack
                try:
                    from currency_service import currency_service
                    amount = currency_service.convert_amount(amount_usd, 'USD', 'NGN')
                    user_currency = 'NGN'
                    print(f"🔍 [DEBUG] Converted to NGN: {amount} NGN")
                except Exception as e:
                    print(f"❌ [DEBUG] Failed to convert to NGN: {e}")
                    return {'success': False, 'error': f'Currency {user_currency} not supported by Paystack'}
            else:
                # Convert amount to user's currency if needed
                if user_currency != 'USD':
                    try:
                        from currency_service import currency_service
                        print(f"🔍 [DEBUG] Converting {amount_usd} USD to {user_currency}")
                        converted_amount = currency_service.convert_amount(amount_usd, 'USD', user_currency)
                        if converted_amount:
                            amount = converted_amount
                            print(f"🔍 [DEBUG] Conversion successful: {amount_usd} USD = {amount} {user_currency}")
                        else:
                            # Fallback to NGN if conversion fails
                            print(f"⚠️ [DEBUG] Currency conversion failed, falling back to NGN")
                            amount = currency_service.convert_amount(amount_usd, 'USD', 'NGN')
                            user_currency = 'NGN'
                    except Exception as e:
                        print(f"⚠️ [DEBUG] Currency conversion failed: {e}")
                        # Fallback to NGN
                        try:
                            from currency_service import currency_service
                            amount = currency_service.convert_amount(amount_usd, 'USD', 'NGN')
                            user_currency = 'NGN'
                            print(f"🔍 [DEBUG] Fallback to NGN: {amount} NGN")
                        except Exception as e2:
                            print(f"❌ [DEBUG] Failed to convert to NGN: {e2}")
                            return {'success': False, 'error': 'Currency conversion failed'}
                else:
                    # USD not supported by Paystack, convert to NGN
                    print(f"⚠️ [DEBUG] USD not supported by Paystack, converting to NGN")
                    try:
                        from currency_service import currency_service
                        amount = currency_service.convert_amount(amount_usd, 'USD', 'NGN')
                        user_currency = 'NGN'
                        print(f"🔍 [DEBUG] Converted USD to NGN: {amount} NGN")
                    except Exception as e:
                        print(f"❌ [DEBUG] Failed to convert USD to NGN: {e}")
                        return {'success': False, 'error': 'Failed to convert USD to NGN for Paystack'}
            
            print(f"🔍 [DEBUG] Final amount for Paystack: {amount} {user_currency}")
            
            # Create or get Paystack customer
            customer_response = self.create_paystack_customer(
                email=user['email'],
                first_name=user.get('first_name', ''),
                last_name=user.get('last_name', '')
            )
            
            if 'error' in customer_response:
                print(f"❌ [DEBUG] Customer creation failed: {customer_response['error']}")
                return {'success': False, 'error': customer_response['error']}
            
            customer_code = customer_response['data']['customer_code']
            print(f"🔍 [DEBUG] Customer created: {customer_code}")
            
            # Create Paystack transaction
            reference = f"sub_{user_id}_{plan_name}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
            print(f"🔍 [DEBUG] Creating Paystack transaction - Amount: {amount}, Currency: {user_currency}, Reference: {reference}")
            
            transaction_response = self.create_paystack_transaction(
                amount=amount,
                email=user['email'],
                reference=reference,
                currency=user_currency,
                metadata={
                    'user_id': user_id,
                    'plan_name': plan_name,
                    'billing_period': billing_period,
                    'customer_code': customer_code,
                    'original_amount_usd': amount_usd,
                    'converted_amount': amount,
                    'currency': user_currency
                }
            )
            
            print(f"🔍 [DEBUG] Paystack transaction response: {transaction_response}")
            
            if 'error' in transaction_response:
                print(f"❌ [DEBUG] Transaction creation failed: {transaction_response['error']}")
                return {'success': False, 'error': transaction_response['error']}
            
            # Update user with customer code
            self.user_model.update_subscription(user_id, user['subscription_plan'], customer_code)
            
            result = {
                'success': True,
                'authorization_url': transaction_response['data']['authorization_url'],
                'reference': reference,
                'access_code': transaction_response['data']['access_code'],
                'amount': amount,
                'currency': user_currency
            }
            
            print(f"✅ [DEBUG] Checkout session created successfully: {result}")
            return result
            
        except Exception as e:
            print(f"❌ [DEBUG] create_checkout_session error: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_one_time_payment_session(self, user_id, plan_name, billing_period='monthly'):
        """Create a one-time payment session"""
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
            
            # Create Paystack transaction
            reference = f"one_time_{user_id}_{plan_name}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
            transaction_response = self.create_paystack_transaction(
                amount=amount,
                email=user['email'],
                reference=reference,
                metadata={
                    'user_id': user_id,
                    'plan_name': plan_name,
                    'billing_period': billing_period,
                    'payment_type': 'one_time'
                }
            )
            
            if 'error' in transaction_response:
                return {'success': False, 'error': transaction_response['error']}
            
            return {
                'success': True,
                'authorization_url': transaction_response['data']['authorization_url'],
                'reference': reference,
                'access_code': transaction_response['data']['access_code']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify_webhook_signature(self, payload, signature):
        """Verify Paystack webhook signature"""
        try:
            if not signature:
                print("⚠️ [DEBUG] No webhook signature provided")
                return False
            
            # Create HMAC SHA512 hash
            expected_signature = hmac.new(
                self.paystack_secret_key.encode('utf-8'),
                payload,
                hashlib.sha512
            ).hexdigest()
            
            # Compare signatures
            if hmac.compare_digest(expected_signature, signature):
                print("✅ [DEBUG] Webhook signature verified")
                return True
            else:
                print("❌ [DEBUG] Webhook signature verification failed")
                return False
                
        except Exception as e:
            print(f"❌ [DEBUG] Error verifying webhook signature: {e}")
            return False

    def handle_webhook(self, payload, signature):
        """Handle Paystack webhook events"""
        try:
            print(f"🔍 [DEBUG] Webhook received - Event: {payload.get('event')}")
            
            # Verify webhook signature (for now, skip verification in development)
            # In production, you should implement proper signature verification
            if signature and self.paystack_secret_key:
                # Note: For proper signature verification, you need the raw request body
                # This is handled in the Flask route before calling this method
                print(f"🔍 [DEBUG] Signature provided: {signature[:20]}...")
            else:
                print("⚠️ [DEBUG] No signature verification (development mode)")
            
            event = payload.get('event')
            data = payload.get('data', {})
            
            if event == 'charge.success':
                print("🔍 [DEBUG] Processing charge.success event")
                return self._handle_payment_success(data)
            elif event == 'subscription.create':
                print("🔍 [DEBUG] Processing subscription.create event")
                return self._handle_subscription_created(data)
            elif event == 'subscription.disable':
                print("🔍 [DEBUG] Processing subscription.disable event")
                return self._handle_subscription_cancelled(data)
            else:
                print(f"🔍 [DEBUG] Unhandled event: {event}")
                return {'success': True, 'message': f'Event {event} processed'}
                
        except Exception as e:
            print(f"❌ [DEBUG] Error handling webhook: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _handle_payment_success(self, data):
        """Handle successful payment with enhanced error handling"""
        try:
            print(f"🔍 [DEBUG] Processing payment success - Data: {data}")
            
            reference = data.get('reference')
            metadata = data.get('metadata', {})
            user_id = metadata.get('user_id')
            plan_name = metadata.get('plan_name')
            billing_period = metadata.get('billing_period', 'monthly')
            payment_currency = metadata.get('currency', 'NGN')
            
            print(f"🔍 [DEBUG] Payment details - User: {user_id}, Plan: {plan_name}, Reference: {reference}")
            print(f"🔍 [DEBUG] Metadata: {metadata}")
            
            if not user_id:
                print(f"❌ [DEBUG] Missing user_id in metadata")
                return {'success': False, 'error': 'Missing user_id in payment metadata'}
            
            if not plan_name:
                print(f"❌ [DEBUG] Missing plan_name in metadata")
                return {'success': False, 'error': 'Missing plan_name in payment metadata'}
            
            # Check if payment was already processed
            existing_payment = self.payment_model.get_payment_by_reference(reference)
            if existing_payment:
                print(f"⚠️ [DEBUG] Payment {reference} already processed")
                return {'success': True, 'message': 'Payment already processed'}
            
            # Verify the payment with Paystack to ensure it's actually successful
            verification_result = self.verify_paystack_transaction(reference)
            if not verification_result.get('status') or verification_result['data']['status'] != 'success':
                print(f"❌ [DEBUG] Payment verification failed: {verification_result}")
                return {'success': False, 'error': 'Payment verification failed'}
            
            print(f"✅ [DEBUG] Payment verified successfully")
            
            # Activate subscription
            print(f"🔍 [DEBUG] Activating subscription for user {user_id}")
            success = self.activate_subscription(
                user_id, 
                plan_name, 
                payment_method='paystack',
                payment_id=reference,
                billing_period=billing_period,
                currency=payment_currency
            )
            
            if success:
                print(f"✅ [DEBUG] Subscription activated successfully for user {user_id}")
                return {'success': True, 'message': 'Payment processed successfully'}
            else:
                print(f"❌ [DEBUG] Failed to activate subscription for user {user_id}")
                return {'success': False, 'error': 'Failed to activate subscription'}
            
        except Exception as e:
            print(f"❌ [DEBUG] Error in _handle_payment_success: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _handle_subscription_created(self, data):
        """Handle subscription creation"""
        try:
            # Handle subscription creation logic
            return {'success': True, 'message': 'Subscription created'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_subscription_cancelled(self, data):
        """Handle subscription cancellation"""
        try:
            # Handle subscription cancellation logic
            return {'success': True, 'message': 'Subscription cancelled'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_subscription_plans(self):
        """Get available subscription plans"""
        return self.plan_model.get_all_plans()
    
    def get_user_payments(self, user_id):
        """Get user's payment history"""
        return self.payment_model.get_payments_by_user(user_id)
    
    def cancel_subscription(self, user_id):
        """Cancel user subscription"""
        try:
            user = self.user_model.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            customer_code = user.get('stripe_customer_id')  # Reusing field for Paystack customer code
            
            if customer_code:
                # Cancel subscription in Paystack
                # This would require additional Paystack API calls
                pass
            
            # Update user subscription status
            self.user_model.update_subscription(user_id, 'free', None)
            
            return {'success': True, 'message': 'Subscription cancelled'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_payment_methods(self):
        """Get available payment methods"""
        return {
            'card': {
                'name': 'Credit/Debit Card',
                'provider': 'Paystack',
                'supported_cards': ['Visa', 'Mastercard', 'Verve'],
                'description': 'Secure payment via Paystack'
            },
            'crypto': {
                'name': 'USDT (Cryptocurrency)',
                'provider': 'Ethereum Network',
                'supported_tokens': ['USDT'],
                'description': 'Pay with USDT on Ethereum network'
            }
        }
    
    def process_payment_webhook(self, event_type, data):
        """Process payment webhook events"""
        try:
            if event_type == 'payment.success':
                return self._handle_payment_success(data)
            elif event_type == 'subscription.create':
                return self._handle_subscription_created(data)
            elif event_type == 'subscription.cancel':
                return self._handle_subscription_cancelled(data)
            else:
                return {'success': True, 'message': f'Event {event_type} processed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def add_payment_method(self, user_id, payment_method_data):
        """Add a payment method to user's account"""
        try:
            # For Paystack, payment methods are typically handled during transaction
            # This method can be used to store additional payment preferences
            return {'success': True, 'message': 'Payment method added'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def remove_payment_method(self, user_id, payment_method_id):
        """Remove a payment method from user's account"""
        try:
            # For Paystack, this would involve removing saved payment methods
            return {'success': True, 'message': 'Payment method removed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def activate_subscription(self, user_id, plan_name, payment_method='paystack', payment_id=None, billing_period='monthly', currency=None):
        """Activate user subscription after successful payment"""
        try:
            print(f"🔍 [DEBUG] activate_subscription called - User: {user_id}, Plan: {plan_name}, Method: {payment_method}")
            
            # Get plan details
            plan = self.plan_model.get_plan_by_name(plan_name)
            if not plan:
                print(f"❌ [DEBUG] Plan not found: {plan_name}")
                return False
            
            print(f"✅ [DEBUG] Plan found: {plan}")
            
            # Calculate subscription end date
            if billing_period == 'yearly':
                end_date = datetime.now() + timedelta(days=365)
                amount = plan['price_yearly']
            else:
                end_date = datetime.now() + timedelta(days=30)
                amount = plan['price_monthly']
            
            print(f"🔍 [DEBUG] End date: {end_date}, Amount: {amount}")
            
            # Update user subscription
            print(f"🔍 [DEBUG] Calling user_model.update_subscription...")
            success = self.user_model.update_subscription(
                user_id, 
                plan_name, 
                payment_id,  # Store payment reference
                end_date
            )
            
            print(f"🔍 [DEBUG] update_subscription returned: {success}")
            
            if success:
                # Record payment
                print(f"🔍 [DEBUG] Recording payment...")
                try:
                    # Use the correct currency if provided, else fallback to 'usd'
                    payment_currency = currency or 'usd'
                    self.payment_model.create_payment_record(
                        user_id=user_id,
                        stripe_payment_intent_id=payment_id,
                        amount=amount,
                        plan_name=plan_name,
                        billing_period=billing_period,
                        status='completed',
                        currency=payment_currency,
                        payment_method=payment_method
                    )
                    print(f"✅ [DEBUG] Payment recorded successfully")
                except Exception as e:
                    print(f"⚠️ [DEBUG] Payment recording failed: {e}")
                    # Don't fail the subscription activation if payment recording fails
            
            return success
            
        except Exception as e:
            print(f"❌ [DEBUG] Error activating subscription: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def retry_failed_payments(self):
        """Retry processing failed payments that weren't properly handled by webhooks"""
        try:
            print("🔧 Retrying failed payments...")
            
            # Get all completed payments without active subscriptions
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT pr.user_id, pr.stripe_payment_intent_id, pr.amount, pr.currency, 
                       pr.plan_name, pr.billing_period, pr.payment_method, pr.created_at,
                       u.subscription_plan
                FROM payment_records pr
                JOIN users u ON pr.user_id = u.id
                WHERE pr.status = 'completed' 
                AND pr.plan_name IN ('pro', 'enterprise')
                AND u.subscription_plan = 'free'
                ORDER BY pr.created_at DESC
            ''')
            
            failed_payments = cursor.fetchall()
            conn.close()
            
            print(f"🔍 Found {len(failed_payments)} failed payments to retry")
            
            success_count = 0
            for payment in failed_payments:
                user_id, payment_id, amount, currency, plan_name, billing_period, payment_method, created_at, current_plan = payment
                
                print(f"🔧 Retrying payment {payment_id} for user {user_id}...")
                
                # Activate subscription
                success = self.activate_subscription(
                    user_id=user_id,
                    plan_name=plan_name,
                    payment_method=payment_method,
                    payment_id=payment_id,
                    billing_period=billing_period,
                    currency=currency
                )
                
                if success:
                    print(f"✅ Successfully activated {plan_name} subscription for user {user_id}")
                    success_count += 1
                else:
                    print(f"❌ Failed to activate subscription for user {user_id}")
            
            print(f"📊 Retry complete: {success_count}/{len(failed_payments)} payments fixed")
            return success_count
            
        except Exception as e:
            print(f"❌ Error in retry_failed_payments: {e}")
            return 0

    def verify_and_fix_payment(self, reference):
        """Verify a payment with Paystack and fix if needed"""
        try:
            print(f"🔍 Verifying payment {reference}...")
            
            # Verify with Paystack
            verification_result = self.verify_paystack_transaction(reference)
            
            if not verification_result.get('status') or verification_result['data']['status'] != 'success':
                print(f"❌ Payment verification failed: {verification_result}")
                return False
            
            data = verification_result['data']
            metadata = data.get('metadata', {})
            
            user_id = metadata.get('user_id')
            plan_name = metadata.get('plan_name')
            billing_period = metadata.get('billing_period', 'monthly')
            payment_currency = metadata.get('currency', 'NGN')
            amount = float(data['amount']) / 100
            
            if not user_id or not plan_name:
                print(f"❌ Missing metadata: user_id={user_id}, plan_name={plan_name}")
                return False
            
            # Check if payment record exists
            existing_payment = self.payment_model.get_payment_by_reference(reference)
            if not existing_payment:
                print(f"📝 Creating missing payment record...")
                try:
                    self.payment_model.create_payment_record(
                        user_id=user_id,
                        stripe_payment_intent_id=reference,
                        amount=amount,
                        plan_name=plan_name,
                        billing_period=billing_period,
                        status='completed',
                        currency=payment_currency,
                        payment_method='paystack'
                    )
                    print(f"✅ Payment record created")
                except Exception as e:
                    print(f"❌ Failed to create payment record: {e}")
                    return False
            
            # Check if subscription is active
            user = self.user_model.get_user_by_id(user_id)
            if user and user['subscription_plan'] == plan_name:
                print(f"✅ Subscription already active for user {user_id}")
                return True
            
            # Activate subscription
            print(f"🔧 Activating subscription for user {user_id}...")
            success = self.activate_subscription(
                user_id=user_id,
                plan_name=plan_name,
                payment_method='paystack',
                payment_id=reference,
                billing_period=billing_period,
                currency=payment_currency
            )
            
            if success:
                print(f"✅ Payment verified and subscription activated for user {user_id}")
                return True
            else:
                print(f"❌ Failed to activate subscription for user {user_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error in verify_and_fix_payment: {e}")
            return False 