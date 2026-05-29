import re
import json
import os
from datetime import datetime

# パスの設定
LOG_FILE_PATH = "server.log"         # マイクラのサーバーログのパス
OUTPUT_JSON_PATH = "playtime.json"   # WEBサイト表示用のJSON
TOTAL_STATS_PATH = "total_stats.json" # 過去の累積データを保存するファイル

def load_total_stats():
    """過去の累積データを読み込む関数。ファイルがなければ初期構造を返す。"""
    if os.path.exists(TOTAL_STATS_PATH):
        try:
            with open(TOTAL_STATS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 最低限必要なキーが存在するかチェックし、なければ初期化
                if "accumulated_uptime_seconds" in data:
                    return data
        except Exception as e:
            print(f"警告: {TOTAL_STATS_PATH} の読み込みに失敗したため、新規作成します。({e})")
    
    return {
        "accumulated_uptime_seconds": 0,
        "accumulated_open_count": 0,
        "players": {} # xuid -> {name, playtime_seconds, join_count, last_seen}
    }

def parse_logs():
    # 過去の累積（貯金）を読み込み
    total_stats = load_total_stats()

    # ログを解析するための正規表現パターン
    log_pattern = re.compile(
        r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}):\d{3} INFO\] Player (connected|disconnected): ([^,]+), xuid: (\d+)'
    )
    time_pattern = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

    # 今回のログファイル内での集計用変数
    current_log_players = {}  # xuid -> {name, playtime_seconds, join_count, last_seen}
    active_sessions = {}      # xuid -> login_datetime
    first_log_time = None
    last_log_time = None
    current_log_open_count = 0

    # 1. 現在の server.log を解析（存在する場合のみ）
    if os.path.exists(LOG_FILE_PATH) and os.path.getsize(LOG_FILE_PATH) > 0:
        with open(LOG_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                t_match = time_pattern.match(line)
                if t_match and first_log_time is None:
                    first_log_time = datetime.strptime(t_match.group(1), "%Y-%m-%d %H:%M:%S")

                if "INFO] Starting Server" in line or "INFO] Server started" in line:
                    current_log_open_count += 1

                match = log_pattern.match(line)
                if match:
                    time_str, event, name, xuid = match.groups()
                    current_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    last_log_time = current_time

                    if xuid not in current_log_players:
                        current_log_players[xuid] = {
                            "name": name,
                            "xuid": xuid,
                            "playtime_seconds": 0,
                            "join_count": 0,
                            "last_seen": time_str
                        }
                    
                    current_log_players[xuid]["name"] = name

                    if event == "connected":
                        active_sessions[xuid] = current_time
                        current_log_players[xuid]["join_count"] += 1
                    elif event == "disconnected":
                        if xuid in active_sessions:
                            login_time = active_sessions[xuid]
                            duration = (current_time - login_time).total_seconds()
                            current_log_players[xuid]["playtime_seconds"] += int(duration)
                            del active_sessions[xuid]
                        current_log_players[xuid]["last_seen"] = time_str

        # 現在もオンライン中のプレイヤーの処理
        if last_log_time:
            for xuid, login_time in active_sessions.items():
                duration = (last_log_time - login_time).total_seconds()
                current_log_players[xuid]["playtime_seconds"] += int(duration)
                current_log_players[xuid]["last_seen"] = "オンライン中"

    # ログが空、または存在しない場合の安全装置
    if current_log_open_count == 0 and first_log_time is not None:
        current_log_open_count = 1

    # 今回のログから計算される起動時間
    current_log_uptime_seconds = 0
    if first_log_time:
        current_log_uptime_seconds = int((datetime.now() - first_log_time).total_seconds())


    # 2. 過去の貯金データ（total_stats）と、今回のログのデータを合算する
    final_server_uptime = total_stats["accumulated_uptime_seconds"] + current_log_uptime_seconds
    final_server_open_count = total_stats["accumulated_open_count"] + current_log_open_count

    # プレイヤーデータの合算用辞書（過去のデータをベースに引き継ぐ）
    final_players_map = dict(total_stats["players"])

    for xuid, c_data in current_log_players.items():
        if xuid in final_players_map:
            # 過去にデータがある場合は、プレイ時間とログイン回数を足し算
            final_players_map[xuid]["playtime_seconds"] += c_data["playtime_seconds"]
            final_players_map[xuid]["join_count"] += c_data["join_count"]
            # 名前と最終ログインは最新のログの内容に更新
            final_players_map[xuid]["name"] = c_data["name"]
            final_players_map[xuid]["last_seen"] = c_data["last_seen"]
        else:
            # 新規プレイヤーの場合はそのまま登録
            final_players_map[xuid] = c_data


    # 3. データの書き出し
    
    # 【WEB表示用】playtime.json を作成
    output_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server_uptime_seconds": final_server_uptime,
        "server_open_count": final_server_open_count,
        "players": list(final_players_map.values())
    }
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # 👈【ここを書き忘れていました】次回計算のために、合算データを total_stats.json にも上書き保存して貯金する
    new_total_stats = {
        "accumulated_uptime_seconds": final_server_uptime,
        "accumulated_open_count": final_server_open_count,
        "players": final_players_map
    }
    with open(TOTAL_STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_total_stats, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] playtime.json および total_stats.json を正常に更新しました。")

if __name__ == "__main__":
    parse_logs()