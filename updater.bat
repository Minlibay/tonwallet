
        timeout /t 2 /nobreak > NUL
        xcopy /y /s "update\*" "."
        rmdir /s /q update
        start "" "C:\Users\soull\PycharmProjects\GENERATE\.venv\Scripts\python.exe" C:\Users\soull\PycharmProjects\GENERATE\.venv\app.py
        del updater.bat
        exit
        