import nextcord
from nextcord.ext import commands
from bs4 import BeautifulSoup
import aiohttp
import asyncio


class SasageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="사사게")
    async def search_sasage(self, ctx, *, keyword: str):
        """Inven 사사게 게시판에서 키워드 검색"""
        # Inven 사사게 검색 URL
        search_url = f"https://www.inven.co.kr/board/lostark/5355?query=list&p=1&sterm=&name=subjcont&keyword={keyword}"

        # 초기 임베드
        embed = nextcord.Embed(
            title="🔍 검색 중...",
            description="잠시만 기다려주세요! 검색을 진행하고 있습니다.\n[□□□□□□□□□□]",  # 초기 프로그래스바
            color=nextcord.Color.red()
        )
        status_message = await ctx.send(embed=embed)

        try:
            # aiohttp로 요청
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers={"User-Agent": "Mozilla/5.0"}) as response:
                    if response.status != 200:
                        await status_message.edit(content=f"페이지 요청 실패: {response.status}")
                        return

                    # HTML 가져오기
                    html = await response.text()

                    # BeautifulSoup 파싱
                    soup = BeautifulSoup(html, "html.parser")
                    posts = soup.select("tbody > tr")  # 게시글 선택

                    if not posts:
                        embed = nextcord.Embed(
                            description=f"🎉 **{keyword}**님은 아주 깨끗한 분이시네요! 사사게 기록이 전혀 없습니다! 😇",
                            color=nextcord.Color.red()
                        )
                        await status_message.edit(embed=embed)
                        return

                    # 검색 결과 처리
                    results = []
                    total_posts = len(posts)
                    for index, post in enumerate(posts):
                        title_element = post.select_one("td.tit a.subject-link")
                        date_element = post.select_one("td.date")
                        if title_element and date_element:
                            title_with_server = title_element.text.strip()
                            # `[기타]` 카테고리는 무시
                            if "[기타]" in title_with_server:
                                continue

                            # 링크와 제목 가져오기
                            link = f"{title_element['href']}"
                            date = date_element.text.strip().replace("-", "/")  # 날짜 형식 수정
                            results.append((date, title_with_server, link))

                        # 프로그래스바 업데이트
                        progress = int((index + 1) / total_posts * 10)  # 진행 상태 계산
                        progress_bar = "■" * progress + "□" * (10 - progress)
                        embed.description = f"잠시만 기다려주세요! 검색을 진행하고 있습니다.\n[{progress_bar}]"
                        await status_message.edit(embed=embed)
                        await asyncio.sleep(0.1)  # 잠시 대기 (너무 빠른 업데이트 방지)

                    # 결과 출력
                    if results:
                        description_lines = []
                        for date, title_with_server, link in results[:10]:  # 최대 10개 표시
                            # 제목에서 서버명을 제외하고 링크 적용
                            server, title = title_with_server.split("]", 1)
                            server = f"{server}]"
                            title = title.strip()

                            description_lines.append(
                                f"📅 {date} - {server} [{title}]({link})\n"
                            )

                        description = "\n".join(description_lines)
                        embed = nextcord.Embed(
                            title=f"🔍 '{keyword}'님의 사사게 기록이 총 {len(results)}건 발견되었습니다!",
                            description=description,
                            color=nextcord.Color.red()
                        )
                        embed.set_footer(text="🎯 클릭해서 자세한 내용을 확인해보세요!")
                        await status_message.edit(embed=embed)
                    else:
                        # 검색 결과가 없는 경우 출력
                        embed = nextcord.Embed(
                            description=f"🎉 **{keyword}**님은 아주 깨끗한 분이시네요! 사사게 기록이 전혀 없습니다! 😇",
                            color=nextcord.Color.red()
                        )
                        await status_message.edit(embed=embed)

        except Exception as e:
            # 예외 처리
            print(f"크롤링 오류: {e}")
            embed = nextcord.Embed(
                title="⚠️ 어라? 검색 중에 오류가 발생했어요!",
                description="다시 시도해 주세요~ 😅",
                color=nextcord.Color.red()
            )
            await status_message.edit(embed=embed)


def setup(bot):
    bot.add_cog(SasageCog(bot))