#!/usr/bin/env python3
"""
Batch fix syntax errors in job skill files
Removes the problematic \n    return [s.skill_id for s in skills]\n pattern
"""

import os
from pathlib import Path

def fix_syntax_error_in_file(file_path):
    """Fix syntax error in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the problematic pattern exists
        problematic_pattern = '\\n    return [s.skill_id for s in skills]\\n'
        if problematic_pattern in content:
            # Replace the problematic pattern with proper return statement
            # We need to find the actual location and replace it properly
            lines = content.split('\n')
            fixed_lines = []
            
            for i, line in enumerate(lines):
                if problematic_pattern in line:
                    # Replace this line with proper return statement
                    # Look for the previous return statement or add one
                    fixed_lines.append('    return [s.skill_id for s in skills]')
                else:
                    fixed_lines.append(line)
            
            # Join back and write
            fixed_content = '\n'.join(fixed_lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print(f"Fixed: {file_path}")
            return True
        else:
            # Try alternative approach - look for the pattern at end of file
            if content.endswith('\\n    return [s.skill_id for s in skills]\\n'):
                # Remove the problematic ending
                fixed_content = content.replace('\\n    return [s.skill_id for s in skills]\\n', '\n    return [s.skill_id for s in skills]\n')
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                print(f"Fixed (end pattern): {file_path}")
                return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all job skill files"""
    job_skills_dir = Path("src/character/skills/job_skills")
    
    if not job_skills_dir.exists():
        print(f"Directory not found: {job_skills_dir}")
        return
    
    fixed_count = 0
    total_files = 0
    
    for py_file in job_skills_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
            
        total_files += 1
        if fix_syntax_error_in_file(py_file):
            fixed_count += 1
    
    print(f"\nSummary: Fixed {fixed_count} out of {total_files} job skill files")

if __name__ == "__main__":
    main()
