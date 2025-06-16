#!/usr/bin/env python3
import os
import sys
import signal
import subprocess
import re

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 1. Kill all Flask/Python processes on common ports
def kill_flask_ports():
    ports = [5000, 5001, 5002, 5004]
    killed = False
    for port in ports:
        try:
            output = subprocess.check_output(f"lsof -ti :{port}", shell=True).decode().strip()
            if output:
                for pid in output.split('\n'):
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"✅ Killed process {pid} on port {port}")
                    killed = True
        except subprocess.CalledProcessError:
            pass
    if not killed:
        print("✅ No Flask/Python processes found on ports 5000, 5001, 5002, 5004.")

# 2. Check for credentials.json
def check_credentials():
    cred_path = os.path.join(PROJECT_ROOT, 'credentials.json')
    if not os.path.exists(cred_path):
        print("❌ credentials.json is missing! Please download it from Google Cloud Console and place it in the project root.")
    else:
        print("✅ credentials.json found.")

# 3. Check for OpenAI API key in .env
def check_openai_key():
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if not os.path.exists(env_path):
        print("❌ .env file is missing! Please create it and add your OPENAI_API_KEY.")
        return
    with open(env_path) as f:
        content = f.read()
    if 'OPENAI_API_KEY=' not in content or 'OPENAI_API_KEY=' in content and not content.split('OPENAI_API_KEY=')[1].strip():
        print("❌ OPENAI_API_KEY is missing or empty in .env! Please add a valid key.")
    else:
        print("✅ OPENAI_API_KEY found in .env.")

# 4. Check EmailProcessor initialization
def check_email_processor():
    app_py = os.path.join(PROJECT_ROOT, 'app.py')
    if not os.path.exists(app_py):
        print("⚠️ app.py not found!")
        return
    with open(app_py) as f:
        content = f.read()
    match = re.search(r'EmailProcessor\((.*?)\)', content)
    if match:
        args = match.group(1).strip()
        if args and args != '':
            print(f"⚠️ EmailProcessor is initialized with arguments: {args}. Check if this matches the class definition in email_processor.py.")
        else:
            print("✅ EmailProcessor is initialized with no arguments.")
    else:
        print("⚠️ EmailProcessor initialization not found in app.py.")

# 5. Check for 'import stripe' in payment_service.py
def check_stripe_import():
    ps_path = os.path.join(PROJECT_ROOT, 'payment_service.py')
    if not os.path.exists(ps_path):
        print("⚠️ payment_service.py not found!")
        return
    with open(ps_path) as f:
        content = f.read()
    if 'import stripe' in content:
        print("❌ 'import stripe' found in payment_service.py. Remove it if you are not using Stripe.")
    else:
        print("✅ No 'import stripe' found in payment_service.py.")

# 6. Check for /test-session route in app.py
def check_test_session_route():
    app_py = os.path.join(PROJECT_ROOT, 'app.py')
    if not os.path.exists(app_py):
        print("⚠️ app.py not found!")
        return
    with open(app_py) as f:
        content = f.read()
    if '/test-session' in content:
        print("✅ /test-session route found in app.py.")
    else:
        print("❌ /test-session route is missing in app.py. Add it to test session persistence.")

if __name__ == '__main__':
    print("\n🚀 Running Flask App One-Click Fix Script\n" + '='*60)
    kill_flask_ports()
    check_credentials()
    check_openai_key()
    check_email_processor()
    check_stripe_import()
    check_test_session_route()
    print("\n✅ All checks complete. Please fix any ❌ or ⚠️ issues above before running your app again.\n") 