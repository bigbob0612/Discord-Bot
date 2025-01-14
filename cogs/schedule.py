import nextcord
from nextcord.ext import commands
import aiohttp
import json
from datetime import datetime, timedelta
import os

# settings.json에서 설정 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE_DIR, "../../config/settings.json")

with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
    settings = json.load(file)

NOTION_API_TOKEN = settings["notion"]["token"]
NOTION_DATABASE_ID = settings["notion"]["db_id"]
NOTION_URL = settings["notion"]["url"]
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


class NotionScheduleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_notion_data(self):
        """노션 데이터베이스에서 일정 가져오기"""
        url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=NOTION_HEADERS) as response:
                if response.status != 200:
                    raise Exception(f"일정을 가져오지 못했습니다: {response.status}")
                return await response.json()

    async def add_notion_event(self, boss, iso_datetime, difficulty, proficiency):
        """노션 데이터베이스에 일정 추가"""
        url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "이름": {"title": [{"text": {"content": boss}}]},
                "날짜": {"date": {"start": iso_datetime}},
                "난이도": {"select": {"name": difficulty}},
                "숙련도": {"select": {"name": proficiency}},
            },
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=NOTION_HEADERS, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"일정을 추가하지 못했습니다: {response.status}")
                return await response.json()

    @commands.command(name="일정")
    async def show_schedule(self, ctx):
        """노션 캘린더에서 현재 등록된 레이드 일정을 가져옵니다."""
        try:
            data = await self.fetch_notion_data()

            # 현재 시각 (KST 기준)
            now = datetime.utcnow() + timedelta(hours=9)

            # 일정 정보 추출
            events = []
            for index, result in enumerate(data.get("results", []), start=1):
                properties = result["properties"]
                title = properties["이름"]["title"][0]["text"]["content"] if properties["이름"]["title"] else "제목 없음"

                # ISO 8601 날짜 포맷 변환
                iso_date = properties["날짜"]["date"]["start"]
                event_date = datetime.fromisoformat(iso_date.replace("Z", "+00:00")) + timedelta(hours=9)

                # 과거 일정 제외
                if event_date < now:
                    continue

                formatted_date = event_date.strftime("%Y-%m-%d %H:%M")
                difficulty = properties["난이도"]["select"]["name"] if properties["난이도"]["select"] else "난이도 없음"
                proficiency = properties["숙련도"]["select"]["name"] if properties["숙련도"]["select"] else "숙련도 없음"

                # 인덱스를 붙여가며 레이드 정보를 추가
                events.append(f"{index}️⃣  {formatted_date} {title} {difficulty} ({proficiency})")

            # 메시지 생성
            if events:
                event_list = "\n".join(events)
            else:
                event_list = "❌ 현재 등록된 일정이 없습니다."

            # 임베드 생성
            embed = nextcord.Embed(
                title="📅 **현재 등록된 레이드 일정**:",
                color=nextcord.Color.red()
            )
            embed.add_field(
                name="\u200b",
                value=event_list,
                inline=False
            )
            embed.add_field(
                name="\u200b",
                value=(f"🔗 참여 신청은 노션에서만 가능합니다 : [노션 링크]({NOTION_URL})"),
                inline=False
            )

            # 임베드 전송
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"⚠️ 일정 가져오기 중 오류가 발생했습니다: {e}")

    @commands.command(name="레이드")
    async def add_raid(self, ctx, 날짜: str, 시간: str, 보스: str, 난이도: str, 숙련도: str):
        """새로운 레이드 일정을 노션 캘린더에 등록합니다."""
        try:
            # 날짜와 시간을 결합하여 ISO 8601 형식으로 변환
            datetime_str = f"{날짜} {시간}"
            iso_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").isoformat()

            # 노션 데이터 추가
            await self.add_notion_event(보스, iso_datetime, 난이도, 숙련도)

            # 임베드 생성
            embed = nextcord.Embed(
                title="📝 새로운 레이드 일정이 등록되었습니다!",
                color=nextcord.Color.red()
            )
            embed.add_field(name="📅 날짜", value=날짜, inline=False)
            embed.add_field(name="⏰ 시간", value=시간, inline=False)
            embed.add_field(name="⚔️ 보스", value=f"{보스} {난이도} ({숙련도})", inline=False)
            embed.add_field(
                name="🔗 참여 신청",
                value=(f"참여 신청은 노션에서만 가능합니다: [노션 링크]({NOTION_URL})"),
                inline=False
            )

            # 임베드 전송
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"⚠️ 일정 등록 중 오류가 발생했습니다: {e}")

def setup(bot):
    bot.add_cog(NotionScheduleCog(bot))