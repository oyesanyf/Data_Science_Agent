@echo off
echo ============================================================
echo FIXING NUMPY/OPENCV COMPATIBILITY ISSUE
echo ============================================================
echo.
echo The issue: numpy 2.x is incompatible with opencv-python
echo Solution: Downgrade numpy to 1.x series
echo.
echo ============================================================
echo STEP 1: Uninstalling incompatible numpy...
echo ============================================================
uv pip uninstall -y numpy

echo.
echo ============================================================
echo STEP 2: Installing compatible numpy version...
echo ============================================================
uv pip install "numpy>=1.24,<2.0"

echo.
echo ============================================================
echo STEP 3: Installing opencv-python...
echo ============================================================
uv pip install "opencv-python>=4.8.0"

echo.
echo ============================================================
echo STEP 4: Verifying installation...
echo ============================================================
python -c "import numpy; print(f'NumPy version: {numpy.__version__}')"
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"

echo.
echo ============================================================
echo FIX COMPLETE! You can now restart the server.
echo ============================================================
echo.
echo Run: start_server.bat
echo.
pause

