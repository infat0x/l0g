import json
import re
import ipaddress
from typing import List, Dict, Any, Set
from colorama import Fore, Style

class LogParser:
    IP_PATTERN = re.compile(
        r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
        r'|'
        r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}'
        r'|'
        r'(?:[0-9a-fA-F]{1,4}:){1,7}:'
        r'|'
        r'(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}'
        r'|'
        r'(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}'
        r'|'
        r'(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}'
        r'|'
        r'(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}'
        r'|'
        r'(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}'
        r'|'
        r'[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}'
        r'|'
        r':(?::[0-9a-fA-F]{1,4}){1,7}'
        r'|'
        r'::'
    )
    
    COMMON_LOG_PATTERNS = {
        'apache_combined': r'(\S+) (\S+) (\S+) \[([^\]]+)\] "([^"]*)" (\d+) (\d+) "([^"]*)" "([^"]*)"',
        'nginx': r'(\S+) - (\S+) \[([^\]]+)\] "([^"]*)" (\d+) (\d+) "([^"]*)" "([^"]*)" (\S+)',
        'iis': r'(\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+)',
    }
    
    def __init__(self):
        self.parsed_ips = set()
        self.artifacts = []
        self.log_entries = []
    
    def parse_log(self, content: str) -> Dict[str, Any]:
        try:
            if self._is_json_format(content):
                return self._parse_json_log(content)
            else:
                return self._parse_text_log(content)
        except Exception as e:
            print(f"{Fore.RED}Error parsing log: {str(e)}{Style.RESET_ALL}")
            return {'ips': [], 'artifacts': [], 'log_entries': []}
    
    def _is_json_format(self, content: str) -> bool:
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, ValueError):
            lines = content.strip().split('\n')
            if len(lines) > 1:
                try:
                    for line in lines[:3]:
                        json.loads(line)
                    return True
                except (json.JSONDecodeError, ValueError):
                    pass
            return False
    
    def _parse_json_log(self, content: str) -> Dict[str, Any]:
        try:
            data = json.loads(content)
            if isinstance(data, list):
                entries = data
            else:
                entries = [data]
        except json.JSONDecodeError:
            entries = []
            for line in content.strip().split('\n'):
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        for entry in entries:
            self._extract_from_json_entry(entry)
        
        return {
            'ips': list(self.parsed_ips),
            'artifacts': self.artifacts,
            'log_entries': entries
        }
    
    def _parse_text_log(self, content: str) -> Dict[str, Any]:
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
            
            ips_in_line = set()
            try:
                json_start = line.find('{')
                if json_start != -1:
                    json_str = line[json_start:]
                    obj = json.loads(json_str)
                    if isinstance(obj, dict) and isinstance(obj.get('remote_addr'), str):
                        candidate_ip = obj.get('remote_addr')
                        try:
                            ipaddress.ip_address(candidate_ip)
                            ips_in_line.add(candidate_ip)
                        except ValueError:
                            pass
            except Exception:
                pass

            if not ips_in_line:
                ips_in_line = self._extract_ips_from_text(line)
            self.parsed_ips.update(ips_in_line)
            
            self.log_entries.append({
                'line_number': line_num,
                'content': line,
                'ips_found': list(ips_in_line)
            })
        
        return {
            'ips': list(self.parsed_ips),
            'artifacts': self.artifacts,
            'log_entries': self.log_entries
        }

    def parse_log_file(self, file_path: str) -> Dict[str, Any]:
        self.parsed_ips = set()
        self.artifacts = []
        self.log_entries = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    ips_in_line = set()
                    try:
                        json_start = line.find('{')
                        if json_start != -1:
                            json_str = line[json_start:]
                            obj = json.loads(json_str)
                            if isinstance(obj, dict) and isinstance(obj.get('remote_addr'), str):
                                candidate_ip = obj.get('remote_addr')
                                try:
                                    ipaddress.ip_address(candidate_ip)
                                    ips_in_line.add(candidate_ip)
                                except ValueError:
                                    pass
                    except Exception:
                        pass
                    if not ips_in_line:
                        ips_in_line = self._extract_ips_from_text(line)
                    self.parsed_ips.update(ips_in_line)
                    self.log_entries.append({
                        'line_number': line_num,
                        'content': line.rstrip('\n'),
                        'ips_found': list(ips_in_line)
                    })
            return {
                'ips': list(self.parsed_ips),
                'artifacts': self.artifacts,
                'log_entries': self.log_entries
            }
        except Exception as e:
            print(f"{Fore.RED}Error parsing file: {str(e)}{Style.RESET_ALL}")
            return {'ips': [], 'artifacts': [], 'log_entries': []}
    
    def _extract_from_json_entry(self, entry: Dict[str, Any]) -> None:
        if isinstance(entry, dict):
            remote = entry.get('remote_addr')
            if isinstance(remote, str):
                try:
                    ipaddress.ip_address(remote)
                    self.parsed_ips.add(remote)
                    return
                except ValueError:
                    pass
    
    def _extract_ips_from_text(self, text: str) -> Set[str]:
        ips = set()
        matches = self.IP_PATTERN.findall(text)
        
        for match in matches:
            try:
                ipaddress.ip_address(match)
                ips.add(match)
            except ValueError:
                continue
        
        return ips
    
    def filter_and_sort_ips(self, ips: List[str]) -> Dict[str, Any]:
        unique_ips = list(set(ips))
        public_ips = []
        private_ips = []
        
        for ip in unique_ips:
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    private_ips.append(ip)
                else:
                    public_ips.append(ip)
            except ValueError:
                continue
        
        return {
            'all_ips': unique_ips,
            'public_ips': public_ips,
            'private_ips': private_ips,
            'total_count': len(unique_ips),
            'public_count': len(public_ips),
            'private_count': len(private_ips)
        }
    
    def get_statistics(self, log_entries: List[Dict]) -> Dict[str, Any]:
        stats = {
            'total_entries': len(log_entries),
            'entries_with_ips': 0,
            'unique_ips': len(self.parsed_ips),
            'error_codes': {},
            'ip_frequency': {}
        }
        
        for entry in log_entries:
            if 'ips_found' in entry and entry['ips_found']:
                stats['entries_with_ips'] += 1
                
                for ip in entry['ips_found']:
                    stats['ip_frequency'][ip] = stats['ip_frequency'].get(ip, 0) + 1
            
            if 'content' in entry:
                status_match = re.search(r' (\d{3}) ', entry['content'])
                if status_match:
                    status_code = status_match.group(1)
                    stats['error_codes'][status_code] = stats['error_codes'].get(status_code, 0) + 1
        
        return stats
