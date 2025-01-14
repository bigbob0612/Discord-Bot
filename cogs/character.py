import nextcord
from nextcord.ext import commands
from services.lostark_api import (
    fetch_character_siblings,
    fetch_character_profile,
    fetch_character_gems,
    fetch_character_cards,
    parse_gem_info,
    parse_card_info
)

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="닉네임")
    async def character_info(self, ctx, *, character_name: str):
        """로스트아크 캐릭터 정보 조회"""
        try:
            # 캐릭터 데이터 가져오기
            siblings = await fetch_character_siblings(character_name)
            profile = await fetch_character_profile(character_name)
            gems_data = await fetch_character_gems(character_name)
            cards_data = await fetch_character_cards(character_name)  # 카드 정보 추가

            if not siblings or not profile:
                await ctx.send(f"❌ '{character_name}' 캐릭터 정보를 찾을 수 없습니다.", delete_after=300)
                return

            # 보석 정보 파싱
            gems = parse_gem_info(gems_data.get("Gems", []))
            gems_description = " / ".join(
                [f"{gem} {count}개" for gem, count in gems.items()]
            ) if gems else "보석 정보 없음"

            # 카드 정보 파싱
            card_info = parse_card_info(cards_data)

            # 캐릭터 정보
            if profile is None:
                character_image = None
            else:
                character_image = profile.get("CharacterImage", None)
            character_name = profile.get("CharacterName", "알 수 없음")
            item_level = profile.get("ItemMaxLevel", "알 수 없음")
            character_class = profile.get("CharacterClassName", "알 수 없음")

            # 첫 번째 임베드 생성 (캐릭터 사진과 제목)
            embed_photo = nextcord.Embed(
                title="📸 캐릭터 정보:",
                color=nextcord.Color.red()
            )
            if character_image:
                embed_photo.set_image(url=character_image)

            # 두 번째 임베드 생성 (나머지 정보)
            embed_info = nextcord.Embed(
                title="",
                description=(
                    f"- **닉네임**: {character_name}\n"
                    f"- **아이템 레벨**: {item_level}\n"
                    f"- **직업**: {character_class}\n"
                    f"- **보석**: {gems_description}\n"
                    f"- **카드**: {card_info}\n\n"
                    f"🔗 **자세한 정보는 로아와에서 확인하세요**: [로아와 링크](https://loawa.com/char/{character_name})"
                ),
                color=nextcord.Color.red()
            )

            # 두 개의 임베드 전송
            await ctx.send(embed=embed_photo, delete_after=300)
            await ctx.send(embed=embed_info, delete_after=300)

        except Exception as e:
            # 오류 발생 시
            await ctx.send("⚠️ 캐릭터 정보를 가져오는 중 오류가 발생했습니다. 다시 시도해주세요.", delete_after=300)
            print(f"오류 발생: {e}")

    @commands.command(name="원정대")
    async def expedition_info(self, ctx, *, expedition_name: str):
        """로스트아크 원정대 캐릭터 정보 조회"""
        try:
            # 원정대 캐릭터 목록 가져오기
            siblings = await fetch_character_siblings(expedition_name)

            if not siblings or not isinstance(siblings, list):
                await ctx.send(f"❌ '{expedition_name}' 원정대의 정보를 찾을 수 없습니다.", delete_after=300)
                return
            
            # ItemMaxLevel 기준으로 내림차순 정렬
            siblings = sorted(
                siblings,
                key=lambda x: float(x.get("ItemMaxLevel", "0.00").replace(',', '')),
                reverse=True
            )
            
            emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]

            # 최대 6개의 캐릭터만 처리
            for idx, character in enumerate(siblings[:6]):  # 상위 6개 캐릭터
                character_name = character.get("CharacterName", "알 수 없음")
                item_level = character.get("ItemMaxLevel", "알 수 없음")
                character_class = character.get("CharacterClassName", "알 수 없음")

                # 보석 데이터 가져오기
                gems_data = await fetch_character_gems(character_name)
                gems = parse_gem_info(gems_data.get("Gems", [])) if gems_data else {}
                gems_description = " / ".join(
                    [f"{gem} {count}개" for gem, count in gems.items()]
                ) if gems else "보석 정보 없음"

                # 카드 데이터 가져오기
                cards_data = await fetch_character_cards(character_name)
                card_info = parse_card_info(cards_data)

                # 프로필 데이터 가져오기
                profile = await fetch_character_profile(character_name)
                if profile is None:
                    character_image = None
                else:
                    character_image = profile.get("CharacterImage", None)

                # 개별 캐릭터 임베드 생성
                embed = nextcord.Embed(
                    title=f"📜 캐릭터 정보  {emoji_numbers[idx]}",
                    description=(
                        f"**닉네임**: {character_name}\n"
                        f"**아이템 레벨**: {item_level}\n"
                        f"**직업**: {character_class}\n"
                        f"**보석**: {gems_description}\n"
                        f"**카드**: {card_info}\n\n"
                        f"🔗 **자세한 정보는 로아와에서 확인하세요**: "
                        f"[로아와 링크](https://loawa.com/char/{character_name})"
                    ),
                    color=nextcord.Color.red()
                )

                # 캐릭터 이미지가 있으면 추가
                if character_image:
                    embed.set_thumbnail(url=character_image)

                # 각 캐릭터별 임베드 전송
                await ctx.send(embed=embed, delete_after=300)

        except Exception as e:
            # 오류 발생 시
            await ctx.send("⚠️ 원정대 정보를 가져오는 중 오류가 발생했습니다. 다시 시도해주세요.", delete_after=300)
            print(f"오류 발생: {e}")

def setup(bot):
    bot.add_cog(CharacterCog(bot))