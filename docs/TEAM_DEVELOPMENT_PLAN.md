# Kế Hoạch Triển Khai Chi Tiết Theo Từng Thành Viên (C Backend + Web Client)

Tài liệu này phân rã chi tiết nhiệm vụ, tên file mã nguồn phụ trách, giao thức lệnh và tiêu chí hoàn thành (Definition of Done) cho từng thành viên trong nhóm.

---

## 🗂️ 1. Cấu trúc Mã nguồn Dự kiến Sau Khi Hoàn Thiện

```text
LTM_QUIZNET/
├── c_backend/                   # Toàn bộ Máy chủ Mạng viết bằng Ngôn ngữ C (Port 9000)
│   ├── cJSON.h / cJSON.c        # [TV1] Xử lý JSON (Đã có)
│   ├── stream_io.h / .c         # [TV1] Xử lý truyền dòng TCP & ClientSession (Đã xong)
│   ├── auth_question.h / .c     # [TV1] Đăng ký, Đăng nhập, Phiên, Câu hỏi (Đã xong ~90%)
│   ├── server_core.c            # [TV1] Master Socket, select(), điều phối lệnh (Đã xong khung)
│   ├── logger.h / .c            # [TV2] Ghi log hoạt động mạng vào network.log
│   ├── room_manager.h / .c      # [TV2] Quản lý phòng thi RAM, broadcast, Timer pthread, Luyện tập
│   ├── exam_engine.h / .c       # [TV3] Đổi đáp án (Mutex), Nộp bài, Chấm điểm & Leaderboard
│   ├── analytics.h / .c         # [TV3] Lưu lịch sử SQLite & tổng hợp dữ liệu 3 đồ thị
│   └── Makefile                 # Biên dịch tất cả thành file chạy quiznet_server
├── bridge.py                    # [Cả nhóm] Cầu nối trung gian WebSocket (8000) <-> TCP C (9000)
├── static/                      # Giao diện Client SPA (HTML5/CSS3/JS + Chart.js)
├── docs/                        # Tài liệu kỹ thuật & kế hoạch dự án
└── quiz_system.db               # Cơ sở dữ liệu SQLite 3 (5 bảng)
```

---

## 👤 2. KẾ HOẠCH CHI TIẾT — THÀNH VIÊN 1
**Trọng tâm:** *Hạ tầng Socket Core, Xác thực, Quản lý phiên & Ngân hàng câu hỏi.*

### ✅ Phần đã hoàn thành:
* Tạo bộ khung TCP Socket (`socket`, `bind`, `listen`, `accept`, `select()`) tại `server_core.c` (Port `9000`).
* Cài đặt bộ đệm xử lý truyền dòng (`recv_buf`, `extract_line`, `send_all`, `send_line`) chống dính/phân mảnh gói TCP tại `stream_io.c`.
* Xây dựng các lệnh `REGISTER`, `LOGIN` (tự động gửi `FORCE_LOGOUT` đá socket cũ khi đăng nhập trùng), `GET_QUESTIONS`, `ADD_QUESTION` (chỉ `role == "admin"`), `GET_CATEGORIES` (lấy danh sách chủ đề) và `GET_STUDENTS_LIST` (lấy danh sách sinh viên cho TV2 chọn vào phòng thi).

### 📋 Công việc cần làm tiếp:
1. **(Nâng cao - Tùy chọn) Băm mật khẩu**:
   * Dùng hàm hash (SHA-256) thay vì lưu mật khẩu thô trong bảng `users`.
2. **Cập nhật Giao diện Client (`static/index.html`, `static/js/app.js`)**:
   * Tạo Modal/Màn hình **Đăng nhập & Đăng ký** bắt buộc trước khi vào sảnh.
   * Hiển thị tên người dùng + Role (`Admin` / `Student`) và trạng thái phiên Socket trên Header.
   * Ẩn hoặc khóa nút **"Thêm câu hỏi mới"** nếu tài khoản đang đăng nhập là `student`.
3. **Hỗ trợ tích hợp**:
   * Mở hook trong `dispatch_command()` của `server_core.c` để gắn các hàm xử lý lệnh của TV2 và TV3.

---

## 👤 3. KẾ HOẠCH CHI TIẾT — THÀNH VIÊN 2
**Trọng tâm:** *Quản lý Phòng thi theo lịch hẹn & danh sách sinh viên (Whitelist), Đồng bộ Realtime, Luyện tập & Ghi log mạng.*

### 📋 Công việc cần làm (Backend C):
1. **Cập nhật Schema SQLite (`exam_rooms` & `activity_logs`)**:
   * Bổ sung vào bảng `exam_rooms`: `scheduled_start_time TIMESTAMP` (giờ hẹn bắt đầu) và `allowed_users_json TEXT` (danh sách username sinh viên được phép thi).
   * Tạo bảng `activity_logs` để lưu lịch sử sự kiện mạng song song với file `network.log`.
2. **Xây dựng Module Ghi log mạng (`logger.h` / `logger.c`)**:
   * Viết hàm `log_network_event(ClientSession *c, const char *cmd, const char *detail)` ghi ra file `network.log` và bảng `activity_logs` kèm thời gian thực, `IP:Port`, `Socket FD`, `Username`, kích thước bytes và trạng thái.
3. **Xây dựng Module Quản lý Phòng thi (`room_manager.h` / `room_manager.c`)**:
   * Định nghĩa `struct ExamRoom` (có thêm `scheduled_start_time`, mảng `allowed_users`, cờ `is_public`) và `struct Participant` trên RAM, bảo vệ bằng `pthread_mutex_t`.
   * Cài đặt các lệnh giao thức:
     * `CREATE_ROOM|{"room_name":"...","duration":15,"easy":5,"medium":3,"hard":2,"start_time":"2026-11-25 14:30:00","allowed_users":["sv1","sv2"],"is_public":0}`: Sinh định danh phòng, lưu RAM + SQLite, thực hiện **Selective Broadcast** (chỉ đẩy phòng thi tới các `sock_fd` của sinh viên có tên trong `allowed_users` và Host).
     * `LIST_ROOMS|{}`: Lọc và chỉ trả về các phòng mà `client->username` có quyền thấy (nằm trong danh sách `allowed_users`, là Host, hoặc phòng công khai) kèm trạng thái (`waiting`, `in_progress`, `finished`).
     * `JOIN_ROOM|{"room_code":"..."}` & `LEAVE_ROOM|{"room_code":"..."}`: Sinh viên bấm thẳng vào phòng trên giao diện **không cần nhập mã**; kiểm tra quyền nằm trong Whitelist + phòng còn `waiting`, thêm `sock_fd` vào phòng, broadcast `PARTICIPANT_JOINED` cho cả phòng chờ đến giờ thi.
     * `START_EXAM|{"room_code":"..."}` & **Luồng tự động bắt đầu theo lịch**: Hỗ trợ cả **2 cơ chế**: (1) Luồng Timer kiểm tra mỗi giây: khi tới `scheduled_start_time` tự động phát đề; (2) Chủ phòng (Host) bấm nút "Bắt đầu ngay" hoặc "Kết thúc sớm". Bốc đề ngẫu nhiên, **lọc bỏ đáp án đúng**, broadcast `EXAM_STARTED` tới toàn phòng và chạy đồng hồ đếm ngược tập trung.
     * `START_PRACTICE|{"easy":5,"medium":3,"hard":2,"category":"all","duration":10}`: Bốc ngẫu nhiên đề cá nhân (ẩn đáp án) trả riêng cho 1 client.

### 📋 Công việc cần làm (Giao diện Client):
* Form Tạo phòng: Gọi `GET_STUDENTS_LIST` để hiển thị danh sách sinh viên cho Chủ phòng tick chọn + ô chọn Thời gian bắt đầu (lịch hẹn) + tùy chọn phòng công khai.
* Sảnh danh sách phòng: Chỉ hiển thị các phòng được cấp quyền, sinh viên bấm "Vào phòng" trực tiếp **không cần nhập mã**.
* Phòng chờ (Lobby): Hiển thị đồng hồ đếm ngược tới giờ thi (nếu đang đợi lịch) và danh sách thí sinh kết nối theo thời gian thực.

---

## 👤 4. KẾ HOẠCH CHI TIẾT — THÀNH VIÊN 3
**Trọng tâm:** *Engine Làm bài, Chấm điểm tự động, Bảng xếp hạng & Thống kê đồ thị.*

### 📋 Công việc cần làm (Backend C):
1. **Xây dựng Engine Làm bài & Chấm điểm (`exam_engine.h` / `exam_engine.c`)**:
   * Cài đặt các lệnh giao thức:
     * `UPDATE_ANSWER|{"room_code":"...","q_id":1,"ans":"B"}`: Dùng `pthread_mutex_lock()` cập nhật đáp án tạm của thí sinh trong `struct Participant` trên RAM, gửi trả xác nhận `ANSWER_ACK`.
     * `SUBMIT_EXAM|{"room_code":"..."}`: Đánh dấu thí sinh đã nộp bài sớm, đối chiếu đáp án đúng tính điểm thang 10 và trả kết quả cá nhân.
     * **Cơ chế Hết giờ / Kết thúc phòng (`FINISH_ROOM` hoặc Timer về 0)**: Khóa phòng (`status = finished`), chấm điểm toàn bộ thí sinh chưa nộp, sắp xếp mảng kết quả giảm dần theo điểm và thời gian nộp, lưu vào `room_participants` & `exam_history`, sau đó broadcast `EXAM_FINISHED` kèm Bảng xếp hạng Top 1-2-3.
     * `SUBMIT_PRACTICE|{"question_ids":[...],"answers":{...},"duration_seconds":120}`: Chấm điểm bài luyện tập, trả về chi tiết từng câu + giải thích và lưu vào `exam_history`.
     * `GET_ROOM_RESULTS|{"room_code":"..."}`: Trả lại bảng xếp hạng của các phòng đã kết thúc.
2. **Xây dựng Module Lịch sử & Đồ thị (`analytics.h` / `analytics.c`)**:
   * Cài đặt các lệnh giao thức:
     * `GET_HISTORY|{}`: Truy vấn danh sách bài thi đã làm của `client->username` từ bảng `exam_history`.
     * `GET_HISTORY_DETAIL|{"history_id":1}`: Trả chi tiết từng câu hỏi + đáp án chọn + giải thích của bài thi cũ.
     * `GET_ANALYTICS|{}`: Tính toán các chỉ số KPI (Tổng bài thi, Điểm TB, Điểm cao nhất, % chính xác) và dữ liệu cho **3 biểu đồ** (Biến động điểm qua thời gian, % đúng theo độ khó Dễ/TB/Khó, Tỷ lệ đúng/sai).

### 📋 Công việc cần làm (Giao diện Client):
* Cập nhật `exam.js` và `charts.js` nhận dữ liệu từ giao thức lệnh Socket (thay cho REST API cũ) để vẽ 3 biểu đồ Chart.js, đồng hồ đếm ngược và bảng xếp hạng Podium.

---

## 🔗 5. GIAI ĐOẠN TÍCH HỢP & KIỂM THỬ CUỐI CÙNG (CẢ NHÓM)

1. **Dựng Cầu nối `bridge.py`**:
   * Mở cổng `8000` phục vụ giao diện web `static/` và kênh WebSocket `/ws`.
   * Chuyển tiếp 1:1 mọi thông điệp giữa trình duyệt Web và C TCP Server (Port `9000`).
2. **Thống nhất cập nhật `static/js/api.js` & `static/js/websocket.js`**:
   * Gom toàn bộ tương tác Frontend đi qua **1 kết nối Socket duy nhất** tới Server C.
3. **Kiểm thử chất lượng**:
   * Dùng `nc 127.0.0.1 9000` kiểm tra từng lệnh của TV2 và TV3.
   * Chạy `valgrind --leak-check=full ./quiznet_server` trên WSL Ubuntu để chứng minh **0 bytes leaked** (không rò rỉ bộ nhớ).
   * Mở đồng thời 2–3 tab trình duyệt (1 Admin/Host, 2 Student) thi đấu trực tiếp để quay video / demo bảo vệ.

---

## 🌿 6. QUY ƯỚC LÀM VIỆC GIT CHO NHÓM
* Luôn làm việc trên nhánh `feat/c-backend` (hoặc tách nhánh con `feat/tv1-core`, `feat/tv2-room`, `feat/tv3-exam`), **không code đè lên nhánh `main`** để giữ bản dự phòng.
* Trước khi bắt đầu code mỗi ngày: `git pull origin feat/c-backend`.
* Chỉ commit file mã nguồn (`.c`, `.h`, `.js`, `.html`, `.css`, `.md`, `Makefile`), không commit file thực thi `quiznet_server`, `*.o`, `network.log`.
