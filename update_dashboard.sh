#!/bin/bash

# 1. GitHubリポジトリのディレクトリに移動
cd /home/f1ku2376/minecraft_server/bedrock-server-1.26.20.5/mc-stats

# 2. マイクラサーバーの最新ログをここにコピーしてくる（ファイル名とコピー先を正確に指定）
cp /home/f1ku2376/minecraft_server/bedrock-server-1.26.20.5/server.log ./server.log

# 3. Pythonスクリプトを実行して playtime.json を更新
python3 parse_logs.py

# 4. GitHubに自動でアップロード
git add playtime.json update_dashboard.sh
git commit -m "Auto-update playtime: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main