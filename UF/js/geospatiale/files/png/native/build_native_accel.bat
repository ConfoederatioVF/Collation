@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 (
  echo [ERROR] Failed to initialise MSVC x64 toolchain.
  exit /b 1
)
pushd "%~dp0"
cl /nologo /O2 /arch:AVX2 /GL /EHsc /std:c++20 /LD svea_geopng_accel.cpp /link /LTCG /OUT:svea_geopng_accel.dll
if errorlevel 1 (
  popd
  exit /b 1
)
del /q svea_geopng_accel.obj svea_geopng_accel.lib svea_geopng_accel.exp 2>nul
popd
echo [OK] Built svea_geopng_accel.dll successfully.
