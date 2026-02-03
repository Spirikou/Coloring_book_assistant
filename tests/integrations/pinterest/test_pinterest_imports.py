"""
Test script to identify import issues in Pinterest integration.
Tests each import in the chain with both relative and absolute imports.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.integrations.pinterest.test_logger import TestLogger


def test_relative_import(logger: TestLogger, module_name: str, import_statement: str):
    """Test a relative import."""
    try:
        # Try to import using exec to test the import statement
        namespace = {}
        exec(f"from {import_statement} import *", namespace)
        logger.log_import_attempt(module_name, f"relative ({import_statement})", True)
        return True, None
    except Exception as e:
        logger.log_import_attempt(module_name, f"relative ({import_statement})", False, e)
        return False, e


def test_absolute_import(logger: TestLogger, module_name: str, import_statement: str):
    """Test an absolute import."""
    try:
        namespace = {}
        exec(f"from {import_statement} import *", namespace)
        logger.log_import_attempt(module_name, f"absolute ({import_statement})", True)
        return True, None
    except Exception as e:
        logger.log_import_attempt(module_name, f"absolute ({import_statement})", False, e)
        return False, e


def test_specific_imports(logger: TestLogger):
    """Test specific imports that are used in the codebase."""
    logger.log_action("testing_specific_imports", "Testing specific imports used in codebase", "info")
    
    # Test config imports
    config_imports = [
        ("BROWSER_TYPE", "integrations.pinterest.config"),
        ("DEBUG_PORT", "integrations.pinterest.config"),
        ("SUPPORTED_EXTENSIONS", "integrations.pinterest.config"),
        ("OPENAI_MODEL", "integrations.pinterest.config"),
    ]
    
    for import_name, module_path in config_imports:
        try:
            exec(f"from {module_path} import {import_name}")
            logger.log_action(f"import_{import_name}", f"Successfully imported {import_name} from {module_path}", "success")
        except Exception as e:
            logger.log_error(e, f"Failed to import {import_name} from {module_path}")
    
    # Test model imports
    model_imports = [
        ("BookConfig", "integrations.pinterest.models"),
        ("PinContent", "integrations.pinterest.models"),
        ("ImageInfo", "integrations.pinterest.models"),
    ]
    
    for import_name, module_path in model_imports:
        try:
            exec(f"from {module_path} import {import_name}")
            logger.log_action(f"import_{import_name}", f"Successfully imported {import_name} from {module_path}", "success")
        except Exception as e:
            logger.log_error(e, f"Failed to import {import_name} from {module_path}")


def main():
    """Main test function."""
    with TestLogger("pinterest_imports") as logger:
        logger.log_action("test_start", "Starting Pinterest import tests", "info")
        
        # Test modules in order of dependency
        modules_to_test = [
            ("config", ".config", "integrations.pinterest.config"),
            ("models", ".models", "integrations.pinterest.models"),
            ("content_generator", ".content_generator", "integrations.pinterest.content_generator"),
            ("state_manager", ".state_manager", "integrations.pinterest.state_manager"),
            ("browser_utils", ".browser_utils", "integrations.pinterest.browser_utils"),
            ("pinterest_publisher_ocr", ".pinterest_publisher_ocr", "integrations.pinterest.pinterest_publisher_ocr"),
            ("pinterest_tool", ".pinterest_tool", "integrations.pinterest.pinterest_tool"),
            ("adapter", ".adapter", "integrations.pinterest.adapter"),
        ]
        
        results = {}
        
        for module_name, relative_path, absolute_path in modules_to_test:
            logger.log_action(f"testing_{module_name}", f"Testing imports for {module_name}", "info")
            
            # Test relative import
            rel_success, rel_error = test_relative_import(logger, module_name, relative_path)
            
            # Test absolute import
            abs_success, abs_error = test_absolute_import(logger, module_name, absolute_path)
            
            results[module_name] = {
                "relative": rel_success,
                "absolute": abs_success,
                "relative_error": str(rel_error) if rel_error else None,
                "absolute_error": str(abs_error) if abs_error else None
            }
        
        # Test specific imports
        test_specific_imports(logger)
        
        # Test importing from within the package
        logger.log_action("testing_package_imports", "Testing imports from within package context", "info")
        try:
            # Simulate being inside the package
            import integrations.pinterest.config as config_module
            logger.log_action("package_import_config", "Successfully imported config as module", "success")
        except Exception as e:
            logger.log_error(e, "Failed to import config as module")
        
        # Summary of results
        logger.log_action("generating_results_summary", "Generating import test results summary", "info")
        
        print(f"\n{'='*60}")
        print("Import Test Results Summary")
        print(f"{'='*60}")
        
        for module_name, result in results.items():
            rel_status = "✓" if result["relative"] else "✗"
            abs_status = "✓" if result["absolute"] else "✗"
            print(f"{module_name}:")
            print(f"  Relative import: {rel_status}")
            if result["relative_error"]:
                print(f"    Error: {result['relative_error'][:100]}")
            print(f"  Absolute import: {abs_status}")
            if result["absolute_error"]:
                print(f"    Error: {result['absolute_error'][:100]}")
            print()
        
        # Check sys.path
        logger.log_action("checking_sys_path", "Checking Python sys.path", "info")
        logger.log_action("sys_path_info", f"sys.path has {len(sys.path)} entries", "info")
        for i, path in enumerate(sys.path[:10]):  # First 10 entries
            logger.log_action(f"sys_path_{i}", f"  [{i}] {path}", "info")
        
        # Check if integrations.pinterest is importable
        try:
            import integrations
            logger.log_action("import_integrations", "Successfully imported integrations package", "success")
        except Exception as e:
            logger.log_error(e, "Failed to import integrations package")
        
        try:
            import integrations.pinterest
            logger.log_action("import_pinterest", "Successfully imported integrations.pinterest package", "success")
        except Exception as e:
            logger.log_error(e, "Failed to import integrations.pinterest package")
        
        # Check __file__ paths
        try:
            config_path = Path(integrations.pinterest.config.__file__)
            logger.log_action("config_file_path", f"config.py located at: {config_path}", "info")
        except Exception as e:
            logger.log_error(e, "Could not determine config.py file path")


if __name__ == "__main__":
    main()

