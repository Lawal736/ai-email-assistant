#!/usr/bin/env python3

import requests
import json
import os
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
from models import DatabaseManager

class CurrencyService:
    """Service for handling currency conversion and localization"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.exchange_rates = {}
        self.last_update = None
        self.update_interval = timedelta(hours=1)  # Update rates every hour
        
        # Supported currencies with their symbols and Paystack support
        self.supported_currencies = {
            'USD': {'symbol': '$', 'name': 'US Dollar', 'paystack_supported': True},
            'NGN': {'symbol': '₦', 'name': 'Nigerian Naira', 'paystack_supported': True},
            'EUR': {'symbol': '€', 'name': 'Euro', 'paystack_supported': False},
            'GBP': {'symbol': '£', 'name': 'British Pound', 'paystack_supported': False},
            'CAD': {'symbol': 'C$', 'name': 'Canadian Dollar', 'paystack_supported': False},
            'AUD': {'symbol': 'A$', 'name': 'Australian Dollar', 'paystack_supported': False},
            'GHS': {'symbol': 'GH₵', 'name': 'Ghanaian Cedi', 'paystack_supported': True},
            'KES': {'symbol': 'KSh', 'name': 'Kenyan Shilling', 'paystack_supported': True},
            'ZAR': {'symbol': 'R', 'name': 'South African Rand', 'paystack_supported': True},
            'UGX': {'symbol': 'USh', 'name': 'Ugandan Shilling', 'paystack_supported': True},
            'TZS': {'symbol': 'TSh', 'name': 'Tanzanian Shilling', 'paystack_supported': True},
            'ZMW': {'symbol': 'ZK', 'name': 'Zambian Kwacha', 'paystack_supported': True},
            'XOF': {'symbol': 'CFA', 'name': 'West African CFA Franc', 'paystack_supported': True},
            'XAF': {'symbol': 'FCFA', 'name': 'Central African CFA Franc', 'paystack_supported': True},
        }
        
        # Default to USD if no currency detected
        self.default_currency = 'USD'
        
        # Initialize exchange rates
        self.update_exchange_rates()
    
    def detect_user_currency(self, ip_address: str = None) -> str:
        """Detect user's currency based on IP address with enhanced Nigerian detection"""
        try:
            # Handle local development and proxy scenarios
            if not ip_address or ip_address in ['127.0.0.1', 'localhost', None]:
                # For local development, try to get real IP
                try:
                    response = requests.get('http://ip-api.com/json/?fields=countryCode,currency,country', timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        country_code = data.get('countryCode', '').upper()
                        
                        # Enhanced Nigerian detection
                        if country_code == 'NG':
                            print(f"🇳🇬 Nigerian IP detected, enforcing NGN currency")
                            return 'NGN'
                        
                        currency = data.get('currency', 'USD')
                        if currency in self.supported_currencies:
                            print(f"🌍 Auto-detected currency: {currency} for country: {country_code}")
                            return currency
                except:
                    pass
            else:
                # Use provided IP address for detection
                response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=countryCode,currency,country', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    country_code = data.get('countryCode', '').upper()
                    country_name = data.get('country', '')
                    
                    print(f"🔍 IP Detection: {ip_address} -> {country_name} ({country_code})")
                    
                    # Enhanced Nigerian detection with multiple checks
                    if (country_code == 'NG' or 
                        'nigeria' in country_name.lower() or 
                        country_code in ['NG', 'NGA']):
                        print(f"🇳🇬 Nigerian user detected, enforcing NGN currency")
                        return 'NGN'
                    
                    # Enhanced country-to-currency mapping
                    country_currency_map = {
                        'NG': 'NGN',  # Nigeria
                        'GH': 'GHS',  # Ghana
                        'KE': 'KES',  # Kenya
                        'ZA': 'ZAR',  # South Africa
                        'UG': 'UGX',  # Uganda
                        'TZ': 'TZS',  # Tanzania
                        'ZM': 'ZMW',  # Zambia
                        'BJ': 'XOF',  # Benin (West African CFA)
                        'BF': 'XOF',  # Burkina Faso
                        'CI': 'XOF',  # Côte d'Ivoire
                        'GW': 'XOF',  # Guinea-Bissau
                        'ML': 'XOF',  # Mali
                        'NE': 'XOF',  # Niger
                        'SN': 'XOF',  # Senegal
                        'TG': 'XOF',  # Togo
                        'CM': 'XAF',  # Cameroon (Central African CFA)
                        'CF': 'XAF',  # Central African Republic
                        'TD': 'XAF',  # Chad
                        'CG': 'XAF',  # Republic of the Congo
                        'GQ': 'XAF',  # Equatorial Guinea
                        'GA': 'XAF',  # Gabon
                        'US': 'USD',  # United States
                        'GB': 'GBP',  # United Kingdom
                        'CA': 'CAD',  # Canada
                        'AU': 'AUD',  # Australia
                        'FR': 'EUR',  # France
                        'DE': 'EUR',  # Germany
                        'IT': 'EUR',  # Italy
                        'ES': 'EUR',  # Spain
                    }
                    
                    # Use country-specific mapping first
                    if country_code in country_currency_map:
                        mapped_currency = country_currency_map[country_code]
                        if mapped_currency in self.supported_currencies:
                            print(f"🎯 Country mapping: {country_code} -> {mapped_currency}")
                            return mapped_currency
                    
                    # Fallback to API-provided currency
                    currency = data.get('currency', 'USD')
                    if currency in self.supported_currencies:
                        print(f"🌍 API currency: {currency}")
                        return currency
                
        except Exception as e:
            print(f"⚠️ Currency detection failed: {e}")
        
        # Ultimate fallback
        print(f"🔄 Using default currency: {self.default_currency}")
        return self.default_currency
    
    def update_exchange_rates(self):
        """Update exchange rates from a free API"""
        try:
            # Use exchangerate-api.com (free tier)
            response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.exchange_rates = data.get('rates', {})
                self.last_update = datetime.now()
                print(f"✅ Exchange rates updated: {len(self.exchange_rates)} currencies")
            else:
                print(f"⚠️ Failed to update exchange rates: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Exchange rate update failed: {e}")
            # Use fallback rates if API fails
            self.exchange_rates = {
                'USD': 1.0,
                'NGN': 1500.0,  # Approximate rate
                'EUR': 0.85,
                'GBP': 0.75,
                'CAD': 1.25,
                'AUD': 1.35,
                'GHS': 12.0,
                'KES': 150.0,
                'ZAR': 18.0,
                'UGX': 3700.0,
                'TZS': 2500.0,
                'ZMW': 25.0,
                'XOF': 550.0,
                'XAF': 550.0,
            }
    
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Get exchange rate between two currencies"""
        if from_currency == to_currency:
            return 1.0
        
        # Update rates if needed
        if not self.last_update or datetime.now() - self.last_update > self.update_interval:
            self.update_exchange_rates()
        
        # Convert USD to target currency
        if from_currency == 'USD':
            return self.exchange_rates.get(to_currency, 1.0)
        elif to_currency == 'USD':
            return 1.0 / self.exchange_rates.get(from_currency, 1.0)
        else:
            # Convert through USD
            usd_to_from = 1.0 / self.exchange_rates.get(from_currency, 1.0)
            usd_to_to = self.exchange_rates.get(to_currency, 1.0)
            return usd_to_from * usd_to_to
    
    def convert_price(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert price from one currency to another"""
        rate = self.get_exchange_rate(from_currency, to_currency)
        return round(amount * rate, 2)
    
    def convert_amount(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert amount from one currency to another (alias for convert_price)"""
        return self.convert_price(amount, from_currency, to_currency)
    
    def format_price(self, amount: float, currency: str) -> str:
        """Format price with currency symbol"""
        if currency not in self.supported_currencies:
            currency = self.default_currency
        
        symbol = self.supported_currencies[currency]['symbol']
        
        # Format based on currency
        if currency in ['NGN', 'GHS', 'KES', 'ZAR', 'UGX', 'TZS', 'ZMW', 'XOF', 'XAF']:
            # African currencies: no decimal places
            return f"{symbol}{int(amount):,}"
        else:
            # Other currencies: 2 decimal places
            return f"{symbol}{amount:,.2f}"
    
    def get_currency_info(self, currency: str) -> Dict:
        """Get currency information"""
        return self.supported_currencies.get(currency, self.supported_currencies[self.default_currency])
    
    def is_paystack_supported(self, currency: str) -> bool:
        """Check if currency is supported by Paystack"""
        return self.supported_currencies.get(currency, {}).get('paystack_supported', False)
    
    def get_user_currency_data(self, ip_address: str = None) -> Dict:
        """Get complete currency data for user"""
        currency = self.detect_user_currency(ip_address)
        
        return {
            'currency': currency,
            'symbol': self.supported_currencies[currency]['symbol'],
            'name': self.supported_currencies[currency]['name'],
            'paystack_supported': self.is_paystack_supported(currency),
            'exchange_rate': self.get_exchange_rate('USD', currency)
        }
    
    def convert_plan_prices(self, plans: list, target_currency: str) -> list:
        """Convert plan prices to target currency"""
        converted_plans = []
        
        for plan in plans:
            converted_plan = plan.copy()
            
            # Convert monthly price
            if plan.get('price_monthly', 0) > 0:
                converted_plan['price_monthly'] = self.convert_price(
                    plan['price_monthly'], 'USD', target_currency
                )
            
            # Convert yearly price
            if plan.get('price_yearly', 0) > 0:
                converted_plan['price_yearly'] = self.convert_price(
                    plan['price_yearly'], 'USD', target_currency
                )
            
            # Add currency info
            converted_plan['currency'] = target_currency
            converted_plan['currency_symbol'] = self.supported_currencies[target_currency]['symbol']
            converted_plan['currency_name'] = self.supported_currencies[target_currency]['name']
            converted_plan['paystack_supported'] = self.is_paystack_supported(target_currency)
            
            converted_plans.append(converted_plan)
        
        return converted_plans
    
    def save_user_currency_preference(self, user_id: int, currency: str):
        """Save user's currency preference to database"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Detect database type and use appropriate syntax
            is_postgresql = hasattr(self.db_manager, 'db_config')  # PostgreSQL has db_config
            
            if is_postgresql:
                # PostgreSQL syntax with %s placeholders
                cursor.execute('SELECT id FROM user_preferences WHERE user_id = %s', (user_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing preference
                    cursor.execute('''
                        UPDATE user_preferences 
                        SET currency = %s, updated_at = CURRENT_TIMESTAMP 
                        WHERE user_id = %s
                    ''', (currency, user_id))
                else:
                    # Create new preference
                    cursor.execute('''
                        INSERT INTO user_preferences (user_id, currency, created_at, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (user_id, currency))
            else:
                # SQLite syntax with ? placeholders
                cursor.execute('SELECT id FROM user_preferences WHERE user_id = ?', (user_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing preference
                    cursor.execute('''
                        UPDATE user_preferences 
                        SET currency = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                    ''', (currency, user_id))
                else:
                    # Create new preference
                    cursor.execute('''
                        INSERT INTO user_preferences (user_id, currency, created_at, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (user_id, currency))
            
            conn.commit()
            conn.close()
            print(f"✅ Saved currency preference for user {user_id}: {currency}")
            
        except Exception as e:
            print(f"⚠️ Failed to save currency preference: {e}")
            import traceback
            traceback.print_exc()
    
    def get_user_currency_preference(self, user_id: int) -> str:
        """Get user's saved currency preference"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Detect database type and use appropriate syntax
            is_postgresql = hasattr(self.db_manager, 'db_config')  # PostgreSQL has db_config
            
            if is_postgresql:
                cursor.execute('SELECT currency FROM user_preferences WHERE user_id = %s', (user_id,))
            else:
                cursor.execute('SELECT currency FROM user_preferences WHERE user_id = ?', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0] if isinstance(result, tuple) else result['currency']
            
        except Exception as e:
            print(f"⚠️ Failed to get currency preference: {e}")
            import traceback
            traceback.print_exc()
        
        return self.default_currency

    def get_user_currency(self, user_id: int) -> str:
        """Get user's preferred currency or default"""
        return self.get_user_currency_preference(user_id)

    def get_currency_symbol(self, currency: str) -> str:
        """Get currency symbol for a given currency code"""
        return self.supported_currencies.get(currency, self.supported_currencies[self.default_currency])['symbol']

    def format_amount(self, amount: float, currency: str) -> str:
        """Format amount for display in the given currency"""
        if currency not in self.supported_currencies:
            currency = self.default_currency
        if currency in ['NGN', 'GHS', 'KES', 'ZAR', 'UGX', 'TZS', 'ZMW', 'XOF', 'XAF']:
            return f"{int(amount):,}"
        else:
            return f"{amount:,.2f}"

    def convert_and_format(self, amount_usd: float, from_currency: str, to_currency: str) -> str:
        """Convert USD amount to target currency and format for display"""
        converted = self.convert_price(amount_usd, from_currency, to_currency)
        return self.format_price(converted, to_currency)

# Create the currency service instance
currency_service = CurrencyService() 