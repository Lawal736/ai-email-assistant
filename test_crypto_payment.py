#!/usr/bin/env python3
"""
Test script for crypto payment functionality
This script tests the USDT payment integration and Web3 connectivity.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_web3_connection():
    """Test Web3 connection to Ethereum network"""
    try:
        from web3 import Web3
        
        # Get provider URL from environment
        infura_url = os.getenv('INFURA_URL')
        if not infura_url:
            print("⚠️ INFURA_URL not found in environment variables")
            return False
        
        # Initialize Web3
        w3 = Web3(Web3.HTTPProvider(infura_url))
        
        if w3.is_connected():
            print("✅ Web3 connected to Ethereum network")
            
            # Get latest block number
            latest_block = w3.eth.block_number
            print(f"📦 Latest block: {latest_block}")
            
            return True
        else:
            print("❌ Failed to connect to Ethereum network")
            return False
            
    except ImportError:
        print("❌ Web3 library not installed. Run: pip install web3")
        return False
    except Exception as e:
        print(f"❌ Web3 connection error: {e}")
        return False

def test_usdt_contract():
    """Test USDT contract interaction"""
    try:
        from web3 import Web3
        
        infura_url = os.getenv('INFURA_URL')
        if not infura_url:
            print("⚠️ INFURA_URL not found in environment variables")
            return False
        
        w3 = Web3(Web3.HTTPProvider(infura_url))
        
        # USDT contract address (ERC20 on Ethereum Mainnet)
        usdt_address = "0x75Fc169eD2832e33F74D31430249e09c09358A75"
        
        # Basic ERC20 ABI for balanceOf function
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        # Create contract instance
        contract = w3.eth.contract(
            address=w3.to_checksum_address(usdt_address),
            abi=abi
        )
        
        # Test balanceOf function with a known address (USDT contract itself)
        try:
            balance = contract.functions.balanceOf(
                w3.to_checksum_address(usdt_address)
            ).call()
            
            print("✅ USDT contract interaction successful")
            print(f"📊 Contract balance: {balance} wei")
            
            return True
            
        except Exception as e:
            print(f"❌ USDT contract call failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ USDT contract test error: {e}")
        return False

def test_payment_service():
    """Test PaymentService crypto functionality"""
    try:
        from payment_service import PaymentService
        
        payment_service = PaymentService()
        
        # Test payment methods
        methods = payment_service.get_payment_methods()
        print(f"✅ Found {len(methods)} payment methods:")
        
        for method in methods:
            print(f"   - {method['name']}: {method['description']}")
            if method['type'] == 'crypto':
                print(f"     Contract: {method['contract_address']}")
                print(f"     Network: {method['network']}")
        
        # Test crypto payment session creation
        test_session = payment_service.create_crypto_payment_session(
            amount_usd=19.99,
            user_id=1,
            plan_type='pro'
        )
        
        if 'error' in test_session:
            print(f"❌ Crypto payment session creation failed: {test_session['error']}")
            return False
        
        print("✅ Crypto payment session created successfully")
        print(f"   Payment ID: {test_session['payment_id']}")
        print(f"   Amount: {test_session['amount_usdt']} USDT")
        print(f"   Address: {test_session['usdt_address']}")
        
        return True
        
    except ImportError:
        print("❌ PaymentService not available")
        return False
    except Exception as e:
        print(f"❌ PaymentService test error: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    print("🔧 Testing Environment Configuration:")
    
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'GMAIL_CLIENT_ID',
        'GMAIL_CLIENT_SECRET',
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'STRIPE_PUBLISHABLE_KEY',
        'STRIPE_SECRET_KEY',
        'INFURA_URL'
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value and value != f'your_{var.lower()}_here':
            print(f"✅ {var}: Configured")
        else:
            print(f"⚠️ {var}: Not configured")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("Please update your .env file with the required values.")
        return False
    
    print("\n✅ All required environment variables are configured")
    return True

def main():
    """Main test function"""
    print("🚀 Crypto Payment System Test")
    print("=" * 50)
    
    # Test environment
    env_ok = test_environment()
    
    print("\n" + "=" * 50)
    print("🔗 Testing Web3 Connection:")
    
    # Test Web3 connection
    web3_ok = test_web3_connection()
    
    print("\n" + "=" * 50)
    print("📄 Testing USDT Contract:")
    
    # Test USDT contract
    contract_ok = test_usdt_contract()
    
    print("\n" + "=" * 50)
    print("💳 Testing Payment Service:")
    
    # Test payment service
    payment_ok = test_payment_service()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    results = [
        ("Environment", env_ok),
        ("Web3 Connection", web3_ok),
        ("USDT Contract", contract_ok),
        ("Payment Service", payment_ok)
    ]
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All tests passed! Crypto payment system is ready.")
        print("\nNext steps:")
        print("1. Start the application: python app.py")
        print("2. Visit: http://localhost:5001")
        print("3. Test crypto payment flow in the pricing page")
    else:
        print("⚠️ Some tests failed. Please check the configuration.")
        print("\nCommon issues:")
        print("- Missing environment variables in .env file")
        print("- Invalid Infura URL or API key")
        print("- Network connectivity issues")
        print("- Missing dependencies (run: pip install -r requirements.txt)")

if __name__ == "__main__":
    main() 