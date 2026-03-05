import os
import sys

# Try to read the .env file
env_file = os.path.join(os.path.dirname(__file__), 'backend', '.env')
print(f"Looking for: {env_file}")
print(f"File exists: {os.path.exists(env_file)}")

if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        content = f.read()
        print("=== .env content ===")
        print(content)
        print("=== End ===")

# Also check what environment variables are loaded
print("\n=== Environment variables ===")
print(f"GEMINI_API_KEY: {os.environ.get('GEMINI_API_KEY', 'NOT SET')}")
print(f"GEMINI_API_KEYS: {os.environ.get('GEMINI_API_KEYS', 'NOT SET')}")
print(f"GEMINI_API_KEY_1: {os.environ.get('GEMINI_API_KEY_1', 'NOT SET')}")
