import os
import sys
from pathlib import Path
from src.config import get_config
from src.logger import get_logger
from src.validators import Validator

def check_dependencies():
    """Check if required dependencies are installed."""
    logger = get_logger()
    missing = []
    
    required = {
        'yt_dlp': 'yt-dlp',
        'moviepy': 'moviepy',
        'faster_whisper': 'faster-whisper',
        'google.generativeai': 'google-generativeai',
        'dotenv': 'python-dotenv',
        'selenium': 'selenium',
        'tqdm': 'tqdm',
        'yaml': 'pyyaml',
        'torch': 'torch'
    }
    
    for module, package in required.items():
        try:
            __import__(module)
            logger.info(f"✓ {package} installed")
        except ImportError:
            logger.warning(f"✗ {package} not installed")
            missing.append(package)
    
    return missing

def check_api_keys():
    """Check and guide user through API key setup."""
    logger = get_logger()
    config = get_config()
    
    # Check Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not found in environment variables")
        print("\n" + "="*60)
        print("Gemini API Key Setup")
        print("="*60)
        print("To use the content analyzer, you need a Gemini API key.")
        print("1. Get your API key from: https://makersuite.google.com/app/apikey")
        print("2. Add it to your .env file:")
        print("   GEMINI_API_KEY=your_api_key_here")
        print("\nOr set it as an environment variable:")
        print("   export GEMINI_API_KEY=your_api_key_here")
        
        response = input("\nDo you want to set it now? (y/n): ").strip().lower()
        if response == 'y':
            api_key = input("Enter your Gemini API key: ").strip()
            if api_key:
                is_valid, message = Validator.validate_api_key(api_key, "gemini")
                if is_valid:
                    # Write to .env file
                    env_path = Path('.env')
                    if env_path.exists():
                        with open(env_path, 'a') as f:
                            f.write(f"\nGEMINI_API_KEY={api_key}\n")
                    else:
                        with open(env_path, 'w') as f:
                            f.write(f"GEMINI_API_KEY={api_key}\n")
                    logger.info("API key saved to .env file")
                    os.environ["GEMINI_API_KEY"] = api_key
                else:
                    logger.error(f"Invalid API key: {message}")
                    return False
        else:
            logger.warning("Skipping API key setup. Some features will not work.")
            return False
    else:
        is_valid, message = Validator.validate_api_key(api_key, "gemini")
        if is_valid:
            logger.info("✓ Gemini API key found and valid")
        else:
            logger.warning(f"Gemini API key appears invalid: {message}")
            return False
    
    return True

def check_ffmpeg():
    """Check if ffmpeg is available."""
    logger = get_logger()
    import subprocess
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              timeout=5)
        if result.returncode == 0:
            logger.info("✓ ffmpeg is available")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    logger.warning("✗ ffmpeg not found")
    print("\n" + "="*60)
    print("FFmpeg Setup")
    print("="*60)
    print("FFmpeg is required for video processing.")
    print("Install it from: https://ffmpeg.org/download.html")
    print("Or use your package manager:")
    print("  - Windows: choco install ffmpeg")
    print("  - macOS: brew install ffmpeg")
    print("  - Linux: sudo apt install ffmpeg")
    return False

def check_directories():
    """Create necessary directories."""
    logger = get_logger()
    config = get_config()
    
    dirs = [
        config.get('system.output_dir', 'output'),
        config.get('system.download_dir', 'downloads'),
        config.get('cache.cache_dir', '.cache'),
        'logs'
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.debug(f"✓ Directory ready: {dir_path}")

def test_connections():
    """Test connections to external services."""
    logger = get_logger()
    
    # Test Gemini API if key is available
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content("Say hello")
            logger.info("✓ Gemini API connection successful")
        except Exception as e:
            logger.warning(f"✗ Gemini API connection failed: {e}")
            return False
    
    return True

def run_setup():
    """Run the setup wizard."""
    print("\n" + "="*60)
    print("OpenClip Setup Wizard")
    print("="*60 + "\n")
    
    logger = get_logger()
    logger.info("Starting setup wizard...")
    
    # Check dependencies
    print("\n[1/4] Checking dependencies...")
    missing = check_dependencies()
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install them with: pip install " + " ".join(missing))
        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            return False
    
    # Check FFmpeg
    print("\n[2/4] Checking FFmpeg...")
    if not check_ffmpeg():
        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            return False
    
    # Check API keys
    print("\n[3/4] Checking API keys...")
    api_ok = check_api_keys()
    
    # Create directories
    print("\n[4/4] Setting up directories...")
    check_directories()
    
    # Test connections
    if api_ok:
        print("\n[5/5] Testing connections...")
        test_connections()
    
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print("\nYou can now use OpenClip:")
    print("  python -m src.main <youtube_url>")
    print("\nFor help:")
    print("  python -m src.main --help")
    
    return True

if __name__ == "__main__":
    success = run_setup()
    sys.exit(0 if success else 1)

