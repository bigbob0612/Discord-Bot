import aiosqlite

class Database:
    def __init__(self, db_file):
        self.db_file = db_file

    async def initialize(self):
        """데이터베이스 초기화"""
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    requester TEXT NOT NULL
                )
            """)
            await db.commit()
            print("✅ 데이터베이스가 초기화되었습니다.")

    async def add_song(self, guild_id, url, title, requester):
        """곡 추가"""
        async with aiosqlite.connect(self.db_file) as db:
            try:
                await db.execute("""
                    INSERT INTO songs (guild_id, url, title, requester)
                    VALUES (?, ?, ?, ?)
                """, (guild_id, url, title, requester))
                await db.commit()
                print(f"✅ 곡 추가: guild_id={guild_id}, title={title}, requester={requester}")
            except Exception as e:
                print(f"❌ 곡 추가 중 오류 발생: {e}")

    async def get_next_song(self, guild_id):
        """다음 곡 가져오기"""
        async with aiosqlite.connect(self.db_file) as db:
            try:
                # 다음 곡 가져오기
                cursor = await db.execute("""
                    SELECT id, url, title, requester FROM songs
                    WHERE guild_id = ?
                    ORDER BY id LIMIT 1
                """, (guild_id,))
                song = await cursor.fetchone()

                if not song:
                    print(f"🔍 [DEBUG] 다음 곡 없음: guild_id={guild_id}")
                    return None

                # 곡 삭제
                await db.execute("DELETE FROM songs WHERE id = ?", (song[0],))
                await db.commit()
                print(f"✅ 곡 재생 후 삭제 완료: {song[2]} (guild_id={guild_id})")

                return {
                    "id": song[0],
                    "url": song[1],
                    "title": song[2],
                    "requester": song[3]
                }
            except Exception as e:
                print(f"❌ 다음 곡 가져오기 중 오류 발생: {e}")
                return None

    async def get_queue(self, guild_id):
        """대기열 가져오기"""
        async with aiosqlite.connect(self.db_file) as db:
            try:
                cursor = await db.execute("""
                    SELECT url, title, requester FROM songs
                    WHERE guild_id = ?
                    ORDER BY id
                """, (guild_id,))
                queue = [{"url": row[0], "title": row[1], "requester": row[2]} for row in await cursor.fetchall()]
                print(f"🔍 [DEBUG] 대기열 조회: guild_id={guild_id}, count={len(queue)}")
                return queue
            except Exception as e:
                print(f"❌ 대기열 조회 중 오류 발생: {e}")
                return []

    async def get_queue_count(self, guild_id):
        """대기열 곡 수"""
        async with aiosqlite.connect(self.db_file) as db:
            try:
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM songs WHERE guild_id = ?
                """, (guild_id,))
                count = await cursor.fetchone()
                print(f"🔍 [DEBUG] 대기열 곡 수: guild_id={guild_id}, count={count[0]}")
                return count[0] if count else 0
            except Exception as e:
                print(f"❌ 대기열 곡 수 조회 중 오류 발생: {e}")
                return 0

    async def remove_song(self, guild_id, url):
        """특정 곡 제거"""
        async with aiosqlite.connect(self.db_file) as db:
            try:
                await db.execute("""
                    DELETE FROM songs WHERE guild_id = ? AND url = ?
                """, (guild_id, url))
                await db.commit()
                print(f"✅ 곡 제거: guild_id={guild_id}, url={url}")
            except Exception as e:
                print(f"❌ 곡 제거 중 오류 발생: {e}")

    async def clear_songs(self, guild_id=None):
        """곡 데이터 초기화 (특정 서버 또는 전체)"""
        async with aiosqlite.connect(self.db_file) as db:
            try:
                if guild_id:
                    await db.execute("DELETE FROM songs WHERE guild_id = ?", (guild_id,))
                    print(f"✅ 특정 서버 곡 데이터 초기화 완료: guild_id={guild_id}")
                else:
                    await db.execute("DELETE FROM songs")
                    print("✅ 모든 서버 곡 데이터 초기화 완료")
                await db.commit()
            except Exception as e:
                print(f"❌ 곡 데이터 초기화 중 오류 발생: {e}")