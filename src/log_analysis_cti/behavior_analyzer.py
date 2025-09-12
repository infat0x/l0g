from typing import Dict, Any, List, Set
import re


class BehaviorAnalyzer:

    def __init__(self):
        self.sql_injection_pattern = re.compile(r"('|%27|--|%2D%2D|;|%3B|/\*|\*/|union\s+select|or\s+1=1|sleep\(\d+\))", re.I)
        self.path_traversal_pattern = re.compile(r"\.\./|%2e%2e/|%2e%2e%5c|/etc/passwd|/windows/system32|/proc/self|/sys/", re.I)
        self.admin_bruteforce_pattern = re.compile(r"/(admin|wp-admin|wp-login|login|manager|phpmyadmin)\b", re.I)
        self.shells_pattern = re.compile(r"(\.php\?|\.php$|\.asp$|\.aspx$|\.jsp$|/\w*shell\w*)", re.I)
        self.scanner_ua_pattern = re.compile(r"(nikto|dirbuster|wpscan|nmap|sqlmap)", re.I)

    def analyze(self, log_entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        per_ip: Dict[str, Dict[str, Any]] = {}

        for entry in log_entries:
            content = entry.get('content', '')
            ips = entry.get('ips_found') or []
            if not ips:
                continue

            uri_match = re.search(r'"uri":"([^"]*)"', content)
            method_match = re.search(r'"method":"([A-Z]+)"', content)
            status_match = re.search(r'"status":(\d{3})', content)
            ua_match = re.search(r'"user_agent":"([^"]*)"', content)

            uri = uri_match.group(1) if uri_match else ''
            method = method_match.group(1) if method_match else ''
            status = status_match.group(1) if status_match else ''

            indicators: Set[str] = set()
            if self.sql_injection_pattern.search(uri):
                indicators.add('sql_injection_pattern')
            if self.path_traversal_pattern.search(uri):
                indicators.add('path_traversal')
            if self.admin_bruteforce_pattern.search(uri):
                indicators.add('admin_login_scanning')
            if self.shells_pattern.search(uri):
                indicators.add('webshell_or_executable_probe')
            if method in {'TRACE', 'TRACK', 'DEBUG', 'PUT'}:
                indicators.add(f'unusual_method_{method.lower()}')
            if status in {'401', '403', '404', '405'}:
                indicators.add(f'high_error_rate_{status}')
            if ua_match and self.scanner_ua_pattern.search(ua_match.group(1)):
                indicators.add('known_scanner_user_agent')

            for ip in ips:
                data = per_ip.setdefault(ip, {
                    'count': 0,
                    'methods': set(),
                    'statuses': {},
                    'indicators': set()
                })
                data['count'] += 1
                if method:
                    data['methods'].add(method)
                if status:
                    data['statuses'][status] = data['statuses'].get(status, 0) + 1
                data['indicators'].update(indicators)

        for ip, data in per_ip.items():
            indicators = data['indicators']
            count = data['count']
            error_count = sum(v for k, v in data['statuses'].items() if k in {'401', '403', '404', '405'})

            score = 0.0
            score += 35 if 'sql_injection_pattern' in indicators else 0
            score += 30 if 'path_traversal' in indicators else 0
            score += 25 if 'webshell_or_executable_probe' in indicators else 0
            score += 20 if 'admin_login_scanning' in indicators else 0
            score += 18 if any(x.startswith('unusual_method_') for x in indicators) else 0
            score += 40 if 'known_scanner_user_agent' in indicators else 0

            score += min(25, count * 0.03)
            score += min(25, error_count * 0.07)

            if 'known_scanner_user_agent' in indicators and count >= 30:
                score = max(score, 70)

            score = min(100, int(round(score)))
            if score >= 60:
                level = 'high'
            elif score >= 40:
                level = 'medium'
            elif score >= 10:
                level = 'low'
            else:
                level = 'clean'

            data['risk_score'] = score
            data['threat_level'] = level
            data['methods'] = sorted(list(data['methods']))
            data['indicators'] = sorted(list(data['indicators']))

        return per_ip


