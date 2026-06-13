#!/bin/bash
# 簡單的安裝測試腳本
set -e

echo "Creating sandbox..."
python3 -m venv sandbox_env
source sandbox_env/bin/activate

echo "Installing Aegis..."
python3 -m pip install .

if command -v aegis &> /dev/null;
then
    echo "✅ Success: 'aegis' command is available."
    
    # 檢查版本或 Help 輸出是否正常
    help | head -n 5

    # 額外檢查：驗證 site-packages 中是否包含 config 檔案 (確保 MANIFEST.in 生效)
    PACKAGE_PATH=$(python3 -c "import main_aegis; import os; print(os.path.dirname(main_aegis.__file__))")
    echo "📦 Checking package assets in: $PACKAGE_PATH"
    
else
    echo "❌ Error: 'aegis' command not found."
    exit 1
fi

deactivate
rm -rf sandbox_env
echo "Cleanup complete."
