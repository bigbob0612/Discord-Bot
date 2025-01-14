import nextcord
from nextcord.ext import commands
from utils.vote_db import VoteDatabase
from nextcord import ButtonStyle, Interaction
from nextcord.ui import Button, View
import datetime
import psutil

class VoteButton(Button):
    def __init__(self, label, choice, vote_cog, user_id, channel_id, is_secret):
        super().__init__(label=label, style=ButtonStyle.primary)
        self.choice = choice
        self.vote_cog = vote_cog
        self.user_id = user_id
        self.channel_id = channel_id
        self.is_secret = is_secret

    async def callback(self, interaction: Interaction):
        user_id = interaction.user.id

        # 유저가 이미 투표했는지 확인
        if self.vote_cog.db.has_voted(self.channel_id, user_id):
            await interaction.response.send_message("❌ 이미 투표를 하셨습니다.", ephemeral=True)
            return

        # 투표 저장
        self.vote_cog.db.cast_vote(self.channel_id, user_id, self.choice)

        # 비밀 투표 여부에 따른 응답
        if self.is_secret:
            await interaction.response.send_message("🗳️ 비밀리에 투표가 완료되었습니다! 🤫", ephemeral=True)
        else:
            await interaction.response.send_message(f"🗳️ {interaction.user.name}님이 '{self.choice}'에 투표했습니다! 🎉", ephemeral=False)

class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = VoteDatabase()

    @commands.command(name="투표채널생성")
    async def create_vote_channel(self, ctx, channel_name: str):
        """투표 채널 생성"""
        guild = ctx.guild
        overwrites = {
            guild.default_role: nextcord.PermissionOverwrite(read_messages=True),
            guild.me: nextcord.PermissionOverwrite(read_messages=True)
        }
        channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
        self.db.add_vote_channel(channel.id)
        await ctx.send(f"🎉 '{channel_name}' 채널이 생성되었습니다! 이제 이 채널에서 투표를 설정하세요.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """투표 채널에서 사용자가 친 메시지 자동 삭제"""
        if self.db.is_vote_channel(message.channel.id):
            if message.author != self.bot.user:
                await message.delete()

    @commands.command(name="투표설정")
    async def create_vote(self, ctx, vote_type: str, title: str, end_time: str, participants: str, *choices):
        """투표 설정"""
        if not self.db.is_vote_channel(ctx.channel.id):
            await ctx.send("❌ 이 채널에서는 투표를 설정할 수 없습니다.")
            return

        # 이미 진행 중인 투표가 있는지 확인
        active_vote = self.db.get_active_vote(ctx.channel.id)
        if active_vote:
            await ctx.send("❌ 이미 진행 중인 투표가 있습니다. 기존 투표를 종료한 후 새로운 투표를 설정하세요.")
            return

        # 투표 유형 확인
        if vote_type not in ["일반", "비밀"]:
            await ctx.send("❌ 올바른 투표 유형을 입력하세요 (일반/비밀).")
            return

        # 선택지 개수 확인
        if len(choices) < 2 or len(choices) > 5:
            await ctx.send("❌ 선택지는 최소 2개, 최대 5개여야 합니다.")
            return

        # 시간 확인
        try:
            end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M")
        except ValueError:
            await ctx.send("❌ 시간 형식이 잘못되었습니다. (예: 2023-12-01 18:00)")
            return

        # DB에 투표 생성
        self.db.create_vote(ctx.channel.id, title, vote_type, end_time.isoformat(), participants, choices)

        # 버튼 기반 View 생성
        view = View()
        for index, choice in enumerate(choices, start=1):
            emoji = f"{index}\N{COMBINING ENCLOSING KEYCAP}"  # 1️⃣, 2️⃣, ...
            button = VoteButton(label=f"{emoji} {choice}", choice=choice, vote_cog=self, user_id=None, channel_id=ctx.channel.id, is_secret=(vote_type == "비밀"))
            view.add_item(button)

        # 투표 임베드 출력
        embed = nextcord.Embed(
            title=f"📋 투표 제목: {title}",
            description=(
                f"⏳ 투표 시간: {end_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"👥 참여 인원: {participants}\n\n"
                "선택지:\n" + "\n".join([f"{emoji} {choice}" for emoji, choice in zip([f"{i}\N{COMBINING ENCLOSING KEYCAP}" for i in range(1, len(choices)+1)], choices)])
            ),
            color=nextcord.Color.red(),
        )

        await ctx.send(embed=embed, view=view)

    @commands.command(name="투표참여")
    async def vote(self, ctx, choice_number: int):
        """투표 참여"""
        if not self.db.is_vote_channel(ctx.channel.id):
            await ctx.send("❌ 이 채널에서는 투표에 참여할 수 없습니다.")
            return

        active_vote = self.db.get_active_vote(ctx.channel.id)
        if not active_vote:
            await ctx.send("❌ 현재 진행 중인 투표가 없습니다.")
            return

        choices = active_vote["choices"]
        if choice_number < 1 or choice_number > len(choices):
            await ctx.send(f"❌ 선택지는 1부터 {len(choices)}까지의 숫자여야 합니다.")
            return

        user_id = ctx.author.id
        if self.db.has_voted(ctx.channel.id, user_id):
            await ctx.send("❌ 이미 투표하셨습니다. '투표수정' 명령어를 사용해 투표를 변경하세요.")
            return

        choice = choices[choice_number - 1]
        self.db.cast_vote(ctx.channel.id, user_id, choice)

        if active_vote["vote_type"] == "일반":
            await ctx.send(f"🗳️ {ctx.author.display_name}님이 '{choice}'에 투표했습니다! 🎮")
        else:
            await ctx.send(f"🗳️ {ctx.author.display_name}님이 비밀리에 투표했습니다! 🤫")

    @commands.command(name="투표수정")
    async def modify_vote(self, ctx, choice_number: int):
        """투표 수정"""
        if not self.db.is_vote_channel(ctx.channel.id):
            await ctx.send("❌ 이 채널에서는 투표를 수정할 수 없습니다.")
            return

        active_vote = self.db.get_active_vote(ctx.channel.id)
        if not active_vote:
            await ctx.send("❌ 현재 진행 중인 투표가 없습니다.")
            return

        choices = active_vote["choices"]
        if choice_number < 1 or choice_number > len(choices):
            await ctx.send(f"❌ 선택지는 1부터 {len(choices)}까지의 숫자여야 합니다.")
            return

        user_id = ctx.author.id
        if not self.db.has_voted(ctx.channel.id, user_id):
            await ctx.send("❌ 아직 투표하지 않았습니다. '투표참여' 명령어로 먼저 투표하세요.")
            return

        choice = choices[choice_number - 1]
        self.db.modify_vote(ctx.channel.id, user_id, choice)

        if active_vote["vote_type"] == "일반":
            await ctx.send(f"✏️ {ctx.author.display_name}님이 자신의 선택을 '{choice}'로 수정했습니다! ✨")
        else:
            await ctx.send(f"✏️ {ctx.author.display_name}님이 자신의 선택을 비밀리에 수정했습니다! ✨")
    
    @commands.command(name="투표종료")
    async def end_vote(self, ctx):
        """관리자가 강제로 투표를 종료하거나 자동 종료 조건 확인"""
        active_vote = self.db.get_active_vote(ctx.channel.id)
        if not active_vote:
            await ctx.send("❌ 현재 진행 중인 투표가 없습니다.")
            return

        # 모든 사용자 수 (봇 제외)
        total_members = len([member for member in ctx.channel.members if not member.bot])
        participants = active_vote["participants"]
        total_votes = self.db.count_total_votes(ctx.channel.id)

        # 투표 강제 종료
        self.db.deactivate_vote(ctx.channel.id)

        # 메시지 구성
        if participants == "전체" and total_votes >= total_members:
            message = "✅ 모든 인원이 투표를 완료했습니다! 이제 결과를 확인해볼까요? 🎉"
        elif participants != "전체" and total_votes >= int(participants):
            message = "✅ 모든 지정된 인원이 투표를 완료했습니다! 이제 결과를 확인해볼까요? 🎉"
        else:
            message = "✅ 투표가 강제로 종료되었습니다. 결과를 확인해보세요! 🎉"

        await ctx.send(message)

    @commands.command(name="투표결과")
    async def vote_results(self, ctx):
        """현재 투표 결과를 보여줍니다 (일반/비밀 구분)"""
        ended_vote = self.db.get_latest_vote(ctx.channel.id)
        if not ended_vote:
            await ctx.send("❌ 이 채널에서 종료된 투표가 없습니다.")
            return

        vote_type = ended_vote["vote_type"]
        results = self.db.get_vote_results(ctx.channel.id)
        if not results:
            await ctx.send("❌ 아직 투표가 진행되지 않았습니다.")
            return

        # 사용자 ID를 닉네임으로 변환
        results_with_names = []
        for user_id, choice in results:
            user = ctx.guild.get_member(user_id)  # 서버에서 사용자 객체 가져오기
            username = user.display_name if user else f"Unknown ({user_id})"
            results_with_names.append((username, choice))

        if vote_type == "일반":
            embed = self._generate_public_results_embed(ended_vote, results_with_names)
        else:
            embed = self._generate_secret_results_embed(ended_vote, results)

        await ctx.send(embed=embed)

    def _generate_public_results_embed(self, vote, results_with_names):
        """일반 투표 결과를 임베드로 생성"""
        embed = nextcord.Embed(
            title=f"📊 일반 투표 결과: {vote['title']}",
            color=nextcord.Color.red(),
        )
        description = ""
        for voter, choice in results_with_names:
            description += f"**[{voter}]**: {choice}\n"
        embed.description = description.strip()

        # 최종 결과 계산
        choice_counts = self.db.get_choice_counts(vote["channel_id"])
        winner = max(choice_counts, key=lambda x: x[1])[0]
        embed.add_field(name="🎉 최종 결과", value=f"'{winner}'입니다! 🏆")

        return embed

    def _generate_secret_results_embed(self, vote, results):
        """비밀 투표 결과를 임베드로 생성"""
        embed = nextcord.Embed(
            title=f"📊 비밀 투표 결과: {vote['title']}",
            color=nextcord.Color.red(),
        )
        choice_counts = self.db.get_choice_counts(vote["channel_id"])
        description = ""
        for choice, count in choice_counts:
            description += f"**{choice}**: {count} 표\n"
        embed.description = description.strip()

        # 최종 결과 계산
        winner = max(choice_counts, key=lambda x: x[1])[0]
        embed.add_field(name="🎉 최종 결과", value=f"'{winner}'입니다! 🏆")

        return embed

    @commands.command(name="투표초기화")
    @commands.has_permissions(manage_channels=True)  # 관리자 권한 체크
    async def reset_vote(self, ctx):
        """
        투표를 초기화하고 채널의 모든 메시지를 삭제합니다.
        """
        if not self.db.is_vote_channel(ctx.channel.id):
            await ctx.send("❌ 이 채널은 투표 채널로 등록되어 있지 않습니다.")
            return

        # 데이터베이스에서 해당 채널의 투표 삭제
        self.db.delete_votes_in_channel(ctx.channel.id)

        # 채널 메시지 삭제
        await ctx.channel.purge()

        # 초기화 메시지 전송
        await ctx.send("🔄 투표가 초기화되었고 모든 메시지가 삭제되었습니다. 새로운 투표를 시작할 수 있습니다! 🎉")

    @commands.command(name="리소스체크")
    async def resource_check(self, ctx):
        """
        서버 리소스를 체크하고 부족할 경우 경고 메시지를 출력합니다.
        """
        # CPU, 메모리, 디스크 사용률 가져오기
        cpu_usage = psutil.cpu_percent(interval=1)  # CPU 사용률 (1초 평균)
        memory = psutil.virtual_memory()  # 메모리 상태
        disk = psutil.disk_usage('/')  # 디스크 상태

        # 임계값 설정
        cpu_threshold = 90  # CPU 사용률 85% 이상 경고
        memory_threshold = 90  # 메모리 사용률 85% 이상 경고
        disk_threshold = 90  # 디스크 사용률 90% 이상 경고

        # 리소스 상태 분석
        if (
            cpu_usage > cpu_threshold or
            memory.percent > memory_threshold or
            disk.percent > disk_threshold
        ):
            # 리소스 부족 경고
            await ctx.send("⚠️ 서버 리소스가 부족해요... 잠깐 쉬었다가 다시 시도해주세요~ 😓")
        else:
            # 리소스 양호 상태
            await ctx.send("✅ 서버 리소스 상태가 양호합니다!")

def setup(bot):
    bot.add_cog(VoteCog(bot))
