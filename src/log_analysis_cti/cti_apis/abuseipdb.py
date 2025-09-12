import requests
import time
from typing import Dict, Any, Optional
from colorama import Fore, Style
from ..config import ABUSEIPDB_API_KEY, ABUSEIPDB_BASE_URL, RATE_LIMIT_DELAY, ABUSEIPDB_MAX_AGE
import re

class AbuseIPDBAPI:
    """AbuseIPDB API client for IP abuse analysis"""
    
    def __init__(self, api_key: str = None, progress_cb=None, rate_limit_delay: float = None):
        self.api_key = api_key or ABUSEIPDB_API_KEY
        self.base_url = ABUSEIPDB_BASE_URL
        self.headers = {
            'Key': self.api_key,
            'Accept': 'application/json'
        }
        self.rate_limit_delay = rate_limit_delay if rate_limit_delay is not None else RATE_LIMIT_DELAY
        self._progress_cb = progress_cb
    
    def check_ip_abuse(self, ip_address: str) -> Dict[str, Any]:
        """
        Check IP abuse using AbuseIPDB API
        
        Args:
            ip_address (str): IP address to check
            
        Returns:
            dict: AbuseIPDB analysis results
        """
        if not self.api_key:
            return {
                'error': 'AbuseIPDB API key not configured',
                'ip': ip_address,
                'status': 'error'
            }
        
        try:
            url = f"{self.base_url}/check"
            params = {
                'ipAddress': ip_address,
                'maxAgeInDays': ABUSEIPDB_MAX_AGE,
                'verbose': ''
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                parsed = self._parse_abuseipdb_response(data, ip_address)
                # Fallback: if API returns zero data but website shows otherwise, scrape UI page
                if parsed.get('status') == 'success' and parsed.get('abuse_confidence', 0) == 0 and parsed.get('total_reports', 0) == 0:
                    scraped = self._scrape_abuseipdb_page(ip_address)
                    if scraped:
                        return scraped
                return parsed
            elif response.status_code == 429:
                return {
                    'ip': ip_address,
                    'status': 'rate_limited',
                    'message': 'Rate limit exceeded, please try again later'
                }
            elif response.status_code == 403:
                return {
                    'ip': ip_address,
                    'status': 'error',
                    'message': 'API key invalid or quota exceeded'
                }
            else:
                return {
                    'ip': ip_address,
                    'status': 'error',
                    'message': f'API error: {response.status_code} - {response.text[:200]}'
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'ip': ip_address,
                'status': 'error',
                'message': f'Request failed: {str(e)}'
            }
        except Exception as e:
            return {
                'ip': ip_address,
                'status': 'error',
                'message': f'Unexpected error: {str(e)}'
            }
        finally:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
    
    def _parse_abuseipdb_response(self, data: Dict[str, Any], ip_address: str) -> Dict[str, Any]:
        """Parse AbuseIPDB API response"""
        try:
            if 'data' not in data:
                return {
                    'ip': ip_address,
                    'status': 'error',
                    'message': 'Invalid response format'
                }
            
            ip_data = data['data']
            
            # Extract abuse confidence
            abuse_confidence = ip_data.get('abuseConfidencePercentage', 0)
            
            # Extract country and ISP information
            country_code = ip_data.get('countryCode', 'Unknown')
            country_name = ip_data.get('countryName', 'Unknown')
            isp = ip_data.get('isp', 'Unknown')
            domain = ip_data.get('domain', 'Unknown')
            
            # Extract usage type
            usage_type = ip_data.get('usageType', 'Unknown')
            
            # Extract total reports
            total_reports = ip_data.get('totalReports', 0)
            
            # Extract distinct users
            distinct_users = ip_data.get('numDistinctUsers', 0)
            
            # Extract last reported date
            last_reported = ip_data.get('lastReportedAt', 'Unknown')
            
            # Determine threat level based on abuse confidence
            threat_level = self._determine_threat_level(abuse_confidence, total_reports)
            
            # Extract categories if available
            categories = ip_data.get('reports', [])
            category_summary = self._summarize_categories(categories)
            
            # Calculate risk score based on multiple factors
            risk_score = self._calculate_risk_score(abuse_confidence, total_reports, distinct_users, category_summary)
            
            # Generate comprehensive risk assessment
            risk_assessment = self._generate_risk_assessment(abuse_confidence, total_reports, distinct_users, category_summary)
            
            return {
                'ip': ip_address,
                'status': 'success',
                'abuse_confidence': abuse_confidence,
                'threat_level': threat_level,
                'risk_score': risk_score,
                'risk_assessment': risk_assessment,
                'total_reports': total_reports,
                'distinct_users': distinct_users,
                'last_reported': last_reported,
                'metadata': {
                    'country_code': country_code,
                    'country_name': country_name,
                    'isp': isp,
                    'domain': domain,
                    'usage_type': usage_type
                },
                'categories': category_summary,
                'raw_data': data
            }
        
        except Exception as e:
            return {
                'ip': ip_address,
                'status': 'error',
                'message': f'Error parsing response: {str(e)}'
            }
    
    def _determine_threat_level(self, abuse_confidence: int, total_reports: int) -> str:
        """Determine threat level using stricter mapping (closer to UI semantics)."""
        # AbuseIPDB UI often shows 100% confidence for heavily reported IPs.
        if abuse_confidence >= 90 or total_reports >= 500:
            return 'high'
        elif abuse_confidence >= 50 or total_reports >= 100:
            return 'medium'
        elif abuse_confidence > 0 or total_reports > 0:
            return 'low'
        else:
            return 'clean'
    
    def _summarize_categories(self, categories: list) -> Dict[str, int]:
        """Summarize abuse categories from reports"""
        category_counts = {}
        
        for report in categories:
            if 'categories' in report:
                for category in report['categories']:
                    category_name = self._get_category_name(category)
                    category_counts[category_name] = category_counts.get(category_name, 0) + 1
        
        return category_counts
    
    def _get_category_name(self, category_id: int) -> str:
        """Convert category ID to human-readable name"""
        category_map = {
            1: 'DNS Compromise',
            2: 'DNS Poisoning',
            3: 'Fraud Orders',
            4: 'DDoS Attack',
            5: 'FTP Brute-Force',
            6: 'Ping of Death',
            7: 'Phishing',
            8: 'Fraud VoIP',
            9: 'Open Proxy',
            10: 'Web Spam',
            11: 'Email Spam',
            12: 'Blog Spam',
            13: 'VPN IP',
            14: 'Port Scan',
            15: 'Hacking',
            16: 'SQL Injection',
            17: 'Spoofing',
            18: 'Brute-Force',
            19: 'Bad Web Bot',
            20: 'Exploited Host',
            21: 'Web App Attack',
            22: 'SSH',
            23: 'IoT Targeted'
        }
        return category_map.get(category_id, f'Unknown Category {category_id}')
    
    def _calculate_risk_score(self, abuse_confidence: int, total_reports: int, distinct_users: int, category_summary: Dict[str, int]) -> int:
        """Calculate comprehensive risk score (0-100)"""
        base_score = abuse_confidence
        
        # Adjust based on report volume
        if total_reports >= 1000:
            base_score += 20
        elif total_reports >= 500:
            base_score += 15
        elif total_reports >= 100:
            base_score += 10
        elif total_reports >= 50:
            base_score += 5
        
        # Adjust based on distinct users (indicates widespread abuse)
        if distinct_users >= 100:
            base_score += 15
        elif distinct_users >= 50:
            base_score += 10
        elif distinct_users >= 20:
            base_score += 5
        
        # Adjust based on threat categories
        high_threat_categories = ['DDoS Attack', 'Hacking', 'SQL Injection', 'Web App Attack', 'Exploited Host']
        medium_threat_categories = ['Port Scan', 'Brute-Force', 'Bad Web Bot', 'SSH', 'IoT Targeted']
        
        for category, count in category_summary.items():
            if category in high_threat_categories:
                base_score += min(15, count * 2)
            elif category in medium_threat_categories:
                base_score += min(10, count * 1)
            else:
                base_score += min(5, count)
        
        return min(100, max(0, base_score))
    
    def _generate_risk_assessment(self, abuse_confidence: int, total_reports: int, distinct_users: int, category_summary: Dict[str, int]) -> Dict[str, Any]:
        """Generate comprehensive risk assessment"""
        assessment = {
            'confidence_level': 'Unknown',
            'risk_factors': [],
            'recommendations': [],
            'threat_categories': list(category_summary.keys()),
            'severity': 'Unknown'
        }
        
        # Determine confidence level
        if abuse_confidence >= 90:
            assessment['confidence_level'] = 'Very High'
            assessment['severity'] = 'Critical'
        elif abuse_confidence >= 70:
            assessment['confidence_level'] = 'High'
            assessment['severity'] = 'High'
        elif abuse_confidence >= 50:
            assessment['confidence_level'] = 'Medium'
            assessment['severity'] = 'Medium'
        elif abuse_confidence >= 25:
            assessment['confidence_level'] = 'Low'
            assessment['severity'] = 'Low'
        else:
            assessment['confidence_level'] = 'Very Low'
            assessment['severity'] = 'Minimal'
        
        # Identify risk factors
        if total_reports >= 100:
            assessment['risk_factors'].append(f'High report volume ({total_reports} reports)')
        if distinct_users >= 50:
            assessment['risk_factors'].append(f'Widespread abuse ({distinct_users} distinct users)')
        if abuse_confidence >= 75:
            assessment['risk_factors'].append('High abuse confidence')
        
        # Generate recommendations
        if assessment['severity'] in ['Critical', 'High']:
            assessment['recommendations'].extend([
                'Immediate IP blocking recommended',
                'Investigate recent network activity',
                'Monitor for additional threats'
            ])
        elif assessment['severity'] == 'Medium':
            assessment['recommendations'].extend([
                'Consider temporary IP blocking',
                'Monitor network traffic',
                'Review security logs'
            ])
        else:
            assessment['recommendations'].append('Continue monitoring')
        
        return assessment

    def _scrape_abuseipdb_page(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Fallback: scrape AbuseIPDB web page to extract confidence and reports when API lacks data."""
        try:
            url = f"https://www.abuseipdb.com/check/{ip_address}"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                return None
            html = r.text
            # Confidence of Abuse is 100%
            conf_m = re.search(r"Confidence of Abuse is\s*(\d+)%", html, re.I)
            reports_m = re.search(r"This IP was reported\s*([\d,]+)\s*times", html, re.I)
            conf = int(conf_m.group(1)) if conf_m else 0
            total_reports = int(reports_m.group(1).replace(',', '')) if reports_m else 0
            threat_level = self._determine_threat_level(conf, total_reports)
            return {
                'ip': ip_address,
                'status': 'success',
                'abuse_confidence': conf,
                'threat_level': threat_level,
                'total_reports': total_reports,
                'distinct_users': None,
                'last_reported': None,
                'metadata': {},
                'categories': {},
                'raw_data': {'source': 'scrape'}
            }
        except Exception:
            return None
    
    def batch_check_ips(self, ip_addresses: list) -> Dict[str, Dict[str, Any]]:
        """
        Check multiple IP addresses with rate limiting
        
        Args:
            ip_addresses (list): List of IP addresses to check
            
        Returns:
            dict: Results for each IP address
        """
        results = {}
        
        msg = f"=== AbuseIPDB Analysis ===\nChecking {len(ip_addresses)} IPs with AbuseIPDB..."
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
            results[ip] = self.check_ip_abuse(ip)
        
        return results
