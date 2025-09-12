import requests
import time
from typing import Dict, Any, Optional
from colorama import Fore, Style
from ..config import VIRUSTOTAL_API_KEY, VIRUSTOTAL_BASE_URL, RATE_LIMIT_DELAY

class VirusTotalAPI:
    """VirusTotal API client for IP reputation analysis"""
    
    def __init__(self, api_key: str = None, progress_cb=None, rate_limit_delay: float = None):
        self.api_key = api_key or VIRUSTOTAL_API_KEY
        self.base_url = VIRUSTOTAL_BASE_URL
        self.headers = {
            'x-apikey': self.api_key,
            'Accept': 'application/json'
        }
        self.rate_limit_delay = rate_limit_delay if rate_limit_delay is not None else RATE_LIMIT_DELAY
        self._progress_cb = progress_cb
    
    def check_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """
        Check IP reputation using VirusTotal API
        
        Args:
            ip_address (str): IP address to check
            
        Returns:
            dict: VirusTotal analysis results
        """
        if not self.api_key:
            return {
                'error': 'VirusTotal API key not configured',
                'ip': ip_address,
                'status': 'error'
            }
        
        try:
            url = f"{self.base_url}/ip_addresses/{ip_address}"
            print(f"DEBUG VT: Checking {ip_address} with URL: {url}")
            print(f"DEBUG VT: API Key present: {bool(self.api_key)}")
            response = requests.get(url, headers=self.headers, timeout=30)
            
            print(f"DEBUG VT: Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"DEBUG VT: Success response for {ip_address}")
                return self._parse_virustotal_response(data, ip_address)
            elif response.status_code == 404:
                print(f"DEBUG VT: IP {ip_address} not found in database")
                return {
                    'ip': ip_address,
                    'status': 'not_found',
                    'message': 'IP not found in VirusTotal database'
                }
            elif response.status_code == 429:
                print(f"DEBUG VT: Rate limit exceeded for {ip_address}")
                return {
                    'ip': ip_address,
                    'status': 'rate_limited',
                    'message': 'Rate limit exceeded, please try again later'
                }
            elif response.status_code == 403:
                print(f"DEBUG VT: API key invalid for {ip_address}")
                return {
                    'ip': ip_address,
                    'status': 'error',
                    'message': 'API key invalid or quota exceeded'
                }
            else:
                print(f"DEBUG VT: Error {response.status_code} for {ip_address}: {response.text[:200]}")
                return {
                    'ip': ip_address,
                    'status': 'error',
                    'message': f'API error: {response.status_code} - {response.text[:200]}'
                }
        
        except requests.exceptions.RequestException as e:
            print(f"DEBUG VT: Request failed for {ip_address}: {str(e)}")
            return {
                'ip': ip_address,
                'status': 'error',
                'message': f'Request failed: {str(e)}'
            }
        except Exception as e:
            print(f"DEBUG VT: Unexpected error for {ip_address}: {str(e)}")
            return {
                'ip': ip_address,
                'status': 'error',
                'message': f'Unexpected error: {str(e)}'
            }
        finally:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
    
    def _parse_virustotal_response(self, data: Dict[str, Any], ip_address: str) -> Dict[str, Any]:
        """Parse VirusTotal API response"""
        try:
            attributes = data.get('data', {}).get('attributes', {})
            
            # Extract reputation score
            reputation = attributes.get('reputation', 0)
            
            # Extract last analysis results
            last_analysis_results = attributes.get('last_analysis_results', {})
            
            # Calculate threat categories
            harmless_count = 0
            malicious_count = 0
            suspicious_count = 0
            undetected_count = 0
            
            for engine, result in last_analysis_results.items():
                category = result.get('category', 'undetected')
                if category == 'harmless':
                    harmless_count += 1
                elif category == 'malicious':
                    malicious_count += 1
                elif category == 'suspicious':
                    suspicious_count += 1
                else:
                    undetected_count += 1
            
            # Determine overall threat level
            total_engines = len(last_analysis_results)
            threat_level = self._determine_threat_level(
                malicious_count, suspicious_count, harmless_count, total_engines
            )
            
            # Extract additional metadata
            as_owner = attributes.get('as_owner', 'Unknown')
            asn = attributes.get('asn', 'Unknown')
            country = attributes.get('country', 'Unknown')
            continent = attributes.get('continent', 'Unknown')
            
            return {
                'ip': ip_address,
                'status': 'success',
                'reputation': reputation,
                'threat_level': threat_level,
                'analysis_stats': {
                    'total_engines': total_engines,
                    'harmless': harmless_count,
                    'malicious': malicious_count,
                    'suspicious': suspicious_count,
                    'undetected': undetected_count
                },
                'metadata': {
                    'as_owner': as_owner,
                    'asn': asn,
                    'country': country,
                    'continent': continent
                },
                'last_analysis_date': attributes.get('last_analysis_date'),
                'raw_data': data
            }
        
        except Exception as e:
            return {
                'ip': ip_address,
                'status': 'error',
                'message': f'Error parsing response: {str(e)}'
            }
    
    def _determine_threat_level(self, malicious: int, suspicious: int, harmless: int, total: int) -> str:
        """Determine overall threat level based on analysis results"""
        if total == 0:
            return 'unknown'
        
        malicious_ratio = malicious / total
        suspicious_ratio = suspicious / total
        
        if malicious_ratio >= 0.5:
            return 'high'
        elif malicious_ratio >= 0.1 or suspicious_ratio >= 0.3:
            return 'medium'
        elif malicious_ratio > 0 or suspicious_ratio > 0:
            return 'low'
        else:
            return 'clean'
    
    def get_detailed_analysis(self, ip_address: str) -> Dict[str, Any]:
        """
        Get detailed analysis information from VirusTotal
        
        Args:
            ip_address (str): IP address to analyze
            
        Returns:
            dict: Detailed analysis results
        """
        if not self.api_key:
            return {
                'error': 'VirusTotal API key not configured',
                'ip': ip_address,
                'status': 'error'
            }
        
        try:
            # Get basic IP information
            url = f"{self.base_url}/ip_addresses/{ip_address}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                attributes = data.get('data', {}).get('attributes', {})
                
                # Extract detailed information
                detailed_info = {
                    'ip': ip_address,
                    'status': 'success',
                    'last_analysis_date': attributes.get('last_analysis_date'),
                    'last_analysis_stats': attributes.get('last_analysis_stats', {}),
                    'reputation': attributes.get('reputation', 0),
                    'network': attributes.get('network', ''),
                    'asn': attributes.get('asn', 0),
                    'as_owner': attributes.get('as_owner', ''),
                    'country': attributes.get('country', ''),
                    'continent': attributes.get('continent', ''),
                    'regional_internet_registry': attributes.get('regional_internet_registry', ''),
                    'whois': attributes.get('whois', ''),
                    'crowdsourced_context': attributes.get('crowdsourced_context', []),
                    'last_modification_date': attributes.get('last_modification_date'),
                    'total_votes': attributes.get('total_votes', {}),
                    'tags': attributes.get('tags', []),
                    'raw_data': data
                }
                
                return detailed_info
            else:
                return {
                    'ip': ip_address,
                    'status': 'error',
                    'message': f'HTTP {response.status_code}: {response.text}'
                }
                
        except Exception as e:
            return {
                'ip': ip_address,
                'status': 'error',
                'message': str(e)
            }
    
    def batch_check_ips(self, ip_addresses: list) -> Dict[str, Dict[str, Any]]:
        """
        Check multiple IP addresses with rate limiting
        
        Args:
            ip_addresses (list): List of IP addresses to check
            
        Returns:
            dict: Results for each IP address
        """
        results = {}
        
        msg = f"=== VirusTotal Analysis ===\nChecking {len(ip_addresses)} IPs with VirusTotal..."
        try:
            if self._progress_cb:
                self._progress_cb(msg)
        except Exception:
            pass
        print(f"{Fore.CYAN}{msg}{Style.RESET_ALL}")
        
        for i, ip in enumerate(ip_addresses, 1):
            step = f"[{i}/{len(ip_addresses)}] Checking {ip}..."
            try:
                if self._progress_cb:
                    self._progress_cb(step)
            except Exception:
                pass
            print(f"{Fore.CYAN}{step}{Style.RESET_ALL}")
            results[ip] = self.check_ip_reputation(ip)
        
        return results
