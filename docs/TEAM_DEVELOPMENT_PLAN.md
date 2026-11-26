# Kế Hoạch Triển Khai Chi Tiết Theo Từng Thành Viên (C Backend + RBAC + Web Client)

Tài liệu này phân rã chi tiết nhiệm vụ, ma trận phân quyền RBAC 3 vai trò (`admin`, `teacher`, `student`), tên file mã nguồn phụ trách và giao thức lệnh cho từng thành viên trong nhóm.

---

## 🔐 1. Ma Trận Phân Quyền RBAC (3 Vai Trò)

| Chức năng / Quyền hạn | Admin (`admin`) | Giảng viên (`teacher`) | Sinh viên (`student`) |
| :--- | :---: | :---: | :---: |
| **Phân quyền người dùng (`SET_USER_ROLE`, `GET_ALL_USERS`)** | ✅ | ❌ | ❌ |
| **Sao lưu & Khôi phục CSDL (`DB_BACKUP`, `DB_RESTORE`)** | ✅ | ❌ | ❌ |
| **Xem & Xây dựng kho đề thi (`GET_QUESTIONS`, `ADD/EDIT/DEL_QUESTION`)** | ✅ | ✅ | ❌ *(Bị chặn tuyệt đối)* |
| **Tạo phòng thi chính thức (có lịch hẹn & Whitelist SV)** | ✅ | ✅ | ❌ |
| **Tạo phòng luyện tập / Luyện tập cá nhân (`room_type = practice`)** | ✅ | ✅ | ✅ |
| **Tham gia phòng thi chính thức (nếu có tên trong Whitelist)** | ❌ | ❌ | ✅ |
| **Xem kết quả thi, Lịch sử & 3 biểu đồ thống kê cá nhân** | ✅ | ✅ | ✅ |

---

## 🗂️ 2. Cấu trúc Mã nguồn Dự kiến Sau Khi Hoàn Thiện

```text
LTM_QUIZNET/
├── c_backend/                   # Toàn bộ Máy chủ Mạng viết bằng Ngôn ngữ C (Port 9000)
│   ├── cJSON.h / cJSON.c        # [TV1] Xử lý JSON (Đã có)
│   ├── stream_io.h / .c         # [TV1] Xử lý truyền dòng TCP & ClientSession (Đã xong)
│   ├── auth_question.h / .c     # [TV1] Auth, RBAC (Admin/Teacher/Student), Kho đề, Backup/Restore DB
│   ├── server_core.c            # [TV1] Master Socket, select(), điều phối lệnh
│   ├── logger.h / .c            # [TV2] Ghi log hoạt động mạng vào network.log & activity_logs
│   ├── room_manager.h / .c      # [TV2] Quản lý phòng thi chính thức/luyện tập, Whitelist, Timer pthread
│   ├── exam_engine.h / .c       # [TV3] Đổi đáp án (Mutex), Nộp bài, Chấm điểm & Leaderboard
│   ├── analytics.h / .c         # [TV3] Lưu lịch sử SQLite & tổng hợp dữ liệu 3 đồ thị
│   └── Makefile                 # Biên dịch tất cả thành file chạy quiznet_server
├── backups/                     # Thư mục lưu các bản sao lưu quiz_system.db của Admin
├── bridge.py                    # [Cả nhóm] Cầu nối trung gian WebSocket (8000) <-> TCP C (9000)
├── static/                      # Giao diện Client SPA (HTML5/CSS3/JS + Chart.js)
├── docs/                        # Tài liệu kỹ thuật & kế hoạch dự án
└── quiz_system.db               # Cơ sở dữ liệu SQLite 3 (6 bảng: thêm users & activity_logs)
```

---

## 👤 3. KẾ HOẠCH CHI TIẾT — THÀNH VIÊN 1
**Trọng tâm:** *Hạ tầng Socket Core, Xác thực, Phân quyền RBAC, Quản trị hệ thống (Admin) & Kho đề thi (Giảng viên).*

### ✅ Phần đã hoàn thành:
* Tạo bộ khung TCP Socket (`socket`, `bind`, `listen`, `accept`, `select()`) tại `server_core.c` (Port `9000`).
* Cài đặt bộ đệm xử lý truyền dòng (`recv_buf`, `extract_line`, `send_all`, `send_line`) chống dính/phân mảnh gói TCP tại `stream_io.c`.
* Xây dựng các lệnh `REGISTER`, `LOGIN` (đá socket cũ `FORCE_LOGOUT` khi trùng), `GET_QUESTIONS`, `ADD_QUESTION`, `GET_CATEGORIES`, `GET_STUDENTS_LIST`.

### 📋 Công việc cần cập nhật & làm tiếp:
1. **Cập nhật Phân quyền RBAC trong `auth_question.c`**:
   * **`GET_QUESTIONS`**: Chặn `student` (trả về `FORBIDDEN`); chỉ cho phép `teacher` và `admin` xem kho đề.
   * **`ADD_QUESTION` / `EDIT_QUESTION` / `DELETE_QUESTION`**: Cho phép `teacher` và `admin` xây dựng kho đề thi. (Có thể thêm cột `created_by` trong bảng `questions`).
   * **`GET_CATEGORIES`**: Cho phép cả `student` gọi để chọn chủ đề khi luyện tập.
2. **Bổ sung Chức năng Quản trị Admin (`auth_question.c` hoặc `admin.c`)**:
   * `GET_ALL_USERS|{}`: Liệt kê toàn bộ tài khoản và vai trò (`student`, `teacher`, `admin`).
   * `SET_USER_ROLE|{"username":"sv1","role":"teacher"}`: Phân quyền cho tài khoản (chỉ `admin`).
   * `DB_BACKUP|{}` & `DB_RESTORE|{"filename":"..."}`: Sao lưu nóng CSDL bằng `sqlite3_backup_init()` vào thư mục `backups/` và khôi phục lại CSDL khi có sự cố (chỉ `admin`).
3. **Cập nhật Giao diện Client (`static/index.html`, `static/js/app.js`)**:
   * Tạo màn hình **Đăng nhập & Đăng ký** bắt buộc trước khi vào hệ thống.
   * **Hiển thị Menu động theo RBAC**:
     * Ẩn hoàn toàn Tab *"Ngân Hàng Câu Hỏi"* đối với tài khoản `student`.
     * Hiển thị Tab *"Quản Trị Hệ Thống"* (Phân quyền User + Backup/Restore CSDL) riêng cho `admin`.

---

## 👤 4. KẾ HOẠCH CHI TIẾT — THÀNH VIÊN 2
**Trọng tâm:** *Quản lý Phòng thi chính thức (Giảng viên) & Phòng luyện tập (Sinh viên), Đồng bộ Realtime & Ghi log mạng.*

### 📋 Công việc cần làm (Backend C):
1. **Cập nhật Schema SQLite (`exam_rooms` & `activity_logs`)**:
   * Bổ sung vào bảng `exam_rooms`: `room_type TEXT DEFAULT 'exam'` (`'exam'` hoặc `'practice'`), `scheduled_start_time TIMESTAMP`, `allowed_users_json TEXT`, `is_public BOOLEAN DEFAULT 0`.
   * Tạo bảng `activity_logs` để lưu nhật ký sự kiện mạng song song với file `network.log`.
2. **Xây dựng Module Ghi log mạng (`logger.h` / `logger.c`)**:
   * Ghi lại mọi sự kiện kết nối, đăng nhập, phân quyền RBAC, tạo/vào phòng, bắt đầu thi, backup/restore CSDL, ngắt kết nối đột ngột kèm `IP:Port`, `Socket FD`, `Username`, `Bytes`.
3. **Xây dựng Module Quản lý Phòng thi (`room_manager.h` / `room_manager.c`)**:
   * `CREATE_ROOM`:
     * Nếu là **`teacher`**: Được tạo phòng thi chính thức (`room_type = "exam"`), tạo đề thi ngẫu nhiên theo độ khó, chọn **Thời gian bắt đầu** và **Danh sách sinh viên (Whitelist)** $\rightarrow$ Thực hiện **Selective Broadcast** chỉ đẩy thông tin phòng tới đúng `sock_fd` của sinh viên nằm trong Whitelist (và Host).
     * Nếu là **`student`**: Được tạo phòng tự luyện tập (`room_type = "practice"`) để ôn tập cá nhân hoặc luyện nhóm.
   * `LIST_ROOMS|{}`: Chỉ trả về các phòng mà `client->username` có quyền thấy (được mời vào phòng thi chính thức, hoặc phòng luyện tập của bản thân/công khai).
   * `JOIN_ROOM|{"room_code":"..."}` & `LEAVE_ROOM|{"room_code":"..."}`: Sinh viên bấm thẳng vào phòng trên giao diện **không cần nhập mã**; kiểm tra quyền Whitelist + trạng thái `waiting`, Broadcast `PARTICIPANT_JOINED`.
   * `START_EXAM|{"room_code":"..."}` & **Luồng Timer tự động**: Tự động phát đề khi đến `scheduled_start_time`, đồng thời giữ nút "Bắt đầu ngay" / "Kết thúc sớm" cho Chủ phòng. Lọc bỏ `correct_answer` trước khi Broadcast `EXAM_STARTED`.
   * `START_PRACTICE|{...}`: Tạo nhanh phiên luyện tập cá nhân không cần phòng chờ.

### 📋 Công việc cần làm (Giao diện Client):
* Form Tạo phòng: Phân biệt giao diện tạo **Phòng thi chính thức** (cho Giảng viên: có chọn Whitelist sinh viên qua `GET_STUDENTS_LIST` & giờ hẹn) và **Phòng luyện tập** (cho Sinh viên).
* Màn hình Sảnh phòng (chỉ hiện các phòng được phép, vào thẳng không cần mã) & Phòng chờ (đồng hồ đếm ngược tới giờ thi).

---

## 👤 5. KẾ HOẠCH CHI TIẾT — THÀNH VIÊN 3
**Trọng tâm:** *Engine Làm bài, Chấm điểm tự động, Bảng xếp hạng & Thống kê đồ thị.*

### 📋 Công việc cần làm (Backend C):
1. **Xây dựng Engine Làm bài & Chấm điểm (`exam_engine.h` / `exam_engine.c`)**:
   * `UPDATE_ANSWER|{"room_code":"...","q_id":1,"ans":"B"}`: Dùng `pthread_mutex_lock()` cập nhật đáp án tạm vào RAM, gửi trả `ANSWER_ACK`.
   * `SUBMIT_EXAM|{"room_code":"..."}` & **Tự động thu bài khi hết giờ**: Chấm điểm thang 10, sắp xếp bảng xếp hạng Top 1-2-3, lưu vào `room_participants` & `exam_history`, broadcast `EXAM_FINISHED`.
   * `SUBMIT_PRACTICE|{"question_ids":[...],"answers":{...},"duration_seconds":120}`: Chấm điểm luyện tập, trả chi tiết đúng/sai + giải thích và lưu lịch sử.
   * `GET_ROOM_RESULTS|{"room_code":"..."}`: Xem lại bảng xếp hạng của các phòng thi đã kết thúc.
2. **Xây dựng Module Lịch sử & Đồ thị (`analytics.h` / `analytics.c`)**:
   * `GET_HISTORY|{}`, `GET_HISTORY_DETAIL|{"history_id":1}`: Xem lại bài làm đã thi (không vi phạm quy tắc ẩn kho đề chưa thi của Giảng viên).
   * `GET_ANALYTICS|{}`: Tính toán KPI và dữ liệu cho **3 biểu đồ Chart.js**.

### 📋 Công việc cần làm (Giao diện Client):
* Cập nhật `exam.js` và `charts.js` giao tiếp qua Socket Bridge để hiển thị bài thi, đồng hồ, bảng xếp hạng Podium và 3 biểu đồ phân tích.

---

## 🔗 6. GIAI ĐOẠN TÍCH HỢP & KIỂM THỬ CUỐI CÙNG (CẢ NHÓM)
1. Dựng **`bridge.py`** (WebSocket 8000 $\leftrightarrow$ Raw TCP C 9000) và gom toàn bộ `static/js/api.js` + `websocket.js` đi qua 1 kênh Socket duy nhất.
2. Kiểm thử toàn diện 3 vai trò (`admin`, `teacher`, `student`), kiểm tra chặn quyền `FORBIDDEN` ở tầng Socket và chạy `valgrind --leak-check=full ./quiznet_server` đảm bảo không rò rỉ bộ nhớ.

---

## 🌿 7. QUY ƯỚC LÀM VIỆC GIT CHO NHÓM
* Luôn làm việc trên nhánh `feat/c-backend` (hoặc nhánh con theo tính năng), giữ nguyên nhánh `main` làm bản dự phòng.
* Chỉ commit file mã nguồn (`.c`, `.h`, `.js`, `.html`, `.css`, `.md`, `Makefile`), không commit `quiznet_server`, `*.o`, `network.log`, `backups/*.db`.
