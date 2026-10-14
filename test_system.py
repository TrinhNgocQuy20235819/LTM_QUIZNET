"""
test_system.py - Kịch bản kiểm thử tự động toàn diện hệ thống thi trắc nghiệm
Kiểm tra cả HTTP REST API và WebSocket Real-time
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import asyncio
import json
import urllib.request
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

def test_rest_apis():
    print("\n--- [1] KIỂM THỬ REST APIs ---")

    # 1.1 Lấy danh mục
    req = urllib.request.urlopen(f"{BASE_URL}/api/categories")
    cats = json.loads(req.read().decode('utf-8'))
    print(f"✅ /api/categories: Đã lấy {len(cats['categories'])} chủ đề.")

    # 1.2 Lấy danh sách câu hỏi
    req = urllib.request.urlopen(f"{BASE_URL}/api/questions?difficulty=easy")
    easy_q = json.loads(req.read().decode('utf-8'))
    print(f"✅ /api/questions (easy): {easy_q['total']} câu hỏi dễ.")

    # 1.3 Tạo phòng thi mới
    room_payload = {
        "room_name": "Phòng Thi Thử Nghiệm Tự Động",
        "host_name": "ThiSinhHost",
        "duration_minutes": 15,
        "easy_count": 3,
        "medium_count": 2,
        "hard_count": 1
    }
    data = json.dumps(room_payload).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/rooms", data=data, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    room_res = json.loads(resp.read().decode('utf-8'))
    room_code = room_res["room_code"]
    print(f"✅ /api/rooms (Tạo phòng): Thành công với mã phòng #{room_code}")

    # 1.4 Danh sách phòng thi
    req = urllib.request.urlopen(f"{BASE_URL}/api/rooms")
    rooms_list = json.loads(req.read().decode('utf-8'))
    print(f"✅ /api/rooms (Xem danh sách): {len(rooms_list['rooms'])} phòng thi hiện có.")

    # 1.5 Bắt đầu bài thi luyện tập
    practice_payload = {
        "user_name": "NguyenVanA",
        "duration_minutes": 10,
        "easy_count": 2,
        "medium_count": 2,
        "hard_count": 1,
        "category": "all"
    }
    data = json.dumps(practice_payload).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/practice/start", data=data, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    prac_res = json.loads(resp.read().decode('utf-8'))
    print(f"✅ /api/practice/start: Đã phát đề gồm {len(prac_res['questions'])} câu hỏi.")

    # 1.6 Nộp bài luyện tập
    q_ids = [q["id"] for q in prac_res["questions"]]
    submit_payload = {
        "user_name": "NguyenVanA",
        "question_ids": q_ids,
        "answers": {str(q_ids[0]): "B", str(q_ids[1]): "C"},
        "duration_seconds": 120
    }
    data = json.dumps(submit_payload).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/practice/submit", data=data, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    sub_res = json.loads(resp.read().decode('utf-8'))
    print(f"✅ /api/practice/submit: Điểm: {sub_res['score']}, Đúng: {sub_res['correct_count']}/{sub_res['total_questions']} câu.")

    # 1.7 Xem lịch sử làm bài
    req = urllib.request.urlopen(f"{BASE_URL}/api/history/NguyenVanA")
    hist_res = json.loads(req.read().decode('utf-8'))
    print(f"✅ /api/history/NguyenVanA: Có {len(hist_res['history'])} bài thi đã ghi nhận.")

    # 1.8 Xem thống kê đồ thị
    req = urllib.request.urlopen(f"{BASE_URL}/api/analytics/NguyenVanA")
    stats_res = json.loads(req.read().decode('utf-8'))
    print(f"✅ /api/analytics/NguyenVanA: Điểm TB: {stats_res['avg_score']}, Tỷ lệ đúng: {stats_res['overall_accuracy']}%")

    return room_code

async def test_websocket_room(room_code):
    print("\n--- [2] KIỂM THỬ WEBSOCKETS PHÒNG THI THỜI GIAN THỰC ---")

    host_ws_url = f"{WS_URL}/ws/room/{room_code}/ThiSinhHost"
    student_ws_url = f"{WS_URL}/ws/room/{room_code}/ThiSinh2"

    async with websockets.connect(host_ws_url) as ws_host, \
               websockets.connect(student_ws_url) as ws_student:

        # 2.1 Nhận thông báo người tham gia
        msg = await ws_host.recv()
        data = json.loads(msg)
        print(f"✅ WebSocket Host nhận: {data['type']} (Thí sinh: {len(data['participants'])} người)")

        # 2.2 Chủ phòng bấm Bắt đầu thi
        print("-> Host gửi: HOST_START_EXAM")
        await ws_host.send(json.dumps({"action": "HOST_START_EXAM"}))

        # Nhận gói tin EXAM_STARTED (bỏ qua các gói PARTICIPANT_JOINED trung gian)
        while True:
            msg = await ws_host.recv()
            exam_data = json.loads(msg)
            if exam_data.get("type") == "EXAM_STARTED":
                break
        print(f"✅ Host nhận đề thi EXAM_STARTED: {len(exam_data['questions'])} câu hỏi, thời gian {exam_data['duration_seconds']}s")

        while True:
            msg = await ws_student.recv()
            student_data = json.loads(msg)
            if student_data.get("type") == "EXAM_STARTED":
                break
        print(f"✅ Thí sinh 2 nhận đề thi EXAM_STARTED đồng bộ từ server")

        # 2.3 Thí sinh 2 đổi đáp án câu 1 sang 'B'
        q1_id = exam_data['questions'][0]['id']
        await ws_student.send(json.dumps({"action": "UPDATE_ANSWER", "question_id": q1_id, "option": "B"}))
        ack = await ws_student.recv()
        ack_data = json.loads(ack)
        print(f"✅ Thí sinh 2 cập nhật đáp án: {ack_data['type']} cho câu #{ack_data['question_id']} -> {ack_data['option']}")

        # 2.4 Thí sinh 2 đổi lại đáp án sang 'C' (kiểm tra tính năng cho phép thay đổi đáp án khi còn thời gian)
        await ws_student.send(json.dumps({"action": "UPDATE_ANSWER", "question_id": q1_id, "option": "C"}))
        ack2 = await ws_student.recv()
        ack_data2 = json.loads(ack2)
        print(f"✅ Thí sinh 2 thay đổi đáp án lần 2: câu #{ack_data2['question_id']} -> {ack_data2['option']}")

        # 2.5 Thí sinh 2 nộp bài sớm
        await ws_student.send(json.dumps({
            "action": "SUBMIT_EXAM",
            "answers": {str(q1_id): "C"}
        }))
        while True:
            res_sub = await ws_student.recv()
            res_data = json.loads(res_sub)
            if res_data.get("type") == "SUBMISSION_RESULT":
                break
        print(f"✅ Thí sinh 2 nộp bài sớm: Điểm {res_data['score']}, Đúng {res_data['correct_count']}/{res_data['total_questions']}")

        # 2.6 Chủ phòng kết thúc phòng thi
        print("-> Host gửi: HOST_END_EXAM")
        await ws_host.send(json.dumps({"action": "HOST_END_EXAM"}))

        # Cả hai nhận bảng xếp hạng chung
        while True:
            finish_host = await ws_host.recv()
            finish_data = json.loads(finish_host)
            if finish_data.get("type") == "EXAM_FINISHED":
                break
        print(f"✅ Nhận bảng xếp hạng tổng kết: {len(finish_data['leaderboard'])} người xếp hạng.")
        for r in finish_data['leaderboard']:
            print(f"   Top {r['rank']}: {r['user_name']} - {r['score']} điểm ({r['correct_count']}/{r['total_questions']} câu)")

    print("\n🎉 TOÀN BỘ CÁC TÍNH NĂNG ĐÃ VƯỢT QUA KIỂM THỬ THÀNH CÔNG!")

if __name__ == "__main__":
    room_code = test_rest_apis()
    asyncio.run(test_websocket_room(room_code))
