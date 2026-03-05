import os
env_path = r'c:\Users\HP\OneDrive\OneDrive - The Hope Haven Charitable Trust\Documents\football\backend\.env'
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        print(f.read())
else:
    print("File not found")
