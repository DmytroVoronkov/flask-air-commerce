@echo off
:: Create virtual environment
python -m venv venv

:: Activate virtual environment
call app\venv\Scripts\activate

:: Install requirements
pip install -r app\requirements.txt

echo Virtual environment created and dependencies installed.
echo To activate the virtual environment, run: call venv\Scripts\activate
pause