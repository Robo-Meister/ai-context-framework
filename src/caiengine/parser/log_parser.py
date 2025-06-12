import re
from datetime import datetime
from typing import Dict, Any, List, Optional

LOG_LEVELS = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']

ROLE_KEYWORDS = {
    'admin': ['admin', 'administrator', 'root'],
    'user': ['user', 'client', 'customer'],
    'service': ['service', 'daemon', 'agent']
}

SITUATION_KEYWORDS = {
    'network': ['timeout', 'connection', 'disconnect', 'network'],
    'database': ['db', 'database', 'sql', 'query'],
    'security': ['auth', 'login', 'password', 'security', 'token'],
    'performance': ['slow', 'lag', 'high load', 'cpu', 'memory']
}

class LogParser:
    def parse_timestamp(self, log_line: str) -> Optional[datetime]:
        match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', log_line)
        if match:
            return datetime.strptime(match.group(0), '%Y-%m-%dT%H:%M:%S')
        return None

    def detect_roles(self, log_line: str) -> List[str]:
        lower_line = log_line.lower()
        return [
            role for role, keywords in ROLE_KEYWORDS.items()
            if any(kw in lower_line for kw in keywords)
        ] or ['unknown']

    def detect_situations(self, log_line: str) -> List[str]:
        results = set()
        upper_line = log_line.upper()
        for level in LOG_LEVELS:
            if level in upper_line:
                results.add(level)
        lower_line = log_line.lower()
        for situation, keywords in SITUATION_KEYWORDS.items():
            if any(kw in lower_line for kw in keywords):
                results.add(situation)
        return list(results) or ['general']

    def compute_score(self, context: Dict[str, Any]) -> float:
        # Higher score for errors or critical logs
        situations = context.get('situations', [])
        if 'CRITICAL' in situations or 'ERROR' in situations:
            return 0.9
        elif 'WARN' in situations:
            return 0.7
        else:
            return 0.5

    def transform(self, log_line: str) -> Dict[str, Any]:
        context = {
            "timestamp": self.parse_timestamp(log_line),
            "roles": self.detect_roles(log_line),
            "situations": self.detect_situations(log_line),
            "content": log_line
        }
        context['score'] = self.compute_score(context)
        return context

    def transform_batch(self, log_lines: List[str]) -> List[Dict[str, Any]]:
        current_entry = []
        results = []

        for line in log_lines:
            if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line):
                # Start of a new log entry
                if current_entry:
                    results.append(self.transform("\n".join(current_entry)))
                    current_entry = []
            current_entry.append(line)

        if current_entry:
            results.append(self.transform("\n".join(current_entry)))

        return results
