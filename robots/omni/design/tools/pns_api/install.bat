@echo off
rem Installs into src\build\install\msvc-win64-release (KiCad bakes its install prefix in at configure time)
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cmake --install C:\Users\Jerome\kicad-dev\src\build\msvc-win64-release || exit /b 1
xcopy /Y /Q /D C:\Users\Jerome\kicad-dev\src\build\msvc-win64-release\vcpkg_installed\x64-windows\bin\*.dll C:\Users\Jerome\kicad-dev\src\build\install\msvc-win64-release\bin\ >nul
rem Embedded Python needs its stdlib next to the binaries (same as kicad-win-builder)
xcopy /Y /Q /E /D C:\Users\Jerome\kicad-dev\src\build\msvc-win64-release\vcpkg_installed\x64-windows\tools\python3\* C:\Users\Jerome\kicad-dev\src\build\install\msvc-win64-release\bin\ >nul
echo INSTALLED
