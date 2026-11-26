#ifndef STREAM_IO_H
#define STREAM_IO_H

#include <stddef.h>

#define MAX_RECV_BUF 16384
#define MAX_USERNAME 64
#define MAX_ROLE     32

// Cấu trúc lưu thông tin kết nối & phiên làm việc của mỗi Client Socket
typedef struct {
    int sock_fd;
    char ip_addr[32];
    int port;

    // Bộ đệm phục vụ xử lý truyền dòng (TCP Byte-Stream Framing)
    char recv_buf[MAX_RECV_BUF];
    int buf_len;

    // Thông tin phiên xác thực (Session Management)
    int is_logged_in;
    int user_id;
    char username[MAX_USERNAME];
    char role[MAX_ROLE]; // "admin" hoặc "student"
} ClientSession;

/**
 * Khởi tạo lại trạng thái mặc định cho một slot ClientSession
 */
void init_client_session(ClientSession *client);

/**
 * Gửi toàn bộ mảng byte qua TCP socket (xử lý trường hợp send() chỉ gửi được 1 phần)
 * Trả về 0 nếu thành công, -1 nếu lỗi/ngắt kết nối
 */
int send_all(int sock_fd, const char *data, size_t len);

/**
 * Đóng gói và gửi một thông điệp theo chuẩn giao thức dòng: COMMAND|JSON_PAYLOAD\n
 */
int send_line(int sock_fd, const char *cmd, const char *json_payload);

/**
 * Đọc dữ liệu mới từ socket vào bộ đệm của client.
 * Trả về:
 *   > 0: số byte vừa nhận được
 *     0: client đã đóng kết nối (FIN)
 *    -1: lỗi socket
 */
int read_into_buffer(ClientSession *client);

/**
 * Trích xuất 1 dòng hoàn chỉnh (kết thúc bằng '\n') từ recv_buf của client.
 * Tự động loại bỏ '\r' nếu client gửi '\r\n' (ví dụ telnet/netcat).
 * Trả về:
 *   1: đã lấy được 1 dòng hợp lệ vào out_line
 *   0: chưa đủ 1 dòng hoàn chỉnh (cần đợi các gói TCP tiếp theo)
 */
int extract_line(ClientSession *client, char *out_line, size_t max_len);

#endif
