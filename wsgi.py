import sys
import os

# Add the project directory to the Python path
path = '/home/yourusername/myproject'
if path not in sys.path:
    sys.path.append(path)

from app import app as application

if __name__ == "__main__":
    application.run()

