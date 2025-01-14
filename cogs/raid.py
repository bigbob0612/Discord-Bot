import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Button, button
from utils.raid_db import RaidDatabase


class RaidGuideCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = RaidDatabase()

    @commands.command(name="레이드추가")
    async def add_raid(self, ctx, raid_type: str, raid_name: str, link: str):
        """레이드 정보 추가"""
        self.db.add_raid(raid_type, raid_name, link)
        await ctx.send(f"✅ {raid_type} 레이드에 '{raid_name}'이(가) 추가되었습니다!")

    @commands.command(name="레이드수정")
    async def update_raid(self, ctx, raid_type: str, raid_name: str, link: str):
        """레이드 정보 수정"""
        if not self.db.raid_exists(raid_type, raid_name):
            await ctx.send(f"❌ '{raid_type}' 레이드에 '{raid_name}'이(가) 존재하지 않습니다.")
            return
        self.db.update_raid(raid_type, raid_name, link)
        await ctx.send(f"✅ '{raid_type}' 레이드에 '{raid_name}'의 정보가 수정되었습니다!")

    @commands.command(name="레이드삭제")
    async def delete_raid(self, ctx, raid_type: str, raid_name: str):
        """레이드 정보 삭제"""
        if not self.db.raid_exists(raid_type, raid_name):
            await ctx.send(f"❌ '{raid_type}' 레이드에 '{raid_name}'이(가) 존재하지 않습니다.")
            return
        self.db.delete_raid(raid_type, raid_name)
        await ctx.send(f"✅ '{raid_type}' 레이드에 '{raid_name}'이(가) 삭제되었습니다!")

    @commands.command(name="공략")
    async def show_raid_guide(self, ctx):
        """공략 버튼을 보여줍니다"""
        # 레이드 종류 가져오기
        raid_types = self.db.get_all_raid_types()
        if not raid_types:
            await ctx.send("❌ 등록된 레이드가 없습니다. `!레이드추가` 명령어로 추가해주세요.")
            return

        # 버튼 View 생성
        view = RaidTypeView(self.db)
        embed = nextcord.Embed(
            title="📝 어떤 레이드의 공략을 보고 싶으신가요?",
            description="\n".join([f"{index+1}️⃣ {raid_type} 레이드" for index, raid_type in enumerate(raid_types)]),
            color=nextcord.Color.red()
        )
        await ctx.send(embed=embed, view=view)


class RaidTypeView(View):
    def __init__(self, db):
        super().__init__(timeout=180)
        self.db = db

        # 레이드 종류 버튼 추가
        raid_types = self.db.get_all_raid_types()
        for index, raid_type in enumerate(raid_types):
            self.add_item(RaidTypeButton(label=f"{index+1}️⃣ {raid_type}", raid_type=raid_type, db=db))


class RaidTypeButton(Button):
    def __init__(self, label, raid_type, db):
        super().__init__(style=nextcord.ButtonStyle.primary, label=label)
        self.raid_type = raid_type
        self.db = db

    async def callback(self, interaction: nextcord.Interaction):
        raids = self.db.get_raids_by_type(self.raid_type)
        if not raids:
            await interaction.response.send_message(f"❌ {self.raid_type} 레이드에 등록된 정보가 없습니다.", ephemeral=True)
            return

        # 버튼 View 생성
        view = RaidBossView(self.db, self.raid_type)
        embed = nextcord.Embed(
            title=f"📝 {self.raid_type} 레이드의 어떤 보스 공략을 보고 싶으신가요?",
            description="\n".join([f"{index+1}️⃣ {raid[0]}" for index, raid in enumerate(raids)]),
            color=nextcord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RaidBossView(View):
    def __init__(self, db, raid_type):
        super().__init__(timeout=180)
        self.db = db
        self.raid_type = raid_type

        # 보스 버튼 추가
        raids = self.db.get_raids_by_type(raid_type)
        for index, (raid_name, link) in enumerate(raids):
            self.add_item(RaidBossButton(label=f"{index+1}️⃣ {raid_name}", raid_name=raid_name, link=link))


class RaidBossButton(Button):
    def __init__(self, label, raid_name, link):
        super().__init__(style=nextcord.ButtonStyle.secondary, label=label)
        self.raid_name = raid_name
        self.link = link

    async def callback(self, interaction: nextcord.Interaction):
        embed = nextcord.Embed(
            title=f"📝 {self.raid_name} 공략 페이지",
            description=f"[{self.raid_name} 공략 페이지]({self.link})",
            color=nextcord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(RaidGuideCog(bot))