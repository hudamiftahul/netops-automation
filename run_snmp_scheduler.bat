
@echo off

cd /d "C:\Users\mifta\Documents\project\netops-automation-platform"

echo Starting NetOps SNMP Scheduler...

".venv\Scripts\python.exe" -u "src\snmp_scheduler.py" >> "data\snmp_scheduler.log" 2>&1

echo SNMP Scheduler stopped with exit code %ERRORLEVEL%
