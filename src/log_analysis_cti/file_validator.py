import os
import sys
from pathlib import Path
from colorama import Fore, Style

class FileValidator:
    @staticmethod
    def validate_file_path(file_path):
        try:
            path = Path(file_path)
            
            if not path.exists():
                return False, f"File does not exist: {file_path}", None
            
            if not path.is_file():
                return False, f"Path is not a file: {file_path}", None
            
            if not os.access(file_path, os.R_OK):
                return False, f"File is not readable: {file_path}", None
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                return True, None, content
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as file:
                        content = file.read()
                    return True, None, content
                except Exception as e:
                    return False, f"Could not read file with any encoding: {str(e)}", None
            except Exception as e:
                return False, f"Error reading file: {str(e)}", None
                
        except Exception as e:
            return False, f"Unexpected error during validation: {str(e)}", None
    
    @staticmethod
    def print_usage():
        print(f"{Fore.CYAN}Log Analysis & CTI Tool{Style.RESET_ALL}")
        print("=" * 50)
        print("Usage: python main.py <log_file_path>")
        print("\nExample:")
        print("  python main.py access.log")
        print("  python main.py /path/to/security.log")
        print("\nFeatures:")
        print("  - Parse log files (JSON, plain text)")
        print("  - Extract IP addresses and artifacts")
        print("  - Enrich with CTI data (VirusTotal, AbuseIPDB, Cisco Talos)")
        print("  - Generate comprehensive threat intelligence reports")
        print("\nRequired API Keys:")
        print("  - VIRUSTOTAL_API_KEY (for VirusTotal integration)")
        print("  - ABUSEIPDB_API_KEY (for AbuseIPDB integration)")
        print("  - Set these in a .env file or environment variables")
