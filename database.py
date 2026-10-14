"""
database.py - Quản lý Cơ sở dữ liệu SQLite cho Website Thi Trắc Nghiệm Trực Tuyến
Được thiết kế cho môn học Lập Trình Mạng (BTL)
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "quiz_system.db")

def get_connection():
    """Tạo kết nối tới SQLite database và bật hỗ trợ Foreign Keys"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Khởi tạo cấu trúc các bảng dữ liệu nếu chưa tồn tại"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Bảng Ngân hàng câu hỏi (Questions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_answer TEXT NOT NULL, -- 'A', 'B', 'C', hoặc 'D'
        difficulty TEXT NOT NULL,     -- 'easy', 'medium', 'hard'
        category TEXT NOT NULL,       -- Chủ đề (Mạng máy tính, Giao thức, Kiến trúc mạng,...)
        explanation TEXT,             -- Lời giải thích chi tiết
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Bảng Phòng thi (Exam Rooms)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_rooms (
        room_code TEXT PRIMARY KEY,
        room_name TEXT NOT NULL,
        host_name TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        num_questions INTEGER NOT NULL,
        easy_count INTEGER DEFAULT 0,
        medium_count INTEGER DEFAULT 0,
        hard_count INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'waiting', -- 'waiting', 'in_progress', 'finished'
        question_ids_json TEXT,                 -- Danh sách ID câu hỏi của đề thi [1, 2, ...]
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        ended_at TIMESTAMP
    );
    """)

    # 3. Bảng Người tham gia phòng thi & Điểm số (Room Participants)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS room_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT NOT NULL,
        user_name TEXT NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        submitted_at TIMESTAMP,
        is_submitted BOOLEAN DEFAULT 0,
        score REAL DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        total_questions INTEGER DEFAULT 0,
        answers_json TEXT, -- Lưu đáp án người dùng chọn: {"1": "A", "2": "C"}
        FOREIGN KEY (room_code) REFERENCES exam_rooms(room_code) ON DELETE CASCADE,
        UNIQUE(room_code, user_name)
    );
    """)

    # 4. Bảng Lịch sử làm bài (Exam History) - Dùng cho cả Thi phòng và Luyện tập cá nhân
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        exam_type TEXT NOT NULL, -- 'room' hoặc 'practice'
        room_code TEXT,          -- Có thể NULL nếu là thi luyện tập
        title TEXT NOT NULL,     -- Tên phòng hoặc Tên bài luyện tập
        total_questions INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        score REAL NOT NULL,     -- Thang điểm 10
        duration_seconds INTEGER NOT NULL, -- Thời gian thực tế đã làm bài
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        details_json TEXT        -- Dữ liệu câu hỏi, đáp án chọn, đáp án đúng để xem lại chi tiết
    );
    """)

    conn.commit()
    conn.close()

def get_questions_by_difficulty(easy_count: int, medium_count: int, hard_count: int, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy ngẫu nhiên câu hỏi theo cấu hình số lượng từng độ khó"""
    conn = get_connection()
    cursor = conn.cursor()
    selected_questions = []

    configs = [
        ('easy', easy_count),
        ('medium', medium_count),
        ('hard', hard_count)
    ]

    for diff, count in configs:
        if count <= 0:
            continue
        query = "SELECT * FROM questions WHERE difficulty = ?"
        params = [diff]
        if category and category != 'all':
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(count)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        for r in rows:
            selected_questions.append(dict(r))

    conn.close()
    return selected_questions

def get_all_questions(difficulty: Optional[str] = None, category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Truy vấn danh sách toàn bộ câu hỏi có hỗ trợ lọc và tìm kiếm"""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM questions WHERE 1=1"
    params = []

    if difficulty and difficulty != 'all':
        query += " AND difficulty = ?"
        params.append(difficulty)
    if category and category != 'all':
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND content LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_question(content: str, option_a: str, option_b: str, option_c: str, option_d: str, 
                 correct_answer: str, difficulty: str, category: str, explanation: str = "") -> int:
    """Thêm một câu hỏi mới vào ngân hàng câu hỏi"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions (content, option_a, option_b, option_c, option_d, correct_answer, difficulty, category, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (content, option_a, option_b, option_c, option_d, correct_answer.upper(), difficulty, category, explanation))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def save_exam_history(user_name: str, exam_type: str, title: str, total_questions: int, 
                      correct_count: int, score: float, duration_seconds: int, 
                      details: Dict[str, Any], room_code: Optional[str] = None) -> int:
    """Lưu bài thi đã hoàn thành vào lịch sử của người dùng"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO exam_history (user_name, exam_type, room_code, title, total_questions, 
                                  correct_count, score, duration_seconds, details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_name, exam_type, room_code, title, total_questions, correct_count, score, 
          duration_seconds, json.dumps(details, ensure_ascii=False)))
    hist_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return hist_id

def get_user_exam_history(user_name: str) -> List[Dict[str, Any]]:
    """Lấy danh sách các bài thi mà người dùng đã thực hiện"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_name, exam_type, room_code, title, total_questions, 
               correct_count, score, duration_seconds, completed_at
        FROM exam_history
        WHERE user_name = ?
        ORDER BY completed_at DESC
    """, (user_name,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_history_detail(history_id: int) -> Optional[Dict[str, Any]]:
    """Lấy thông tin chi tiết (kèm danh sách câu hỏi & đáp án) của một bài thi cụ thể"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exam_history WHERE id = ?", (history_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    if data.get("details_json"):
        data["details"] = json.loads(data["details_json"])
    return data

def get_user_analytics(user_name: str) -> Dict[str, Any]:
    """Tổng hợp dữ liệu thống kê kết quả thi cho người dùng để vẽ đồ thị"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM exam_history WHERE user_name = ? ORDER BY completed_at ASC", (user_name,))
    history_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    total_exams = len(history_rows)
    if total_exams == 0:
        return {
            "total_exams": 0,
            "avg_score": 0.0,
            "highest_score": 0.0,
            "overall_accuracy": 0.0,
            "score_trend": [],
            "difficulty_stats": {"easy": {"correct": 0, "total": 0}, "medium": {"correct": 0, "total": 0}, "hard": {"correct": 0, "total": 0}},
            "results_distribution": {"correct": 0, "wrong": 0}
        }

    scores = [r["score"] for r in history_rows]
    avg_score = round(sum(scores) / total_exams, 2)
    highest_score = max(scores)

    total_correct = sum(r["correct_count"] for r in history_rows)
    total_q = sum(r["total_questions"] for r in history_rows)
    overall_accuracy = round((total_correct / total_q * 100), 1) if total_q > 0 else 0.0

    # Dữ liệu biến động điểm số theo thời gian (Line chart)
    score_trend = []
    for r in history_rows:
        score_trend.append({
            "id": r["id"],
            "title": r["title"],
            "date": r["completed_at"],
            "score": r["score"],
            "correct_count": r["correct_count"],
            "total_questions": r["total_questions"]
        })

    # Phân tích theo độ khó (Dễ / Trung bình / Khó)
    diff_stats = {
        "easy": {"correct": 0, "total": 0},
        "medium": {"correct": 0, "total": 0},
        "hard": {"correct": 0, "total": 0}
    }

    for r in history_rows:
        try:
            details = json.loads(r["details_json"])
            for q in details.get("questions", []):
                diff = q.get("difficulty", "medium").lower()
                if diff not in diff_stats:
                    diff = "medium"
                diff_stats[diff]["total"] += 1
                if q.get("user_answer") == q.get("correct_answer"):
                    diff_stats[diff]["correct"] += 1
        except Exception:
            pass

    return {
        "total_exams": total_exams,
        "avg_score": avg_score,
        "highest_score": highest_score,
        "overall_accuracy": overall_accuracy,
        "score_trend": score_trend,
        "difficulty_stats": diff_stats,
        "results_distribution": {
            "correct": total_correct,
            "wrong": total_q - total_correct
        }
    }
