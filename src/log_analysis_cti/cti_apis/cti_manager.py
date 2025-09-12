from typing import Dict, List, Any
from colorama import Fore, Style
from .virustotal import VirusTotalAPI
from .abuseipdb import AbuseIPDBAPI

class CTIManager:
    """Manages all CTI API integrations and aggregates results"""
    
    def __init__(self, virustotal_key: str = None, abuseipdb_key: str = None, progress_cb=None, rate_limit_delay: float = None):
        self.virustotal = VirusTotalAPI(virustotal_key, progress_cb=progress_cb, rate_limit_delay=rate_limit_delay)
        self.abuseipdb = AbuseIPDBAPI(abuseipdb_key, progress_cb=progress_cb, rate_limit_delay=rate_limit_delay)
        self._progress_cb = progress_cb
    
    def enrich_ips(self, ip_addresses: List[str], behavior_results: Dict[str, Any] = None) -> Dict[str, Dict[str, Any]]:
        """
        Enrich IP addresses with threat intelligence from all sources
        
        Args:
            ip_addresses (List[str]): List of IP addresses to enrich
            
        Returns:
            Dict[str, Dict[str, Any]]: Enriched data for each IP
        """
        msg = f"Starting CTI enrichment for {len(ip_addresses)} IP addresses..."
        try:
            if self._progress_cb:
                self._progress_cb(msg)
        except Exception:
            pass
        print(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")
        
        # Initialize results structure
        enriched_data = {}
        
        for ip in ip_addresses:
            enriched_data[ip] = {
                'ip': ip,
                'virustotal': {},
                'abuseipdb': {},
                'behavior': behavior_results.get(ip, {}) if behavior_results else {},
                'overall_threat_level': 'unknown',
                'risk_score': 0,
                'abuse_confidence': None
            }
        
        # Optimize: Check API keys first to avoid unnecessary calls
        vt_available = bool(self.virustotal.api_key)
        abuse_available = bool(self.abuseipdb.api_key)
        
        # Get data from available sources
        vt_results = {}
        abuse_results = {}
        
        if vt_available:
            print(f"\n{Fore.CYAN}=== VirusTotal Analysis ==={Style.RESET_ALL}")
            vt_results = self.virustotal.batch_check_ips(ip_addresses)
        
        if abuse_available:
            print(f"\n{Fore.CYAN}=== AbuseIPDB Analysis ==={Style.RESET_ALL}")
            abuse_results = self.abuseipdb.batch_check_ips(ip_addresses)
        
        # Aggregate results
        for ip in ip_addresses:
            enriched_data[ip]['virustotal'] = vt_results.get(ip, {})
            enriched_data[ip]['abuseipdb'] = abuse_results.get(ip, {})
            if behavior_results:
                enriched_data[ip]['behavior'] = behavior_results.get(ip, {})
            # Expose abuseipdb confidence at top level for UI
            if enriched_data[ip]['abuseipdb'].get('status') == 'success':
                enriched_data[ip]['abuse_confidence'] = enriched_data[ip]['abuseipdb'].get('abuse_confidence')
            
            # Calculate overall threat level and risk score
            threat_level, risk_score = self._calculate_overall_assessment(enriched_data[ip])
            enriched_data[ip]['overall_threat_level'] = threat_level
            enriched_data[ip]['risk_score'] = risk_score
        
        return enriched_data
    
    def _calculate_overall_assessment(self, ip_data: Dict[str, Any]) -> tuple:
        """
        Calculate overall threat level and risk score based on all sources
        
        Args:
            ip_data (Dict[str, Any]): Enriched data for a single IP
            
        Returns:
            tuple: (threat_level, risk_score)
        """
        threat_scores = []
        risk_factors = []
        
        # VirusTotal assessment
        vt_data = ip_data.get('virustotal', {})
        if vt_data.get('status') == 'success':
            vt_threat = vt_data.get('threat_level', 'unknown')
            vt_reputation = vt_data.get('reputation', 0)
            
            if vt_threat == 'high':
                threat_scores.append(3)
                risk_factors.append(0.4)
            elif vt_threat == 'medium':
                threat_scores.append(2)
                risk_factors.append(0.2)
            elif vt_threat == 'low':
                threat_scores.append(1)
                risk_factors.append(0.1)
            else:
                threat_scores.append(0)
                risk_factors.append(0)
        
        # AbuseIPDB assessment
        abuse_data = ip_data.get('abuseipdb', {})
        if abuse_data.get('status') == 'success':
            abuse_threat = abuse_data.get('threat_level', 'unknown')
            abuse_confidence = abuse_data.get('abuse_confidence', 0)
            abuse_risk_score = abuse_data.get('risk_score', 0)
            
            # Use AbuseIPDB's calculated risk score if available
            if abuse_risk_score > 0:
                risk_factors.append(abuse_risk_score / 100.0 * 0.4)  # Weight AbuseIPDB risk score heavily
            
            if abuse_threat == 'high':
                threat_scores.append(3)
                risk_factors.append(0.3)
            elif abuse_threat == 'medium':
                threat_scores.append(2)
                risk_factors.append(0.15)
            elif abuse_threat == 'low':
                threat_scores.append(1)
                risk_factors.append(0.05)
            else:
                threat_scores.append(0)
                risk_factors.append(0)
        
        # Talos removed - no longer used
        
        # Behavior-based assessment (internal heuristic)
        behavior_data = ip_data.get('behavior', {})
        if behavior_data:
            beh_threat = behavior_data.get('threat_level', 'unknown')
            beh_score = behavior_data.get('risk_score', 0)
            if beh_threat == 'high':
                threat_scores.append(3)
                risk_factors.append(0.4)
            elif beh_threat == 'medium':
                threat_scores.append(2)
                risk_factors.append(0.25)
            elif beh_threat == 'low':
                threat_scores.append(1)
                risk_factors.append(0.1)
            else:
                threat_scores.append(0)
                risk_factors.append(0)
            # Add normalized behavior score contribution
            risk_factors.append(min(1.0, beh_score / 100.0) * 0.5)

        # Calculate risk score (0-100)
        risk_score = min(100, sum(risk_factors) * 100)
        
        # Calculate overall threat level
        if not threat_scores:
            return 'unknown', risk_score
        
        avg_threat_score = sum(threat_scores) / len(threat_scores)
        
        # Priority: If risk score > 70%, automatically mark as high threat
        if risk_score > 70:
            threat_level = 'high'
        elif avg_threat_score >= 2.5:
            threat_level = 'high'
        elif avg_threat_score >= 1.5:
            threat_level = 'medium'
        elif avg_threat_score >= 0.5:
            threat_level = 'low'
        else:
            threat_level = 'clean'
        
        return threat_level, risk_score
    
    def get_summary_statistics(self, enriched_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics from enriched data
        
        Args:
            enriched_data (Dict[str, Dict[str, Any]]): Enriched IP data
            
        Returns:
            Dict[str, Any]: Summary statistics
        """
        stats = {
            'total_ips': len(enriched_data),
            'threat_levels': {
                'high': 0,
                'medium': 0,
                'low': 0,
                'clean': 0,
                'unknown': 0
            },
            'risk_distribution': {
                'high_risk': 0,    # 70-100
                'medium_risk': 0,  # 30-69
                'low_risk': 0,     # 1-29
                'no_risk': 0       # 0
            },
            'source_availability': {
                'virustotal': 0,
                'abuseipdb': 0
            },
            'suspicious_ips': [],
            'clean_ips': []
        }
        
        for ip, data in enriched_data.items():
            # Count threat levels
            threat_level = data.get('overall_threat_level', 'unknown')
            stats['threat_levels'][threat_level] += 1
            
            # Count risk distribution
            risk_score = data.get('risk_score', 0)
            if risk_score >= 70:
                stats['risk_distribution']['high_risk'] += 1
                stats['suspicious_ips'].append(ip)
            elif risk_score >= 30:
                stats['risk_distribution']['medium_risk'] += 1
            elif risk_score > 0:
                stats['risk_distribution']['low_risk'] += 1
            else:
                stats['risk_distribution']['no_risk'] += 1
                stats['clean_ips'].append(ip)
            
            # Count source availability
            if data.get('virustotal', {}).get('status') == 'success':
                stats['source_availability']['virustotal'] += 1
            if data.get('abuseipdb', {}).get('status') == 'success':
                stats['source_availability']['abuseipdb'] += 1
        
        return stats
