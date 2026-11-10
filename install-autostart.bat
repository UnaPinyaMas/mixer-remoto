@echo off
rem EN: Makes the Mixer start by itself (no window) when you log in to Windows, with a watchdog
rem     that restarts it if it crashes or hangs.
rem ES: Hace que el Mixer arranque solo (sin ventana) al iniciar sesion en Windows, con un vigilante
rem     que lo reinicia si se cae o se queda colgado.
setlocal
set "DIR=%~dp0"
for /f "delims=" %%i in ('where pythonw.exe') do set "PYW=%%i" & goto :found
echo pythonw.exe not found. Install Python first.
echo No encuentro pythonw.exe. Instala Python primero.
pause & exit /b 1
:found
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MixerRemoto.lnk"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath='%PYW%'; $s.Arguments='supervisor.py'; $s.WorkingDirectory='%DIR%'; $s.WindowStyle=7; $s.Save()"
echo.
echo Done. The Mixer will start with Windows and restart itself if it fails.
echo Listo. El Mixer se iniciara solo con Windows y se reiniciara si falla.
echo.
echo Starting it now... / Arrancandolo ahora mismo...
start "" "%PYW%" supervisor.py
echo.
echo To remove it, delete / Para quitarlo, borra:  %LNK%
pause
