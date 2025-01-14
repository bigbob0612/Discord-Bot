import aiohttp
import os
from utils.json_loader import load_json
from bs4 import BeautifulSoup
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "../../config/settings.json")
config = load_json(CONFIG_PATH)
LOSTARK_API_KEY = config["lostark"]["key"]

HEADERS = {"Authorization": f"Bearer {LOSTARK_API_KEY}"}

async def fetch_character_siblings(character_name):
    """로스트아크 캐릭터 형제 정보 가져오기"""
    url = f"https://developer-lostark.game.onstove.com/characters/{character_name}/siblings"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            response.raise_for_status()
            return await response.json()

async def fetch_character_profile(character_name):
    """로스트아크 캐릭터 프로필 정보 가져오기"""
    url = f"https://developer-lostark.game.onstove.com/armories/characters/{character_name}/profiles"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            response.raise_for_status()
            return await response.json()
        
async def fetch_character_gems(character_name):
    """로스트아크 캐릭터 보석 정보 가져오기"""
    url = f"https://developer-lostark.game.onstove.com/armories/characters/{character_name}/gems"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            response.raise_for_status()
            return await response.json()
        
async def fetch_character_cards(character_name: str):
    """로스트아크 캐릭터 카드 정보 가져오기"""
    base_url = f"https://developer-lostark.game.onstove.com/armories/characters/{character_name}/cards"
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, headers=HEADERS) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"카드 정보 API 요청 실패: {response.status}")
                return None

def parse_gem_info(gems):
    """보석 정보 파싱"""
    if not gems:  # gems가 None 또는 빈 리스트일 경우
        return {}

    gem_counts = {}
    for gem in gems:
        name_html = gem.get("Name", "")

        # BeautifulSoup으로 태그 제거
        soup = BeautifulSoup(name_html, "html.parser")
        clean_name = soup.get_text()

        # "레벨"과 보석 종류 추출
        if "레벨" in clean_name:
            gem_level, gem_type = clean_name.split("레벨", 1)
            gem_type = gem_type.split("의")[0].strip()  # 보석 종류 추출 ("멸화", "홍염" 등)
            gem_level = gem_level.strip() + "레벨"  # 레벨 추가 ("7레벨", "8레벨" 등)

            key = f"{gem_level} {gem_type}"
            gem_counts[key] = gem_counts.get(key, 0) + 1

    return gem_counts

async def fetch_card_info(character_name: str, api_key: str):
    """로스트아크 API를 통해 카드 정보 가져오기"""
    base_url = f"https://developer-lostark.game.onstove.com/armories/characters/{character_name}/cards"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(base_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"API 요청 실패: {response.status}")
                    return None
        except Exception as e:
            print(f"API 호출 중 오류 발생: {e}")
            return None

async def fetch_auction_gem_data(level: int, gem_type: str):
        """옥션 데이터를 검색합니다."""
        url = "https://developer-lostark.game.onstove.com/auctions/items"
        payload = {
            "ItemLevelMin": 0,
            "ItemLevelMax": 0,
            "Sort": "BUY_PRICE",
            "CategoryCode": 210000,  # 보석 카테고리 코드
            "ItemGradeQuality": 0,  # 품질
            "SkillOptions": [],
            "ItemName": f"{level}레벨 {gem_type}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch auction data: {response.status}")
                return await response.json()
            
async def fetch_markets_engraving_data(engraving_type: str):
        """마켓 데이터를 검색합니다."""
        url = "https://developer-lostark.game.onstove.com/markets/items/"
        payload = {
            "CategoryCode": 40000,
            "Sort": "CURRENT_MIN_PRICE",
            "ItemGrade": "유물",
            "ItemName": f"{engraving_type}",
            "SortCondition": "DESC"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch auction data: {response.status}")
                return await response.json()

async def fetch_markets_enhance_data(item_name: str):
        """마켓 데이터를 검색합니다."""
        url = "https://developer-lostark.game.onstove.com/markets/items/"
        payload = {
            "CategoryCode": 50000,
            "Sort": "CURRENT_MIN_PRICE",
            "itemName": f"{item_name}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch auction data: {response.status}")
                return await response.json()

            
async def fetch_accessory_data(item_grade_quality, category_code, item_grade, etc_options, page_no):
    """
    악세서리 검색 요청을 API에 보내고 결과를 반환합니다.
    """
    url = "https://developer-lostark.game.onstove.com/auctions/items"
    payload = {
        "pageNo": page_no,
        "ItemGradeQuality": item_grade_quality,
        "CategoryCode": category_code,
        "ItemGrade": item_grade if item_grade else "",
        "ItemTier": 4,
        "EtcOptions": etc_options
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch accessory data: {response.status}")
            return await response.json()

            

CARD_ABBREVIATIONS = {
    "세상을 구하는 빛": "세구빛",
    "남겨진 바람의 절벽": "남바절",
    "창세의 빛": "창빛",
    "운명의 부름": "운부",
    "밤의 그림자": "밤그",
    "세상의 끝에서": "세끝",
    "악몽의 땅": "악땅",
    "에버그레이스의 축복": "에버그",
}
        
def parse_card_info(cards):
    """카드 정보 파싱"""
    if not cards or "Effects" not in cards or not cards["Effects"]:
        return "카드 정보 없음"

    # Items의 마지막 Name 추출
    effects = cards["Effects"]
    last_effect = effects[-1] if effects else None
    if not last_effect or "Items" not in last_effect or not last_effect["Items"]:
        return "카드 정보 없음"

    card_info = last_effect["Items"][-1]["Name"]

    # 데이터 파싱
    if "(" in card_info and ")" in card_info:
        base_name, details = card_info.split("(", 1)
        details = details.strip(")")  # 괄호 제거
        base_name = base_name.strip()  # 카드 이름 양쪽 공백 제거

        # 정규 표현식으로 숫자 + "세트" 제거
        base_name = re.sub(r"\d+\s*세트", "", base_name).strip()
        # 줄임말 변환
        base_name = CARD_ABBREVIATIONS.get(base_name, base_name)

        # 괄호 안의 정보 파싱
        if "각성합계" in details:
            total_awakening = details.replace("각성합계", "").strip()  # 각성합계 숫자만 남김
            return f"{base_name} {total_awakening}각"  # 각성 합계 추가
        else:
            return base_name
    else:
        base_name = card_info.strip()  # 괄호가 없다면 카드 이름만 반환
        return CARD_ABBREVIATIONS.get(base_name, base_name)