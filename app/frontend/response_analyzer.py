import re
from enum import Enum
from typing import Any, Dict, List, Optional


class ResponseType(Enum):
    """Enumeration of possible response types."""
    TEXT = "text"
    TABLE = "table"
    LIST = "list"
    CHART = "chart"

class ResponseAnalyzer:
    """Analyzes text responses to determine the best visualization method."""
    
    # Keywords and patterns for different response types
    TABLE_PATTERNS = [
        r"\|.*\|",  # Markdown table
        r"^\s*[-+]+[-+]+$",  # Table separator
        r"^\s*\|.*\|$",  # Table row
    ]
    
    LIST_PATTERNS = [
        r"^\s*[-*]\s+",  # Bullet points
        r"^\s*\d+\.\s+",  # Numbered lists
    ]
    
    CHART_KEYWORDS = [
        "chart", "graph", "plot", "visualization", "data points",
        "trend", "series", "axis", "values", "distribution"
    ]
    
    @staticmethod
    def analyze_response(text: str) -> ResponseType:
        """Analyze the response text to determine the best visualization method."""
        # Check for table patterns
        for pattern in ResponseAnalyzer.TABLE_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                return ResponseType.TABLE
        
        # Check for list patterns
        for pattern in ResponseAnalyzer.LIST_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                return ResponseType.LIST
        
        # Check for chart keywords
        text_lower = text.lower()
        for keyword in ResponseAnalyzer.CHART_KEYWORDS:
            if keyword in text_lower:
                return ResponseType.CHART
        
        # Default to text if no other patterns match
        return ResponseType.TEXT
    
    @staticmethod
    def format_datetime(dt_str: str) -> str:
        """Format datetime string for display."""
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return dt_str
    
    @staticmethod
    def parse_table(text: str) -> Dict[str, List[str]]:
        """Parse markdown table into a dictionary of columns."""
        lines = text.strip().split('\n')
        if len(lines) < 3:  # Need header, separator, and at least one data row
            return {}
            
        # Parse header
        header = [cell.strip() for cell in lines[0].strip('|').split('|')]
        
        # Skip separator line
        data_rows = lines[2:]
        
        # Parse data rows
        columns = {col: [] for col in header}
        for row in data_rows:
            cells = [cell.strip() for cell in row.strip('|').split('|')]
            if len(cells) == len(header):
                for col, cell in zip(header, cells):
                    columns[col].append(cell)
        
        return columns
    
    @staticmethod
    def parse_list(text: str) -> List[str]:
        """Parse markdown list into a list of items."""
        lines = text.strip().split('\n')
        items = []
        
        for line in lines:
            # Remove bullet points or numbers
            line = re.sub(r'^\s*[-*]\s+', '', line)
            line = re.sub(r'^\s*\d+\.\s+', '', line)
            if line.strip():
                items.append(line.strip())
        
        return items
    
    @staticmethod
    def parse_chart_data(text: str) -> Dict[str, Any]:
        """Extract chart data from text response."""
        # This is a placeholder - actual implementation would depend on
        # the specific chart data format in the response
        return {
            "type": "line",  # Default chart type
            "data": [],  # Would be populated with actual data
            "labels": [],  # Would be populated with actual labels
        } 