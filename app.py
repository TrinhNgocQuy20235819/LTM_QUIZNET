"""
app.py - Máy chủ Web & API Trung tâm cho Hệ Thống Thi Trắc Nghiệm Trực Tuyến
Công nghệ: FastAPI + WebSockets + Uvicorn + SQLite
Phục vụ môn học: Lập Trình Mạng (Network Programming)
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import json
import asyncio
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from database import (
    init_db, get_connection, get_all_questions, add_question,
    get_questions_by_difficulty, save_exam_history,
    get_user_exam_history, get_history_detail, get_user_analytics
)
from seed_questions import seed_database
from models import (
    CreateRoomRequest, StartPracticeRequest, 
    SubmitPracticeRequest, AddQuestionRequest
)
from room_manager import room_manager, Participant

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Vòng đời ứng dụng: Khởi tạo CSDL, nạp câu hỏi mẫu và nạp các phòng thi hiện có"""
    print("[SERVER] Khởi tạo Cơ sở dữ liệu SQLite...")
    init_db()
    seed_database()
    print("[SERVER] Nạp trạng thái các phòng thi từ CSDL...")
    room_manager.load_existing_rooms_from_db()
    print("[SERVER] Hệ thống thi trắc nghiệm đã sẵn sàng hoạt động!")
    yield
    print("[SERVER] Đang dừng máy chủ...")

app = FastAPI(
    title="Hệ Thống Thi Trắc Nghiệm Mạng Trực Tuyến",
    description="Ứng dụng thi trắc nghiệm hỗ trợ phòng thi mạng thời gian thực (WebSockets) & chế độ luyện tập",
    version="1.0.0",
    lifespan=lifespan
)

# Cấu hình CORS để hỗ trợ mọi kết nối nội bộ hoặc mở rộng
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# CÁC API RESTful (HTTP)
# ==========================================

@app.get("/api/categories")
async def get_categories():
    """Lấy danh sách các chủ đề kiến thức có trong ngân hàng câu hỏi"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM questions ORDER BY category ASC")
    cats = [row["category"] for row in cursor.fetchall()]
    conn.close()
    return {"categories": cats}

@app.get("/api/questions")
async def list_questions(
    difficulty: Optional[str] = Query("all"),
    category: Optional[str] = Query("all"),
    search: Optional[str] = Query(None)
):
    """Truy vấn danh sách câu hỏi trong ngân hàng theo bộ lọc"""
    questions = get_all_questions(difficulty, category, search)
    return {"total": len(questions), "questions": questions}

@app.post("/api/questions")
async def create_question(req: AddQuestionRequest):
    """Thêm một câu hỏi mới vào ngân hàng câu hỏi"""
    new_id = add_question(
        content=req.content,
        option_a=req.option_a,
        option_b=req.option_b,
        option_c=req.option_c,
        option_d=req.option_d,
        correct_answer=req.correct_answer,
        difficulty=req.difficulty,
        category=req.category,
        explanation=req.explanation or ""
    )
    return {"success": True, "message": "Đã thêm câu hỏi thành công!", "question_id": new_id}

@app.get("/api/rooms")
async def list_rooms():
    """Xem danh sách các phòng thi và trạng thái tương ứng (waiting, in_progress, finished)"""
    rooms = room_manager.get_all_rooms_summary()
    return {"rooms": rooms}

@app.post("/api/rooms")
async def create_room(req: CreateRoomRequest):
    """Tạo phòng thi mới với cấu hình số lượng câu, độ khó, thời gian làm bài"""
    total_q = req.easy_count + req.medium_count + req.hard_count
    if total_q <= 0:
        raise HTTPException(status_code=400, detail="Tổng số câu hỏi phải lớn hơn 0")

    room = await room_manager.create_room(
        room_name=req.room_name,
        host_name=req.host_name,
        duration_minutes=req.duration_minutes,
        easy_count=req.easy_count,
        medium_count=req.medium_count,
        hard_count=req.hard_count
    )
    return {
        "success": True,
        "message": "Tạo phòng thi thành công!",
        "room_code": room.room_code,
        "room": room.to_summary()
    }

@app.get("/api/rooms/{room_code}")
async def get_room_detail(room_code: str):
    """Lấy thông tin chi tiết của một phòng thi"""
    room = room_manager.get_room(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng thi này!")
    
    participants = [p.to_dict() for p in room.participants.values()]
    return {
        "room": room.to_summary(),
        "participants": participants
    }

@app.get("/api/rooms/{room_code}/results")
async def get_room_results(room_code: str):
    """Xem kết quả thi của phòng thi đã kết thúc (Bảng xếp hạng điểm số & thí sinh)"""
    room = room_manager.get_room(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng thi này!")
    
    if room.status != "finished":
        raise HTTPException(status_code=400, detail="Phòng thi chưa kết thúc, chưa thể xem bảng kết quả chính thức!")

    leaderboard = room.calculate_results_leaderboard()
    return {
        "room_code": room.room_code,
        "room_name": room.room_name,
        "duration_minutes": room.duration_minutes,
        "total_questions": len(room.questions) if room.questions else room.num_questions,
        "leaderboard": leaderboard
    }

# ==========================================
# CHẾ ĐỘ LUYỆN TẬP (PRACTICE MODE)
# ==========================================

@app.post("/api/practice/start")
async def start_practice(req: StartPracticeRequest):
    """Bắt đầu bài thi luyện tập cá nhân: Chọn ngẫu nhiên câu hỏi theo cấu hình độ khó"""
    questions = get_questions_by_difficulty(
        easy_count=req.easy_count,
        medium_count=req.medium_count,
        hard_count=req.hard_count,
        category=req.category
    )

    total_requested = req.easy_count + req.medium_count + req.hard_count
    if len(questions) < total_requested:
        # Bổ sung câu hỏi nếu chưa đủ
        needed = total_requested - len(questions)
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

    if not questions:
        raise HTTPException(status_code=400, detail="Không có câu hỏi phù hợp với yêu cầu!")

    # Ẩn đáp án đúng khi gửi về client
    public_questions = []
    for q in questions:
        public_questions.append({
            "id": q["id"],
            "content": q["content"],
            "option_a": q["option_a"],
            "option_b": q["option_b"],
            "option_c": q["option_c"],
            "option_d": q["option_d"],
            "difficulty": q["difficulty"],
            "category": q["category"]
        })

    return {
        "success": True,
        "total_questions": len(public_questions),
        "duration_seconds": req.duration_minutes * 60,
        "questions": public_questions
    }

@app.post("/api/practice/submit")
async def submit_practice(req: SubmitPracticeRequest):
    """Nộp bài thi luyện tập: Chấm điểm, thông báo số câu đúng và lưu lịch sử làm bài"""
    if not req.question_ids:
        raise HTTPException(status_code=400, detail="Danh sách câu hỏi trống!")

    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ','.join('?' for _ in req.question_ids)
    cursor.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", req.question_ids)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Map question id to question data
    q_map = {q["id"]: q for q in rows}

    correct_count = 0
    details = []

    for q_id in req.question_ids:
        q = q_map.get(q_id)
        if not q:
            continue
        user_ans = req.answers.get(str(q_id), "").upper()
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

    total_q = len(req.question_ids)
    score = round((correct_count / total_q) * 10, 2) if total_q > 0 else 0.0

    # Lưu vào lịch sử người dùng
    save_exam_history(
        user_name=req.user_name,
        exam_type="practice",
        title=f"Luyện tập ({total_q} câu hỏi)",
        total_questions=total_q,
        correct_count=correct_count,
        score=score,
        duration_seconds=req.duration_seconds,
        details={"questions": details}
    )

    return {
        "success": True,
        "score": score,
        "correct_count": correct_count,
        "total_questions": total_q,
        "percentage": round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0,
        "details": details
    }

# ==========================================
# LỊCH SỬ & THỐNG KÊ (HISTORY & ANALYTICS)
# ==========================================

@app.get("/api/history/{user_name}")
async def get_history(user_name: str):
    """Xem danh sách các bài thi người dùng đã làm (Cả phòng thi và luyện tập)"""
    history = get_user_exam_history(user_name)
    return {"history": history}

@app.get("/api/history/detail/{history_id}")
async def get_history_by_id(history_id: int):
    """Xem chi tiết bài thi đã làm trong quá khứ kèm câu trả lời và lời giải"""
    detail = get_history_detail(history_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài thi này!")
    return detail

@app.get("/api/analytics/{user_name}")
async def get_analytics(user_name: str):
    """Thống kê bằng đồ thị về các bài thi người dùng đã làm"""
    analytics = get_user_analytics(user_name)
    return analytics


# ==========================================
# WEBSOCKETS - GIAO TIẾP MẠNG THỜI GIAN THỰC
# ==========================================

@app.websocket("/ws/lobby")
async def websocket_lobby(websocket: WebSocket):
    """WebSocket cho màn hình Sảnh: Nhận các thông báo cập nhật phòng thi theo thời gian thực"""
    await websocket.accept()
    room_manager.lobby_websockets.append(websocket)
    try:
        # Gửi ngay danh sách phòng hiện tại cho client
        await websocket.send_text(json.dumps({
            "type": "LOBBY_ROOMS_UPDATE",
            "rooms": room_manager.get_all_rooms_summary()
        }, ensure_ascii=False))

        # Giữ kết nối mở để lắng nghe ping hoặc ngắt kết nối
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if websocket in room_manager.lobby_websockets:
            room_manager.lobby_websockets.remove(websocket)


@app.websocket("/ws/room/{room_code}/{user_name}")
async def websocket_room(websocket: WebSocket, room_code: str, user_name: str):
    """
    WebSocket phòng thi: Xử lý tương tác thời gian thực giữa Thí sinh và Chủ phòng
    - Thí sinh vào phòng chờ
    - Chủ phòng bắt đầu thi (phát đề thi từ server)
    - Thay đổi đáp án đã chọn trong lúc làm bài
    - Nộp bài sớm hoặc nộp khi hết giờ
    - Chủ phòng kết thúc phòng thi
    - Thông báo điểm số và bảng xếp hạng
    """
    await websocket.accept()
    room = room_manager.get_room(room_code)

    if not room:
        await websocket.send_text(json.dumps({
            "type": "ERROR",
            "message": f"Không tìm thấy phòng thi với mã {room_code}!"
        }, ensure_ascii=False))
        await websocket.close()
        return

    # Nếu phòng đã kết thúc, gửi thông báo và kết quả ngay
    if room.status == "finished":
        leaderboard = room.calculate_results_leaderboard()
        await websocket.send_text(json.dumps({
            "type": "ROOM_ALREADY_FINISHED",
            "room_code": room_code,
            "leaderboard": leaderboard
        }, ensure_ascii=False))
        await websocket.close()
        return

    # Nếu phòng đang thi và người này chưa từng tham gia lúc chờ -> Không cho vào giữa chừng
    if room.status == "in_progress" and user_name not in room.participants:
        await websocket.send_text(json.dumps({
            "type": "ERROR",
            "message": "Phòng thi đã bắt đầu, bạn không thể tham gia giữa chừng!"
        }, ensure_ascii=False))
        await websocket.close()
        return

    # Đăng ký / Cập nhật người tham gia
    is_host = (user_name == room.host_name)
    if user_name not in room.participants:
        p = Participant(user_name=user_name, is_host=is_host)
        room.participants[user_name] = p
    else:
        p = room.participants[user_name]
    p.websocket = websocket

    # Lưu người tham gia vào DB
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO room_participants (room_code, user_name) VALUES (?, ?)
    """, (room.room_code, user_name))
    conn.commit()
    conn.close()

    # Thông báo cho tất cả người trong phòng biết có thành viên mới tham gia hoặc kết nối lại
    participants_list = [part.to_dict() for part in room.participants.values()]
    await room.broadcast({
        "type": "PARTICIPANT_JOINED",
        "user_name": user_name,
        "is_host": is_host,
        "room_status": room.status,
        "participants": participants_list
    })

    # Cập nhật số lượng người tham gia ở trang Sảnh
    await room_manager.broadcast_lobby_update()

    # Nếu người này vào lại khi bài thi đang diễn ra, gửi lại đề thi cho họ tiếp tục làm bài
    if room.status == "in_progress":
        remaining_seconds = int(room.ended_at - time.time()) if room.ended_at else 0
        await websocket.send_text(json.dumps({
            "type": "EXAM_RECONNECTED",
            "questions": room.get_public_questions(),
            "remaining_seconds": max(0, remaining_seconds),
            "saved_answers": p.answers,
            "is_submitted": p.is_submitted
        }, ensure_ascii=False))

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
            except Exception:
                continue

            action = msg.get("action")

            # 1. Chủ phòng quyết định BẮT ĐẦU THI
            if action == "HOST_START_EXAM":
                if not is_host:
                    await websocket.send_text(json.dumps({
                        "type": "ERROR",
                        "message": "Chỉ có chủ phòng mới có quyền bắt đầu bài thi!"
                    }, ensure_ascii=False))
                    continue

                if room.status != "waiting":
                    await websocket.send_text(json.dumps({
                        "type": "ERROR",
                        "message": "Phòng thi hiện không ở trạng thái chờ bắt đầu!"
                    }, ensure_ascii=False))
                    continue

                success = await room_manager.start_exam(room.room_code, user_name)
                if not success:
                    await websocket.send_text(json.dumps({
                        "type": "ERROR",
                        "message": "Không thể bắt đầu bài thi, vui lòng kiểm tra lại ngân hàng câu hỏi!"
                    }, ensure_ascii=False))

            # 2. Chủ phòng quyết định KẾT THÚC PHÒNG THI SỚM
            elif action == "HOST_END_EXAM":
                if not is_host:
                    await websocket.send_text(json.dumps({
                        "type": "ERROR",
                        "message": "Chỉ có chủ phòng mới có quyền kết thúc phòng thi!"
                    }, ensure_ascii=False))
                    continue

                await room_manager.end_exam(room.room_code, reason="HOST_ENDED")

            # 3. Thí sinh cập nhật/thay đổi đáp án đã chọn khi còn thời gian
            elif action == "UPDATE_ANSWER":
                if room.status != "in_progress" or p.is_submitted:
                    continue
                q_id = str(msg.get("question_id"))
                option = msg.get("option", "").upper()
                if q_id and option:
                    p.answers[q_id] = option
                    # Phản hồi xác nhận đã lưu đáp án về client
                    await websocket.send_text(json.dumps({
                        "type": "ANSWER_SAVED",
                        "question_id": q_id,
                        "option": option
                    }, ensure_ascii=False))

            # 4. Thí sinh nộp bài sớm hoặc nộp bài khi hết giờ
            elif action == "SUBMIT_EXAM":
                if p.is_submitted:
                    await websocket.send_text(json.dumps({
                        "type": "ALREADY_SUBMITTED",
                        "message": "Bạn đã nộp bài rồi!"
                    }, ensure_ascii=False))
                    continue

                # Lưu các đáp án gửi kèm (nếu có)
                incoming_answers = msg.get("answers", {})
                for q_k, opt_v in incoming_answers.items():
                    p.answers[str(q_k)] = str(opt_v).upper()

                # Chấm điểm cá nhân ngay lập tức
                grade_info = room.grade_participant(user_name)

                # Phản hồi kết quả điểm cho thí sinh này
                await websocket.send_text(json.dumps({
                    "type": "SUBMISSION_RESULT",
                    "score": grade_info["score"],
                    "correct_count": grade_info["correct_count"],
                    "total_questions": grade_info["total_questions"],
                    "details": grade_info["details"],
                    "message": f"Nộp bài thành công! Bạn trả lời đúng {grade_info['correct_count']}/{grade_info['total_questions']} câu."
                }, ensure_ascii=False))

                # Thông báo cho cả phòng biết thí sinh này đã nộp bài
                submitted_count = sum(1 for part in room.participants.values() if part.is_submitted)
                await room.broadcast({
                    "type": "PARTICIPANT_SUBMITTED_NOTIFICATION",
                    "user_name": user_name,
                    "submitted_count": submitted_count,
                    "total_count": len(room.participants)
                })

                # Nếu tất cả thí sinh đã nộp bài, tự động kết thúc phòng thi
                if submitted_count >= len(room.participants) and room.status == "in_progress":
                    await asyncio.sleep(1) # Đợi 1 giây tạo hiệu ứng
                    await room_manager.end_exam(room.room_code, reason="ALL_SUBMITTED")

    except WebSocketDisconnect:
        p.websocket = None
        # Báo cho phòng biết có người ngắt kết nối
        await room.broadcast({
            "type": "PARTICIPANT_DISCONNECTED",
            "user_name": user_name
        })
    except Exception as e:
        print(f"Lỗi WebSocket client {user_name} tại phòng {room_code}: {e}")
        p.websocket = None


# ==========================================
# GIAO DIỆN WEB & STATIC FILES
# ==========================================

# Gắn thư mục static để phục vụ file CSS, JS, hình ảnh
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    """Phục vụ trang chủ ứng dụng web"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Website Thi Trắc Nghiệm Trực Tuyến - Máy chủ đang hoạt động!"})

if __name__ == "__main__":
    import uvicorn
    # Chạy máy chủ Uvicorn trên cổng 8000
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
