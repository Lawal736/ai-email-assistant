#!/usr/bin/env python3
"""
Script to help set up OAuth 2.0 redirect URIs for the AI Email Assistant
"""

def print_oauth_setup_instructions():
    """Print instructions for setting up OAuth 2.0 redirect URIs"""
    
    print("=" * 60)
    print("GOOGLE CLOUD CONSOLE OAUTH SETUP INSTRUCTIONS")
    print("=" * 60)
    print()
    print("To fix the 'Missing required parameter: redirect_uri' error,")
    print("you need to add the redirect URI to your OAuth 2.0 client:")
    print()
    print("1. Go to Google Cloud Console:")
    print("   https://console.cloud.google.com/")
    print()
    print("2. Select your project: ai-assistant-project-462808")
    print()
    print("3. Navigate to: APIs & Services > Credentials")
    print()
    print("4. Find your OAuth 2.0 Client ID and click on it")
    print()
    print("5. In the 'Authorized redirect URIs' section, add:")
    print("   http://localhost:5001/oauth2callback")
    print()
    print("6. Click 'Save'")
    print()
    print("7. Download the updated credentials.json file")
    print()
    print("8. Replace your current credentials.json with the new one")
    print()
    print("=" * 60)
    print("ALTERNATIVE: Convert to Desktop Application")
    print("=" * 60)
    print()
    print("If you prefer to use desktop application flow instead:")
    print()
    print("1. In Google Cloud Console, go to Credentials")
    print("2. Click 'Create Credentials' > 'OAuth 2.0 Client IDs'")
    print("3. Choose 'Desktop application' as the application type")
    print("4. Give it a name like 'AI Email Assistant Desktop'")
    print("5. Download the new credentials.json")
    print("6. Replace your current credentials.json")
    print()
    print("The desktop application flow doesn't require redirect URIs.")
    print("=" * 60)

if __name__ == "__main__":
    print_oauth_setup_instructions() 