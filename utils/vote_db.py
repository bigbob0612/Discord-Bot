import sqlite3


class VoteDatabase:
    def __init__(self, db_path="vote.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """데이터베이스 테이블 생성"""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            channel_id INTEGER PRIMARY KEY,
            vote_title TEXT,
            vote_type TEXT,
            end_time TEXT,
            participants TEXT,
            choices TEXT,
            is_active BOOLEAN DEFAULT 1
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS vote_channels (
            channel_id INTEGER PRIMARY KEY
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_votes (
            channel_id INTEGER,
            user_id INTEGER,
            choice TEXT,
            PRIMARY KEY (channel_id, user_id)
        )
        """)
        self.conn.commit()

    def add_vote_channel(self, channel_id):
        """투표 채널 추가"""
        self.cursor.execute("""
        INSERT INTO vote_channels (channel_id)
        VALUES (?)
        """, (channel_id,))
        self.conn.commit()

    def is_vote_channel(self, channel_id):
        """채널이 투표 채널인지 확인"""
        self.cursor.execute("""
        SELECT 1
        FROM vote_channels
        WHERE channel_id = ?
        """, (channel_id,))
        return self.cursor.fetchone() is not None

    def delete_vote_channel(self, channel_id):
        """투표 채널 삭제"""
        self.cursor.execute("""
        DELETE FROM vote_channels
        WHERE channel_id = ?
        """, (channel_id,))
        self.conn.commit()

    def create_vote(self, channel_id, title, vote_type, end_time, participants, choices):
        """새로운 투표 생성"""
        self.cursor.execute("""
        INSERT INTO votes (channel_id, vote_title, vote_type, end_time, participants, choices, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (channel_id, title, vote_type, end_time, participants, ",".join(choices)))
        self.conn.commit()

    def get_active_vote(self, channel_id):
        """현재 채널에서 진행 중인 투표를 반환"""
        self.cursor.execute("""
        SELECT vote_title, vote_type, end_time, participants, choices
        FROM votes
        WHERE channel_id = ? AND is_active = 1
        """, (channel_id,))
        vote = self.cursor.fetchone()
        if vote:
            return {
                "title": vote[0],
                "vote_type": vote[1],
                "end_time": vote[2],
                "participants": vote[3],
                "choices": vote[4].split(","),
            }
        return None

    def deactivate_vote(self, channel_id):
        """투표 종료"""
        self.cursor.execute("""
        UPDATE votes
        SET is_active = 0
        WHERE channel_id = ?
        """, (channel_id,))
        self.conn.commit()

    def has_voted(self, channel_id, user_id):
        """사용자가 투표했는지 확인"""
        self.cursor.execute("""
        SELECT 1
        FROM user_votes
        WHERE channel_id = ? AND user_id = ?
        """, (channel_id, user_id))
        return self.cursor.fetchone() is not None

    def cast_vote(self, channel_id, user_id, choice):
        """사용자의 투표 저장"""
        self.cursor.execute("""
        INSERT OR REPLACE INTO user_votes (channel_id, user_id, choice)
        VALUES (?, ?, ?)
        """, (channel_id, user_id, choice))
        self.conn.commit()

    def modify_vote(self, channel_id, user_id, new_choice):
        """사용자의 투표 수정"""
        self.cursor.execute("""
        UPDATE user_votes
        SET choice = ?
        WHERE channel_id = ? AND user_id = ?
        """, (new_choice, channel_id, user_id))
        self.conn.commit()

    def get_vote_results(self, channel_id):
        """투표 결과 반환 (일반 투표: 사용자와 선택, 비밀 투표: 선택지별 표 수)"""
        self.cursor.execute("""
        SELECT user_id, choice
        FROM user_votes
        WHERE channel_id = ?
        """, (channel_id,))
        return self.cursor.fetchall()
    
    def get_latest_vote(self, channel_id):
        """가장 최근에 종료된 투표를 반환"""
        self.cursor.execute("""
            SELECT channel_id, vote_title, vote_type, end_time, participants, choices
            FROM votes
            WHERE channel_id = ? AND is_active = 0
            ORDER BY end_time DESC LIMIT 1
        """, (channel_id,))
        vote = self.cursor.fetchone()
        if vote:
            return {
                "channel_id": vote[0],
                "title": vote[1],
                "vote_type": vote[2],
                "end_time": vote[3],
                "participants": vote[4],
                "choices": vote[5].split(","),
            }
        return None
    
    def get_choice_counts(self, channel_id):
        """선택지별 투표 수 반환"""
        self.cursor.execute("""
        SELECT choice, COUNT(*)
        FROM user_votes
        WHERE channel_id = ?
        GROUP BY choice
        """, (channel_id,))
        return self.cursor.fetchall()

    def count_total_votes(self, channel_id):
        """현재 채널에서 투표에 참여한 총 사용자 수"""
        self.cursor.execute("""
        SELECT COUNT(*)
        FROM user_votes
        WHERE channel_id = ?
        """, (channel_id,))
        return self.cursor.fetchone()[0]
    
    def delete_votes_in_channel(self, channel_id):
        """특정 채널의 모든 투표 데이터를 삭제"""
        self.cursor.execute("""
        DELETE FROM votes
        WHERE channel_id = ?
        """, (channel_id,))
        self.cursor.execute("""
        DELETE FROM user_votes
        WHERE channel_id = ?
        """, (channel_id,))
        self.conn.commit()