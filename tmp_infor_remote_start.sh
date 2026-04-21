set +e
tmux kill-session -t infor-hub-api 2>/dev/null
tmux new -d -s infor-hub-api "cd /share/home/lijiyao/CCCC/Infor_hub && apptainer exec --bind /share/home/lijiyao/CCCC:/share/home/lijiyao/CCCC /share/home/lijiyao/CCCC/apptainer/inforhub.sif python -m uvicorn api.app:app --host 127.0.0.1 --port 8010 > /share/home/lijiyao/CCCC/.logs/infor_hub_api_8010.log 2>&1"
sleep 6
tmux has-session -t infor-hub-api 2>/dev/null && echo running || echo stopped
ss -lntp | grep -E ":(8010)\\b"
curl -sS --max-time 10 http://127.0.0.1:8010/health