@echo off
C:\tools\itmux\bin\bash.exe --login -c "export PATH=/bin; /bin/tmux attach-session -t main 2>/dev/null || /bin/tmux new-session -s main"
