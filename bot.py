import nextcord
from nextcord.ext import commands
from utils.json_loader import load_json
from utils.music_db import Database
from cogs.music import MusicCog
from cogs.sasage import SasageCog
from cogs.character import CharacterCog
from cogs.auth import AuthCog
from cogs.rolechange import RoleChangeCog
from cogs.schedule import NotionScheduleCog
from cogs.auction import AuctionCog
from cogs.accessory import AccessoryCog
from cogs.vote import VoteCog
from cogs.raid import RaidGuideCog
from cogs.help import HelpCog
from cogs.cleanup import CommandCleanupCog
from cogs.inquiry import InquiryCog
import os

# 설정 파일 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "../config/settings.json")
config = load_json(CONFIG_PATH)

# SQLite 초기화
database = Database(config["database"]["file"])

# 봇 설정
TOKEN = config["bot"]["token"]
PREFIX = config["bot"]["prefix"]

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트 활성화
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

database = Database("music_queue.db")

@bot.event
async def on_ready():
    await database.initialize() # SQLite 초기화
    await bot.change_presence(activity=nextcord.Game(name='Lost Ark'))

    print(f"봇이 준비되었습니다: {bot.user}")

bot.add_cog(MusicCog(bot, database))
bot.add_cog(SasageCog(bot))
bot.add_cog(CharacterCog(bot))
bot.add_cog(AuthCog(bot))
bot.add_cog(RoleChangeCog(bot))
bot.add_cog(NotionScheduleCog(bot))
bot.add_cog(AuctionCog(bot))
bot.add_cog(AccessoryCog(bot))
bot.add_cog(VoteCog(bot))
bot.add_cog(RaidGuideCog(bot))
bot.add_cog(HelpCog(bot))
bot.add_cog(CommandCleanupCog(bot))
bot.add_cog(InquiryCog(bot))

#봇 실행
bot.run(TOKEN)