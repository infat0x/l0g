from typing import Optional
import os
import requests


class AIClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 30):
        # Default to Mistral chat completions if not provided
        self.base_url = base_url or os.getenv("AI_API_URL") or "https://api.mistral.ai/v1/chat/completions"
        self.api_key = api_key or os.getenv("AI_API_KEY") or ""
        self.timeout = timeout

    def _truncate_logs_for_token_limit(self, logs_text: str, max_chars: int = 8000) -> str:
        """Truncate logs to fit within token limits"""
        if len(logs_text) <= max_chars:
            return logs_text
        
        # Split by lines and keep most recent/relevant entries
        lines = logs_text.split('\n')
        if len(lines) <= 50:  # If less than 50 lines, just truncate
            return logs_text[:max_chars] + "\n... [truncated]"
        
        # Keep first few lines (headers) and last most lines
        header_lines = lines[:5]  # Keep first 5 lines
        remaining_chars = max_chars - len('\n'.join(header_lines)) - 100  # Reserve space for truncation notice
        
        # Take lines from the end until we hit char limit
        truncated_lines = []
        for line in reversed(lines[5:]):
            if len('\n'.join(truncated_lines) + line) > remaining_chars:
                break
            truncated_lines.insert(0, line)
        
        result = '\n'.join(header_lines + truncated_lines)
        if len(result) < len(logs_text):
            result += f"\n... [truncated {len(logs_text) - len(result)} characters]"
        
        return result

    def _filter_relevant_logs(self, logs_text: str, ip: str) -> str:
        """Filter logs to keep only most relevant entries for the IP"""
        lines = logs_text.split('\n')
        relevant_lines = []
        
        # Priority keywords that indicate security-relevant entries
        security_keywords = ['error', 'failed', 'denied', 'blocked', 'attack', 'suspicious', 'malicious', 'unauthorized', 'forbidden', 'intrusion']
        
        for line in lines:
            if ip in line:
                # Always include lines with the IP
                relevant_lines.append(line)
            elif any(keyword in line.lower() for keyword in security_keywords):
                # Include security-relevant lines even if they don't contain the IP
                relevant_lines.append(line)
        
        # If we have too many lines, prioritize by relevance
        if len(relevant_lines) > 100:
            # Keep lines with IP first, then security keywords
            ip_lines = [line for line in relevant_lines if ip in line]
            security_lines = [line for line in relevant_lines if ip not in line]
            relevant_lines = ip_lines + security_lines[:50]  # Keep max 50 security lines
        
        return '\n'.join(relevant_lines)

    def summarize_ip_logs(self, ip: str, logs_text: str) -> str:
        if not self.base_url:
            return "AI_API_URL is not configured. Set it in Settings or environment."
        try:
            # Filter and truncate logs to avoid token limit issues
            filtered_logs = self._filter_relevant_logs(logs_text, ip)
            truncated_logs = self._truncate_logs_for_token_limit(filtered_logs, max_chars=6000)
            
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Detect Mistral endpoint shape; otherwise use generic payload
            if "mistral.ai" in self.base_url:
                payload = {
                    "model": os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
                    "temperature": 0.2,
                    "max_tokens": 800,  # Increased slightly for better analysis
                    "messages": [
                        {"role": "system", "content": "You are a cybersecurity analyst. Analyze web server logs and provide concise security insights. Focus on threats, anomalies, and actionable recommendations."},
                        {"role": "user", "content": f"Analyze filtered logs for IP address {ip}. Provide:\n1. Key security findings (bullet points)\n2. Risk level assessment (Low/Medium/High)\n3. Recommended actions\n\nLogs:\n{truncated_logs}"}
                    ]
                }
            else:
                payload = {"ip": ip, "logs": truncated_logs}
            
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code >= 200 and resp.status_code < 300:
                try:
                    data = resp.json()
                    # Mistral format: choices[0].message.content
                    if isinstance(data, dict) and "choices" in data and data.get("choices"):
                        choice = data["choices"][0]
                        msg = choice.get("message", {})
                        text = msg.get("content")
                    else:
                        text = data.get("text") or data.get("result") or data.get("message")
                    return text or resp.text
                except Exception:
                    return resp.text
            return f"AI error {resp.status_code}: {resp.text[:500]}"
        except Exception as e:
            return f"AI request failed: {str(e)}"
    
    def generate_comprehensive_report(self, log_stats: dict, enriched_data: dict, cti_stats: dict, 
                                    statistics_data: dict, map_data: dict, ai_output: str) -> str:
        """Generate comprehensive report using AI with all tab data"""
        if not self.base_url or not self.api_key:
            return "AI_API_URL or AI_API_KEY is not configured. Set them in Settings."
        
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Prepare comprehensive data for AI
            report_data = {
                "log_statistics": log_stats,
                "ip_analysis": enriched_data,
                "threat_intelligence": cti_stats,
                "statistics_summary": statistics_data.get('ai_summary', ''),
                "map_analysis": map_data,
                "ai_insights": ai_output
            }
            
            # Create detailed prompt for comprehensive report generation
            prompt = f"""
You are a senior cybersecurity analyst creating a comprehensive CTI (Cyber Threat Intelligence) report. 
Generate a professional, detailed report that includes:

1. Executive Summary with key findings
2. Threat Intelligence Analysis with charts/graphs descriptions
3. Geographic Analysis based on map data
4. Statistics Analysis with visualizations
5. AI-Generated Insights and Recommendations
6. Risk Assessment and Mitigation Strategies

Data provided:
- Log Statistics: {log_stats}
- IP Analysis Results: {enriched_data}
- Threat Intelligence: {cti_stats}
- Statistics Summary: {statistics_data.get('ai_summary', 'No statistics available')}
- Map Data: {map_data}
- AI Insights: {ai_output}

Please format the report with:
- Clear section headers (use ## for main sections, ### for subsections)
- Bullet points for key findings
- Tables for data presentation
- Bold text for important metrics
- Professional language suitable for security teams

Include specific recommendations based on the threat levels and geographic distribution of IPs.
"""
            
            if "mistral.ai" in self.base_url:
                payload = {
                    "model": os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
                    "temperature": 0.1,
                    "max_tokens": 2000,
                    "messages": [
                        {"role": "system", "content": "You are a senior cybersecurity analyst creating comprehensive CTI reports. Generate professional, detailed reports with clear sections, bullet points, tables, and actionable recommendations."},
                        {"role": "user", "content": prompt}
                    ]
                }
            else:
                payload = {"report_data": report_data, "prompt": prompt}
            
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code >= 200 and resp.status_code < 300:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and "choices" in data and data.get("choices"):
                        choice = data["choices"][0]
                        msg = choice.get("message", {})
                        text = msg.get("content")
                    else:
                        text = data.get("text") or data.get("result") or data.get("message")
                    return text or resp.text
                except Exception:
                    return resp.text
            return f"AI error {resp.status_code}: {resp.text[:500]}"
        except Exception as e:
            return f"Failed to generate comprehensive report: {str(e)}"


