# Pinterest Integration Tests

Test scripts to identify and debug Pinterest publishing import errors.

## Running the Tests

### Option 1: From Project Root (Recommended)

Navigate to the `Coloring_book_assistant` directory and run:

```powershell
# Windows PowerShell
cd C:\Users\alexa\.cursor\projects\Coloring_book_assistant
python tests/integrations/pinterest/test_pinterest_imports.py
python tests/integrations/pinterest/test_pinterest_publishing.py
python tests/integrations/pinterest/compare_imports.py
```

### Option 2: Using Python Module Syntax

From the project root:

```powershell
cd C:\Users\alexa\.cursor\projects\Coloring_book_assistant
python -m tests.integrations.pinterest.test_pinterest_imports
python -m tests.integrations.pinterest.test_pinterest_publishing
python -m tests.integrations.pinterest.compare_imports
```

### Option 3: Using uv (if you use uv for dependency management)

```powershell
cd C:\Users\alexa\.cursor\projects\Coloring_book_assistant
uv run python tests/integrations/pinterest/test_pinterest_imports.py
uv run python tests/integrations/pinterest/test_pinterest_publishing.py
uv run python tests/integrations/pinterest/compare_imports.py
```

## Test Scripts

### 1. test_pinterest_imports.py

Tests all imports in the Pinterest integration chain:
- Tests relative imports (`.config`, `.models`, etc.)
- Tests absolute imports (`integrations.pinterest.config`, etc.)
- Shows Python environment and sys.path
- Logs each import attempt with full tracebacks

**What it does:**
- Tests importing each module: config, models, content_generator, state_manager, browser_utils, pinterest_publisher_ocr, pinterest_tool, adapter
- Tests both relative and absolute import paths
- Provides detailed error messages for failed imports

### 2. test_pinterest_publishing.py

Functional test of the publishing workflow:
- Creates test folder with sample JSON and images
- Tests full import chain
- Tests PinterestPublisher initialization
- Tests publish_pinterest_pins_core with dry_run=True
- Tests workflow integration

**What it does:**
- Creates a minimal test environment
- Tests the complete publishing workflow without actually publishing
- Verifies all components work together

### 3. compare_imports.py

Compares imports between original Pinterest_agent and current integration:
- Shows side-by-side differences
- Identifies import style changes (absolute → relative)
- Tests import resolution
- Generates fix recommendations

**What it does:**
- Compares import statements in each file
- Identifies which imports changed from absolute to relative
- Tests if imports can be resolved
- Provides recommendations for fixes

## Log Files

All tests generate detailed log files in:
```
tests/integrations/pinterest/logs/
```

Log files are named with timestamps:
- `pinterest_imports_YYYYMMDD_HHMMSS.log`
- `pinterest_publishing_YYYYMMDD_HHMMSS.log`
- `compare_imports_YYYYMMDD_HHMMSS.log`

Each log file contains:
- Timestamped entries for each action
- Full tracebacks for errors
- Python environment information
- Import attempt results
- Test summary with success/failure counts

## Expected Output

When you run a test, you'll see:
1. **Real-time console output** with colored messages:
   - Green for successes
   - Red for errors
   - Cyan for info messages
   - Yellow for warnings

2. **Detailed log file** with all actions and errors

3. **Summary at the end** showing:
   - Total actions performed
   - Number of successes
   - Number of failures
   - Success rate
   - Log file location

## Troubleshooting

If tests fail to run:

1. **Check you're in the right directory:**
   ```powershell
   Get-Location
   # Should show: C:\Users\alexa\.cursor\projects\Coloring_book_assistant
   ```

2. **Verify test files exist:**
   ```powershell
   Test-Path tests/integrations/pinterest/test_pinterest_imports.py
   # Should return: True
   ```

3. **Check Python path:**
   ```powershell
   python --version
   # Should show Python 3.x
   ```

4. **If import errors occur:**
   - Check that all `__init__.py` files exist in the package structure
   - Verify the project root is in sys.path
   - Check the log files for detailed error information

## Next Steps

After running the tests:
1. Review the console output for immediate feedback
2. Check the log files for detailed error information
3. Use the compare_imports.py results to identify import issues
4. Fix any identified problems based on the test results

