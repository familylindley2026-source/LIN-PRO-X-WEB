@echo off
title Actualizando LIN-PRO X WEB
color 0B

echo ===================================================
echo 🚀 INICIANDO ACTUALIZACION EN LA NUBE (LIN-PRO X)
echo ===================================================
echo.

echo [1/3] Empaquetando los archivos modificados...
git add .
echo.

echo [2/3] Creando punto de control y registro...
git commit -m "Actualizacion automatica de mejoras y correcciones"
echo.

echo [3/3] Subiendo cambios al servidor (GitHub)...
git push origin main
echo.

echo ===================================================
echo ✅ ¡ACTUALIZACION COMPLETADA CON EXITO!
echo ===================================================
echo.
pause