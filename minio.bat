@echo off

REM 启动 MinIO
start cmd /k "%~dp0\minio\minio.exe server /data"

REM 检查 MinIO 进程是否启动
tasklist | findstr /i "minio.exe"

REM 检查 MinIO 端口是否被占用
netstat -ano | findstr "9000"
if %errorlevel% equ 0 (
  echo Port is in use
) else (
  echo Port is not in use
)