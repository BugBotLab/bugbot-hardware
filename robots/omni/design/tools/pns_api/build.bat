@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d C:\Users\Jerome\kicad-dev\src
echo START %DATE% %TIME%
if "%1"=="configure" (
  cmake --preset msvc-win64-release || exit /b 1
)
cmake --build --preset win64-release -- -k 0 || exit /b 1
echo END %DATE% %TIME%
