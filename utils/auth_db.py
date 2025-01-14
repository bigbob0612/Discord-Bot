import sqlite3


class Database:
    def __init__(self, db_path="auth_channels.db"):
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self.initialize_database()

    def initialize_database(self):
        """데이터베이스 초기화"""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_channels (
            guild_id INTEGER PRIMARY KEY,
            auth_channel_id INTEGER,
            log_channel_id INTEGER
        )
        """)
        self.connection.commit()

    def set_auth_channel(self, guild_id, channel_id):
        """인증 채널 설정"""
        self.cursor.execute("""
        INSERT OR REPLACE INTO auth_channels (guild_id, auth_channel_id, log_channel_id)
        VALUES (?, ?, COALESCE((SELECT log_channel_id FROM auth_channels WHERE guild_id = ?), NULL))
        """, (guild_id, channel_id, guild_id))
        self.connection.commit()

    def get_auth_channel(self, guild_id):
        """인증 채널 가져오기"""
        self.cursor.execute("""
        SELECT auth_channel_id FROM auth_channels WHERE guild_id = ?
        """, (guild_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def set_log_channel(self, guild_id, channel_id):
        """로그 채널 설정"""
        self.cursor.execute("""
        INSERT OR REPLACE INTO auth_channels (guild_id, auth_channel_id, log_channel_id)
        VALUES (?, COALESCE((SELECT auth_channel_id FROM auth_channels WHERE guild_id = ?), NULL), ?)
        """, (guild_id, guild_id, channel_id))
        self.connection.commit()

    def get_log_channel(self, guild_id):
        """로그 채널 가져오기"""
        self.cursor.execute("""
        SELECT log_channel_id FROM auth_channels WHERE guild_id = ?
        """, (guild_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def remove_auth_channel(self, guild_id):
        """인증 채널 삭제"""
        self.cursor.execute("""
        UPDATE auth_channels
        SET auth_channel_id = NULL
        WHERE guild_id = ?
        """, (guild_id,))
        self.connection.commit()

    def remove_log_channel(self, guild_id):
        """로그 채널 삭제"""
        self.cursor.execute("""
        UPDATE auth_channels
        SET log_channel_id = NULL
        WHERE guild_id = ?
        """, (guild_id,))
        self.connection.commit()

    def get_all_guild_ids(self):
        """모든 서버 ID 가져오기"""
        self.cursor.execute("""
        SELECT guild_id FROM auth_channels
        """)
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        """데이터베이스 연결 닫기"""
        self.connection.close()