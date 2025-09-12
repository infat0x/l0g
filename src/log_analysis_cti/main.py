#!/usr/bin/env python3
import sys
import os
from colorama import init, Fore, Style
from .file_validator import FileValidator
from .log_parser import LogParser
from .cti_apis.cti_manager import CTIManager
from .report_generator import ReportGenerator
from .behavior_analyzer import BehaviorAnalyzer

init(autoreset=True)

def main():
    if len(sys.argv) != 2:
        FileValidator.print_usage()
        sys.exit(1)
    
    log_file_path = sys.argv[1]
    
    print(f"{Fore.GREEN}Log Analysis & CTI Tool{Style.RESET_ALL}")
    print("=" * 50)
    print(f"Analyzing log file: {log_file_path}")
    print()
    
    try:
        print(f"{Fore.CYAN}Step 1: Validating log file...{Style.RESET_ALL}")
        is_valid, error_msg, file_content = FileValidator.validate_file_path(log_file_path)
        
        if not is_valid:
            print(f"{Fore.RED}Error: {error_msg}{Style.RESET_ALL}")
            sys.exit(1)
        
        print(f"{Fore.GREEN}✓ File validation successful{Style.RESET_ALL}")
        print()
        
        print(f"{Fore.CYAN}Step 2: Parsing log file...{Style.RESET_ALL}")
        parser = LogParser()
        if os.path.getsize(log_file_path) > 5 * 1024 * 1024:
            parsed_data = parser.parse_log_file(log_file_path)
        else:
            parsed_data = parser.parse_log(file_content)
        
        if not parsed_data['ips']:
            print(f"{Fore.YELLOW}Warning: No IP addresses found in log file{Style.RESET_ALL}")
            sys.exit(0)
        
        print(f"{Fore.GREEN}✓ Found {len(parsed_data['ips'])} unique IP addresses{Style.RESET_ALL}")
        print()
        
        print(f"{Fore.CYAN}Step 3: Filtering and categorizing IP addresses...{Style.RESET_ALL}")
        filtered_ips = parser.filter_and_sort_ips(parsed_data['ips'])
        
        print(f"  • Total unique IPs: {filtered_ips['total_count']}")
        print(f"  • Public IPs: {filtered_ips['public_count']}")
        print(f"  • Private IPs: {filtered_ips['private_count']}")
        print()
        
        print(f"{Fore.CYAN}Step 4: Analyzing behavior heuristics...{Style.RESET_ALL}")
        behavior = BehaviorAnalyzer()
        behavior_results = behavior.analyze(parsed_data['log_entries'])
        print(f"{Fore.GREEN}✓ Behavior analysis completed{Style.RESET_ALL}")
        print()

        if filtered_ips['public_ips']:
            print(f"{Fore.CYAN}Step 5: Enriching IPs with CTI data...{Style.RESET_ALL}")
            cti_manager = CTIManager()
            enriched_data = cti_manager.enrich_ips(filtered_ips['public_ips'], behavior_results)
            
            cti_stats = cti_manager.get_summary_statistics(enriched_data)
            print(f"{Fore.GREEN}✓ CTI enrichment completed{Style.RESET_ALL}")
            print()
        else:
            print(f"{Fore.YELLOW}No public IPs found for CTI analysis{Style.RESET_ALL}")
            enriched_data = {ip: {
                'ip': ip,
                'virustotal': {},
                'abuseipdb': {},
                'behavior': behavior_results.get(ip, {}),
                'overall_threat_level': behavior_results.get(ip, {}).get('threat_level', 'unknown'),
                'risk_score': behavior_results.get(ip, {}).get('risk_score', 0)
            } for ip in parsed_data['ips']}
            cti_stats = {
                'total_ips': len(enriched_data),
                'threat_levels': {'high': 0, 'medium': 0, 'low': 0, 'clean': 0, 'unknown': 0},
                'risk_distribution': {'high_risk': 0, 'medium_risk': 0, 'low_risk': 0, 'no_risk': 0},
                'source_availability': {'virustotal': 0, 'abuseipdb': 0},
                'suspicious_ips': [],
                'clean_ips': []
            }
        
        print(f"{Fore.CYAN}Step 6: Generating statistics...{Style.RESET_ALL}")
        log_stats = parser.get_statistics(parsed_data['log_entries'])
        log_stats.update(filtered_ips)
        
        print(f"{Fore.GREEN}✓ Statistics generated{Style.RESET_ALL}")
        print()
        
        print(f"{Fore.CYAN}Step 7: Generating reports...{Style.RESET_ALL}")
        report_generator = ReportGenerator(output_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'out', 'reports'))
        
        text_report_path = report_generator.generate_comprehensive_report(
            log_stats, enriched_data, cti_stats
        )
        
        json_report_path = report_generator.generate_json_report(
            log_stats, enriched_data, cti_stats
        )
        
        print(f"{Fore.GREEN}✓ Reports generated successfully{Style.RESET_ALL}")
        print()
        
        print(f"{Fore.CYAN}Step 8: Analysis Summary{Style.RESET_ALL}")
        print("-" * 30)
        
        if enriched_data:
            report_generator.print_summary_table(cti_stats)
        
        print(f"\n{Fore.CYAN}Generated Reports:{Style.RESET_ALL}")
        print(f"  • Text Report: {text_report_path}")
        print(f"  • JSON Report: {json_report_path}")
        
        print(f"\n{Fore.CYAN}Recommendations:{Style.RESET_ALL}")
        high_risk = cti_stats['threat_levels']['high']
        medium_risk = cti_stats['threat_levels']['medium']
        
        if high_risk > 0:
            print(f"  • {Fore.RED}{high_risk} HIGH RISK IPs detected - immediate action recommended{Style.RESET_ALL}")
        if medium_risk > 0:
            print(f"  • {Fore.YELLOW}{medium_risk} MEDIUM RISK IPs detected - monitoring recommended{Style.RESET_ALL}")
        if high_risk == 0 and medium_risk == 0:
            print(f"  • {Fore.GREEN}No high or medium risk IPs detected{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}Analysis completed successfully!{Style.RESET_ALL}")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Analysis interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()
