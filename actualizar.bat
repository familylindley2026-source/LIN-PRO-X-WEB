@echo off
echo Iniciando despliegue continuo en LIN-PRO-X...
git add .
git commit -m "Actualizacion general de plataforma"
git push
echo.
echo ¡Actualizacion enviada a la nube con exito!