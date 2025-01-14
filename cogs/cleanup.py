from nextcord.ext import commands, tasks
from datetime import datetime, timedelta

class CommandCleanupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_log = []  # [(message, timestamp)] 형태로 메시지 저장
        self.cleanup_task.start()  # 자동 삭제 태스크 시작

    @commands.Cog.listener()
    async def on_message(self, message):
        """모든 메시지를 감시"""
        if message.author == self.bot.user:  # 봇 메시지는 무시
            return

        if message.content.startswith(self.bot.command_prefix):  # 명령어인지 확인
            # 메시지와 현재 시간을 저장
            self.message_log.append((message, datetime.now()))

    @tasks.loop(minutes=1)
    async def cleanup_task(self):
        """주기적으로 메시지를 삭제"""
        now = datetime.now()
        to_delete = []

        for msg, timestamp in self.message_log:
            if now - timestamp >= timedelta(hours=3):  # 3시간 경과
                try:
                    await msg.delete()
                except Exception as e:
                    print(f"메시지 삭제 중 오류 발생: {e}")
                to_delete.append((msg, timestamp))

        # 삭제된 메시지를 로그에서 제거
        self.message_log = [entry for entry in self.message_log if entry not in to_delete]

    @cleanup_task.before_loop
    async def before_cleanup_task(self):
        """봇이 준비될 때까지 기다리기"""
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """메시지가 삭제되면 로그에서도 제거"""
        self.message_log = [entry for entry in self.message_log if entry[0].id != message.id]


def setup(bot: commands.Bot):
    bot.add_cog(CommandCleanupCog(bot))