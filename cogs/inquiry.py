import nextcord
from nextcord.ext import commands

class InquiryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="문의하기")
    async def create_inquiry_channel(self, ctx):
        """문의 채널을 생성합니다."""
        guild = ctx.guild
        guild_master_role = nextcord.utils.get(guild.roles, name="길드마스터")

        if not guild_master_role:
            await ctx.send("⚠️ 길드마스터 역할이 존재하지 않습니다. 관리자에게 문의하세요.", delete_after=10)
            return

        # "문의 채널" 카테고리 확인
        inquiry_category = nextcord.utils.get(guild.categories, name="문의 채널")
        if not inquiry_category:
            await ctx.send("⚠️ '문의 채널'이라는 카테고리가 존재하지 않습니다. 관리자에게 문의하세요.", delete_after=10)
            return

        # 기존 문의 채널 확인
        existing_channel = nextcord.utils.get(
            inquiry_category.channels,
            name=f"문의-{str(ctx.author.id)[:4]}"
        )

        if existing_channel:
            await ctx.send("⚠️ 이미 문의 중인 채널이 있습니다.", delete_after=10)
            return

        # 채널 생성
        overwrites = {
            guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
            ctx.author: nextcord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild_master_role: nextcord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        inquiry_channel = await guild.create_text_channel(
            name=f"문의-{str(ctx.author.id)[:4]}",
            category=inquiry_category,
            overwrites=overwrites
        )

        await ctx.message.delete()
        await inquiry_channel.send(f"✅ {ctx.author.mention}, 문의 채널이 생성되었습니다: {inquiry_channel.mention}", delete_after=10)

    @commands.command(name="문의종료")
    async def close_inquiry_channel(self, ctx):
        """현재 문의 채널을 삭제합니다."""
        if not ctx.channel.name.startswith("문의-"):
            await ctx.send("⚠️ 문의 채널에서만 이 명령어를 사용할 수 있습니다.", delete_after=10)
            return

        await ctx.channel.delete(reason="문의 종료 요청")


def setup(bot):
    bot.add_cog(InquiryCog(bot))