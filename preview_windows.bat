@echo off
cd /d %~dp0
python -m http.server 8000
echo Open Chrome: http://localhost:8000/previews/index.html
