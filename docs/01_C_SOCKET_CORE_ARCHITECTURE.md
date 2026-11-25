# Kiến Trúc C Socket Core & Xử Lý Truyền Dòng (Thành Viên 1)

Tài liệu này giải thích chi tiết cấu trúc mã nguồn C trong thư mục `c_backend/`, giao thức truyền dòng TCP, cơ chế I/O Multiplexing và tương tác CSDL bằng SQLite C API.

---

## 1. Cấu trúc thư mục `c_backend/`

| Tập tin | Vai trò kỹ thuật |
| :--- | :--- |
| `cJSON.h` / `cJSON.c` | Thư viện C nhẹ (single-file) dùng để phân giải (parse) và đóng gói chuỗi JSON. |
| `stream_io.h` / `stream_io.c` | Cài đặt `ClientSession` và bộ đệm xử lý truyền dòng TCP (`\n`), chống dính gói/phân mảnh gói tin. |
| `auth_question.h` / `auth_question.c` | Xử lý Đăng ký, Đăng nhập, Quản lý phiên trùng lặp, Phân quyền (`admin`/`student`) và Ngân hàng câu hỏi qua `sqlite3.h`. |
| `server_core.c` | Khởi tạo Master TCP Socket (Port `9000`), quản lý đa kết nối bằng `select()`, tách lệnh `CMD\|JSON_PAYLOAD` và điều phối. |
| `Makefile` | Tự động hóa quá trình biên dịch với GCC (`-Wall -Wextra -lpthread -lsqlite3`). |

---

## 2. Cơ chế Xử lý Truyền dòng (`stream_io.c`)

Trong lập trình mạng TCP (`SOCK_STREAM`), dữ liệu được truyền dưới dạng **luồng byte liên tục (Byte Stream)** không có ranh giới gói tin. Hai hiện tượng thường gặp là:
- **Phân mảnh gói (Fragmentation)**: Một lệnh bị chia làm 2 lần `recv()` mới nhận đủ.
- **Dính gói (Sticky Packet)**: Nhiều lệnh bị gộp chung trong 1 lần `recv()`.

### Giải pháp cài đặt:
1. Mỗi kết nối được cấp một bộ đệm riêng `recv_buf[16384]` và biến `buf_len` trong `ClientSession`.
2. **`read_into_buffer()`**: Đọc dữ liệu mới từ socket và nối vào cuối `recv_buf`.
3. **`extract_line()`**:
   - Dùng `memchr()` tìm ký tự xuống dòng `\n`.
   - Nếu chưa thấy `\n` $\rightarrow$ trả về `0`, giữ nguyên bộ đệm để đợi gói TCP tiếp theo.
   - Nếu thấy `\n` $\rightarrow$ cắt đúng đoạn lệnh đưa ra ngoài (xóa `\r` nếu là `\r\n`), sau đó dùng `memmove()` dịch phần dữ liệu dư lên đầu bộ đệm để xử lý cho vòng lặp kế tiếp.
4. **`send_all()` & `send_line()`**: Dùng vòng lặp `while (total_sent < len)` đảm bảo gửi đủ 100% số byte qua mạng theo đúng định dạng chuẩn:
   ```text
   COMMAND|JSON_PAYLOAD\n
   ```

---

## 3. Cơ chế Vào/Ra Đa kết nối (`server_core.c`)

1. **Khởi tạo Socket chuẩn POSIX**:
   - `socket(AF_INET, SOCK_STREAM, 0)`: Tạo TCP Socket.
   - `setsockopt(..., SO_REUSEADDR, ...)`: Tránh lỗi *"Address already in use"* do trạng thái `TIME_WAIT` khi khởi động lại server.
   - `bind()` & `listen(master_fd, 32)`: Gắn cổng `9000` và mở hàng đợi kết nối.
   - `signal(SIGPIPE, SIG_IGN)`: Bỏ qua tín hiệu `SIGPIPE` để server không bị sập khi client ngắt kết nối đột ngột lúc server đang gửi dữ liệu.
2. **I/O Multiplexing với `select()`**:
   - Theo dõi đồng thời `master_fd` và mảng `g_clients[MAX_CLIENTS]` trong cùng 1 tiến trình.
   - Khi `master_fd` sẵn sàng $\rightarrow$ gọi `accept()`, lấy IP/Port qua `inet_ntop()` và `ntohs()`, gán vào slot trống và gửi bản tin `WELCOME`.
   - Khi `client_fd` sẵn sàng $\rightarrow$ đọc vào bộ đệm và chạy `while (extract_line(...))` để xử lý hết tất cả các dòng lệnh có trong bộ đệm.
3. **Bộ phân giải lệnh (`dispatch_command`)**:
   - Tách chuỗi tại ký tự `|` đầu tiên thành `cmd` và `payload`.
   - Định tuyến tới các hàm xử lý tương ứng (`PING`, `REGISTER`, `LOGIN`, `GET_QUESTIONS`, `ADD_QUESTION`...).

---

## 4. Xác thực, Quản lý Phiên & Phân quyền (`auth_question.c`)

1. **Bảo mật truy vấn SQLite C API (`sqlite3.h`)**:
   - Sử dụng **Prepared Statement** (`sqlite3_prepare_v2`, `sqlite3_bind_text`, `sqlite3_step`, `sqlite3_finalize`) để ngăn chặn tuyệt đối tấn công SQL Injection.
2. **Quản lý phiên gắn liền với Socket FD (`LOGIN`)**:
   - Khi đăng nhập thành công, thông tin `user_id`, `username`, `role` được gắn trực tiếp vào `ClientSession` của socket đó.
   - **Xử lý đăng nhập trùng lặp**: Server quét mảng `all_clients[]`; nếu phát hiện cùng một `username` đang online ở một `sock_fd` khác, server gửi bản tin `FORCE_LOGOUT` xuống socket cũ và đóng kết nối cũ (`close()`).
3. **Kiểm soát quyền truy cập (`ADD_QUESTION`)**:
   - Kiểm tra `client->is_logged_in == 1` và `strcmp(client->role, "admin") == 0`. Nếu là tài khoản `student`, server từ chối và trả về mã `FORBIDDEN`.

---

## 5. Hướng dẫn Biên dịch & Kiểm thử bằng Netcat

### Kết nối WSL Ubuntu:
```bash
wsl -d Ubuntu
```

### Biên dịch và chạy Server (Terminal 1 - WSL Ubuntu):
```bash
cd /mnt/d/LTM_QUIZNET/c_backend
make
./quiznet_server
```

### Giả lập Client kết nối TCP thuần (Terminal 2 - WSL Ubuntu):
```bash
nc 127.0.0.1 9000
```

### Các lệnh mẫu để kiểm thử trực tiếp:
```text
PING|{}
REGISTER|{"username":"sinhvien1","password":"123"}
LOGIN|{"username":"sinhvien1","password":"123"}
GET_QUESTIONS|{"difficulty":"easy","category":"all"}
ADD_QUESTION|{"content":"Test","option_a":"A","option_b":"B","option_c":"C","option_d":"D","correct_answer":"A","difficulty":"easy","category":"Test"}
LOGIN|{"username":"admin","password":"admin123"}
```
