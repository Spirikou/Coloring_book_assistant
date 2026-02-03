"""
Antivirus interference checks for Pinterest automation.
Specifically checks for Bitdefender interference and missing files.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple


def check_critical_files() -> Dict[str, any]:
    """
    Check if critical files for Pinterest automation exist.
    
    Returns:
        dict with: all_present (bool), missing_files (list), details (dict)
    """
    # Get the integrations/pinterest directory
    pinterest_dir = Path(__file__).parent
    
    critical_files = {
        "config.py": pinterest_dir / "config.py",
        "models.py": pinterest_dir / "models.py",
        "content_generator.py": pinterest_dir / "content_generator.py",
        "state_manager.py": pinterest_dir / "state_manager.py",
        "pinterest_publisher_ocr.py": pinterest_dir / "pinterest_publisher_ocr.py",
        "pinterest_tool.py": pinterest_dir / "pinterest_tool.py",
        "adapter.py": pinterest_dir / "adapter.py",
        "browser_utils.py": pinterest_dir / "browser_utils.py",
        "workflow_logger.py": pinterest_dir / "workflow_logger.py",
    }
    
    missing_files = []
    file_status = {}
    
    for name, path in critical_files.items():
        exists = path.exists()
        file_status[name] = {
            "exists": exists,
            "path": str(path)
        }
        if not exists:
            missing_files.append(name)
    
    # Check for __init__.py
    init_file = pinterest_dir / "__init__.py"
    if not init_file.exists():
        missing_files.append("__init__.py")
        file_status["__init__.py"] = {
            "exists": False,
            "path": str(init_file)
        }
    
    return {
        "all_present": len(missing_files) == 0,
        "missing_files": missing_files,
        "file_status": file_status,
        "total_checked": len(critical_files) + 1,
        "total_missing": len(missing_files)
    }


def check_playwright_installation() -> Dict[str, any]:
    """
    Check if Playwright is properly installed and browser binaries exist.
    
    Returns:
        dict with: installed (bool), browsers_available (list), issues (list)
    """
    issues = []
    browsers_available = []
    
    try:
        import playwright
        playwright_installed = True
    except ImportError:
        playwright_installed = False
        issues.append("Playwright Python package not installed")
        return {
            "installed": False,
            "browsers_available": [],
            "issues": issues
        }
    
    # Check if playwright browsers are installed
    # Note: We don't actually need to start playwright to use it - we connect to existing browser
    # So browser binaries are optional if using connect_existing=True
    try:
        from playwright.sync_api import sync_playwright
        
        # Just verify we can import it - don't try to start it
        # Browser binaries might be missing but that's OK if we're connecting to existing browser
        browsers_available.append("playwright_imported")
        
    except Exception as e:
        # This is a real issue - can't even import playwright
        issues.append(f"Error importing Playwright: {str(e)}")
        return {
            "installed": playwright_installed,
            "browsers_available": [],
            "issues": issues
        }
    
    # Note: We don't check for browser binaries because:
    # 1. We use connect_existing=True (connect to existing browser)
    # 2. Browser binaries might be in user's home directory (not easily checkable)
    # 3. The actual error will show up when trying to connect
    
    return {
        "installed": playwright_installed,
        "browsers_available": browsers_available,
        "issues": issues
    }


def get_bitdefender_warning() -> Dict[str, any]:
    """
    Get Bitdefender-specific warnings and recommendations.
    
    Returns:
        dict with warning message and recommendations
    """
    warning = {
        "title": "⚠️ Bitdefender Antivirus Detected",
        "message": "Bitdefender's Advanced Threat Detection may interfere with browser automation.",
        "recommendations": [
            "Temporarily disable Bitdefender's Advanced Threat Detection",
            "Add the project folder to Bitdefender's exclusions list",
            "Add the browser executable to Bitdefender's exclusions",
            "Check Bitdefender's quarantine to see if any files were deleted",
            "After making changes, restart the Streamlit app"
        ],
        "exclusion_paths": [
            str(Path(__file__).parent.parent.parent),  # Project root
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware"),  # Brave browser
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome"),  # Chrome browser
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge"),  # Edge browser
        ]
    }
    
    return warning


def run_full_check() -> Dict[str, any]:
    """
    Run all checks and return comprehensive status.
    
    Returns:
        dict with all check results
    """
    file_check = check_critical_files()
    playwright_check = check_playwright_installation()
    bitdefender_warning = get_bitdefender_warning()
    
    # Determine overall status
    # Only file issues are critical - Playwright browser binaries are optional
    # since we use connect_existing=True (connect to existing browser)
    critical_playwright_issues = [
        issue for issue in playwright_check["issues"]
        if "importing" in issue.lower() or "not installed" in issue.lower()
    ]
    
    has_issues = (
        not file_check["all_present"] or
        not playwright_check["installed"] or
        len(critical_playwright_issues) > 0
    )
    
    return {
        "has_issues": has_issues,
        "file_check": file_check,
        "playwright_check": playwright_check,
        "bitdefender_warning": bitdefender_warning,
        "recommendations": _generate_recommendations(file_check, playwright_check)
    }


def _generate_recommendations(file_check: Dict, playwright_check: Dict) -> List[str]:
    """Generate specific recommendations based on check results."""
    recommendations = []
    
    if not file_check["all_present"]:
        recommendations.append(
            f"❌ {len(file_check['missing_files'])} critical file(s) missing: {', '.join(file_check['missing_files'])}"
        )
        recommendations.append("   → Check Bitdefender quarantine and restore deleted files")
        recommendations.append("   → Reinstall the project if files cannot be restored")
    
    if not playwright_check["installed"]:
        recommendations.append("❌ Playwright not installed")
        recommendations.append("   → Run: uv sync (or pip install playwright)")
    
    # Only show browser binary warnings if it's a critical issue
    # Since we use connect_existing=True, browser binaries are optional
    critical_issues = [issue for issue in playwright_check["issues"] 
                      if "importing" in issue.lower() or "not installed" in issue.lower()]
    if critical_issues:
        for issue in critical_issues:
            recommendations.append(f"⚠️ {issue}")
        recommendations.append("   → Run: uv sync (or pip install playwright)")
    
    if not recommendations:
        recommendations.append("✅ All checks passed - no issues detected")
    
    return recommendations

