import sqlite3

class RaidDatabase:
    def __init__(self, db_path="raid.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """테이블 생성"""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS raids (
            raid_type TEXT,
            raid_name TEXT,
            link TEXT,
            PRIMARY KEY (raid_type, raid_name)
        )
        """)
        self.conn.commit()

    def add_raid(self, raid_type, raid_name, link):
        """레이드 추가"""
        self.cursor.execute("""
        INSERT OR IGNORE INTO raids (raid_type, raid_name, link)
        VALUES (?, ?, ?)
        """, (raid_type, raid_name, link))
        self.conn.commit()

    def update_raid(self, raid_type, raid_name, link):
        """레이드 수정"""
        self.cursor.execute("""
        UPDATE raids
        SET link = ?
        WHERE raid_type = ? AND raid_name = ?
        """, (link, raid_type, raid_name))
        self.conn.commit()

    def delete_raid(self, raid_type, raid_name):
        """레이드 삭제"""
        self.cursor.execute("""
        DELETE FROM raids
        WHERE raid_type = ? AND raid_name = ?
        """, (raid_type, raid_name))
        self.conn.commit()

    def get_raids_by_type(self, raid_type):
        """특정 레이드 종류의 모든 레이드 반환"""
        self.cursor.execute("""
        SELECT raid_name, link
        FROM raids
        WHERE raid_type = ?
        """, (raid_type,))
        return self.cursor.fetchall()

    def get_all_raid_types(self):
        """모든 레이드 종류 반환"""
        self.cursor.execute("""
        SELECT DISTINCT raid_type
        FROM raids
        """)
        return [row[0] for row in self.cursor.fetchall()]

    def raid_exists(self, raid_type, raid_name):
        """특정 레이드가 존재하는지 확인"""
        self.cursor.execute("""
        SELECT 1
        FROM raids
        WHERE raid_type = ? AND raid_name = ?
        """, (raid_type, raid_name))
        return self.cursor.fetchone() is not None