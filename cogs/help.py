from nextcord.ext import commands
import nextcord


class HelpView(nextcord.ui.View):
    def __init__(self, commands_list, bot, per_page=5):
        super().__init__(timeout=None)
        self.commands_list = commands_list
        self.bot = bot
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(self.commands_list) - 1) // self.per_page

        # 초기 버튼 상태
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0  # 이전 버튼 비활성화 여부
        self.children[1].disabled = self.current_page == self.max_page  # 다음 버튼 비활성화 여부

    def get_page_commands(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        return self.commands_list[start:end]

    async def update_embed(self, interaction):
        embed = nextcord.Embed(
            title="📜 명령어 목록",
            description=f"페이지 {self.current_page + 1}/{self.max_page + 1}",
            color=nextcord.Color.red()
        )

        for command in self.get_page_commands():
            embed.add_field(name=command["name"], value=command["description"], inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="이전", style=nextcord.ButtonStyle.secondary)
    async def previous_page(self, button, interaction: nextcord.Interaction):
        self.current_page -= 1
        self.update_buttons()
        await self.update_embed(interaction)

    @nextcord.ui.button(label="다음", style=nextcord.ButtonStyle.secondary)
    async def next_page(self, button, interaction: nextcord.Interaction):
        self.current_page += 1
        self.update_buttons()
        await self.update_embed(interaction)


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="명령어")
    async def show_commands(self, ctx):
        """봇의 모든 명령어를 보여줍니다."""
        commands_list = [
            {"name": "!노래 [URL]", "description": "유튜브 URL의 음악을 재생하거나 대기열에 추가합니다."},
            {"name": "!정지", "description": "현재 재생 중인 음악을 멈춥니다."},
            {"name": "!재생", "description": "멈춘 음악을 다시 재생합니다."},
            {"name": "!스킵", "description": "현재 음악을 건너뛰고 다음 곡을 재생합니다."},
            {"name": "!대기열", "description": "현재 대기열에 있는 곡들을 확인합니다."},
            {"name": "!투표채널생성 [채널명]", "description": "새로운 투표 채널을 생성합니다."},
            {"name": "!사사게 [닉네임]", "description": "해당 닉네임으로 사사게 게시판을 검색합니다."},
            {"name": "!닉네임 [닉네임]", "description": "해당 닉네임의 캐릭터 정보를 확인합니다."},
            {"name": "!원정대 [닉네임]", "description": "해당 닉네임 기준으로 아이템 레벨이 높은 순으로 상위 6개의 원정대 캐릭터를 확인합니다."},
            {"name": "!일정", "description": "길드의 노션 캘린더에 등록된 레이드 일정을 디스코드에서 확인할 수 있습니다."},
            {"name": "!레이드 [날짜] [시] [분] [보스] [난이도] [숙련도]", "description": "새로운 레이드 일정을 등록합니다. \n예시) !레이드 2023-12-01 18:00 발탄 하드 숙련"},
            {"name": "!보석 [레벨] [보석종류]", "description": "입력한 보석의 레벨과 종류에 따라 경매장에서 해당 보석의 최저가를 검색합니다."},
            {"name": "!유각 [각인명]", "description": "입력한 각인명을 기준으로 경매장에서 해당 각인의 가격을 검색합니다."},
            {"name": "!유각시세", "description": "현재 경매장에서 가장 비싼 유각(각인서) 시세 상위 10개를 보여줍니다."},
            {"name": "!강화재료", "description": "현재 경매장에서 강화재료의 가장 싼 시세를 보여줍니다."},
            {"name": "!악세", "description": "악세서리와 옵션, 품질을 선택하여 경매장에서 검색합니다."},
            {"name": "!투표채널생성 [채널명]", "description": "새로운 투표 채널을 생성합니다."},
            {"name": "!투표설정 [유형] [제목] [시간] [인원] [선택지1] [선택지2]...", "description": "새로운 투표를 설정합니다. \n예시) !투표설정 일반 \"최고의 게임\" \"2023-12-03 18:00\" 전체 \"롤\" \"오버워치\" \"발로란트\""},
            {"name": "!투표참여 [선택지 번호]", "description": "현재 투표에 참여합니다."},
            {"name": "!투표수정 [선택지 번호]", "description": "자신의 투표 선택을 수정합니다."},
            {"name": "!투표종료", "description": "현재 진행 중인 투표를 강제로 종료합니다."},
            {"name": "!투표결과", "description": "현재 투표의 결과를 확인합니다."},
            {"name": "!투표초기화", "description": "현재 채널의 투표 데이터를 초기화합니다."},
            {"name": "!리소스체크", "description": "서버의 CPU 및 메모리 사용률을 확인합니다."},
            {"name": "!공략", "description": "레이드 공략 메뉴를 보여줍니다."},
            {"name": "!레이드추가 [레이드종류] [보스 이름] [링크]", "description": "새로운 레이드 공략 정보를 추가합니다."},
            {"name": "!레이드수정 [레이드종류] [보스 이름] [새로운 링크]", "description": "기존 레이드 공략 정보를 수정합니다."},
            {"name": "!레이드삭제 [레이드종류] [보스 이름]", "description": "레이드 공략 정보를 삭제합니다."},
            {"name": "!문의하기", "description": "길드마스터만 볼 수 있는 1대1 문의하는 채널을 생성합니다."},
            {"name": "!문의종료", "description": "문의 채널을 종료합니다."}
        ]

        embed = nextcord.Embed(
            title="📜 명령어 목록",
            description="페이지 1/1",
            color=nextcord.Color.red()
        )

        # 첫 번째 페이지의 명령어 추가
        for command in commands_list[:5]:
            embed.add_field(name=command["name"], value=command["description"], inline=False)

        view = HelpView(commands_list, self.bot)

        await ctx.send(embed=embed, view=view)


def setup(bot: commands.Bot):
    bot.add_cog(HelpCog(bot))