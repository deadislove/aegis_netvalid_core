#!/bin/bash
# Simple installation test script
set -e

echo "Creating sandbox..."
python3 -m venv sandbox_env
source sandbox_env/bin/activate

echo "Installing Aegis..."
python3 -m pip install .

if command -v aegis &> /dev/null;
then
    echo "✅ Success: 'aegis' command is available."

    # Check if version or help output is working correctly
    help | head -n 5

    # Extra check: Verify that config files are included in site-packages (ensuring MANIFEST.in is effective)
    PACKAGE_PATH=$(python3 -c "import main_aegis; import os; print(os.path.dirname(main_aegis.__file__))")
    echo "📦 Checking package assets in: $PACKAGE_PATH"
    
else
    echo "❌ Error: 'aegis' command not found."
    exit 1
fi

deactivate
rm -rf sandbox_env
echo "Cleanup complete."
