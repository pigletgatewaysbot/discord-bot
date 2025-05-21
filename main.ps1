$venvPath = ".venv"
$requirementsPath = "requirements.txt"

& $venvPath\Scripts\Activate.ps1

& $venvPath\Scripts\python.exe -m pip install --upgrade pip

& $venvPath\Scripts\python.exe -m pip install -r $requirementsPath

& $venvPath\Scripts\python.exe main.py