import nextcord
from nextcord.ext import commands
from nextcord.ui import Button, View, Modal, TextInput
from utils.auth_db import Database
from services.lostark_api import fetch_character_siblings, fetch_character_profile
from datetime import datetime


class AuthModal(Modal):
    def __init__(self, bot, member, log_channel_id):
        super().__init__(title="로스트아크 인증하기")
        self.bot = bot
        self.member = member
        self.log_channel_id = log_channel_id

        self.nickname_input = TextInput(
            label="로스트아크 닉네임을 입력해주세요",
            placeholder="예: 슬레이어킹",
            required=True,
            max_length=30
        )
        self.add_item(self.nickname_input)

    async def callback(self, interaction: nextcord.Interaction):
        nickname = self.nickname_input.value.strip()
        guild = interaction.guild

        try:
            # 이미 인증된 멤버인지 확인
            existing_roles = [
                role.name for role in self.member.roles
                if role.name not in ["@everyone"]
            ]
            if existing_roles:
                await interaction.response.send_message(
                    "⚠️ 이미 원정대가 인증되었습니다! 다시 시도할 필요는 없어요~ 😉",
                    ephemeral=True
                )
                return

            siblings = await fetch_character_siblings(nickname)
            profile = await fetch_character_profile(nickname)

            if not siblings or not profile:
                await interaction.response.send_message(
                    "❌ 어라? 잘못된 닉네임입니다! 올바른 로스트아크 닉네임을 입력해주세요~ 😅",
                    ephemeral=True
                )
                return

            main_character = profile.get("CharacterName", "알 수 없음")
            server_name = profile.get("ServerName", "알 수 없음")
            character_class = profile.get("CharacterClassName", "알 수 없음")

            role_server = nextcord.utils.get(guild.roles, name=server_name)
            role_class = nextcord.utils.get(guild.roles, name=character_class)

            if not role_server:
                role_server = await guild.create_role(name=server_name)
            if not role_class:
                role_class = await guild.create_role(name=character_class)

            # 기존 역할 제거
            for role in self.member.roles:
                if role.name != "@everyone":
                    await self.member.remove_roles(role)

            # 역할 부여
            await self.member.add_roles(role_server, role_class)

            # 별명 변경
            try:
                await self.member.edit(nick=nickname)
            except nextcord.Forbidden:
                await interaction.response.send_message(
                    "⚠️ 봇에게 '별명 변경' 또는 '역할 관리' 권한이 없어요! 관리자님, 저 좀 도와주세요~ 🙏",
                    ephemeral=True
                )
                return

            # 인증 성공 메시지
            await interaction.response.send_message(
                f"🎉 '{nickname}' 님의 원정대가 성공적으로 인증되었습니다!\n"
                f"별명이 '{nickname}'으로 변경되었어요~ 😎\n"
                f"부여된 역할: [{server_name}], [{character_class}]",
                ephemeral=True
            )

            # 로그 채널에 기록
            if self.log_channel_id:
                log_channel = guild.get_channel(self.log_channel_id)
                if log_channel:
                    embed = nextcord.Embed(
                        title="📋 로그 기록",
                        description=(
                            f"**닉네임**: {nickname}\n"
                            f"**날짜**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                            f"**부여된 역할**: [{server_name}], [{character_class}]"
                        ),
                        color=nextcord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    await log_channel.send(embed=embed)

        except nextcord.Forbidden:
            await interaction.response.send_message(
                "⚠️ 봇에게 '별명 변경' 또는 '역할 관리' 권한이 없어요! 관리자님, 저 좀 도와주세요~ 🙏",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"⚠️ 인증 처리 중 오류가 발생했습니다: {e}",
                ephemeral=True
            )
            print(f"[ERROR] 인증 처리 중 오류: {e}")


class AuthView(View):
    def __init__(self, bot, guild_id, log_channel_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
        self.log_channel_id = log_channel_id

        button = Button(
            label="원정대 인증하기",
            style=nextcord.ButtonStyle.primary,
            custom_id=f"auth_button_{guild_id}"
        )
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction: nextcord.Interaction):
        modal = AuthModal(self.bot, interaction.user, self.log_channel_id)
        await interaction.response.send_modal(modal)


class AuthCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

        # Persistent View 복구
        self.bot.loop.create_task(self.restore_views())

    async def restore_views(self):
        """봇 재시작 후 Persistent View 복구"""
        await self.bot.wait_until_ready()
        for guild_id in self.db.get_all_guild_ids():
            log_channel_id = self.db.get_log_channel(guild_id)
            self.bot.add_view(AuthView(self.bot, guild_id, log_channel_id))

    @commands.command(name="인증활성화")
    @commands.has_permissions(administrator=True)
    async def enable_auth(self, ctx):
        """현재 채널에서 원정대 인증 활성화"""
        self.db.set_auth_channel(ctx.guild.id, ctx.channel.id)

        log_channel_id = self.db.get_log_channel(ctx.guild.id)
        view = AuthView(self.bot, ctx.guild.id, log_channel_id)
        await ctx.message.delete()
        await ctx.send(
            content="✅ **밑에 버튼을 눌러 원정대를 인증해주세요.**",
            view=view
        )

    @commands.command(name="로그채널설정")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: nextcord.TextChannel = None):
        """로그 채널 설정"""
        if channel is None:
            await ctx.send("⚠️ 로그 채널을 지정해주세요. 예: `!로그채널설정 #로그채널`")
            return

        try:
            self.db.set_log_channel(ctx.guild.id, channel.id)
            await ctx.send(f"✅ 로그 채널이 {channel.mention}으로 설정되었습니다.")
        except Exception as e:
            await ctx.send(f"⚠️ 로그 채널 설정 중 오류가 발생했습니다: {e}")

    @commands.command(name="인증비활성화")
    @commands.has_permissions(administrator=True)
    async def disable_auth(self, ctx):
        """원정대 인증 비활성화"""
        self.db.remove_auth_channel(ctx.guild.id)
        await ctx.send("❌ 인증이 비활성화되었습니다.", delete_after=10)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """새로운 멤버가 서버에 들어왔을 때 환영 메시지 전송"""
        channel_id = self.db.get_auth_channel(member.guild.id)
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        welcome_message = await channel.send(
            content=(
                f"👋 환영합니다, {member.mention}!\n"
                "로스트아크 관련 역할을 받으려면 이 채널에서 원정대를 인증해주세요!\n"
                "원정대 인증 후 자동으로 적합한 역할이 부여되고, 별명이 로스트아크 닉네임으로 변경됩니다~ 🎮"
            )
        )
        # 5분 후 메시지 삭제
        await welcome_message.delete(delay=300)


def setup(bot):
    bot.add_cog(AuthCog(bot))