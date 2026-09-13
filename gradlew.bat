@echo off
setlocal
set "ROOT_DIR=%~dp0"
for /f "tokens=2 delims==" %%G in ('findstr /b "distributionUrl=" "%ROOT_DIR%gradle\wrapper\gradle-wrapper.properties"') do set "DIST_URL=%%G"
if not defined DIST_URL (
  echo Unable to determine Gradle distribution URL.
  exit /b 1
)
set "DIST_URL=%DIST_URL:\=/%"
for /f "tokens=1,2 delims=-" %%A in ("%DIST_URL%") do set "_unused=%%A"
set "VERSION=9.3.1"
set "CACHE_DIR=%USERPROFILE%\.gradle\bootstrap-dists"
set "DIST_DIR=%CACHE_DIR%\gradle-%VERSION%"
set "GRADLE_BIN=%DIST_DIR%\bin\gradle.bat"
if not exist "%GRADLE_BIN%" (
  where curl >nul 2>nul
  if errorlevel 1 (
    echo curl is required to bootstrap Gradle on Windows.
    exit /b 1
  )
  if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"
  set "TMP_DIR=%TEMP%\aicf-gradle-%VERSION%"
  if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
  mkdir "%TMP_DIR%"
  curl --fail --location --retry 3 --output "%TMP_DIR%\gradle.zip" "https://services.gradle.org/distributions/gradle-%VERSION%-bin.zip"
  powershell -NoProfile -Command "Expand-Archive -LiteralPath '%TMP_DIR%\gradle.zip' -DestinationPath '%TMP_DIR%\extracted' -Force"
  if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
  move "%TMP_DIR%\extracted\gradle-%VERSION%" "%DIST_DIR%" >nul
  rmdir /s /q "%TMP_DIR%"
)
call "%GRADLE_BIN%" %*
exit /b %ERRORLEVEL%
