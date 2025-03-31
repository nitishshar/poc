#!/usr/bin/env python
"""
Helper script to fix the ChatService class in the backend by adding the missing get_sessions method.
This addresses the 'AttributeError: 'ChatService' object has no attribute 'get_sessions'' error.

Instructions:
1. Run this script from the project root directory
2. It will add the missing get_sessions method to the ChatService class
3. Restart your backend server to apply the changes
"""

import os
import re
import sys
from pathlib import Path


def find_chat_service_file():
    """Find the file containing the ChatService class."""
    base_dir = Path('.')
    
    # Likely locations
    possible_paths = [
        'app/services',
        'app/core/services',
        'app/chat',
        'app',
    ]
    
    for path in possible_paths:
        service_dir = base_dir / path
        if not service_dir.exists():
            continue
            
        # Look for files that might contain the ChatService class
        for file in service_dir.glob('**/*.py'):
            with open(file, 'r') as f:
                content = f.read()
                # Check if this file contains a ChatService class definition
                if re.search(r'class\s+ChatService', content):
                    return file
    
    return None

def add_get_sessions_method(file_path):
    """Add the missing get_sessions method to the ChatService class."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if the method already exists
    if re.search(r'def\s+get_sessions\s*\(', content):
        print("The get_sessions method already exists in the ChatService class.")
        return False
    
    # Find the ChatService class
    match = re.search(r'class\s+ChatService.*?:', content)
    if not match:
        print("Could not find ChatService class definition.")
        return False
    
    # Find where to insert the method - after the last method in the class
    # Look for class methods
    methods = re.finditer(r'(\s+)def\s+\w+\s*\(self', content)
    last_method = None
    for method in methods:
        last_method = method
    
    if not last_method:
        print("Could not determine where to insert the method.")
        return False
    
    # Get the indentation from the last method
    indentation = last_method.group(1)
    
    # Create the new method with proper indentation
    new_method = f"\n{indentation}def get_sessions(self):\n"
    new_method += f"{indentation}    \"\"\"Get all chat sessions.\"\"\"\n"
    new_method += f"{indentation}    try:\n"
    new_method += f"{indentation}        # Get all sessions from the session store\n"
    new_method += f"{indentation}        return self.session_store.get_all_sessions()\n"
    new_method += f"{indentation}    except Exception as e:\n"
    new_method += f"{indentation}        # Log the error\n"
    new_method += f"{indentation}        print(f\"Error getting sessions: {{str(e)}}\")\n"
    new_method += f"{indentation}        # Return an empty list on error\n"
    new_method += f"{indentation}        return []\n"
    
    # Find the position to insert the new method
    # We'll insert after the last method in the class
    last_method_end = last_method.end()
    
    # Find the end of the last method's block
    method_block_end = last_method_end
    lines = content.split('\n')
    method_start_line = content[:last_method_end].count('\n')
    
    for i, line in enumerate(lines[method_start_line:], method_start_line):
        if line.strip() and not line.startswith(indentation):
            method_block_end = sum(len(l) + 1 for l in lines[:i])
            break
    
    # Insert the new method
    new_content = content[:method_block_end] + new_method + content[method_block_end:]
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    return True

def main():
    print("Looking for ChatService class...")
    file_path = find_chat_service_file()
    
    if not file_path:
        print("Could not find the file containing the ChatService class.")
        print("Please add the get_sessions method manually.")
        return 1
    
    print(f"Found ChatService in: {file_path}")
    
    if add_get_sessions_method(file_path):
        print("Successfully added get_sessions method to ChatService class!")
        print("Please restart your backend server to apply the changes.")
        return 0
    else:
        print("Failed to add get_sessions method.")
        print("You may need to add it manually.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 