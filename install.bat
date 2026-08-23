@echo off
rem Paper-to-BIM 安裝程式（Windows：按兩下即可）
rem 這支只負責找到 Python 然後把工作交給 install.py。
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 install.py %*
    goto done
)
where python >nul 2>&1
if %errorlevel%==0 (
    python install.py %*
    goto done
)
echo 找不到 Python 3。請先安裝：
echo     winget install Python.Python.3.12
echo 或到 https://www.python.org/downloads/windows/ 下載，
echo 安裝時務必勾選 tcl/tk and IDLE。
:done
echo.
pause
