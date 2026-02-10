@echo off
echo ========================================
echo   INSTALADOR DE DEPENDENCIAS
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist ".venv_new" (
    echo Creando entorno virtual...
    python -m venv .venv_new
    echo.
)

echo Actualizando pip...
.\.venv_new\Scripts\python.exe -m pip install --upgrade pip
echo.

echo Instalando dependencias principales...
.\.venv_new\Scripts\python.exe -m pip install -r requirements.txt
echo.

echo Instalando PyTorch con soporte GPU (CUDA)...
.\.venv_new\Scripts\python.exe -m pip uninstall torch torchvision -y
.\.venv_new\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
echo.

echo ========================================
echo   INSTALACION COMPLETADA
echo ========================================
echo.
echo Ahora puedes ejecutar: run.bat
echo.
pause
