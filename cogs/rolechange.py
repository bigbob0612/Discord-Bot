import nextcord
from nextcord.ext import commands
from nextcord.ui import Button, View, UserSelect
from typing import Optional


class RoleChangeView(View):
    def __init__(self, embed: nextcord.Embed):
        super().__init__(timeout=None)
        self.embed = embed
        self.selected_user: Optional[nextcord.Member] = None
        self.user_select_menu = UserSelectMenu(self)

        # 구성원 선택 드롭다운
        self.add_item(self.user_select_menu)

        # 역할 변경 버튼들
        self.add_item(RoleButton("🟦 길드마스터", "길드마스터", self))
        self.add_item(RoleButton("🟩 부길드마스터", "부길드마스터", self))
        self.add_item(RoleButton("🟨 임원", "임원", self))
        self.add_item(RoleButton("🟧 길드원", "길드원", self))

        # 취소 버튼
        self.add_item(CancelButton(self))


class UserSelectMenu(UserSelect):
    def __init__(self, parent_view: RoleChangeView):
        super().__init__(
            placeholder="역할을 변경할 구성원을 선택하세요.",
            min_values=1,
            max_values=1,
        )
        self.parent_view = parent_view

    async def callback(self, interaction: nextcord.Interaction):
        try:
            selected_user = self.values[0]  # Member 객체 그대로 사용
            self.parent_view.selected_user = selected_user

            # 임베드 내용 수정
            self.parent_view.embed.description = (
                "서버 구성원의 역할을 변경하거나 추가할 수 있습니다.\n"
                "아래 메뉴를 사용해 원하는 구성원을 선택한 뒤, 역할을 지정하세요.\n\n"
                f"🔘 **현재 선택된 구성원**: {selected_user.display_name}\n"
                "🎭 **역할 목록**: [길드마스터, 부길드마스터, 임원, 길드원]\n\n"
                "🛠️ **역할 설정 방법**\n"
                "1. 구성원을 선택합니다.\n"
                "2. 변경할 역할을 클릭하여 지정합니다.\n\n"
                "**관리자 전용 기능입니다!**"
            )

            # 메시지 업데이트
            await interaction.message.edit(embed=self.parent_view.embed, view=self.parent_view)

            # 피드백 메시지 전송
            await interaction.response.send_message(
                f"✅ {selected_user.display_name} 님이 선택되었습니다.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "❌ 어라? 존재하지 않는 유저입니다! 유효한 유저를 선택해주세요~ 😅",
                ephemeral=True,
            )


class RoleButton(Button):
    def __init__(self, label: str, role_name: str, parent_view: RoleChangeView):
        super().__init__(label=label, style=nextcord.ButtonStyle.secondary)
        self.role_name = role_name
        self.parent_view = parent_view

    async def callback(self, interaction: nextcord.Interaction):
        selected_user = self.parent_view.selected_user

        if not selected_user:
            await interaction.response.send_message(
                "⚠️ 먼저 구성원을 선택해주세요.", ephemeral=True
            )
            return

        try:
            # 역할 부여/제거 로직
            guild = interaction.guild
            role = nextcord.utils.get(guild.roles, name=self.role_name)

            if not role:
                role = await guild.create_role(name=self.role_name)

            # 기존 역할 제거
            for user_role in selected_user.roles:
                if user_role.name in ["길드마스터", "부길드마스터", "임원", "길드원"]:
                    await selected_user.remove_roles(user_role)

            # 새 역할 부여
            await selected_user.add_roles(role)

            await interaction.response.send_message(
                f"✅ {selected_user.display_name} 님에게 역할 [{self.role_name}]이(가) 부여되었습니다!",
                ephemeral=True,
            )
        except nextcord.Forbidden:
            await interaction.response.send_message(
                "⚠️ 봇에게 '역할 관리' 권한이 없습니다! 관리자님, 권한을 확인해주세요~ 🙏",
                ephemeral=True,
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ 역할 변경 중 오류가 발생했습니다! 다시 시도해주세요~ 😓",
                ephemeral=True,
            )


class CancelButton(Button):
    def __init__(self, parent_view: RoleChangeView):
        super().__init__(label="❌ 변경 취소", style=nextcord.ButtonStyle.gray)
        self.parent_view = parent_view

    async def callback(self, interaction: nextcord.Interaction):
        selected_user = self.parent_view.selected_user

        # 선택 초기화
        self.parent_view.selected_user = None

        # 드롭다운 초기화 (플레이스홀더 변경 및 값 초기화)
        self.parent_view.user_select_menu.placeholder = "역할을 변경할 구성원을 선택하세요."
        self.parent_view.user_select_menu.disabled = False

        # 선택된 유저가 있는 경우, 역할 제거
        if selected_user:
            try:
                for role in selected_user.roles:
                    if role.name in ["길드마스터", "부길드마스터", "임원", "길드원"]:
                        await selected_user.remove_roles(role)
            except nextcord.Forbidden:
                await interaction.response.send_message(
                    "⚠️ 봇에게 '역할 관리' 권한이 없습니다! 관리자님, 권한을 확인해주세요~ 🙏",
                    ephemeral=True,
                )
                return

        # 임베드 초기화
        self.parent_view.embed.description = (
            "서버 구성원의 역할을 변경하거나 추가할 수 있습니다.\n"
            "아래 메뉴를 사용해 원하는 구성원을 선택한 뒤, 역할을 지정하세요.\n\n"
            "🔘 **현재 선택된 구성원**: [미선택]\n"
            "🎭 **역할 목록**: [길드마스터, 부길드마스터, 임원, 길드원]\n\n"
            "🛠️ **역할 설정 방법**\n"
            "1. 구성원을 선택합니다.\n"
            "2. 변경할 역할을 클릭하여 지정합니다.\n\n"
            "**관리자 전용 기능입니다!**"
        )

        # 메시지 업데이트
        await interaction.message.edit(embed=self.parent_view.embed, view=self.parent_view)

        # 작업 취소 메시지
        await interaction.response.send_message(
            "🛑 역할 변경이 취소되었으며, 선택된 구성원의 역할이 초기화되었습니다.", ephemeral=True
        )


class RoleChangeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="역할변경")
    @commands.has_permissions(administrator=True)
    async def change_role(self, ctx):
        """역할 변경 패널"""
        embed = nextcord.Embed(
            title="📜 **역할 변경 패널**",
            description=(
                "서버 구성원의 역할을 변경하거나 추가할 수 있습니다.\n"
                "아래 메뉴를 사용해 원하는 구성원을 선택한 뒤, 역할을 지정하세요.\n\n"
                "🔘 **현재 선택된 구성원**: [미선택]\n"
                "🎭 **역할 목록**: [길드마스터, 부길드마스터, 임원, 길드원]\n\n"
                "🛠️ **역할 설정 방법**\n"
                "1. 구성원을 선택합니다.\n"
                "2. 변경할 역할을 클릭하여 지정합니다.\n\n"
                "**관리자 전용 기능입니다!**"
            ),
            color=nextcord.Color.red(),
        )

        view = RoleChangeView(embed)
        await ctx.send(embed=embed, view=view)


def setup(bot):
    bot.add_cog(RoleChangeCog(bot))