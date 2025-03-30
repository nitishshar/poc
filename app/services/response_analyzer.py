import re
import json
import pandas as pd
from enum import Enum, auto
import numpy as np
from typing import Dict, List, Any, Union, Optional


class ResponseType(Enum):
    """Enumeration of possible response types for visualization."""
    TEXT = auto()         # Plain text responses
    TABLE = auto()        # Table-like content
    CHART = auto()        # Chart/graph content
    IMAGE = auto()        # Image content/references
    FILE = auto()         # File download references
    LIST = auto()         # List-formatted content
    ERROR = auto()        # Error messages
    METADATA = auto()     # Document metadata
    MULTI = auto()        # Multiple content types combined


class ResponseAnalyzer:
    """
    Analyze text responses to determine the best visualization method.
    
    This class examines response text and user queries to decide how to
    best represent the information visually in the UI.
    """
    
    def __init__(self):
        # Chart-related keywords that might suggest data suitable for charts
        self.chart_keywords = [
            "graph", "chart", "plot", "trend", "distribution", "histogram", 
            "bar chart", "pie chart", "line graph", "scatter plot", "time series",
            "comparison", "percentage", "statistics", "visualization", "diagram",
            "proportion", "frequency", "count"
        ]
        
        # Keywords that might indicate table data
        self.table_keywords = [
            "table", "grid", "row", "column", "cell", "header", "value",
            "tabular", "matrix", "csv", "spreadsheet", "data frame", "dataset",
            "data set", "entries", "records", "fields"
        ]
        
        # Keyboard patterns for matching Markdown tables
        self.markdown_table_pattern = r"\|[^|]+\|[^|]+\|"
        self.markdown_table_separator = r"\|[\s*:?\-+]+\|"
        
        # Pattern for CSV-like content
        self.csv_pattern = r"^([^,\n]+,){2,}[^,\n]+(\n([^,\n]+,){2,}[^,\n]+){1,}"
        
        # Pattern for list items
        self.list_pattern = r"(\n\s*[-*•]\s+[^\n]+){3,}"
        self.numbered_list_pattern = r"(\n\s*\d+\.\s+[^\n]+){3,}"

    def analyze(self, query: str, response: str) -> Dict[str, Any]:
        """
        Analyze the response text and determine the best visualization.
        
        Args:
            query: The user's query that generated this response
            response: The text response to analyze
            
        Returns:
            Dictionary with analysis results containing:
                - response_type: The determined ResponseType enum
                - visualization_type: Specific visualization type (e.g., "bar", "line")
                - visualization_data: Data extracted for visualization
                - confidence: Confidence score of the determination
        """
        result = {
            "response_type": ResponseType.TEXT,  # Default to TEXT
            "visualization_type": None,
            "visualization_data": None,
            "confidence": 0.0
        }
        
        # Skip analysis for very short responses
        if len(response) < 20:
            result["confidence"] = 1.0
            return result
        
        # Check for error messages first
        if self._is_error_message(response):
            result["response_type"] = ResponseType.ERROR
            result["confidence"] = 0.9
            return result
            
        # Check for table content
        table_score, table_data = self._analyze_table_content(query, response)
        
        # Check for chart content
        chart_score, chart_type, chart_data = self._analyze_chart_content(query, response)
        
        # Check for list content
        list_score, list_data = self._analyze_list_content(response)
        
        # Determine the highest scoring content type
        max_score = max(table_score, chart_score, list_score)
        
        # Default confidence threshold
        threshold = 0.6
        
        if max_score < threshold:
            # If no strong signal, default to text
            result["response_type"] = ResponseType.TEXT
            result["confidence"] = 1.0 - max_score  # Confidence in it being plain text
        elif table_score == max_score:
            result["response_type"] = ResponseType.TABLE
            result["visualization_data"] = table_data
            result["confidence"] = table_score
        elif chart_score == max_score:
            result["response_type"] = ResponseType.CHART
            result["visualization_type"] = chart_type
            result["visualization_data"] = chart_data
            result["confidence"] = chart_score
        elif list_score == max_score:
            result["response_type"] = ResponseType.LIST
            result["visualization_data"] = list_data
            result["confidence"] = list_score
        
        return result
    
    def _is_error_message(self, text: str) -> bool:
        """Check if the text appears to be an error message."""
        error_indicators = [
            "error", "exception", "failed", "failure", "invalid", 
            "not found", "cannot", "unable to", "couldn't", "can't"
        ]
        
        lower_text = text.lower()
        
        # Check if the text starts with error indicators
        if any(lower_text.startswith(indicator) for indicator in error_indicators):
            return True
            
        # Check if the text has error expressions with some emphasis
        error_patterns = [
            r"error[:\-]", r"exception[:\-]", r"failed to", r"not found", 
            r"cannot \w+", r"unable to \w+"
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, lower_text):
                return True
                
        return False
    
    def _analyze_table_content(self, query: str, text: str) -> tuple:
        """
        Analyze if the text contains table-like content.
        
        Returns:
            tuple: (confidence_score, extracted_table_data)
        """
        score = 0.0
        table_data = None
        
        # Check if query is asking for tabular data
        lower_query = query.lower()
        if any(keyword in lower_query for keyword in self.table_keywords):
            score += 0.3
        
        # Check for markdown tables
        if re.search(self.markdown_table_pattern, text) and re.search(self.markdown_table_separator, text):
            score += 0.5
            table_data = self._extract_markdown_table(text)
            
            # Increase score if extraction was successful
            if table_data and len(table_data.get("data", [])) > 1:
                score += 0.3
            
        # Check for CSV-like content
        elif re.search(self.csv_pattern, text, re.MULTILINE):
            score += 0.4
            table_data = self._extract_csv_data(text)
            
            # Increase score if extraction was successful
            if table_data and len(table_data.get("data", [])) > 1:
                score += 0.3
                
        # Check for raw data that looks like a table
        elif self._contains_tabular_structure(text):
            score += 0.3
            table_data = self._extract_tabular_data(text)
            
            # Increase score if extraction was successful
            if table_data and len(table_data.get("data", [])) > 1:
                score += 0.2
        
        # Cap score at 1.0
        return min(score, 1.0), table_data
    
    def _analyze_chart_content(self, query: str, text: str) -> tuple:
        """
        Analyze if the text contains chart-worthy content.
        
        Returns:
            tuple: (confidence_score, chart_type, extracted_chart_data)
        """
        score = 0.0
        chart_type = "bar"  # Default chart type
        chart_data = None
        
        # Check if query is asking for chart data
        lower_query = query.lower()
        if any(keyword in lower_query for keyword in self.chart_keywords):
            score += 0.3
            
            # Determine chart type from query
            if "pie" in lower_query or "proportion" in lower_query or "percentage" in lower_query:
                chart_type = "pie"
            elif "line" in lower_query or "trend" in lower_query or "time series" in lower_query:
                chart_type = "line"
            elif "bar" in lower_query or "column" in lower_query or "histogram" in lower_query:
                chart_type = "bar"
        
        # Check for number pairs that could be chart data
        if self._contains_data_pairs(text):
            score += 0.4
            chart_data = self._extract_data_pairs(text)
            
            # Increase score if extraction was successful
            if chart_data and len(chart_data.get("labels", [])) > 1:
                score += 0.2
                
                # Refine chart type based on data patterns
                if self._looks_like_time_series(chart_data.get("labels", [])):
                    chart_type = "line"
                elif len(chart_data.get("labels", [])) <= 8 and all(isinstance(v, (int, float)) and v >= 0 for v in chart_data.get("values", [])):
                    chart_type = "pie"
        
        # Cap score at 1.0
        return min(score, 1.0), chart_type, chart_data
    
    def _analyze_list_content(self, text: str) -> tuple:
        """
        Analyze if the text contains list-like content.
        
        Returns:
            tuple: (confidence_score, extracted_list_items)
        """
        score = 0.0
        list_data = None
        
        # Check for bullet point lists
        if re.search(self.list_pattern, text):
            score += 0.6
            list_data = self._extract_list_items(text)
            
            # Increase score if extraction was successful
            if list_data and len(list_data) > 2:
                score += 0.3
                
        # Check for numbered lists
        elif re.search(self.numbered_list_pattern, text):
            score += 0.6
            list_data = self._extract_numbered_list(text)
            
            # Increase score if extraction was successful
            if list_data and len(list_data) > 2:
                score += 0.3
        
        # Cap score at 1.0
        return min(score, 1.0), list_data
    
    def _extract_markdown_table(self, text: str) -> Dict[str, Any]:
        """Extract data from a markdown table format."""
        try:
            lines = text.strip().split('\n')
            table_lines = []
            in_table = False
            
            # Find table lines
            for line in lines:
                line = line.strip()
                if line.startswith('|') and line.endswith('|'):
                    table_lines.append(line)
                    in_table = True
                elif in_table and not (line.startswith('|') and line.endswith('|')):
                    in_table = False
            
            if len(table_lines) < 3:  # Need header, separator, and at least one row
                return None
                
            # Extract headers
            headers = [cell.strip() for cell in table_lines[0].split('|')[1:-1]]
            
            # Skip the separator row
            data_rows = []
            for i in range(2, len(table_lines)):
                cells = [cell.strip() for cell in table_lines[i].split('|')[1:-1]]
                data_rows.append(cells)
            
            return {
                "headers": headers,
                "data": data_rows
            }
        except Exception:
            return None
    
    def _extract_csv_data(self, text: str) -> Dict[str, Any]:
        """Extract data from CSV-like text."""
        try:
            # Find the CSV-like section
            csv_match = re.search(self.csv_pattern, text, re.MULTILINE)
            if not csv_match:
                return None
                
            csv_text = csv_match.group(0)
            lines = csv_text.strip().split('\n')
            
            if not lines:
                return None
                
            # Check if the first line is a header
            headers = [h.strip() for h in lines[0].split(',')]
            data_rows = []
            
            for i in range(1, len(lines)):
                cells = [cell.strip() for cell in lines[i].split(',')]
                if len(cells) == len(headers):  # Only include rows with correct number of cells
                    data_rows.append(cells)
            
            return {
                "headers": headers,
                "data": data_rows
            }
        except Exception:
            return None
    
    def _extract_tabular_data(self, text: str) -> Dict[str, Any]:
        """Extract data that appears to be in a tabular structure but not in markdown or CSV format."""
        try:
            # Look for spaces or tabs as separators
            lines = text.strip().split('\n')
            potential_tables = []
            
            # Find consecutive lines with similar structure
            current_table = []
            for line in lines:
                line = line.strip()
                if not line:
                    if current_table:
                        potential_tables.append(current_table)
                        current_table = []
                    continue
                
                # Check if line has multiple whitespace-separated tokens
                tokens = re.split(r'\s{2,}', line)
                if len(tokens) >= 3:  # At least 3 columns to be considered tabular
                    current_table.append(tokens)
            
            if current_table:
                potential_tables.append(current_table)
            
            # Find the largest potential table
            best_table = max(potential_tables, key=len) if potential_tables else None
            
            if not best_table or len(best_table) < 2:  # Need at least a header and one row
                return None
                
            # First row as headers
            headers = best_table[0]
            data_rows = best_table[1:]
            
            return {
                "headers": headers,
                "data": data_rows
            }
        except Exception:
            return None
    
    def _contains_tabular_structure(self, text: str) -> bool:
        """Check if text contains a structure that looks like a table."""
        lines = text.strip().split('\n')
        aligned_columns = 0
        
        for i in range(len(lines) - 1):
            # Check for aligned whitespace in consecutive lines
            line1 = lines[i]
            line2 = lines[i + 1]
            
            # Find positions of multiple consecutive whitespaces
            spaces1 = [m.start() for m in re.finditer(r'\s{2,}', line1)]
            spaces2 = [m.start() for m in re.finditer(r'\s{2,}', line2)]
            
            # Count matching positions (with some tolerance)
            matches = sum(1 for s1 in spaces1 for s2 in spaces2 if abs(s1 - s2) <= 2)
            
            if matches >= 2:  # At least 2 aligned whitespace regions
                aligned_columns += 1
        
        # Consider it tabular if we have at least 3 consecutive lines with aligned columns
        return aligned_columns >= 2
    
    def _contains_data_pairs(self, text: str) -> bool:
        """Check if text contains name-value pairs that could be chart data."""
        # Look for patterns like "Label: value" or "Label - value"
        pair_pattern = r"([A-Za-z0-9 ]+)\s*[:|-]\s*(\d+\.?\d*)"
        matches = re.findall(pair_pattern, text)
        
        return len(matches) >= 3  # At least 3 data points for a chart
    
    def _extract_data_pairs(self, text: str) -> Dict[str, list]:
        """Extract label-value pairs that could be used for charts."""
        # Look for patterns like "Label: value" or "Label - value"
        pair_pattern = r"([A-Za-z0-9 ]+)\s*[:|-]\s*(\d+\.?\d*)"
        matches = re.findall(pair_pattern, text)
        
        if not matches:
            return None
            
        labels = []
        values = []
        
        for label, value in matches:
            labels.append(label.strip())
            try:
                values.append(float(value.strip()))
            except ValueError:
                values.append(0)  # Fallback value if conversion fails
        
        return {
            "labels": labels,
            "values": values
        }
    
    def _looks_like_time_series(self, labels: list) -> bool:
        """Check if the labels appear to be time-based (dates, months, years)."""
        # Check for year patterns
        year_pattern = r"^(19|20)\d{2}$"
        year_matches = [bool(re.match(year_pattern, str(label))) for label in labels]
        
        # Check for month names or abbreviations
        month_names = ["jan", "feb", "mar", "apr", "may", "jun", 
                      "jul", "aug", "sep", "oct", "nov", "dec"]
        month_matches = [str(label).lower().startswith(tuple(month_names)) for label in labels]
        
        # Check for date patterns
        date_pattern = r"\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?"
        date_matches = [bool(re.match(date_pattern, str(label))) for label in labels]
        
        # Check for sequential numbers
        try:
            nums = [float(label) for label in labels]
            sequential = all(nums[i] <= nums[i+1] for i in range(len(nums)-1))
        except (ValueError, TypeError):
            sequential = False
        
        # Consider it a time series if any of these patterns is predominant
        return (sum(year_matches) > len(labels) * 0.7 or
                sum(month_matches) > len(labels) * 0.7 or
                sum(date_matches) > len(labels) * 0.7 or
                sequential)
    
    def _extract_list_items(self, text: str) -> List[str]:
        """Extract bullet point list items from text."""
        # Find bullet point lines
        bullet_pattern = r"^\s*[-*•]\s+(.+)$"
        matches = re.findall(bullet_pattern, text, re.MULTILINE)
        
        return [item.strip() for item in matches] if matches else None
    
    def _extract_numbered_list(self, text: str) -> List[str]:
        """Extract numbered list items from text."""
        # Find numbered list lines
        number_pattern = r"^\s*\d+\.\s+(.+)$"
        matches = re.findall(number_pattern, text, re.MULTILINE)
        
        return [item.strip() for item in matches] if matches else None 