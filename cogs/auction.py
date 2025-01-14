import nextcord
from nextcord.ext import commands
from services.lostark_api import fetch_auction_gem_data, fetch_markets_engraving_data, fetch_markets_enhance_data

class AuctionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # 유효한 각인서 목록
        self.valid_engravings = {
            "각성", "강령술", "강화 방패", "결투의 대가", "구슬동자", "굳은 의지", "급소 타격", "기습의 대가", "기습구조", 
            "달인의 저력", "돌격대장", "마나 효율 증가", "마나의 흐름", "바리케이드", "번개의 분노", "부러진 뼈", 
            "분쇄의 주먹", "불굴", "선수필승", "속전속결", "슈퍼차지", "승부사", "시선 집중", "실드 관통", 
            "아드레날린", "안정된 상태", "약자 무시", "에테르 포식자", "여신의 가호", "예리한 둔기", "원한", 
            "위기 모면", "저주받은 인형", "전문의", "정기 흡수", "정밀 단도", "중갑 착용", "질량 증가", 
            "최대 마나 증가", "추진력", "타격의 대가", "탈출의 명수", "폭발물 전문가"
        }

    @commands.command(name="보석")
    async def gem_search(self, ctx, level: int, gem_type: str):
        """
        경매장에서 보석 최저가 검색
        사용법: !보석 [레벨] [보석종류]
        """
        try:
            # 보석 종류 코드 매핑
            gem_type_map = {
                "겁화",
                "작열",
                "멸화",
                "홍염",
            }
            if gem_type not in gem_type_map:
                await ctx.send("⚠️ 유효하지 않은 보석 종류입니다. (겁화, 작열, 멸화, 홍염 중 하나를 선택하세요.)")
                return

            # 경매장 데이터 검색
            gem_data = await fetch_auction_gem_data(level, gem_type)

            # 최저가 검색
            items = gem_data.get("Items", [])
            if not items:
                await ctx.send(f"❌ {level}레벨 {gem_type} 보석의 데이터를 찾을 수 없습니다.")
                return

            # 최저가 아이템 추출
            cheapest_item = min(items, key=lambda x: x["AuctionInfo"]["BuyPrice"])
            cheapest_price = cheapest_item["AuctionInfo"]["BuyPrice"]

            await ctx.send(f"💎 {level}레벨 {gem_type}의 최저가는 {cheapest_price:,} 골드입니다.")
        except Exception as e:
            await ctx.send(f"⚠️ 보석 검색 중 오류가 발생했습니다: {e}")

    @commands.command(name="유각")
    async def engraving_search(self, ctx, *, engraving_name: str):
        """
        경매장에서 각인서 최저가 검색
        사용법: !유각 [각인명]
        """
        try:
            engraving_name = engraving_name.strip()  # 공백 제거

            # 각인서 이름 검증
            if engraving_name not in self.valid_engravings:
                await ctx.send("⚠️ 유효하지 않은 각인서 이름입니다. 정확한 이름을 입력해주세요.")
                return

            # 경매장 데이터 검색
            engraving_data = await fetch_markets_engraving_data(engraving_name)

            # 각인서 데이터 확인
            items = engraving_data.get("Items", [])
            if not items:
                await ctx.send(f"❌ '{engraving_name}' 각인서의 데이터를 찾을 수 없습니다.")
                return

            # 최저가 아이템 추출
            cheapest_item = items[0]  # API 응답은 최저가 순으로 정렬된다고 가정
            current_min_price = cheapest_item["CurrentMinPrice"]

            await ctx.send(f"📜 '{engraving_name}' 각인의 최저가는 {current_min_price:,} 골드입니다.")
        except Exception as e:
            await ctx.send(f"⚠️ 각인서 검색 중 오류가 발생했습니다: {e}")

    @commands.command(name="유각시세")
    async def top_engraving_prices(self, ctx):
        """
        경매장에서 가장 비싼 각인서 상위 10개를 가져옵니다.
        사용법: !유각시세
        """
        try:
            # 유각 전체 데이터를 가져오기 위해 빈 이름으로 요청
            engraving_data = await fetch_markets_engraving_data("")
            
            # 각인서 데이터 확인
            items = engraving_data.get("Items", [])
            if not items:
                await ctx.send("❌ 경매장에서 유효한 각인서 데이터를 찾을 수 없습니다.")
                return

            # 상위 10개 정렬 (현재 최저가 기준 내림차순 정렬)
            sorted_items = sorted(items, key=lambda x: x["CurrentMinPrice"], reverse=True)[:10]

            # 임베드 생성
            embed = nextcord.Embed(
                title="📊 현재 경매장 유각 시세 TOP 10",
                description="\u200b",
                color=nextcord.Color.red()
            )

            # 정렬된 각인서 데이터를 임베드에 추가
            for idx, item in enumerate(sorted_items, start=1):
                name = item["Name"]
                price = item["CurrentMinPrice"]
                if idx == 10:
                    idx_display = "1️⃣0️⃣"  # 10번째는 숫자를 이모티콘으로 분리
                else:
                    idx_display = f"{idx}️⃣"  # 나머지는 숫자 이모티콘 그대로 사용
                embed.add_field(name=f"\u200b{idx_display} {name} - {price:,} 골드", value="", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"⚠️ 유각 시세를 가져오는 중 오류가 발생했습니다: {e}")

    @commands.command(name="강화재료")
    async def enhance_items_prices(self, ctx):

        try:
            enhance_data = await fetch_markets_enhance_data("운명")
            fusion_data = await fetch_markets_enhance_data("아비도스")
            enhance_item = enhance_data.get("Items", [])
            fusion_item = fusion_data.get("Items", [])
            if not enhance_item:
                await ctx.send("❌ 경매장에서 유효한 각인서 데이터를 찾을 수 없습니다.")
                return

            if not fusion_item:
                await ctx.send("❌ 경매장에서 유효한 각인서 데이터를 찾을 수 없습니다.")
                return
            
            # 임베드 생성
            embed = nextcord.Embed(
                title="📊 현재 강화재료 시세",
                description="\u200b",
                color=nextcord.Color.red()
            )

            for idx, item in enumerate(enhance_item, start=1):
                name = item["Name"]
                price = item["CurrentMinPrice"]
                embed.add_field(name=f"\u200b{name}  {price:,}골드", value="", inline=False)
            
            for idx, item in enumerate(fusion_item, start=1):
                name = item["Name"]
                price = item["CurrentMinPrice"]
                embed.add_field(name=f"\u200b{name}  {price:,}골드", value="", inline=False)

            await ctx.send(embed=embed)
        
        except Exception as e:
            await ctx.send(f"⚠️ 시세를 가져오는 중 오류가 발생했습니다: {e}")

def setup(bot):
    bot.add_cog(AuctionCog(bot))