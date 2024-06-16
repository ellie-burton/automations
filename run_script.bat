@echo off
taskkill /F /IM Python3.11.exe /T
start cmd /k "C:\Users\ekate\AppData\Local\Microsoft\WindowsApps\python C:\GitHub\automations\weeklyemail.py > C:\GitHub\automations\weeklyemail.log 2>&1"
