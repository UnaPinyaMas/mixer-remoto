@echo off
rem Hace que el Mixer arranque solo (sin ventana) al iniciar sesion en Windows,
rem con un vigilante que lo reinicia si se cae o se queda colgado.
setlocal
set "DIR=%~dp0"
for /f "delims=" %%i in ('where pythonw.exe') do set "PYW=%%i" & goto :found
echo No encuentro pythonw.exe. Instala Python primero.
pause & exit /b 1
:found
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MixerRemoto.lnk"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath='%PYW%'; $s.Arguments='supervisor.py'; $s.WorkingDirectory='%DIR%'; $s.WindowStyle=7; $s.Save()"
echo.
echo Listo. El Mixer se iniciara solo al encender el PC y se reiniciara si falla.
echo Arrancandolo ahora mismo...
start "" "%PYW%" supervisor.py
echo.
echo Para quitarlo: borra  %LNK%
pause
