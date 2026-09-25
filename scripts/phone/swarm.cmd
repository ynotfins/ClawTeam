@echo off
rem Phone-friendly wrapper: works from any cmd.exe SSH session (Windows OpenSSH default shell).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0swarm.ps1" %*
