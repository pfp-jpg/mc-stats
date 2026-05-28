#!/bin/bash

# 1. GitHubリポジトリのディレクトリに移動 (あなたの環境の絶対パスに書き換えてください)
cd /home/f1ku2376/mc-stats

# 2. マイクラサーバーの最新ログをリポジトリ内にコピーしてくる場合（必要に応じてコメントアウトを解除）
cp /home/f1ku2376/minecraft_server/bedrock-server-1.26.20.5

# 3. Pythonスクリプトを実行して JSON を更新
python3 parse_logs.py

# 4. GitHubに自動でアップロード
git add playtime.json
git commit -m "Auto-update playtime: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main