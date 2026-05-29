import re
import json
import os
from datetime import datetime

# パスの設定
LOG_FILE_PATH = "server.log"         # マイクラのサーバーログのパス
OUTPUT_JSON_PATH = "playtime.json"   # WEBサイト表示用のJSON

def parse_logs():
    # ログを解析するための正規表現パターン
    log_pattern = re.compile(
        r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}):\d{3} INFO\] Player (connected|disconnected): ([^,]+), xuid: (\d+)'
    )
    time_pattern = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

    player_stats = {}      # xuid -> {name, xuid, playtime_seconds, join_count, last_seen}
    active_sessions = {}   # xuid -> login_datetime
    first_log_time = None
    last_log_time = None
    server_open_count = 0  # 鯖開閉回数のカウンタ

    if not os.path.exists(LOG_FILE_PATH):
        print(f"エラー: {LOG_FILE_PATH} が見つかりません。")
        return

    # ログファイルを読み込んで集計
    with open(LOG_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # ログ全体の「一番最初の行の時刻」をサーバー起動時刻として記録
            t_match = time_pattern.match(line)
            if t_match and first_log_time is None:
                first_log_time = datetime.strptime(t_match.group(1), "%Y-%m-%d %H:%M:%S")

            # サーバーが開いた回数をカウント
            if "INFO] Starting Server" in line or "INFO] Server started" in line:
                server_open_count += 1

            match = log_pattern.match(line)
            if match:
                time_str, event, name, xuid = match.groups()
                current_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                last_log_time = current_time

                # プレイヤーの初期登録
                if xuid not in player_stats:
                    player_stats[xuid] = {
                        "name": name,
                        "xuid": xuid,
                        "playtime_seconds": 0,
                        "join_count": 0,
                        "last_seen": time_str
                    }
                
                # プレイヤー名の変更があった場合、最新の名前に更新
                player_stats[xuid]["name"] = name

                if event == "connected":
                    active_sessions[xuid] = current_time
                    player_stats[xuid]["join_count"] += 1  # ログイン回数を+1
                elif event == "disconnected":
                    if xuid in active_sessions:
                        login_time = active_sessions[xuid]
                        duration = (current_time - login_time).total_seconds()
                        player_stats[xuid]["playtime_seconds"] += int(duration)
                        del active_sessions[xuid]
                    player_stats[xuid]["last_seen"] = time_str

    # ログ全体で一度も起動ログが引っかからなかった場合の安全装置
    if server_open_count == 0 and first_log_time is not None:
        server_open_count = 1

    # 現在もオンライン中のプレイヤーの時間を、ログの最終記録時刻まで加算
    if last_log_time:
        for xuid, login_time in active_sessions.items():
            duration = (last_log_time - login_time).total_seconds()
            player_stats[xuid]["playtime_seconds"] += int(duration)
            player_stats[xuid]["last_seen"] = "オンライン中"

    # サーバー全体の合計起動時間を計算（最初のログから現在時刻までの秒数）
    server_uptime_seconds = 0
    if first_log_time:
        server_uptime_seconds = int((datetime.now() - first_log_time).total_seconds())

    # HTML側で扱うためのJSON構造に変換
    output_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server_uptime_seconds": server_uptime_seconds,
        "server_open_count": server_open_count,
        "players": list(player_stats.values())
    }

    # JSONファイルとして書き出し
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] playtime.json を正常に更新しました。")

if __name__ == "__main__":
    parse_logs()