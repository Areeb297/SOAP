"""
TextBlob initialization script for medical spell checker
This script ensures TextBlob corpora are downloaded
"""

import subprocess
import sys

def setup_textblob():
    """Download required TextBlob corpora"""
    try:
        # Try importing textblob first
        import textblob
        
        # Download corpora
        print("Downloading TextBlob corpora...")
        subprocess.check_call([sys.executable, "-m", "textblob.download_corpora"])
        print("TextBlob corpora downloaded successfully!")
        
    except ImportError:
        print("TextBlob not installed. Please run: pip install textblob")
        return False
    except Exception as e:
        print(f"Error setting up TextBlob: {e}")
        return False
    
    return True

if __name__ == "__main__":
    setup_textblob()
