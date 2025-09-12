#!/usr/bin/env python3
"""
Setup script for Log Analysis & CTI Tool
"""
import os
import sys
import subprocess
from pathlib import Path

def install_requirements():
    """Install required Python packages"""
    print("Installing required packages...")
    try:
        req_path = os.path.join('scripts', 'packaging', 'requirements.txt')
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    directories = [os.path.join("out", "reports"), "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")

def setup_environment():
    """Set up environment file"""
    print("Setting up environment configuration...")
    
    env_file = Path(".env")
    env_example = Path("env_example.txt")
    
    if not env_file.exists() and env_example.exists():
        # Copy example to .env
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✓ Created .env file from template")
        print("  Please edit .env file with your API keys")
    else:
        print("✓ Environment file already exists")

def run_tests():
    """Run basic tests"""
    print("Running basic tests...")
    try:
        # Test basic imports
        from log_analysis_cti import file_validator, log_parser, behavior_analyzer, report_generator
        from log_analysis_cti.cti_apis.cti_manager import CTIManager
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("Log Analysis & CTI Tool - Setup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("✗ Python 3.7 or higher is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Setup environment
    setup_environment()
    
    # Run tests
    if not run_tests():
        print("⚠ Setup completed but tests failed")
        print("  You may need to check your configuration")
    else:
        print("\n✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit .env file with your API keys (optional)")
        print("2. Run: python -m log_analysis_cti.main <log_file_path>")
        print("3. Check the out/reports/ directory for results")

if __name__ == "__main__":
    main()
