@echo off
:: Esta linea asegura que la consola se abra exactamente en la carpeta del proyecto
cd /d "%~dp0"

title Actualizando LIN-PRO X WEB en la Nube
color 0B

echo ===================================================
echo 🚀 INICIANDO ACTUALIZACION EN LA NUBE (LIN-PRO X)
echo ===================================================
echo.

echo [1/4] Activando entorno virtual de Python (.venv)...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [ADVERTENCIA] No se encontro la carpeta .venv.
)
echo.

echo [2/4] Empaquetando los archivos modificados...
git add .
echo.

echo [3/4] Creando punto de control y registro...
git commit -m "Actualizacion automatica de mejoras y correcciones"
echo.

echo [4/4] Subiendo cambios al servidor (GitHub)...
git push origin main
echo.

echo ===================================================
echo ✅ ¡PROCESO FINALIZADO!
echo ===================================================
echo.
pause