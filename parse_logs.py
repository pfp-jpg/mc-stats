import re
import json
import os
from datetime import datetime

# パスの設定
LOG_FILE_PATH = "server.log"         # マイクラのサーバーログのパス
OUTPUT_JSON_PATH = "playtime.json"   # WEBサイト表示・兼・過去データ保持用のJSON

def load_existing_data():
    """現在WEBに表示されている（これまでの全データが入った）playtime.jsonを読み込む"""
    if os.path.exists(OUTPUT_JSON_PATH):
        try:
            with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 必要なキーが存在するか確認
                if "server_uptime_seconds" in data and "players" in data:
                    # プレイヤーリストを扱いやすいようにxuidの辞書型に変換して返す
                    player_dict = {}
                    for p in data["players"]:
                        if "xuid" in p:
                            player_dict[p["xuid"]] = p
                    
                    return {
                        "server_uptime_seconds": data.get("server_uptime_seconds", 0),
                        "server_open_count": data.get("server_open_count", 0),
                        "players": player_dict
                    }
        except Exception as e:
            print(f"警告: {OUTPUT_JSON_PATH} の読み込みに失敗しました。新規に集計します。({e})")
    
    # 既存データがない、または壊れている場合の初期構造
    return {
        "server_uptime_seconds": 0,
        "server_open_count": 0,
        "players": {}
    }

def parse_logs():
    # 1. まず「これまでの合計データ（playtime.json）」をベースとして読み込む
    base_data = load_existing_data()

    # ログを解析するための正規表現パターン
    log_pattern = re.compile(
        r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}):\d{3} INFO\] Player (connected|disconnected): ([^,]+), xuid: (\d+)'
    )
    time_pattern = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

    # 今回のログファイル内での集計用
    current_log_players = {}  # xuid -> {name, playtime_seconds, join_count, last_seen}
    active_sessions = {}      # xuid -> login_datetime
    first_log_time = None
    last_log_time = None
    current_log_open_count = 0

    # 2. 現在の server.log を解析（新しく増えた分だけをカウント）
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

    # ログから計算される今回の起動時間
    current_log_uptime_seconds = 0
    if first_log_time:
        current_log_uptime_seconds = int((datetime.now() - first_log_time).total_seconds())


    # 3. 【ここが本来やるべきだった合算処理】
    # 「これまでの playtime.json の数値」＋「今回の新しいログの数値」を足し算する
    final_server_uptime = base_data["server_uptime_seconds"] + current_log_uptime_seconds
    final_server_open_count = base_data["server_open_count"] + current_log_open_count

    # プレイヤーデータの合算（既存のデータをベースに引き継ぐ）
    final_players_map = base_data["players"]

    for xuid, c_data in current_log_players.items():
        if xuid in final_players_map:
            # すでにデータがあるプレイヤーは、これまでのデータに「新しく増えた分」を足し算
            final_players_map[xuid]["playtime_seconds"] += c_data["playtime_seconds"]
            final_players_map[xuid]["join_count"] += c_data["join_count"]
            # 名前と最終ログイン時間は最新のログに更新
            final_players_map[xuid]["name"] = c_data["name"]
            final_players_map[xuid]["last_seen"] = c_data["last_seen"]
        else:
            # 新規プレイヤーの場合はそのまま追加
            final_players_map[xuid] = c_data


    # 4. 最終的な合算データを playtime.json に保存
    output_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server_uptime_seconds": final_server_uptime,
        "server_open_count": final_server_open_count,
        "players": list(final_players_map.values())
    }

    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] playtime.json を合算して正常に更新しました。")

if __name__ == "__main__":
    parse_logs()