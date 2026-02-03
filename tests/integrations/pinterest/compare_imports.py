"""
Compare import statements between original Pinterest_agent and current integration.
Identifies differences and tests import resolution.
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.integrations.pinterest.test_logger import TestLogger


def extract_imports(file_path: Path) -> List[Tuple[str, str]]:
    """Extract import statements from a Python file."""
    imports = []
    
    if not file_path.exists():
        return imports
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Match import statements
        # Pattern: from <module> import <items>
        pattern = r'from\s+([\w.]+)\s+import\s+([\w\s,()*]+)'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            module = match.group(1)
            items = match.group(2).strip()
            imports.append((module, items))
        
        # Also match: import <module>
        pattern2 = r'^import\s+([\w.]+)'
        matches2 = re.finditer(pattern2, content, re.MULTILINE)
        
        for match in matches2:
            module = match.group(1)
            imports.append((module, "*"))
            
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return imports


def compare_file_imports(original_path: Path, integration_path: Path, logger: TestLogger) -> Dict:
    """Compare imports between original and integration versions of a file."""
    filename = original_path.name
    logger.log_action(f"comparing_{filename}", f"Comparing imports in {filename}", "info")
    
    original_imports = extract_imports(original_path)
    integration_imports = extract_imports(integration_path)
    
    result = {
        "filename": filename,
        "original_imports": original_imports,
        "integration_imports": integration_imports,
        "differences": []
    }
    
    # Find differences
    original_modules = {imp[0] for imp in original_imports}
    integration_modules = {imp[0] for imp in integration_imports}
    
    # Modules only in original
    only_original = original_modules - integration_modules
    if only_original:
        result["differences"].append({
            "type": "only_in_original",
            "modules": list(only_original)
        })
        logger.log_action(f"only_original_{filename}", f"Modules only in original: {only_original}", "info")
    
    # Modules only in integration
    only_integration = integration_modules - original_modules
    if only_integration:
        result["differences"].append({
            "type": "only_in_integration",
            "modules": list(only_integration)
        })
        logger.log_action(f"only_integration_{filename}", f"Modules only in integration: {only_integration}", "info")
    
    # Check for relative vs absolute imports
    for orig_imp, orig_items in original_imports:
        # Check if original uses absolute import
        if not orig_imp.startswith('.'):
            # Find corresponding import in integration
            for int_imp, int_items in integration_imports:
                # Check if integration uses relative import
                if int_imp.startswith('.') and orig_imp.split('.')[-1] == int_imp.lstrip('.').split('.')[-1]:
                    result["differences"].append({
                        "type": "import_style_change",
                        "original": orig_imp,
                        "integration": int_imp,
                        "change": "absolute -> relative"
                    })
                    logger.log_action(f"import_style_{orig_imp}", 
                                    f"Import style changed: {orig_imp} -> {int_imp}", "info")
    
    return result


def test_import_resolution(module_path: str, logger: TestLogger) -> bool:
    """Test if an import path can be resolved."""
    try:
        exec(f"import {module_path}")
        logger.log_action(f"resolve_{module_path}", f"Successfully resolved: {module_path}", "success")
        return True
    except Exception as e:
        logger.log_action(f"resolve_{module_path}", f"Failed to resolve: {module_path}", "failure")
        logger.log_error(e, f"Import resolution failed for {module_path}")
        return False


def main():
    """Main comparison function."""
    with TestLogger("compare_imports") as logger:
        logger.log_action("test_start", "Starting import comparison", "info")
        
        # Paths
        pinterest_agent_path = project_root.parent / "Pinterest_agent"
        integration_path = project_root / "integrations" / "pinterest"
        
        logger.log_action("check_paths", "Checking project paths", "info")
        logger.log_action("pinterest_agent_path", f"Pinterest_agent path: {pinterest_agent_path}", 
                         "success" if pinterest_agent_path.exists() else "failure")
        logger.log_action("integration_path", f"Integration path: {integration_path}", 
                         "success" if integration_path.exists() else "failure")
        
        if not pinterest_agent_path.exists():
            logger.log_action("pinterest_agent_missing", 
                            "Pinterest_agent project not found. Skipping comparison.", "failure")
            return
        
        # Files to compare
        files_to_compare = [
            "config.py",
            "models.py",
            "content_generator.py",
            "state_manager.py",
            "pinterest_publisher_ocr.py",
            "pinterest_tool.py",
        ]
        
        comparison_results = []
        
        for filename in files_to_compare:
            original_file = pinterest_agent_path / filename
            integration_file = integration_path / filename
            
            if not original_file.exists():
                logger.log_action(f"original_missing_{filename}", 
                                f"Original file not found: {original_file}", "failure")
                continue
            
            if not integration_file.exists():
                logger.log_action(f"integration_missing_{filename}", 
                                f"Integration file not found: {integration_file}", "failure")
                continue
            
            result = compare_file_imports(original_file, integration_file, logger)
            comparison_results.append(result)
        
        # Print summary
        print(f"\n{'='*60}")
        print("Import Comparison Summary")
        print(f"{'='*60}\n")
        
        for result in comparison_results:
            print(f"File: {result['filename']}")
            print(f"  Original imports: {len(result['original_imports'])}")
            print(f"  Integration imports: {len(result['integration_imports'])}")
            
            if result['differences']:
                print(f"  Differences found: {len(result['differences'])}")
                for diff in result['differences']:
                    if diff['type'] == 'import_style_change':
                        print(f"    - {diff['change']}: {diff['original']} -> {diff['integration']}")
                    elif diff['type'] == 'only_in_original':
                        print(f"    - Only in original: {', '.join(diff['modules'])}")
                    elif diff['type'] == 'only_in_integration':
                        print(f"    - Only in integration: {', '.join(diff['modules'])}")
            else:
                print(f"  No differences found")
            print()
        
        # Test import resolution for key modules
        logger.log_action("test_resolution", "Testing import resolution", "info")
        
        test_modules = [
            "integrations.pinterest.config",
            "integrations.pinterest.models",
            "integrations.pinterest.content_generator",
            "integrations.pinterest.state_manager",
            "integrations.pinterest.pinterest_publisher_ocr",
            "integrations.pinterest.pinterest_tool",
        ]
        
        resolution_results = {}
        for module in test_modules:
            resolution_results[module] = test_import_resolution(module, logger)
        
        # Generate recommendations
        logger.log_action("generate_recommendations", "Generating fix recommendations", "info")
        
        print(f"\n{'='*60}")
        print("Recommendations")
        print(f"{'='*60}\n")
        
        failed_resolutions = [mod for mod, success in resolution_results.items() if not success]
        if failed_resolutions:
            print("Failed Import Resolutions:")
            for mod in failed_resolutions:
                print(f"  - {mod}")
            print("\nPossible fixes:")
            print("  1. Ensure all __init__.py files exist in the package structure")
            print("  2. Check that sys.path includes the project root")
            print("  3. Verify relative imports use correct syntax (from .module import ...)")
            print("  4. Check for circular import issues")
        else:
            print("All imports resolved successfully!")
        
        logger.log_action("comparison_complete", "Import comparison completed", "info")


if __name__ == "__main__":
    main()

