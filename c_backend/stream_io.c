#include "stream_io.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <errno.h>

void init_client_session(ClientSession *client) {
    client->sock_fd = -1;
    memset(client->ip_addr, 0, sizeof(client->ip_addr));
    client->port = 0;
    memset(client->recv_buf, 0, sizeof(client->recv_buf));
    client->buf_len = 0;
    client->is_logged_in = 0;
    client->user_id = -1;
    memset(client->username, 0, sizeof(client->username));
    memset(client->role, 0, sizeof(client->role));
}

int send_all(int sock_fd, const char *data, size_t len) {
    size_t total_sent = 0;
    while (total_sent < len) {
        ssize_t n = send(sock_fd, data + total_sent, len - total_sent, 0);
        if (n <= 0) {
            return -1;
        }
        total_sent += (size_t)n;
    }
    return 0;
}

int send_line(int sock_fd, const char *cmd, const char *json_payload) {
    if (sock_fd < 0 || !cmd) return -1;
    const char *payload = json_payload ? json_payload : "{}";

    size_t msg_len = strlen(cmd) + 1 + strlen(payload) + 2; // cmd + '|' + payload + '\n' + '\0'
    char stack_buf[4096];
    char *send_buf = stack_buf;

    if (msg_len > sizeof(stack_buf)) {
        // Cấp phát động tạm thời nếu đề thi hoặc danh sách câu hỏi lớn hơn 4KB
        send_buf = (char *)malloc(msg_len);
        if (!send_buf) return -1;
    }

    int written = snprintf(send_buf, msg_len, "%s|%s\n", cmd, payload);
    int res = send_all(sock_fd, send_buf, (size_t)written);

    if (send_buf != stack_buf) {
        free(send_buf);
    }
    return res;
}

int read_into_buffer(ClientSession *client) {
    int space_left = MAX_RECV_BUF - client->buf_len - 1;
    if (space_left <= 0) {
        // Bộ đệm đầy bất thường -> reset để tránh tràn bộ nhớ
        client->buf_len = 0;
        space_left = MAX_RECV_BUF - 1;
    }

    ssize_t n = recv(client->sock_fd, client->recv_buf + client->buf_len, (size_t)space_left, 0);
    if (n > 0) {
        client->buf_len += (int)n;
        client->recv_buf[client->buf_len] = '\0';
        return (int)n;
    } else if (n == 0) {
        return 0; // Client đóng kết nối sạch
    } else {
        if (errno == EWOULDBLOCK || errno == EAGAIN) {
            return 1;
        }
        return -1;
    }
}

int extract_line(ClientSession *client, char *out_line, size_t max_len) {
    char *newline_ptr = memchr(client->recv_buf, '\n', (size_t)client->buf_len);
    if (!newline_ptr) {
        return 0; // Chưa gặp ký tự kết thúc dòng '\n'
    }

    size_t line_len = (size_t)(newline_ptr - client->recv_buf);
    size_t copy_len = (line_len < max_len - 1) ? line_len : (max_len - 1);

    memcpy(out_line, client->recv_buf, copy_len);
    out_line[copy_len] = '\0';

    // Xóa ký tự '\r' ở cuối nếu có (CRLF -> LF)
    if (copy_len > 0 && out_line[copy_len - 1] == '\r') {
        out_line[copy_len - 1] = '\0';
    }

    // Dịch phần dữ liệu còn dư trong bộ đệm lên đầu (xử lý dính gói TCP)
    size_t consumed = line_len + 1;
    int remaining = client->buf_len - (int)consumed;
    if (remaining > 0) {
        memmove(client->recv_buf, client->recv_buf + consumed, (size_t)remaining);
    }
    client->buf_len = remaining;
    client->recv_buf[client->buf_len] = '\0';

    return 1;
}
