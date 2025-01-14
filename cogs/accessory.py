import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Select, Button
from services.lostark_api import fetch_accessory_data

class PreviousPageButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="이전 페이지", style=nextcord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction):
        if self.parent_view.page_no > 1:
            self.parent_view.page_no -= 1
            await self.parent_view.fetch_and_display_results(interaction)


class NextPageButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="다음 페이지", style=nextcord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction):
        self.parent_view.page_no += 1
        await self.parent_view.fetch_and_display_results(interaction)

class AccessorySearchView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_accessory = None
        self.selected_quality = "70"  # 기본 품질값
        self.selected_options = ["선택해주세요"] * 3
        self.selected_type = None  # 고대, 유물 선택
        self.step = 1  # 단계 관리
        self.page_no = 1  # 페이지 번호 추가

        # 초기 메뉴 추가: 품질 선택과 악세서리 선택
        self.add_item(QualitySelectMenu(self))
        self.add_item(AccessorySelectMenu(self))

    async def fetch_and_display_results(self, interaction):
        try:
            # 유효성 검사
            valid_options = OptionSelectMenu.OPTIONS_MAP[self.selected_accessory].keys()
            invalid_options = [
                option for option in self.selected_options
                if option != "선택 안 함" and option not in valid_options
            ]
            if invalid_options:
                await interaction.response.send_message(
                    f"⚠️ 다음 옵션은 유효하지 않습니다: {', '.join(invalid_options)}",
                    ephemeral=True
                )
                return

            # 품질 변환
            item_grade_quality = int(self.selected_quality)

            # 카테고리 코드 설정
            category_code_map = {
                "목걸이": 200010,
                "귀걸이": 200020,
                "반지": 200030
            }
            category_code = category_code_map[self.selected_accessory]

            # 고대/유물 설정
            item_grade = self.selected_type if self.selected_accessory in ["목걸이", "귀걸이", "반지"] else ""

            # 옵션 매핑
            etc_options = []
            for option in self.selected_options:
                if option != "선택 안 함":
                    option_data = OptionSelectMenu.OPTIONS_MAP[self.selected_accessory][option]
                    etc_options.append({
                        "FirstOption": 7,  # 고정값
                        "SecondOption": option_data["SecondOption"],
                        "MinValue": option_data["MinValue"] or 0,
                        "MaxValue": option_data["MaxValue"] or 0,
                    })

            # API 호출
            results = await fetch_accessory_data(
                page_no=self.page_no,
                item_grade_quality=item_grade_quality,
                category_code=category_code,
                item_grade=item_grade,
                etc_options=etc_options
            )



            # 결과 처리
            items = results.get("Items", [])
            if not items:
                embed = nextcord.Embed(
                    title=f":mag: 검색 결과 (페이지 {self.page_no})",
                    description=":x: 해당 조건에 맞는 아이템이 없습니다.",
                    color=nextcord.Color.red()
                )
                self.clear_items()
                self.add_item(PreviousPageButton(self))
                self.add_item(NextPageButton(self))

                # 메시지 업데이트
                if interaction.response.is_done():
                    await interaction.followup.edit_message(self.message.id, embed=embed, view=self)
                else:
                    await interaction.response.edit_message(embed=embed, view=self)
                return

            # 결과를 임베드로 표시
            embed = nextcord.Embed(
                title=f":mag: 검색 결과 (페이지 {self.page_no})",
                description="",
                color=nextcord.Color.red()
            )
            for item in items[:10]:  # 상위 10개 아이템만 표시
                # 옵션 정보 문자열 생성
                options_text = ""
                for option in item['Options']:
                    if option['Type'] == 'ACCESSORY_UPGRADE':
                        if option['IsValuePercentage']:  # True 조건
                            options_text += f"{option['OptionName']} {option['Value']}%\n"
                        else:
                            options_text += f"{option['OptionName']} +{option['Value']}\n"

                # Embed 필드 추가
                embed.add_field(
                    name=f"\u200b\n[{item['Grade']}] {item['Name']}",
                    value=(
                        f"입찰가: {item['AuctionInfo']['StartPrice']} 구매가: {item['AuctionInfo']['BuyPrice']}\n"
                        f"품질: {item['GradeQuality']}\n"
                        f"{options_text.strip()}\n" # 옵션 정보 추가
                    ),
                    inline=False
                )

            # View 업데이트 (페이지 버튼 포함)
            self.clear_items()
            self.add_item(PreviousPageButton(self))
            self.add_item(NextPageButton(self))

            # 메시지 업데이트
            if interaction.response.is_done():
                await interaction.followup.edit_message(self.message.id, embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            embed = nextcord.Embed(
                title="⚠️ 오류 발생",
                description=f"검색 중 오류가 발생했습니다: {e}",
                color=nextcord.Color.red()
            )
            if interaction.response.is_done():
                await interaction.followup.edit_message(self.message.id, embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)

    async def update_message(self, interaction):
        """단계별 임베드 메시지 업데이트"""
        embed = nextcord.Embed(color=nextcord.Color.red())

        if self.step == 1:
            embed.title = "🛠️ 어떤 악세서리를 찾고 싶으신가요?"
            embed.description = (
                "품질을 먼저 선택한 후, 원하는 악세서리를 선택하세요.\n\n"
                "1️⃣ 목걸이\n2️⃣ 귀걸이\n3️⃣ 반지\n\n"
                f"현재 선택된 품질: **{self.selected_quality}**"
            )
            self.clear_items()
            self.add_item(QualitySelectMenu(self))
            self.add_item(AccessorySelectMenu(self))

        elif self.step == 2:
            embed.title = "🛠️ 옵션을 선택하세요"
            embed.description = f"현재 선택된 악세서리: {self.selected_accessory}\n\n" \
                                "원하는 옵션을 최대 3개까지 선택할 수 있습니다."
            self.clear_items()
            for slot in range(3):
                self.add_item(OptionSelectMenu(self, slot))

        elif self.step == 3:
            embed.title = "🛠️ 고대, 유물을 선택하세요"
            embed.description = "1️⃣ 고대\n2️⃣ 유물"
            self.clear_items()
            self.add_item(AccessoryTypeSelectMenu(self))

        elif self.step == 4:
            options = [opt for opt in self.selected_options if opt != "선택 안 함"]
            embed.title = "📊 선택된 조건"
            embed.description = (
                f"선택된 악세서리: {self.selected_accessory}\n"
                f"선택된 옵션: [{', '.join(options)}]\n"
                f"품질: {self.selected_quality}\n\n"
                "해당 조건에 맞는 아이템을 검색 중입니다..."
            )
            self.clear_items()  # 마지막 단계에서 모든 드롭다운 삭제
            await self.fetch_and_display_results(interaction)
            return  # 마지막 단계에서 메시지만 갱신
    
        # 메시지와 View를 업데이트
        if interaction.message:
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.followup.send(embed=embed, view=self)

class QualitySelectMenu(Select):
    def __init__(self, parent_view):
        options = [
            nextcord.SelectOption(label="70", value="70"),
            nextcord.SelectOption(label="80", value="80"),
            nextcord.SelectOption(label="90", value="90"),
            nextcord.SelectOption(label="100", value="100"),
        ]
        super().__init__(placeholder="품질을 선택하세요 (기본값: 70)", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction):
        self.parent_view.selected_quality = self.values[0]
        await self.parent_view.update_message(interaction)


class AccessorySelectMenu(Select):
    def __init__(self, parent_view):
        options = [
            nextcord.SelectOption(label="목걸이", value="목걸이"),
            nextcord.SelectOption(label="귀걸이", value="귀걸이"),
            nextcord.SelectOption(label="반지", value="반지"),
        ]
        super().__init__(placeholder="악세서리를 선택하세요", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction):
        self.parent_view.selected_accessory = self.values[0]
        self.parent_view.step = 2

        # 다음 단계로 옵션 선택 메뉴 추가
        self.parent_view.clear_items()
        for slot in range(3):  # 드롭다운 3개 추가
            self.parent_view.add_item(OptionSelectMenu(self.parent_view, slot))
        await self.parent_view.update_message(interaction)


class OptionSelectMenu(Select):
    OPTIONS_MAP = {
        "목걸이": {
            "추가 피해(하)": {"SecondOption": 41, "MinValue": 1, "MaxValue": 8},
            "추가 피해(중)": {"SecondOption": 41, "MinValue": 9, "MaxValue": 10},
            "추가 피해(상)": {"SecondOption": 41, "MinValue": 11, "MaxValue": 11},
            "적에게 주는 피해(하)": {"SecondOption": 42, "MinValue": 1, "MaxValue": 9},
            "적에게 주는 피해(중)": {"SecondOption": 42, "MinValue": 10, "MaxValue": 11},
            "적에게 주는 피해(상)": {"SecondOption": 42, "MinValue": 12, "MaxValue": 12},
            "공격력 +(하)": {"SecondOption": 53, "MinValue": 1, "MaxValue": 10},
            "공격력 +(중)": {"SecondOption": 53, "MinValue": 11, "MaxValue": 11},
            "공격력 +(상)": {"SecondOption": 53, "MinValue": 12, "MaxValue": 12},
            "무기공격력 +(하)": {"SecondOption": 54, "MinValue": 1, "MaxValue": 9},
            "무기공격력 +(중)": {"SecondOption": 54, "MinValue": 10, "MaxValue": 11},
            "무기공격력 +(상)": {"SecondOption": 54, "MinValue": 12, "MaxValue": 12},
            "서폿 아덴 획득량(하)": {"SecondOption": 43, "MinValue": 1, "MaxValue": 9},
            "서폿 아덴 획득량(중)": {"SecondOption": 43, "MinValue": 10, "MaxValue": 11},
            "서폿 아덴 획득량(상)": {"SecondOption": 43, "MinValue": 12, "MaxValue": 12},
            "낙인력(하)": {"SecondOption": 44, "MinValue": 1, "MaxValue": 7},
            "낙인력(중)": {"SecondOption": 44, "MinValue": 8, "MaxValue": 11},
            "낙인력(상)": {"SecondOption": 44, "MinValue": 12, "MaxValue": 12},
            "최대 생명력": {"SecondOption": 55, "MinValue": None},
            "최대 마나": {"SecondOption": 56, "MinValue": None},
            "상태이상 공격 지속시간": {"SecondOption": 57, "MinValue": None},
            "전투 중 생명력 회복량": {"SecondOption": 58, "MinValue": None},
    },
    "귀걸이": {
        "공격력 %(하)": {"SecondOption": 45, "MinValue": 1, "MaxValue": 9},
        "공격력 %(중)": {"SecondOption": 45, "MinValue": 10, "MaxValue": 11},
        "공격력 %(상)": {"SecondOption": 45, "MinValue": 12, "MaxValue": 12},
        "무기공격력 %(하)": {"SecondOption": 46, "MinValue": 1, "MaxValue": 9},
        "무기공격력 %(중)": {"SecondOption": 46, "MinValue": 10, "MaxValue": 11},
        "무기공격력 %(상)": {"SecondOption": 46, "MinValue": 12, "MaxValue": 12},
        "공격력 +(하)": {"SecondOption": 53, "MinValue": 1, "MaxValue": 10},
        "공격력 +(중)": {"SecondOption": 53, "MinValue": 11, "MaxValue": 11},
        "공격력 +(상)": {"SecondOption": 53, "MinValue": 12, "MaxValue": 12},
        "무기공격력 +(하)": {"SecondOption": 54, "MinValue": 1, "MaxValue": 8},
        "무기공격력 +(중)": {"SecondOption": 54, "MinValue": 9, "MaxValue": 11},
        "무기공격력 +(상)": {"SecondOption": 54, "MinValue": 12, "MaxValue": 12},
        "파티원 회복효과": {"SecondOption": 47, "MinValue": None},
        "파티원 보호막 효과": {"SecondOption": 48, "MinValue": None},
        "최대 생명력": {"SecondOption": 55, "MinValue": None},
        "최대 마나": {"SecondOption": 56, "MinValue": None},
        "상태이상 공격 지속시간": {"SecondOption": 57, "MinValue": None},
        "전투 중 생명력 회복량": {"SecondOption": 58, "MinValue": None},
    },
    "반지": {
        "치명타 적중률(하)": {"SecondOption": 49, "MinValue": 1, "MaxValue": 9},
        "치명타 적중률(중)": {"SecondOption": 49, "MinValue": 10, "MaxValue": 11},
        "치명타 적중률(상)": {"SecondOption": 49, "MinValue": 12, "MaxValue": 12},
        "치명타 피해(하)": {"SecondOption": 50, "MinValue": 1, "MaxValue": 9},
        "치명타 피해(중)": {"SecondOption": 50, "MinValue": 10, "MaxValue": 11},
        "치명타 피해(상)": {"SecondOption": 50, "MinValue": 12, "MaxValue": 12},
        "공격력 +(하)": {"SecondOption": 53, "MinValue": 1, "MaxValue": 10},
        "공격력 +(중)": {"SecondOption": 53, "MinValue": 11, "MaxValue": 11},
        "공격력 +(상)": {"SecondOption": 53, "MinValue": 12, "MaxValue": 12},
        "무기공격력 +(하)": {"SecondOption": 54, "MinValue": 1, "MaxValue": 8},
        "무기공격력 +(중)": {"SecondOption": 54, "MinValue": 9, "MaxValue": 10},
        "무기공격력 +(상)": {"SecondOption": 54, "MinValue": 11, "MaxValue": 12},
        "아군 공격력 강화 효과(하)": {"SecondOption": 51, "MinValue": 1, "MaxValue": 9},
        "아군 공격력 강화 효과(중)": {"SecondOption": 51, "MinValue": 10, "MaxValue": 11},
        "아군 공격력 강화 효과(상)": {"SecondOption": 51, "MinValue": 12, "MaxValue": 12},
        "아군 피해량 강화 효과(하)": {"SecondOption": 52, "MinValue": 1, "MaxValue": 9},
        "아군 피해량 강화 효과(중)": {"SecondOption": 52, "MinValue": 10, "MaxValue": 11},
        "아군 피해량 강화 효과(상)": {"SecondOption": 52, "MinValue": 12, "MaxValue": 12},
        "최대 생명력": {"SecondOption": 55, "MinValue": None},
        "최대 마나": {"SecondOption": 56, "MinValue": None},
        "상태이상 공격 지속시간": {"SecondOption": 57, "MinValue": None},
        "전투 중 생명력 회복량": {"SecondOption": 58, "MinValue": None},
        },
    }

    def __init__(self, parent_view, slot):
        self.parent_view = parent_view
        self.slot = slot
        accessory_type = parent_view.selected_accessory
        selected_options = parent_view.selected_options

        # 이미 선택된 옵션의 그룹명을 추적
        already_selected_groups = [
            option.split("(")[0]
            for idx, option in enumerate(selected_options)
            if idx != slot and option not in ["선택해주세요", "선택 안 함"]
        ]

        # 드롭다운 옵션 생성 (이미 선택된 그룹은 제외)
        options = [
            nextcord.SelectOption(
                label=option,
                value=option,
                description=None,
                default=selected_options[slot] == option,
            )
            for option in self.OPTIONS_MAP[accessory_type]
            if option.split("(")[0] not in already_selected_groups or selected_options[slot] == option
        ]

        # "선택해주세요"와 "선택 안 함" 옵션 추가
        options.insert(
            0,
            nextcord.SelectOption(
                label="선택해주세요",
                value="선택해주세요",
                description="옵션을 선택하세요",
                default=selected_options[slot] == "선택해주세요",
            ),
        )
        options.append(
            nextcord.SelectOption(
                label="선택 안 함",
                value="선택 안 함",
                description="옵션을 선택하지 않습니다",
                default=selected_options[slot] == "선택 안 함",
            ),
        )

        super().__init__(placeholder=f"옵션 {slot + 1}을 선택하세요", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        value = self.values[0]
        self.parent_view.selected_options[self.slot] = value

        # 검증 및 다음 단계 진행
        if all(
            option in self.OPTIONS_MAP[self.parent_view.selected_accessory]
            or option == "선택 안 함"
            for option in self.parent_view.selected_options
        ):
            # 모든 드롭다운이 유효하면 다음 단계로 이동
            if "선택해주세요" not in self.parent_view.selected_options:
                if self.parent_view.selected_accessory == "반지":
                    # 반지를 선택한 경우 고대/유물 선택 없이 바로 네 번째 단계로 이동
                    self.parent_view.step = 3
                else:
                    self.parent_view.step = 3

        # 드롭다운 갱신
        self.parent_view.clear_items()
        if self.parent_view.step == 4:
            await self.parent_view.update_message(interaction)
        elif self.parent_view.step == 3:
            self.parent_view.add_item(AccessoryTypeSelectMenu(self.parent_view))
            await self.parent_view.update_message(interaction)
        else:
            for slot in range(3):
                self.parent_view.add_item(OptionSelectMenu(self.parent_view, slot))
            await self.parent_view.update_message(interaction)

class AccessoryTypeSelectMenu(Select):
    def __init__(self, parent_view):
        options = [
            nextcord.SelectOption(label="고대", value="고대"),
            nextcord.SelectOption(label="유물", value="유물"),
        ]
        super().__init__(placeholder="고대/유물을 선택하세요", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction):
        self.parent_view.selected_type = self.values[0]
        self.parent_view.step = 4

        # 마지막 단계: 결과 출력
        self.parent_view.clear_items()
        await self.parent_view.update_message(interaction)


class AccessoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="악세")
    async def accessory_search(self, ctx):
        """악세서리 검색 명령어"""
        view = AccessorySearchView()
        embed = nextcord.Embed(
            title="🛠️ 어떤 악세서리를 찾고 싶으신가요?",
            description=(
                "품질을 먼저 선택한 후, 원하는 악세서리를 선택하세요.\n\n"
                "1️⃣ 목걸이\n2️⃣ 귀걸이\n3️⃣ 반지\n\n"
                "기본 품질은 70이며, 80/90/100 중 선택 가능합니다."
            ),
            color=nextcord.Color.red()
        )
        message = await ctx.send(embed=embed, view=view)
        view.message = message  # 메시지 저장


def setup(bot):
    bot.add_cog(AccessoryCog(bot))