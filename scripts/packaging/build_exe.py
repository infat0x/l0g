#!/usr/bin/env python3
"""
Build script for creating standalone executable
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_build():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous build artifacts...")
    
    dirs_to_clean = ['out/build', 'out/dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   ✓ Removed {dir_name}/")
    
    # Clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))
    
    print("   ✓ Cleaned .pyc files")

def install_pyinstaller():
    """Install PyInstaller if not present"""
    print("📦 Checking PyInstaller installation...")
    try:
        import PyInstaller
        print(f"   ✓ PyInstaller {PyInstaller.__version__} already installed")
    except ImportError:
        print("   📥 Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"])
        print("   ✓ PyInstaller installed")

def build_executable():
    """Build the executable using PyInstaller"""
    print("🔨 Building executable...")
    
    # Check if spec file exists
    spec_path = os.path.join('scripts', 'packaging', 'log_analysis_cti.spec')
    if not os.path.exists(spec_path):
        print("   ❌ Spec file not found!")
        return False
    
    try:
        # Run PyInstaller
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", spec_path]
        print(f"   Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✓ Build successful!")
            return True
        else:
            print("   ❌ Build failed!")
            print("   Error output:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"   ❌ Build error: {e}")
        return False

def create_distribution():
    """Create distribution package"""
    print("📦 Creating distribution package...")
    
    dist_dir = Path("out") / "dist"
    if not dist_dir.exists():
        print("   ❌ Dist directory not found!")
        return False
    
    # Find the executable
    exe_files = list(dist_dir.glob("LogAnalysisCTI.exe"))
    if not exe_files:
        print("   ❌ Executable not found!")
        return False
    
    exe_file = exe_files[0]
    print(f"   ✓ Found executable: {exe_file}")
    
    # Create distribution folder
    dist_package = Path("out") / "LogAnalysisCTI_Standalone"
    if dist_package.exists():
        shutil.rmtree(dist_package)
    
    dist_package.mkdir()
    
    # Copy executable
    shutil.copy2(exe_file, dist_package / "LogAnalysisCTI.exe")
    
    # Copy icon
    icon_path = Path("src") / "log_analysis_cti" / "assets" / "l0g_dark_green.ico"
    if icon_path.exists():
        shutil.copy2(str(icon_path), dist_package / "l0g_dark_green.ico")
    
    # Create README for distribution
    readme_content = """# Log Analysis & CTI Tool - Standalone Version

## 🚀 Quick Start

1. Double-click `LogAnalysisCTI.exe` to launch the application
2. No installation required - all dependencies are included!

## 📋 System Requirements

- Windows 10/11 (64-bit)
- No additional software required

## 🎯 Features

- Modern dark theme GUI
- Interactive maps and charts  
- AI-powered log analysis
- Multiple report formats (HTML, PDF, Excel)
- Real-time progress tracking
- Console animation with hints

## 📁 File Structure

- `LogAnalysisCTI.exe` - Main application
- `l0g_dark_green.ico` - Application icon
- `reports/` - Generated reports (created automatically)

## 🔧 Usage

1. Launch the application
2. Click "Choose Log File" to select your log file
3. Click "Parse Logs" to start analysis
4. View results in different tabs
5. Generate reports in various formats

## 📞 Support

For issues or questions, check the main project documentation.

---
Built with PyInstaller - All dependencies included!
"""
    
    with open(dist_package / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"   ✓ Distribution package created: {dist_package}")
    print(f"   📁 Package size: {sum(f.stat().st_size for f in dist_package.rglob('*') if f.is_file()) / (1024*1024):.1f} MB")
    
    return True

def main():
    """Main build process"""
    print("🏗️  Log Analysis & CTI Tool - Executable Builder")
    print("=" * 50)
    
    # Step 1: Clean
    clean_build()
    
    # Step 2: Install PyInstaller
    install_pyinstaller()
    
    # Step 3: Build
    if not build_executable():
        print("\n❌ Build failed! Check the errors above.")
        return False
    
    # Step 4: Create distribution
    if not create_distribution():
        print("\n❌ Distribution creation failed!")
        return False
    
    print("\n🎉 Build completed successfully!")
    print("\n📦 Distribution package ready:")
    print("   📁 LogAnalysisCTI_Standalone/")
    print("   ├── LogAnalysisCTI.exe")
    print("   ├── l0g_dark_green.ico") 
    print("   └── README.txt")
    print("\n🚀 You can now distribute this folder to anyone!")
    print("   They just need to double-click LogAnalysisCTI.exe")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
