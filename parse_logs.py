import re
import json
import os
from datetime import datetime

# パスの設定
LOG_FILE_PATH = "server.log"         # マイクラのサーバーログのパス
OUTPUT_JSON_PATH = "playtime.json"   # WEBサイト表示用のJSON

def get_real_total_base():
    """
    【完全復活】2026-05-29 11:20:39 時点の本物の合計データ（ベースライン）。
    プログラムの内部に直接保持するため、ログのクリアやバグで消えることは絶対にありません。
    """
    return {
        "server_uptime_seconds": 5441753,
        "server_open_count": 194,
        "players": {
            "2535459849782491": { "name": "F1ku2376", "playtime_seconds": 368758, "join_count": 221, "last_seen": "2026-05-28 18:40:58" },
            "2535412868977356": { "name": "Penbas1675", "playtime_seconds": 305940, "join_count": 92, "last_seen": "2026-05-24 13:08:43" },
            "2535442245226493": { "name": "Remonedo1882", "playtime_seconds": 639105, "join_count": 98, "last_seen": "2026-05-29 04:54:09" },
            "2535426609617963": { "name": "kamonohashi123", "playtime_seconds": 299789, "join_count": 92, "last_seen": "2026-05-24 17:27:54" },
            "2535455351900966": { "name": "NEKOMARU 119", "playtime_seconds": 51744, "join_count": 15, "last_seen": "2026-05-28 19:16:09" },
            "2535417070048526": { "name": "RustyDrake3638", "playtime_seconds": 832, "join_count": 2, "last_seen": "2026-04-04 23:00:16" },
            "2535415842750871": { "name": "zenless zero0", "playtime_seconds": 1723, "join_count": 1, "last_seen": "2026-04-11 23:28:39" }
        }
    }

def parse_logs():
    # 本物の過去データを土台としてセット
    base_data = get_real_total_base()

    # ログを解析するための正規表現パターン
    log_pattern = re.compile(
        r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}):\d{3} INFO\] Player (connected|disconnected): ([^,]+), xuid: (\d+)'
    )
    time_pattern = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

    # 現在の server.log 内だけの新規集計用
    current_log_players = {}
    active_sessions = {}
    first_log_time = None
    last_log_time = None
    current_log_open_count = 0

    # 1. 現在の server.log をゼロからクリーンに解析
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

        # 現在オンライン中のプレイヤーの処理
        if last_log_time:
            for xuid, login_time in active_sessions.items():
                duration = (last_log_time - login_time).total_seconds()
                current_log_players[xuid]["playtime_seconds"] += int(duration)
                current_log_players[xuid]["last_seen"] = "オンライン中"

    # 現在のログから計算される起動時間
    current_log_uptime_seconds = 0
    if first_log_time:
        current_log_uptime_seconds = int((datetime.now() - first_log_time).total_seconds())


    # 2. 【合算処理】確定している本物の土台データに、新しく増えたログの数値をシンプルにプラスする
    final_server_uptime = base_data["server_uptime_seconds"] + current_log_uptime_seconds
    final_server_open_count = base_data["server_open_count"] + current_log_open_count

    # 出力用マップの作成（本物の過去データをそのままコピー）
    final_players_map = {}
    for xuid, b_pdata in base_data["players"].items():
        final_players_map[xuid] = {
            "name": b_pdata["name"],
            "xuid": xuid,
            "playtime_seconds": b_pdata["playtime_seconds"],
            "join_count": b_pdata["join_count"],
            "last_seen": b_pdata["last_seen"]
        }

    # 現在のログの新規データを安全に合算
    for xuid, c_data in current_log_players.items():
        if xuid in final_players_map:
            # 過去にデータがあるプレイヤーは、本物の土台に対して新しく増えた分を足し算
            final_players_map[xuid]["playtime_seconds"] += c_data["playtime_seconds"]
            final_players_map[xuid]["join_count"] += c_data["join_count"]
            final_players_map[xuid]["name"] = c_data["name"]
            final_players_map[xuid]["last_seen"] = c_data["last_seen"]
        else:
            # 新規のプレイヤー（土台にいない人）はそのまま新しく追加
            final_players_map[xuid] = c_data

    # 3. 最終的なデータを playtime.json に書き出し
    output_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server_uptime_seconds": final_server_uptime,
        "server_open_count": final_server_open_count,
        "players": list(final_players_map.values())
    }

    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] playtime.json を本物の合計ベースで安全に更新しました。")

if __name__ == "__main__":
    parse_logs()