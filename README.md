# Hệ Thống Thi Trắc Nghiệm Trực Tuyến Mạng - QuizNet Pro
> **Đề tài Bài Tập Lớn môn học Lập Trình Mạng (Network Programming)**

Website thi trắc nghiệm trực tuyến thời gian thực kết hợp giữa giao thức HTTP (RESTful API) và WebSocket, hỗ trợ chế độ thi đấu phòng thi nhiều người (Multiplayer Exam Rooms) và chế độ luyện tập cá nhân (Practice Mode) với phân loại độ khó câu hỏi và thống kê đồ thị năng lực.

---

## 🌟 1. Các Tính Năng Đã Hoàn Thiện

### 🏢 A. Chế Độ Phòng Thi (Exam Room Mode)
- **Tạo phòng thi mới**: Thiết lập tên phòng thi, thời gian thi (phút) và số lượng câu hỏi theo từng độ khó (**Dễ**, **Trung bình**, **Khó**).
- **Quyền của Chủ phòng (Host)**: Chủ phòng có quyền quyết định thời điểm bấm **Bắt đầu thi** cũng như chủ động **Kết thúc phòng thi sớm**.
- **Danh sách phòng & Trạng thái trực tiếp**: Hiển thị trạng thái của từng phòng theo thời gian thực:
  - 🟡 **Chưa bắt đầu** (`waiting`): Cho phép thí sinh tự do tham gia.
  - 🟢 **Đang diễn ra** (`in_progress`): Bài thi đang được tiến hành.
  - 🔴 **Đã kết thúc** (`finished`): Bấm xem ngay bảng xếp hạng điểm số.
- **Sảnh chờ trực tuyến (Lobby)**: Cập nhật danh sách thí sinh tham gia theo thời gian thực qua kênh WebSocket.
- **Phát đề thi từ Server**: Khi bắt đầu thi, máy chủ trích xuất ngẫu nhiên câu hỏi theo cấu hình độ khó, ẩn đáp án đúng và phát đồng bộ tới tất cả thí sinh.
- **Tự do thay đổi đáp án**: Trong suốt thời gian thi, thí sinh có thể đổi đáp án tùy ý, hệ thống tự động lưu trữ tức thì.
- **Nộp bài sớm**: Hỗ trợ nộp bài trước khi hết giờ (có xác nhận số lượng câu đã làm/chưa làm).
- **Chấm điểm & Bảng xếp hạng (Leaderboard)**: Khi hết giờ hoặc phòng kết thúc, máy chủ tự động chấm điểm, tính thứ hạng Top 1, Top 2, Top 3 (Podium) và hiển thị chi tiết số câu đúng/sai cùng lời giải thích.

### ⚡ B. Chế Độ Luyện Tập (Practice Mode)
- Tùy chỉnh số lượng câu hỏi theo độ khó (**Dễ**, **Trung bình**, **Khó**), thời gian làm bài và theo chủ đề kiến thức.
- Đồng hồ đếm ngược, bảng điều hướng câu hỏi (Palette), nộp bài sớm.
- Nhận kết quả điểm số, độ chính xác %, số câu đúng/tổng câu tức thì và xem giải thích chi tiết cho từng câu hỏi.

### 📚 C. Phân Loại Câu Hỏi & Quản Lý Đề
- Ngân hàng gồm hơn 30+ câu hỏi chuyên sâu về **Mạng máy tính & Lập trình mạng** (Mô hình OSI, TCP/IP, Socket Non-blocking, Subnetting, TCP Handshake, TIME_WAIT, BGP, ARP, v.v.).
- Phân loại rõ ràng 3 mức độ: **Dễ (Easy)**, **Trung bình (Medium)**, **Khó (Hard)**.
- Hỗ trợ thêm câu hỏi mới trực tiếp từ giao diện với các tùy chọn phương án và lời giải thích.

### 📊 D. Lưu Trữ Lịch Sử & Thống Kê Đồ Thị
- Tự động lưu trữ toàn bộ lịch sử các bài thi đã làm (cả Phòng thi và Luyện tập) vào SQLite.
- Bảng lịch sử cho phép xem lại chi tiết bài làm trong quá khứ kèm câu trả lời của thí sinh và đáp án chính xác.
- **Hệ thống 3 Đồ thị trực quan (Chart.js)**:
  1. **Line Chart**: Biến động điểm số qua từng bài thi theo thời gian.
  2. **Bar Chart**: Tỷ lệ làm đúng (%) theo từng mức độ khó (Dễ / Trung bình / Khó).
  3. **Doughnut Chart**: Tỷ lệ trả lời đúng vs trả lời sai/bỏ qua.
  4. Các thẻ chỉ số tổng quan (KPIs): Tổng bài thi, Điểm trung bình, Điểm cao nhất, Tỷ lệ đúng toàn diện.

---

## 🛠️ 2. Cấu Trúc Mã Nguồn

```
d:\LapTrinhMang\BTLProject/
├── app.py                # Máy chủ FastAPI + Định tuyến REST API & WebSockets
├── room_manager.py       # Quản lý vòng đời phòng thi, đồng bộ thời gian thực & chấm điểm
├── database.py           # Quản lý CSDL SQLite, truy vấn câu hỏi, lịch sử & thống kê
├── models.py             # Schema kiểm thực dữ liệu Pydantic
├── seed_questions.py     # Ngân hàng câu hỏi mẫu chuyên ngành Lập Trình Mạng
├── test_system.py        # Kịch bản kiểm thử tự động toàn diện (REST API + WebSocket)
├── run.bat               # File khởi chạy máy chủ 1-click trên Windows
├── static/
│   ├── css/
│   │   └── style.css     # Giao diện Glassmorphism hiện đại, responsive, dark theme
│   ├── js/
│   │   ├── api.js        # Module gọi HTTP REST API
│   │   ├── websocket.js  # Module quản lý kết nối và gói tin WebSocket
│   │   ├── exam.js       # Module điều khiển giao diện làm bài thi trắc nghiệm
│   │   ├── charts.js     # Module vẽ đồ thị phân tích năng lực (Chart.js)
│   │   └── app.js        # Bộ điều phối trung tâm ứng dụng SPA
│   └── index.html        # Giao diện chính của website
└── README.md             # Hướng dẫn chi tiết dự án
```

---

## 🚀 3. Hướng Dẫn Chạy Website

### Cách 1: Chạy bằng file `run.bat`
Click đúp vào file `run.bat` trong thư mục dự án hoặc chạy lệnh:
```powershell
.\run.bat
```

### Cách 2: Chạy trực tiếp từ dòng lệnh
```powershell
py -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Sau khi máy chủ khởi động thành công:
- Truy cập website tại: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**
- Tài liệu API Swagger UI (tự động): **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 🧪 4. Chạy Kiểm Thử Tự Động Toàn Diện

Hệ thống đi kèm file `test_system.py` mô phỏng đầy đủ luồng thi giữa Host và Thí sinh:
```powershell
py test_system.py
```

Kết quả kiểm thử tự động xác nhận toàn bộ tính năng:
- Tạo phòng, lọc câu hỏi theo độ khó.
- WebSocket kết nối phòng chờ, phát đề thi đồng bộ `EXAM_STARTED`.
- Thí sinh cập nhật đáp án, thay đổi đáp án câu hỏi nhiều lần.
- Thí sinh nộp bài sớm, máy chủ chấm điểm tức thì.
- Chủ phòng kết thúc thi, máy chủ gửi bảng xếp hạng `EXAM_FINISHED`.
- Ghi nhận và tính toán biểu đồ thống kê kết quả.
