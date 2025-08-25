import sys
import os

print("--- Python's Search Path (sys.path) ---")
for path in sys.path:
    print(path)

print("\n--- Current Working Directory ---")
print(os.getcwd())

print("\n--- Directory Contents ---")
try:
    print(os.listdir(os.getcwd()))
except Exception as e:
    print(f"Could not list directory contents: {e}")