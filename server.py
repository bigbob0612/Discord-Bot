from flask import Flask, request, jsonify
from utils.json_loader import load_json
from utils.music_db import Database
from nextcord.ext import commands
from cogs.sub_music import SubMusicCog
import asyncio
import threading
import nextcord
import os
import signal

# 설정 파일 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "../config/settings.json")
config = load_json(CONFIG_PATH)

# 서브봇 정의 및 초기화
intents = nextcord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True  # 추가: 메시지 내용 접근 권한
subbot = commands.Bot(command_prefix="?", intents=intents)

# SQLite 초기화
database = Database("subbot_music_queue.db")

async def initialize_database():
    """데이터베이스 초기화"""
    await database.initialize()
    print("✅ SQLite 데이터베이스 초기화 완료")

# Flask 앱 정의
app = Flask(__name__)

# 서브봇 준비 이벤트
@subbot.event
async def on_ready():
    await subbot.change_presence(activity=nextcord.Game(name='Lost Ark'))
    print(f"✅ 서브봇 준비 완료: {subbot.user}")

# 서브봇 명령어 추가
subbot.add_cog(SubMusicCog(subbot, database))

# Flask API 엔드포인트
@app.route("/play", methods=["POST"])
def play_song():
    try:
        data = request.get_json()
        print(f"🔍 요청 데이터: {data}")  # 요청 데이터 출력
        guild_id = int(data["guild_id"])
        voice_channel_id = int(data["voice_channel_id"])
        text_channel_id = int(data["text_channel_id"])
        url = data["url"]
        requester = data.get("requester", "알 수 없음")

        async def handle_request():
            music_cog = subbot.get_cog("SubMusicCog")
            if not music_cog:
                raise RuntimeError("SubMusicCog를 찾을 수 없습니다.")
            await music_cog.play_song_direct(guild_id, voice_channel_id, text_channel_id, url, requester)

        asyncio.run_coroutine_threadsafe(handle_request(), subbot.loop)
        return jsonify({"status": "success", "message": "서브봇이 요청을 처리 중입니다!"})
    except KeyError as e:
        print(f"⚠️ 요청 데이터 누락: {e}")
        return jsonify({"status": "error", "error": f"필수 필드 누락: {e}"}), 400
    except Exception as e:
        print(f"⚠️ 처리 중 오류: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/status", methods=["GET"])
def get_status():
    try:
        music_cog = subbot.get_cog("SubMusicCog")
        if not music_cog:
            return jsonify({"status": "error", "message": "MusicCog not found"}), 404

        # 모든 상태 정보를 반환
        all_states = music_cog.get_all_states()
        return jsonify({"status": "success", "data": all_states})
    except Exception as e:
        print(f"⚠️ 상태 확인 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Flask 실행 함수
def run_flask():
    """Flask 서버 실행"""
    app.run(host="0.0.0.0", port=5001, debug=False)

# 안전한 종료 처리
def shutdown_handler(signal, frame):
    print("🛑 서버 종료 중...")
    subbot.close()
    database.close()  # 데이터베이스 연결 해제
    os._exit(0)

signal.signal(signal.SIGINT, shutdown_handler)

# 메인 실행
if __name__ == "__main__":
    # 이벤트 루프와 데이터베이스 초기화
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(initialize_database())

    # Flask 서버 스레드 실행
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 서브봇 실행
    TOKEN = config["server"]["token"]
    subbot.run(TOKEN)