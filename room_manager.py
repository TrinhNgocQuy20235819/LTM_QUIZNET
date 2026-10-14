"""
room_manager.py - Quản lý Phòng thi & Giao tiếp Mạng thời gian thực (Real-time WebSockets)
Hỗ trợ: Đồng bộ phòng thi, phát đề, kiểm soát thời gian, thu bài, chấm điểm tự động.
"""

import asyncio
import json
import time
import random
import string
from typing import Dict, List, Optional, Any
from fastapi import WebSocket

from database import (
    get_connection, get_questions_by_difficulty, 
    save_exam_history
)

def generate_room_code(length=6) -> str:
    """Sinh mã phòng ngẫu nhiên 6 ký tự gồm chữ hoa và số"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class Participant:
    def __init__(self, user_name: str, is_host: bool = False):
        self.user_name = user_name
        self.is_host = is_host
        self.websocket: Optional[WebSocket] = None
        self.joined_at = time.time()
        self.answers: Dict[str, str] = {} # { "q_id": "A" }
        self.is_submitted = False
        self.submitted_at: Optional[float] = None
        self.score: float = 0.0
        self.correct_count: int = 0
        self.total_questions: int = 0

    def to_dict(self):
        return {
            "user_name": self.user_name,
            "is_host": self.is_host,
            "is_submitted": self.is_submitted,
            "score": self.score,
            "correct_count": self.correct_count,
            "total_questions": self.total_questions,
            "submitted_at": self.submitted_at
        }

class ExamRoom:
    def __init__(self, room_code: str, room_name: str, host_name: str, 
                 duration_minutes: int, easy_count: int, medium_count: int, hard_count: int):
        self.room_code = room_code
        self.room_name = room_name
        self.host_name = host_name
        self.duration_minutes = duration_minutes
        self.duration_seconds = duration_minutes * 60
        self.easy_count = easy_count
        self.medium_count = medium_count
        self.hard_count = hard_count
        self.num_questions = easy_count + medium_count + hard_count
        self.status = "waiting" # 'waiting', 'in_progress', 'finished'
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.ended_at: Optional[float] = None
        
        # Danh sách câu hỏi đầy đủ (kèm đáp án đúng dùng để chấm)
        self.questions: List[Dict[str, Any]] = []
        # Người tham gia: user_name -> Participant
        self.participants: Dict[str, Participant] = {}
        # Task đếm ngược thời gian của server
        self.timer_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def get_public_questions(self) -> List[Dict[str, Any]]:
        """Trả về danh sách câu hỏi đã ẩn đáp án đúng và giải thích để phát cho thí sinh"""
        public_list = []
        for q in self.questions:
            public_list.append({
                "id": q["id"],
                "content": q["content"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "difficulty": q["difficulty"],
                "category": q["category"]
            })
        return public_list

    async def broadcast(self, message: Dict[str, Any]):
        """Gửi gói tin WebSocket tới tất cả người tham gia trong phòng đang kết nối"""
        data_text = json.dumps(message, ensure_ascii=False)
        disconnected = []
        for uname, p in self.participants.items():
            if p.websocket:
                try:
                    await p.websocket.send_text(data_text)
                except Exception:
                    disconnected.append(uname)
        for uname in disconnected:
            self.participants[uname].websocket = None

    def calculate_results_leaderboard(self) -> List[Dict[str, Any]]:
        """Tính bảng xếp hạng điểm số của phòng thi theo thứ tự điểm giảm dần, thời gian nộp nhanh hơn xếp trên"""
        leaderboard = []
        for uname, p in self.participants.items():
            time_taken = int((p.submitted_at - self.started_at)) if (p.submitted_at and self.started_at) else self.duration_seconds
            if time_taken < 0:
                time_taken = 0
            leaderboard.append({
                "user_name": uname,
                "is_host": p.is_host,
                "is_submitted": p.is_submitted,
                "score": p.score,
                "correct_count": p.correct_count,
                "total_questions": len(self.questions) if self.questions else self.num_questions,
                "time_taken_seconds": time_taken
            })
        # Sắp xếp: Điểm giảm dần, thời gian làm bài tăng dần
        leaderboard.sort(key=lambda x: (-x["score"], x["time_taken_seconds"]))
        # Gán thứ hạng
        for rank, item in enumerate(leaderboard, start=1):
            item["rank"] = rank
        return leaderboard

    def grade_participant(self, user_name: str) -> Dict[str, Any]:
        """Chấm bài của một thí sinh dựa trên danh sách câu hỏi và đáp án đã chọn"""
        p = self.participants.get(user_name)
        if not p or not self.questions:
            return {"score": 0.0, "correct_count": 0, "total": 0, "details": []}

        correct_count = 0
        details = []

        for q in self.questions:
            q_id_str = str(q["id"])
            user_ans = p.answers.get(q_id_str, "").upper()
            correct_ans = q["correct_answer"].upper()
            is_correct = (user_ans == correct_ans)
            if is_correct:
                correct_count += 1

            details.append({
                "question_id": q["id"],
                "content": q["content"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "difficulty": q["difficulty"],
                "category": q["category"],
                "explanation": q.get("explanation", "")
            })

        total_q = len(self.questions)
        score = round((correct_count / total_q) * 10, 2) if total_q > 0 else 0.0

        p.score = score
        p.correct_count = correct_count
        p.total_questions = total_q
        p.is_submitted = True
        if not p.submitted_at:
            p.submitted_at = time.time()

        # Lưu kết quả vào DB
        self.save_participant_result_to_db(p, details)

        return {
            "score": score,
            "correct_count": correct_count,
            "total_questions": total_q,
            "details": details
        }

    def save_participant_result_to_db(self, p: Participant, details: List[Dict[str, Any]]):
        """Lưu điểm người tham gia vào bảng room_participants và bảng exam_history"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO room_participants 
                (room_code, user_name, submitted_at, is_submitted, score, correct_count, total_questions, answers_json)
                VALUES (?, ?, datetime('now'), 1, ?, ?, ?, ?)
            """, (self.room_code, p.user_name, p.score, p.correct_count, p.total_questions, json.dumps(p.answers)))
            conn.commit()
            conn.close()

            # Lưu vào lịch sử người dùng
            duration = int((p.submitted_at - self.started_at)) if (p.submitted_at and self.started_at) else self.duration_seconds
            save_exam_history(
                user_name=p.user_name,
                exam_type="room",
                title=f"Phòng thi: {self.room_name} ({self.room_code})",
                total_questions=p.total_questions,
                correct_count=p.correct_count,
                score=p.score,
                duration_seconds=max(0, duration),
                details={"questions": details, "room_code": self.room_code, "room_name": self.room_name},
                room_code=self.room_code
            )
        except Exception as e:
            print(f"Lỗi khi lưu kết quả bài thi vào DB: {e}")

    def to_summary(self):
        """Thông tin tóm tắt phòng thi để hiển thị ở danh sách phòng"""
        return {
            "room_code": self.room_code,
            "room_name": self.room_name,
            "host_name": self.host_name,
            "duration_minutes": self.duration_minutes,
            "num_questions": self.num_questions,
            "easy_count": self.easy_count,
            "medium_count": self.medium_count,
            "hard_count": self.hard_count,
            "status": self.status, # 'waiting', 'in_progress', 'finished'
            "participant_count": len(self.participants),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "ended_at": self.ended_at
        }


class RoomManager:
    """Quản lý tập hợp tất cả các phòng thi trong hệ thống"""
    def __init__(self):
        self.rooms: Dict[str, ExamRoom] = {}
        # Danh sách WebSocket client đang ở trang sảnh (Lobby) để nhận thông báo real-time khi phòng thay đổi
        self.lobby_websockets: List[WebSocket] = []
        self._lock = asyncio.Lock()

    def load_existing_rooms_from_db(self):
        """Đọc lại các phòng thi đã lưu trong DB (đặc biệt là các phòng đã kết thúc) để người dùng xem kết quả"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exam_rooms ORDER BY created_at DESC LIMIT 50")
        rows = cursor.fetchall()
        for r in rows:
            code = r["room_code"]
            if code not in self.rooms:
                room = ExamRoom(
                    room_code=code,
                    room_name=r["room_name"],
                    host_name=r["host_name"],
                    duration_minutes=r["duration_minutes"],
                    easy_count=r["easy_count"],
                    medium_count=r["medium_count"],
                    hard_count=r["hard_count"]
                )
                room.status = r["status"]
                # Nạp danh sách câu hỏi nếu có
                if r["question_ids_json"]:
                    try:
                        q_ids = json.loads(r["question_ids_json"])
                        if q_ids:
                            placeholders = ','.join('?' for _ in q_ids)
                            q_cursor = conn.cursor()
                            q_cursor.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", q_ids)
                            room.questions = [dict(row) for row in q_cursor.fetchall()]
                    except Exception:
                        pass
                
                # Nạp người tham gia từ DB
                p_cursor = conn.cursor()
                p_cursor.execute("SELECT * FROM room_participants WHERE room_code = ?", (code,))
                for p_row in p_cursor.fetchall():
                    part = Participant(user_name=p_row["user_name"], is_host=(p_row["user_name"] == room.host_name))
                    part.is_submitted = bool(p_row["is_submitted"])
                    part.score = p_row["score"]
                    part.correct_count = p_row["correct_count"]
                    part.total_questions = p_row["total_questions"]
                    if p_row["answers_json"]:
                        try:
                            part.answers = json.loads(p_row["answers_json"])
                        except Exception:
                            pass
                    room.participants[p_row["user_name"]] = part

                self.rooms[code] = room
        conn.close()

    async def broadcast_lobby_update(self):
        """Gửi danh sách phòng thi cập nhật tới tất cả client đang theo dõi ở sảnh"""
        rooms_list = self.get_all_rooms_summary()
        payload = json.dumps({"type": "LOBBY_ROOMS_UPDATE", "rooms": rooms_list}, ensure_ascii=False)
        disconnected = []
        for ws in self.lobby_websockets:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            if ws in self.lobby_websockets:
                self.lobby_websockets.remove(ws)

    def get_all_rooms_summary(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tóm tắt tất cả các phòng thi"""
        return [room.to_summary() for room in sorted(self.rooms.values(), key=lambda r: r.created_at, reverse=True)]

    def get_room(self, room_code: str) -> Optional[ExamRoom]:
        return self.rooms.get(room_code.upper())

    async def create_room(self, room_name: str, host_name: str, duration_minutes: int,
                          easy_count: int, medium_count: int, hard_count: int) -> ExamRoom:
        """Tạo phòng thi mới, lưu vào DB và phát sóng cập nhật"""
        room_code = generate_room_code()
        while room_code in self.rooms:
            room_code = generate_room_code()

        room = ExamRoom(
            room_code=room_code,
            room_name=room_name,
            host_name=host_name,
            duration_minutes=duration_minutes,
            easy_count=easy_count,
            medium_count=medium_count,
            hard_count=hard_count
        )
        
        # Tự động thêm chủ phòng vào danh sách người tham gia
        host_p = Participant(user_name=host_name, is_host=True)
        room.participants[host_name] = host_p

        self.rooms[room_code] = room

        # Lưu phòng vào DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO exam_rooms (room_code, room_name, host_name, duration_minutes, num_questions, 
                                    easy_count, medium_count, hard_count, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'waiting')
        """, (room_code, room_name, host_name, duration_minutes, room.num_questions, 
              easy_count, medium_count, hard_count))
        cursor.execute("""
            INSERT OR REPLACE INTO room_participants (room_code, user_name) VALUES (?, ?)
        """, (room_code, host_name))
        conn.commit()
        conn.close()

        await self.broadcast_lobby_update()
        return room

    async def start_exam(self, room_code: str, host_name: str) -> bool:
        """Chủ phòng bấm Bắt đầu thi: Chọn câu hỏi theo độ khó, phát đề, khởi động bộ đếm ngược"""
        room = self.get_room(room_code)
        if not room or room.host_name != host_name or room.status != "waiting":
            return False

        # Chọn câu hỏi từ ngân hàng câu hỏi
        questions = get_questions_by_difficulty(
            easy_count=room.easy_count,
            medium_count=room.medium_count,
            hard_count=room.hard_count
        )
        # Nếu không đủ số lượng câu theo từng độ khó, lấy bổ sung bất kỳ
        if len(questions) < room.num_questions:
            needed = room.num_questions - len(questions)
            conn = get_connection()
            cursor = conn.cursor()
            existing_ids = [q["id"] for q in questions]
            query = "SELECT * FROM questions"
            params = []
            if existing_ids:
                placeholders = ','.join('?' for _ in existing_ids)
                query += f" WHERE id NOT IN ({placeholders})"
                params = existing_ids
            query += " ORDER BY RANDOM() LIMIT ?"
            params.append(needed)
            cursor.execute(query, params)
            for row in cursor.fetchall():
                questions.append(dict(row))
            conn.close()

        room.questions = questions
        room.status = "in_progress"
        room.started_at = time.time()
        room.ended_at = room.started_at + room.duration_seconds

        # Lưu danh sách ID câu hỏi vào DB
        q_ids = [q["id"] for q in questions]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE exam_rooms 
            SET status = 'in_progress', started_at = datetime('now'), question_ids_json = ?
            WHERE room_code = ?
        """, (json.dumps(q_ids), room_code))
        conn.commit()
        conn.close()

        # Phát sóng sự kiện EXAM_STARTED kèm đề thi (đã ẩn đáp án đúng) tới tất cả thí sinh
        public_questions = room.get_public_questions()
        await room.broadcast({
            "type": "EXAM_STARTED",
            "room_code": room.room_code,
            "room_name": room.room_name,
            "questions": public_questions,
            "duration_seconds": room.duration_seconds,
            "started_at": room.started_at,
            "ends_at": room.ended_at
        })

        # Cập nhật danh sách phòng ở Sảnh (chuyển sang 'Đang diễn ra')
        await self.broadcast_lobby_update()

        # Khởi chạy bộ đếm ngược tự động của server
        async def timer_countdown():
            await asyncio.sleep(room.duration_seconds)
            # Khi hết giờ, tự động kết thúc bài thi nếu phòng vẫn đang diễn ra
            if room.status == "in_progress":
                await self.end_exam(room.room_code, reason="TIME_UP")

        room.timer_task = asyncio.create_task(timer_countdown())
        return True

    async def end_exam(self, room_code: str, reason: str = "HOST_ENDED") -> bool:
        """Kết thúc bài thi: Chấm điểm toàn bộ thí sinh, lưu DB, phát bảng xếp hạng kết quả"""
        room = self.get_room(room_code)
        if not room or room.status == "finished":
            return False

        if room.timer_task and not room.timer_task.done():
            room.timer_task.cancel()

        room.status = "finished"
        room.ended_at = time.time()

        # Chấm bài cho tất cả thí sinh (kể cả những ai chưa bấm nộp bài thủ công)
        for uname, p in room.participants.items():
            if not p.is_submitted:
                room.grade_participant(uname)

        # Cập nhật DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE exam_rooms 
            SET status = 'finished', ended_at = datetime('now')
            WHERE room_code = ?
        """, (room_code,))
        conn.commit()
        conn.close()

        leaderboard = room.calculate_results_leaderboard()

        # Phát sóng kết quả thi tới từng thí sinh
        for uname, p in room.participants.items():
            if p.websocket:
                # Gửi bảng xếp hạng chung + chi tiết bài làm cá nhân của chính thí sinh đó
                grade_info = room.grade_participant(uname)
                try:
                    await p.websocket.send_text(json.dumps({
                        "type": "EXAM_FINISHED",
                        "reason": reason,
                        "room_code": room_code,
                        "leaderboard": leaderboard,
                        "personal_result": {
                            "score": p.score,
                            "correct_count": p.correct_count,
                            "total_questions": len(room.questions),
                            "details": grade_info.get("details", [])
                        }
                    }, ensure_ascii=False))
                except Exception:
                    pass

        # Cập nhật danh sách phòng ở Sảnh (chuyển sang 'Đã kết thúc')
        await self.broadcast_lobby_update()
        return True


# Khởi tạo instance Singleton toàn cục của RoomManager
room_manager = RoomManager()
