#!/usr/bin/env python3
"""
Installation script for medical NLP models
This script installs the required spaCy and scispaCy models for medical text processing.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"{'='*60}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("✅ Success!")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required!")
        return False
    
    print("✅ Python version is compatible")
    return True

def install_basic_requirements():
    """Install basic requirements first"""
    commands = [
        ("pip install --upgrade pip", "Upgrading pip"),
        ("pip install wheel setuptools", "Installing build tools"),
        ("pip install spacy>=3.7.0", "Installing spaCy"),
        ("pip install scispacy>=0.5.4", "Installing scispaCy"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def install_spacy_models():
    """Install spaCy models"""
    commands = [
        ("python -m spacy download en_core_web_sm", "Installing basic English model"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            print("⚠️  Warning: Basic model installation failed, but continuing...")
    
    return True

def install_scispacy_models():
    """Install scispaCy models"""
    models = [
        {
            "url": "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz",
            "name": "en_core_sci_sm",
            "description": "Scientific/medical text processing model"
        },
        {
            "url": "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz", 
            "name": "en_ner_bc5cdr_md",
            "description": "Biomedical named entity recognition model"
        }
    ]
    
    for model in models:
        command = f"pip install {model['url']}"
        if not run_command(command, f"Installing {model['description']}"):
            print(f"⚠️  Warning: {model['name']} installation failed")
    
    return True

def test_installation():
    """Test if the installation works"""
    print(f"\n{'='*60}")
    print("🧪 Testing medical NLP installation")
    print(f"{'='*60}")
    
    test_code = '''
import spacy
from medical_spell_check.medical_nlp import MedicalNLP

# Test basic functionality
try:
    nlp = MedicalNLP()
    status = nlp.get_status()
    
    print("Medical NLP Status:")
    print(f"  Available: {status['available']}")
    if status.get('models'):
        print(f"  Main model: {status['models'].get('nlp', 'None')}")
        print(f"  NER model: {status['models'].get('ner', 'None')}")
    
    if status['available']:
        # Test entity recognition
        test_text = "Patient has diabetes and takes metformin 500mg daily. HbA1c is elevated."
        entities = nlp.identify_medical_entities(test_text)
        print(f"  Found {len(entities)} medical entities in test text")
        for entity, start, end, label, category in entities[:3]:  # Show first 3
            print(f"    - {entity} ({category})")
        
        print("✅ Medical NLP is working correctly!")
    else:
        print("⚠️  Medical NLP is not fully available, but basic functionality may work")
        if status.get('error'):
            print(f"     Error: {status['error']}")
            
except Exception as e:
    print(f"❌ Test failed: {e}")
    print("💡 You may need to restart your application after installation")
'''
    
    try:
        exec(test_code)
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 This is normal if you haven't restarted your application yet")
        return False

def main():
    """Main installation process"""
    print("🏥 Medical Spell Checker - Model Installation")
    print("=" * 60)
    print("This script will install the required models for medical NLP processing.")
    print("This may take several minutes as it downloads large model files.")
    print()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install requirements
    print("\n📦 Installing basic requirements...")
    if not install_basic_requirements():
        print("❌ Failed to install basic requirements!")
        sys.exit(1)
    
    # Install spaCy models
    print("\n📦 Installing spaCy models...")
    install_spacy_models()
    
    # Install scispaCy models
    print("\n📦 Installing scispaCy models...")
    install_scispacy_models()
    
    # Test installation
    print("\n🧪 Testing installation...")
    test_installation()
    
    print(f"\n{'='*60}")
    print("🎉 Installation complete!")
    print(f"{'='*60}")
    print()
    print("Next steps:")
    print("1. Restart your Flask application")
    print("2. The medical spell checker will automatically use the new models")
    print("3. Check the legend in the frontend to see if 'Medical NLP Active' appears")
    print()
    print("If you encounter issues:")
    print("- Make sure you have sufficient disk space (models are ~100MB each)")
    print("- Try running this script with administrator/sudo privileges")
    print("- Check your internet connection")
    print()

if __name__ == "__main__":
    main()