#!/usr/bin/env python3
"""
Setup script for the Hybrid AI Email Assistant with Claude models.
This script helps you configure the AI service and test the setup.
"""

import os
import sys
import getpass
from dotenv import load_dotenv

def setup_environment():
    """Set up environment variables for the hybrid AI approach."""
    print("🤖 Hybrid AI Email Assistant Setup")
    print("=" * 50)
    
    # Load existing .env if it exists
    load_dotenv()
    
    # Check current configuration
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    print("🔑 Current API Key Status:")
    print(f"   Anthropic Claude: {'✅ Set' if anthropic_key else '❌ Missing'}")
    print(f"   OpenAI (Fallback): {'✅ Set' if openai_key else '❌ Missing'}")
    print()
    
    # Get Anthropic API Key
    if not anthropic_key:
        print("📝 Setting up Anthropic Claude API Key:")
        print("   Get your key from: https://console.anthropic.com/")
        print("   This is your PRIMARY AI provider for cost optimization.")
        anthropic_key = getpass.getpass("   Anthropic API Key: ").strip()
        
        if anthropic_key:
            # Update .env file
            update_env_file('ANTHROPIC_API_KEY', anthropic_key)
            print("   ✅ Anthropic API Key saved!")
        else:
            print("   ⚠️  No Anthropic key provided. You'll need this for optimal performance.")
    else:
        print("   ✅ Anthropic API Key already configured.")
    
    # Get OpenAI API Key (fallback)
    if not openai_key:
        print("\n📝 Setting up OpenAI API Key (Fallback):")
        print("   Get your key from: https://platform.openai.com/api-keys")
        print("   This is used as fallback when Claude is unavailable.")
        openai_key = getpass.getpass("   OpenAI API Key: ").strip()
        
        if openai_key:
            update_env_file('OPENAI_API_KEY', openai_key)
            print("   ✅ OpenAI API Key saved!")
        else:
            print("   ⚠️  No OpenAI key provided. Fallback won't be available.")
    else:
        print("   ✅ OpenAI API Key already configured.")
    
    # Optional configuration
    print("\n⚙️  Optional Configuration:")
    
    # Complexity threshold
    current_threshold = os.getenv('COMPLEXITY_THRESHOLD', '500')
    print(f"   Current complexity threshold: {current_threshold} characters")
    
    threshold_input = input("   New threshold (press Enter to keep current): ").strip()
    if threshold_input:
        try:
            threshold = int(threshold_input)
            update_env_file('COMPLEXITY_THRESHOLD', str(threshold))
            print(f"   ✅ Complexity threshold updated to {threshold}")
        except ValueError:
            print("   ⚠️  Invalid number, keeping current threshold.")
    
    print("\n🎉 Setup complete!")
    return True

def update_env_file(key, value):
    """Update or add a key-value pair in the .env file."""
    env_file = '.env'
    
    # Read existing .env file
    lines = []
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()
    
    # Find and update the key, or add it
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith(f'{key}='):
            lines[i] = f'{key}={value}\n'
            key_found = True
            break
    
    if not key_found:
        lines.append(f'{key}={value}\n')
    
    # Write back to .env file
    with open(env_file, 'w') as f:
        f.writelines(lines)

def test_setup():
    """Test the hybrid AI setup."""
    print("\n🧪 Testing Hybrid AI Setup")
    print("=" * 30)
    
    try:
        from ai_service import HybridAIService
        
        # Initialize the service
        ai_service = HybridAIService()
        print("✅ HybridAIService initialized successfully")
        
        # Test complexity calculation
        test_email = "Hi, just checking in on the project status. Thanks!"
        complexity = ai_service._calculate_complexity(test_email)
        print(f"✅ Complexity calculation working: {complexity['recommended_model']}")
        
        # Test API connectivity (if keys are available)
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            print("🔍 Testing Claude API connectivity...")
            try:
                result = ai_service.analyze_email(test_email, "summary")
                if result['success']:
                    print(f"✅ Claude API working: {result['model_used']}")
                else:
                    print(f"⚠️  Claude API error: {result['error']}")
            except Exception as e:
                print(f"⚠️  Claude API test failed: {str(e)}")
        else:
            print("⚠️  Skipping Claude API test (no key)")
        
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            print("🔍 Testing OpenAI API connectivity...")
            try:
                # Test fallback functionality
                result = ai_service._call_openai_api([
                    {"role": "user", "content": "Hello"}
                ])
                print("✅ OpenAI API working")
            except Exception as e:
                print(f"⚠️  OpenAI API test failed: {str(e)}")
        else:
            print("⚠️  Skipping OpenAI API test (no key)")
        
        print("\n🎉 Setup test completed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("   Make sure all dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def show_next_steps():
    """Show next steps for the user."""
    print("\n🚀 Next Steps")
    print("=" * 20)
    print("1. 📖 Read the documentation:")
    print("   - HYBRID_AI_GUIDE.md (comprehensive guide)")
    print("   - README.md (project overview)")
    print()
    print("2. 🧪 Run the test suite:")
    print("   python test_hybrid_ai.py")
    print()
    print("3. 🚀 Start the application:")
    print("   python app.py")
    print()
    print("4. 🌐 Access the web interface:")
    print("   http://localhost:5001")
    print()
    print("5. 📊 Monitor usage and costs:")
    print("   - Check Claude console for usage")
    print("   - Monitor fallback rates")
    print("   - Adjust complexity threshold as needed")
    print()
    print("💡 Tips:")
    print("   - Start with default settings")
    print("   - Monitor which models are used most")
    print("   - Adjust complexity threshold based on your email patterns")
    print("   - Keep both API keys for maximum reliability")

def main():
    """Main setup function."""
    try:
        # Setup environment
        if setup_environment():
            # Test the setup
            if test_setup():
                show_next_steps()
            else:
                print("\n❌ Setup test failed. Please check the errors above.")
                sys.exit(1)
        else:
            print("\n❌ Setup failed. Please try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 