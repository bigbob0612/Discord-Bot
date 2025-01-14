import nextcord
from nextcord.ext import commands, tasks
from nextcord import ui, Interaction
from utils.music_db import Database
import yt_dlp
import asyncio
from datetime import timedelta
import requests  # 서브봇과의 통신 추가
import aiohttp
import json
import psutil
import urllib.parse  # URL 파싱을 위해 필요

class MusicState:
    def __init__(self, voice_client=None):
        self.voice_client = voice_client
        self.is_paused = False
        self.current_song = None
        self.queue = []
        self.start_time = None
        self.total_duration = 0
        self.message_lyrics = None
        self.message_time = None
        self.previous_messages = []  # 서버별로 이전 메시지 추적
        self.current_lyrics = []
        self.leave_task = None
        self._is_playing_next = False  # 추가: 다음 곡 재생 상태 추적
        self.is_playing = False  # **노래 재생 상태 추가**
        self.is_finished = False  # **노래 종료 상태 추가**


        # 일시정지 관련 속성 추가
        self.paused_duration = 0  # 일시정지 동안 누적된 시간
        self.paused_time = None  # 일시정지 시작 시점

class MusicView(ui.View):
    def __init__(self, music_cog):
        super().__init__(timeout=None)
        self.music_cog = music_cog

    @ui.button(label="▶︎ 재생", style=nextcord.ButtonStyle.green)
    async def play_button(self, button: ui.Button, interaction: Interaction):
        await self.music_cog.resume_song(interaction)

    @ui.button(label="⏸︎ 정지", style=nextcord.ButtonStyle.red)
    async def stop_button(self, button: ui.Button, interaction: Interaction):
        await self.music_cog.stop_song(interaction)

    @ui.button(label="⏭️ 스킵", style=nextcord.ButtonStyle.blurple)
    async def skip_button(self, button: ui.Button, interaction: Interaction):
        """스킵 버튼 클릭 시 호출"""
        try:
            # 응답 지연 처리
            if not interaction.response.is_done():
                await interaction.response.defer()
    
            # 스킵 처리
            await self.music_cog.skip_song(interaction)
        except nextcord.errors.InteractionResponded:
            # 이미 응답이 처리된 경우 로그만 남김
            print("⚠️ 스킵 버튼: 이미 응답이 처리되었습니다.")
        except Exception as e:
            # 예외 발생 시 응답
            print(f"⚠️ 스킵 버튼 처리 중 오류 발생: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ 스킵 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                    ephemeral=True, delete_after=10
                )
            else:
                await interaction.followup.send(
                    "❌ 스킵 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                    ephemeral=True, delete_after=10
                )

    @ui.button(label="📋 대기열", style=nextcord.ButtonStyle.gray)
    async def queue_button(self, button: ui.Button, interaction: Interaction):
        """
        버튼을 눌렀을 때 대기열 표시
        """
        queue = await self.music_cog.get_queue(interaction.guild_id)

        # 대기열이 비어 있을 경우 텍스트 메시지 출력
        if not queue:
            await interaction.response.send_message(
                "🎶 대기 중인 노래가 없어요! 뭔가 틀어볼까요? 🎧",
                ephemeral=True
            )
            return

        # 대기열이 있을 경우 임베드 표시
        embed = nextcord.Embed(title="현재 대기열", color=nextcord.Color.red())
        for i, song in enumerate(queue[:20]):  # 최대 20곡까지만 표시
            embed.add_field(
                name=f"{i + 1}. {song['title']}",
                value=f"**요청자**: {song['requester']}",
                inline=False,
            )
        embed.set_footer(text=f"총 {len(queue)}개의 곡이 대기 중")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="➕ 노래 추가", style=nextcord.ButtonStyle.success)
    async def add_song_button(self, button: ui.Button, interaction: Interaction):
        """노래 추가 버튼 - 모달 띄우기"""
        modal = AddSongModal(self.music_cog)
        await interaction.response.send_modal(modal)

class AddSongModal(ui.Modal):
    def __init__(self, music_cog):
        super().__init__(title="노래 추가")
        self.music_cog = music_cog  # music_cog 할당

        # URL 입력 필드 생성
        self.url_input = ui.TextInput(
            label="노래 URL",
            placeholder="https://www.youtube.com/watch?v=...",
            style=nextcord.TextInputStyle.short,
            required=True,
            max_length=200,
        )

        # URL 입력 필드를 Modal에 추가
        self.add_item(self.url_input)

    async def callback(self, interaction: Interaction):
        """모달 제출 시 호출"""
        url = self.url_input.value
        guild_id = interaction.guild_id
        requester = interaction.user.display_name

        try:
            # 응답 지연 처리
            await interaction.response.defer(ephemeral=True)

            # 대기열에 추가
            added, position, title = await self.music_cog.add_to_queue(guild_id, url, requester)
            if added:
                await interaction.followup.send(
                    f"✅ **{title}**이(가) 대기열에 추가되었습니다! 현재 {position}번째입니다.",
                    ephemeral=True, delete_after=10
                )
            else:
                await interaction.followup.send(
                    "⚠️ 대기열이 가득 찼습니다! 더 이상 추가할 수 없습니다.",
                    ephemeral=True, delete_after=10
                )
        except nextcord.errors.InteractionResponded:
            # 이미 응답이 처리된 경우 예외 처리
            print("⚠️ 이미 응답이 처리되었습니다.")
        except Exception as e:
            print(f"노래 추가 중 오류 발생: {e}")
            try:
                await interaction.followup.send(
                    "❌ 노래 추가 중 문제가 발생했습니다. URL을 다시 확인해주세요!",
                    ephemeral=True, delete_after=10
                )
            except Exception as inner_exception:
                print(f"⚠️ followup 응답 실패: {inner_exception}")


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database):
        self.bot = bot
        self.database = database
        self.guild_states = {}
        self.guild_tasks = {}  # 서버별 태스크 관리 딕셔너리

    # 텍스트 채널을 안전하게 가져오는 메서드
    def get_text_channel(self, ctx_or_interaction, state):
        """
        ctx_or_interaction에서 텍스트 채널 객체를 추출하거나, 
        기존 메시지를 참조해 채널 객체를 반환합니다.
        """
        if hasattr(ctx_or_interaction, "channel"):  # Context나 Interaction에서 채널 추출
            return ctx_or_interaction.channel
        elif state and state.message_time:  # 이전 메시지의 채널을 참조
            return state.message_time.channel
        else:
            print("⚠️ 텍스트 채널 정보를 가져올 수 없습니다.")
            return None

    def get_state(self, guild_id):
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = MusicState()
        state = self.guild_states[guild_id]
        if not isinstance(state, MusicState):
            print(f"⚠️ state가 MusicState 객체가 아닙니다: {type(state)}")
        return state
    
    def start_task(self, guild_id, task_name):
        """특정 서버의 작업 시작"""
        if guild_id not in self.guild_tasks:
            self.guild_tasks[guild_id] = {}

        existing_task = self.guild_tasks[guild_id].get(task_name)
        if existing_task and not existing_task.done():
            print(f"⚠️ {guild_id}: {task_name} 태스크는 이미 실행 중입니다.")
            return  # 이미 실행 중인 경우 새로 시작하지 않음

        try:
            if task_name == "update_play_time":
                task = asyncio.create_task(self.update_play_time(guild_id))
            elif task_name == "update_lyrics":
                task = asyncio.create_task(self.update_lyrics(guild_id))
            else:
                print(f"⚠️ 알 수 없는 태스크 이름: {task_name}")
                return

            self.guild_tasks[guild_id][task_name] = task
        except Exception as e:
            print(f"⚠️ {guild_id}: {task_name} 태스크 시작 중 오류 발생: {e}")

    def stop_task(self, guild_id, task_name):
        """특정 서버의 작업 중단"""
        if guild_id in self.guild_tasks and task_name in self.guild_tasks[guild_id]:
            task = self.guild_tasks[guild_id][task_name]
            if not task.done():
                task.cancel()  # 태스크 중단
            del self.guild_tasks[guild_id][task_name]

        # 서버의 모든 태스크가 제거되면 서버 상태 제거
        if guild_id in self.guild_tasks and not self.guild_tasks[guild_id]:
            del self.guild_tasks[guild_id]

    async def _delete_previous_messages(self, guild_id):
        """이전 메시지를 삭제"""
        state = self.get_state(guild_id)

        for message in state.previous_messages:
            if message:
                try:
                    await message.delete()
                except nextcord.errors.NotFound:
                    # 메시지가 이미 삭제된 경우 로그만 출력
                    print("❌ 이전 메시지 삭제 중 오류: 메시지가 이미 삭제되었습니다.")
                except Exception as e:
                    # 기타 예외 처리
                    print(f"❌ 이전 메시지 삭제 중 오류: {e}")
        state.previous_messages = []  # 삭제 후 리스트 초기화

    def is_resource_limited(self):
        """서버 리소스 제한 확인"""
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent

        # CPU 사용률 90% 이상 또는 메모리 사용률 90% 이상일 경우 리소스 부족으로 간주
        if cpu_usage > 90 or memory_usage > 90:
            print(f"⚠️ 리소스 부족: CPU {cpu_usage}%, 메모리 {memory_usage}%")
            return True
        return False

    async def fetch_lyrics(self, url):
        """유튜브 자막 데이터 가져오기"""
        ydl_opts = {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "ko"],
            "quiet": True,
            "skip_download": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                subtitles = info.get("subtitles") or info.get("automatic_captions")

                for lang in ["ko", "en"]:  # 우선순위: 한국어 > 영어
                    if subtitles and lang in subtitles:
                        subtitle_url = subtitles[lang][0]["url"]

                        async with aiohttp.ClientSession() as session:
                            async with session.get(subtitle_url) as response:
                                raw_subtitles = await response.text()
                                return self.parse_lyrics(raw_subtitles)

                print("⚠️ 자막 데이터가 없습니다.")
                return []  # 자막이 없으면 빈 리스트 반환
        except Exception as e:
            print(f"❌ 자막 데이터 가져오기 실패: {e}")
            return []

    def parse_lyrics(self, raw_subtitles):
        """유튜브 자막 데이터를 JSON 형식에서 파싱"""
        try:
            # JSON 파싱
            subtitles_json = json.loads(raw_subtitles)
            events = subtitles_json.get("events", [])
            if not events:
                print("⚠️ 자막 이벤트가 비어 있습니다.")
                return []

            lyrics = []
            for event in events:
                start_time = event.get("tStartMs", 0) / 1000  # 밀리초를 초로 변환
                duration = event.get("dDurationMs", 0) / 1000  # 밀리초를 초로 변환
                segments = event.get("segs", [])

                # 텍스트 합치기
                text = "".join(seg.get("utf8", "") for seg in segments if "utf8" in seg)

                # 데이터 추가
                if text.strip():
                    lyrics.append({
                        "start": start_time,
                        "end": start_time + duration,
                        "text": text.strip()
                    })

            return lyrics
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 파싱 실패: {e}")
            return []

    async def _get_song_info(self, url):
        """URL에서 곡 정보를 추출"""
        ydl_opts = {"quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "알 수 없는 제목"),
                    "duration": str(timedelta(seconds=info.get("duration", 0))),
                    "requester": "알 수 없음",  # 요청자 정보를 저장하지 않는 경우 기본값
                }
            except Exception as e:
                print(f"곡 정보 추출 실패: {e}")
                return {"title": "정보 없음", "duration": "알 수 없음", "requester": "알 수 없음"}

    async def add_to_queue(self, guild_id, url, requester):
        """대기열에 곡 추가 (최대 20개 제한)"""
        queue_count = await self.database.get_queue_count(guild_id)
        if queue_count >= 20:
            return False, queue_count, None  # 대기열이 가득 찬 경우

        # URL에서 제목 추출
        ydl_opts = {"quiet": True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "알 수 없는 제목")
        except Exception as e:
            print(f"곡 정보 추출 실패: {e}")
            title = "알 수 없는 제목"

        # 데이터베이스에 추가
        await self.database.add_song(guild_id, url, title, requester)
        return True, queue_count + 1, title

    @commands.command(name="노래")
    async def play_song(self, ctx, url: str):
        guild_id = ctx.guild.id
        voice_channel_id = ctx.author.voice.channel.id if ctx.author.voice else None

        # 사용자가 음성 채널에 있는지 확인
        if not ctx.author.voice:
            await ctx.send("❌ 먼저 음성 채널에 들어가 주세요!", delete_after=10)
            return

        try:
            await ctx.message.delete()  # 사용자가 보낸 명령어 삭제
        except Exception as e:
            print(f"⚠️ 명령어 삭제 중 오류 발생: {e}")

        # URL 파싱 및 'v' 쿼리만 추출
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # 'v' 파라미터만 유지
        if "v" not in query_params:
            await ctx.send("❌ 유효하지 않은 URL입니다! 다시 입력해주세요.", delete_after=10)
            return

        filtered_query = urllib.parse.urlencode({"v": query_params["v"][0]})
        url = urllib.parse.urlunparse(parsed_url._replace(query=filtered_query))

        # 메인 봇 상태 확인
        state = self.get_state(guild_id)

        # 재생 상태 초기화
        if not state.voice_client or not state.voice_client.is_connected():
            state.is_playing = False
            state.is_paused = False

        # 서브봇 상태 확인
        is_subbot_in_use = False
        try:
            response = requests.get("http://localhost:5001/status")
            if response.status_code == 200:
                subbot_data = response.json()
                if subbot_data.get("status") == "success":
                    subbot_states = subbot_data.get("data", {})
                    is_subbot_in_use = any(
                        state.get("is_playing", False) or state.get("voice_channel_id") == voice_channel_id
                        for state in subbot_states.values()
                    )
        except Exception as e:
            print(f"⚠️ 서브봇 상태 확인 중 오류 발생: {e}")

        # 모든 봇이 사용 중인지 확인
        if state.voice_client and state.voice_client.is_connected():
            if state.voice_client.channel.id != voice_channel_id:
                # 메인봇이 다른 채널에 있고, 노래를 재생 중이거나 일시 정지 상태라면 서브봇 요청
                if state.is_playing or state.is_paused:
                    if is_subbot_in_use:
                        await ctx.send("⚠️ 현재 모든 봇이 사용 중입니다. 잠시 후 다시 시도해주세요.", delete_after=10)
                        return
                    else:
                        # 서브봇으로 요청
                        await ctx.send("🔄 서브봇에 요청 중...", delete_after=10)
                        payload = {
                            "guild_id": guild_id,
                            "voice_channel_id": voice_channel_id,
                            "text_channel_id": ctx.channel.id,
                            "url": url,
                            "requester": ctx.author.display_name,
                        }
                        try:
                            subbot_response = requests.post("http://localhost:5001/play", json=payload)
                            if subbot_response.status_code == 200:
                                await ctx.send("✅ 서브봇이 요청을 처리 중입니다!", delete_after=10)
                            else:
                                await ctx.send(f"⚠️ 서브봇 요청 실패: {subbot_response.status_code}", delete_after=10)
                        except Exception as e:
                            print(f"⚠️ 서브봇 요청 중 오류 발생: {e}")
                            await ctx.send("❌ 서브봇 요청 중 오류가 발생했습니다.", delete_after=10)
                        return
                else:
                    # 메인봇이 대기 상태라면 새 채널로 이동 후 요청 처리
                    await state.voice_client.disconnect()
                    state.voice_client = None


        # 메인봇이 연결되어 있지 않으면 새로 연결
        if not state.voice_client or not state.voice_client.is_connected():
            try:
                state.voice_client = await ctx.author.voice.channel.connect()
            except Exception as e:
                print(f"⚠️ 음성 채널 연결 중 오류 발생: {e}")
                await ctx.send("❌ 음성 채널에 연결할 수 없습니다. 다시 시도해주세요!", delete_after=10)
                return

            # 연결 후 바로 음악 재생
            await self._play_audio(ctx, guild_id, url)
            return
        
        # 같은 채널에서 재생 상태 초기화 후 음악 재생
        if not state.is_playing and not state.is_paused:
            await self._play_audio(ctx, guild_id, url)
            return

        # 메인봇, 서브봇 모두 처리 불가능한 경우
        await ctx.send("⚠️ 현재 모든 봇이 사용 중입니다. 잠시 후 다시 시도해주세요.", delete_after=10)

    async def _play_audio(self, ctx_or_interaction, guild_id, url):
        """음악 재생"""
        state = self.get_state(guild_id)

        if hasattr(self, "_is_playing_audio") and self._is_playing_audio:
            print("🔄 이미 재생 중입니다. 중복 호출을 방지합니다.")
            return

        self._is_playing_audio = True  # 재생 시작 플래그 설정

        try:
            # 음성 채널 연결 확인 및 연결 시도
            if not state.voice_client or not state.voice_client.is_connected():
                try:
                    state.voice_client = await ctx_or_interaction.author.voice.channel.connect()
                    print(f"🔊 음성 채널에 연결되었습니다: {state.voice_client.channel}")
                except AttributeError:
                    await self._send_error_message(ctx_or_interaction, "음성 채널에 연결할 수 없습니다! 음성 채널에 먼저 들어가 주세요.")
                    return
                except Exception as e:
                    print(f"⚠️ 음성 채널 연결 중 오류 발생: {e}")
                    await self._send_error_message(ctx_or_interaction, "음성 채널에 연결 중 오류가 발생했습니다.")
                    return

            # 이미 오디오가 재생 중인지 확인
            if state.voice_client and state.voice_client.is_playing():
                print("🔊 이미 오디오가 재생 중입니다. 중복 재생을 방지합니다.")
                return

            # YouTube 데이터 가져오기
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "postprocessors": [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
                ],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    audio_url = info.get("url")
                    if not audio_url:
                        raise ValueError("오디오 URL을 가져오지 못했습니다.")

                    title = info.get("title", "알 수 없는 제목")
                    thumbnail = info.get("thumbnail", None)
                    duration = info.get("duration", 0)
                    state.total_duration = duration

                    print(f"🎶 재생 준비 완료: {title}")

                    # 자막 가져오기
                    state.current_lyrics = await self.fetch_lyrics(url)
                    if not state.current_lyrics:
                        print("⚠️ 가사 데이터를 가져오지 못했습니다.")
                except Exception as e:
                    print(f"음악 재생 중 오류: {e}")
                    await self._send_error_message(ctx_or_interaction, "음악 재생 중 오류가 발생했습니다!")
                    return

            # 현재 재생 곡 정보 업데이트
            state.current_song = {
                "title": title,
                "requester": self._get_requester(ctx_or_interaction),
                "thumbnail": thumbnail,
                "duration": str(timedelta(seconds=duration)),
            }
            state.start_time = asyncio.get_event_loop().time()

            # ffmpeg을 통해 오디오 재생
            ffmpeg_options = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
            try:
                def after_play(error):
                    if error:
                        print(f"재생 중 오류 발생: {error}")
                    state.is_playing = False
                    state.is_finished = True  # 노래가 끝난 상태로 설정
                    state.current_song = None  # 현재 곡 정보 초기화
                    asyncio.run_coroutine_threadsafe(self._play_next(guild_id), self.bot.loop)

                state.voice_client.play(
                    nextcord.FFmpegPCMAudio(audio_url, **ffmpeg_options),
                    after=after_play
                )
                state.is_playing = True  # 재생 중 상태 설정
                state.is_finished = False  # 종료 상태 초기화
            except Exception as e:
                print(f"FFmpeg 오류: {e}")
                await self._send_error_message(ctx_or_interaction, "FFmpeg로 오디오를 재생하는 중 오류가 발생했습니다.")
                return

            # 임베드 생성 및 표시
            await self._send_playing_embeds(
                ctx_or_interaction=ctx_or_interaction,
                title=state.current_song["title"],
                thumbnail=state.current_song["thumbnail"],
                duration=state.total_duration
            )

            # 재생 시간 및 가사 업데이트 작업 시작
            self.start_task(guild_id, "update_play_time")
            self.start_task(guild_id, "update_lyrics")

            # 퇴장 타이머가 설정된 경우 취소
            await self.cancel_leave_timer(state)

        except Exception as e:
            print(f"⚠️ _play_audio 실행 중 오류: {e}")
        finally:
            self._is_playing_audio = False  # 플래그 해제


    async def _send_error_message(self, ctx_or_interaction, message):
        """오류 메시지 전송"""
        try:
            if hasattr(ctx_or_interaction, "send"):
                await ctx_or_interaction.send(f"❌ {message}")
            else:
                await ctx_or_interaction.response.send_message(f"❌ {message}", ephemeral=True)
        except Exception as e:
            print(f"⚠️ 오류 메시지 전송 실패: {e}")

    async def _send_playing_embeds(self, ctx_or_interaction, title, thumbnail, duration):
        """현재 재생 중인 음악 임베드 전송"""
        try:
            state = self.get_state(ctx_or_interaction.guild.id)

            # 텍스트 채널 가져오기
            channel = self.get_text_channel(ctx_or_interaction, state)
            if not channel:
                print(f"⚠️ ctx_or_interaction에서 텍스트 채널을 가져올 수 없습니다: {ctx_or_interaction}")
                return

            requester = state.current_song.get("requester", "알 수 없음")

            # 가사 임베드 생성
            embed_lyrics = nextcord.Embed(
                title="🎵현재 재생 중",
                description=f"**{title}**",
                color=nextcord.Color.red(),
            )
            embed_lyrics.add_field(name="요청자", value=f"**{requester}🎶**")
            embed_lyrics.add_field(name="가사", value="가사를 불러오는 중이에요...🎵", inline=False)

            # 재생 시간 임베드 생성
            embed_time = nextcord.Embed(color=nextcord.Color.red())
            embed_time.set_image(url=thumbnail)
            embed_time.set_footer(text=f"재생 시간: 00:00:00 / {str(timedelta(seconds=duration))}")

            # 메시지 전송
            message_lyrics = await channel.send(embed=embed_lyrics)
            message_time = await channel.send(embed=embed_time, view=MusicView(self))

            # 상태에 저장
            state.message_lyrics = message_lyrics
            state.message_time = message_time
            state.previous_messages.extend([message_lyrics, message_time])

        except Exception as e:
            print(f"⚠️ 현재 재생 중 임베드 전송 실패: {e}")

    def _get_requester(self, ctx_or_interaction):
        """요청자 정보 가져오기 (서버 닉네임)"""
        if hasattr(ctx_or_interaction, "author"):  # Text-based 명령어 (commands.Context)
            member = ctx_or_interaction.guild.get_member(ctx_or_interaction.author.id)
            return member.nick or member.name if member else ctx_or_interaction.author.name
        elif hasattr(ctx_or_interaction, "user"):  # Interaction (Buttons, Slash Commands 등)
            member = ctx_or_interaction.guild.get_member(ctx_or_interaction.user.id)
            return member.nick or member.name if member else ctx_or_interaction.user.name
        return "알 수 없음"
    
    async def _play_next(self, guild_id, ctx_or_interaction=None):
        """다음 곡 재생"""
        state = self.get_state(guild_id)
    
        if not state:
            print(f"⚠️ MusicState를 가져오지 못했습니다: guild_id={guild_id}")
            return
    
        if state._is_playing_next:
            return
    
        state._is_playing_next = True
    
        try:
            if state.voice_client and state.voice_client.is_playing():
                print("🔊 현재 곡이 재생 중입니다. 다음 곡 재생을 대기합니다.")
                return
    
            # 이전 메시지 삭제
            await self._delete_previous_messages(guild_id)
    
            # 데이터베이스에서 다음 곡 가져오기
            next_song = await self.database.get_next_song(guild_id)
            if not next_song:
                print("❌ 다음 곡이 없습니다.")
                self.stop_task(guild_id, "update_play_time")
                self.stop_task(guild_id, "update_lyrics")
                state.is_playing = False
                state.is_finished = True  # 대기 상태로 전환
                await self.start_leave_timer(state)
                return
    
            # 텍스트 채널 가져오기
            channel = self.get_text_channel(ctx_or_interaction, state)
            if not channel:
                print("⚠️ 텍스트 채널을 찾을 수 없습니다. 메시지를 보낼 수 없습니다.")
                return
    
            # 곡 재생
            print(f"🎶 다음 곡 재생 준비: {next_song['title']}")
            await self._play_audio(channel, guild_id, next_song["url"])
    
        except Exception as e:
            print(f"⚠️ 다음 곡 재생 중 오류 발생: {e}")
        finally:
            state._is_playing_next = False

    async def cancel_leave_timer(self, state):
        """퇴장 타이머 취소"""
        if state.leave_task:
            state.leave_task.cancel()  # 타이머 취소
            state.leave_task = None
            print("⏹️ 퇴장 타이머가 취소되었습니다.")

    async def start_leave_timer(self, state):
        """3분 후 음성 채널 떠나기"""
        if not isinstance(state, MusicState):
            print(f"⚠️ state가 MusicState 객체가 아닙니다: {type(state)}")
            return

        if state.leave_task:
            print("⏹️ 이미 퇴장 타이머가 설정되어 있습니다.")
            return  # 이미 타이머가 설정되어 있으면 새로 생성하지 않음

        async def leave_after_timeout():
            try:
                await asyncio.sleep(180)  # 3분 대기
                if state.voice_client and not state.voice_client.is_playing():
                    await state.voice_client.disconnect()
                    state.voice_client = None
                    print("⏹️ 음성 채널에서 떠났습니다.")
            except asyncio.CancelledError:
                print("⏹️ 퇴장 타이머가 취소되었습니다.")
            finally:
                state.leave_task = None  # 타이머 종료 후 초기화

        state.leave_task = asyncio.create_task(leave_after_timeout())
        print("⏹️ 퇴장 타이머가 시작되었습니다.")

    @commands.command(name="정지")
    async def stop_song(self, ctx):
        """음악 정지 명령어"""
        state = self.get_state(ctx.guild.id)

        if not state.voice_client or not state.voice_client.is_playing():
            await ctx.send("⏸️ 현재 재생 중인 음악이 없습니다!", delete_after=10)
            return

        try:
            state.voice_client.pause()
            state.is_paused = True
            state.paused_time = asyncio.get_event_loop().time()  # 정지 시점 기록

            # 재생 시간 및 가사 업데이트 태스크 중단
            self.stop_task(ctx.guild.id, "update_play_time")
            self.stop_task(ctx.guild.id, "update_lyrics")

            await ctx.send("⏸️ 음악이 멈췄습니다.", delete_after=10)
        except Exception as e:
            print(f"음악 정지 중 오류 발생: {e}")
            await ctx.send("⚠️ 음악 정지 중 오류가 발생했습니다.", delete_after=10)

    @commands.command(name="재생")
    async def resume_song(self, ctx):
        """음악 재생 명령어"""
        state = self.get_state(ctx.guild.id)

        if not state.voice_client or not state.voice_client.is_connected():
            await ctx.send("❌ 재생할 곡이 없습니다!", delete_after=10)
            return

        if state.voice_client.is_playing():
            await ctx.send("▶️ 이미 음악이 재생 중입니다!", delete_after=10)
            return

        if state.is_paused:
            try:
                state.voice_client.resume()
                state.is_paused = False

                # 일시정지 시간 반영
                state.paused_duration += asyncio.get_event_loop().time() - state.paused_time
                state.paused_time = None

                # 태스크 재시작
                self.start_task(ctx.guild.id, "update_play_time")
                self.start_task(ctx.guild.id, "update_lyrics")

                await ctx.send("▶️ 음악 재생을 재개합니다.", delete_after=10)
            except Exception as e:
                print(f"⚠️ 음악 재생 중 오류 발생: {e}")
                await ctx.send("⚠️ 음악 재생 중 오류가 발생했습니다. 다시 시도해주세요!", delete_after=10)

    @commands.command(name="스킵")
    async def skip_song(self, ctx_or_interaction):
        """다음 곡으로 스킵"""
        guild_id = ctx_or_interaction.guild.id
        state = self.get_state(guild_id)
        
        try:
            # Interaction 응답 처리
            if isinstance(ctx_or_interaction, Interaction) and not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.defer()
    
            # 현재 곡 중지
            if state.voice_client and state.voice_client.is_playing():
                state.voice_client.stop()
    
            # 다음 곡 재생
            await self._play_next(guild_id, ctx_or_interaction)
        except Exception as e:
            print(f"⚠️ 스킵 처리 중 오류 발생: {e}")
            if isinstance(ctx_or_interaction, Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.defer()
                await ctx_or_interaction.followup.send(
                    "❌ 스킵 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                    ephemeral=True
                )
            else:
                await ctx_or_interaction.send("❌ 스킵 처리 중 오류가 발생했습니다. 다시 시도해주세요.")

    @commands.command(name="대기열")
    async def show_queue(self, ctx):
        """대기열을 임베드 형식으로 출력"""
        queue = await self.get_queue(ctx.guild.id)
        if not queue:
            await ctx.send("🎶 대기 중인 노래가 없어요! 뭔가 틀어볼까요? 🎧", delete_after=10)
            return

        embed = nextcord.Embed(title="현재 대기열", color=nextcord.Color.red())
        for i, song in enumerate(queue[:20]):  # 최대 20곡 표시
            embed.add_field(
                name=f"{i + 1}. {song['title']}",
                value=f"**요청자**: {song['requester']}",
                inline=False
            )
        embed.set_footer(text=f"총 {len(queue)}개의 곡이 대기 중")
        await ctx.send(embed=embed, delete_after=10)
        
    async def get_queue(self, guild_id):
        """
        대기열 조회
        """
        return await self.database.get_queue(guild_id)  # self.database를 통해 대기열 정보 가져오기

    async def update_play_time(self, guild_id):
        """재생 시간 업데이트"""
        state = self.get_state(guild_id)

        try:
            while True:
                if not state.voice_client or not state.voice_client.is_playing():
                    print(f"⏹️ {guild_id}의 update_play_time 태스크 중단: VoiceClient 없음.")
                    break

                # 일시정지 시간을 고려한 경과 시간 계산
                elapsed_seconds = int(asyncio.get_event_loop().time() - state.start_time - state.paused_duration)
                elapsed_formatted = str(timedelta(seconds=elapsed_seconds))
                total_duration_seconds = int(state.total_duration)
                total_duration_formatted = str(timedelta(seconds=total_duration_seconds))

                embed_time = nextcord.Embed(color=nextcord.Color.red())
                if state.current_song.get("thumbnail"):
                    embed_time.set_image(url=state.current_song["thumbnail"])
                embed_time.set_footer(text=f"⏱️ 재생시간: {elapsed_formatted} / {total_duration_formatted}")

                if state.message_time:
                    try:
                        await state.message_time.edit(embed=embed_time, view=MusicView(self))
                    except nextcord.errors.NotFound:
                        print("❌ 메시지를 찾을 수 없습니다. 업데이트 중단.")
                        state.message_time = None  # 메시지 참조 제거

                await asyncio.sleep(1)  # 1초마다 업데이트
        except Exception as e:
            print(f"⚠️ {guild_id}의 재생 시간 업데이트 중 오류 발생: {e}")


    async def update_lyrics(self, guild_id):
        """가사 업데이트"""
        state = self.get_state(guild_id)

        try:
            while True:
                if not state.voice_client or not state.voice_client.is_playing():
                    print(f"⏹️ {guild_id}의 update_lyrics 태스크 중단: VoiceClient 없음.")
                    break

                # 일시정지 시간을 고려한 현재 시간 계산
                delay_time = 1.0
                current_time = (asyncio.get_event_loop().time() - state.start_time - state.paused_duration) - delay_time
                current_lyric = next(
                    (lyric["text"] for lyric in state.current_lyrics if lyric["start"] <= current_time <= lyric["end"]),
                    "현재 표시할 자막이 없습니다."
                )

                embed_lyrics = nextcord.Embed(
                    title="🎵현재 재생 중",
                    description=f"**{state.current_song['title']}**" if state.current_song else "알 수 없는 제목",
                    color=nextcord.Color.red(),
                )
                embed_lyrics.add_field(name="요청자", value=f"**{state.current_song.get('requester', '알 수 없음')}🎶**")
                embed_lyrics.add_field(name="가사", value=current_lyric, inline=False)

                if state.message_lyrics:
                    await state.message_lyrics.edit(embed=embed_lyrics)

                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"⚠️ {guild_id}의 가사 업데이트 중 오류 발생: {e}")

def setup(bot: commands.Bot):
    database = Database("music_queue.db")
    music_cog = MusicCog(bot, database)  # MusicCog 인스턴스 생성
    music_cog.play_song = None
    bot.add_cog(music_cog)               # Cog 추가
