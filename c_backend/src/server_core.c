#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <signal.h>
#include <sqlite3.h>

#include "stream_io.h"
#include "auth_question.h"
#include "db_init.h"

#define SERVER_PORT 9000
#define MAX_CLIENTS 128

static sqlite3 *g_db = NULL;
static ClientSession g_clients[MAX_CLIENTS];

// Bộ phân giải lệnh giao thức truyền dòng: COMMAND|JSON_PAYLOAD
void dispatch_command(ClientSession *client, char *line) {
    if (strlen(line) == 0) return;

    char *sep = strchr(line, '|');
    char *cmd = line;
    char *payload = "{}";

    if (sep) {
        *sep = '\0';
        payload = sep + 1;
    }

    printf("[RECV] FD=%d (%s:%d) | CMD=%s | Payload=%s\n",
           client->sock_fd, client->ip_addr, client->port, cmd, payload);

    // ===== NHÓM LỆNH THÀNH VIÊN 1: AUTH & QUESTIONS =====
    if (strcmp(cmd, "PING") == 0) {
        send_line(client->sock_fd, "PONG", "{\"status\":\"alive\"}");
    } else if (strcmp(cmd, "REGISTER") == 0) {
        handle_register(g_db, client, payload);
    } else if (strcmp(cmd, "LOGIN") == 0) {
        handle_login(g_db, client, g_clients, MAX_CLIENTS, payload);
    } else if (strcmp(cmd, "GET_QUESTIONS") == 0) {
        handle_get_questions(g_db, client, payload);
    } else if (strcmp(cmd, "ADD_QUESTION") == 0) {
        handle_add_question(g_db, client, payload);
    } else if (strcmp(cmd, "GET_CATEGORIES") == 0) {
        handle_get_categories(g_db, client);
    } else if (strcmp(cmd, "GET_STUDENTS_LIST") == 0) {
        handle_get_students_list(g_db, client);
    }
    // ===== CHỪA SẴN HOOK CHO THÀNH VIÊN 2 (ROOM MANAGER) =====
    // else if (strcmp(cmd, "CREATE_ROOM") == 0) { ... }
    // else if (strcmp(cmd, "LIST_ROOMS") == 0) { ... }
    // else if (strcmp(cmd, "JOIN_ROOM") == 0) { ... }
    // else if (strcmp(cmd, "START_EXAM") == 0) { ... }
    //
    // ===== CHỪA SẴN HOOK CHO THÀNH VIÊN 3 (EXAM ENGINE & ANALYTICS) =====
    // else if (strcmp(cmd, "UPDATE_ANSWER") == 0) { ... }
    // else if (strcmp(cmd, "SUBMIT_EXAM") == 0) { ... }
    // else if (strcmp(cmd, "GET_ANALYTICS") == 0) { ... }
    else {
        send_line(client->sock_fd, "UNKNOWN_CMD", "{\"message\":\"Lenh khong duoc ho tro\"}");
    }
}

int main(int argc, char *argv[]) {
    signal(SIGPIPE, SIG_IGN); // Tránh crash server khi client đột ngột ngắt kết nối lúc đang send()

    const char *db_path = (argc > 1) ? argv[1] : "../quiz_system.db";
    if (sqlite3_open(db_path, &g_db) != SQLITE_OK) {
        fprintf(stderr, "[DB ERROR] Khong the mo CSDL tai '%s': %s\n", db_path, sqlite3_errmsg(g_db));
        return 1;
    }
    init_database_schema(g_db);
    printf("[DB] Da ket noi thanh cong SQLite: %s\n", db_path);

    for (int i = 0; i < MAX_CLIENTS; i++) {
        init_client_session(&g_clients[i]);
    }

    // 1. Tạo TCP Socket
    int master_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (master_fd < 0) {
        perror("socket() failed");
        return 1;
    }

    // 2. Bật SO_REUSEADDR để restart server không bị kẹt cổng TIME_WAIT
    int opt = 1;
    setsockopt(master_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    // 3. Bind IP & Port 9000
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(SERVER_PORT);

    if (bind(master_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind() failed");
        close(master_fd);
        return 1;
    }

    // 4. Lắng nghe kết nối (Backlog = 32)
    if (listen(master_fd, 32) < 0) {
        perror("listen() failed");
        close(master_fd);
        return 1;
    }

    printf("============================================================\n");
    printf("  QUIZNET PRO - C TCP SOCKET SERVER DANG CHAY TAI PORT %d\n", SERVER_PORT);
    printf("  Giao thuc: Line-delimited Byte Stream (CMD|JSON_PAYLOAD\\n)\n");
    printf("============================================================\n");

    fd_set read_fds;
    char line_buf[MAX_RECV_BUF];

    // 5. Vòng lặp I/O Multiplexing bằng select()
    while (1) {
        FD_ZERO(&read_fds);
        FD_SET(master_fd, &read_fds);
        int max_fd = master_fd;

        for (int i = 0; i < MAX_CLIENTS; i++) {
            int sd = g_clients[i].sock_fd;
            if (sd > 0) FD_SET(sd, &read_fds);
            if (sd > max_fd) max_fd = sd;
        }

        int activity = select(max_fd + 1, &read_fds, NULL, NULL, NULL);
        if (activity < 0) {
            perror("select() error");
            continue;
        }

        // Có kết nối mới tới Master Socket
        if (FD_ISSET(master_fd, &read_fds)) {
            struct sockaddr_in cli_addr;
            socklen_t addrlen = sizeof(cli_addr);
            int new_fd = accept(master_fd, (struct sockaddr *)&cli_addr, &addrlen);

            if (new_fd >= 0) {
                int added = 0;
                for (int i = 0; i < MAX_CLIENTS; i++) {
                    if (g_clients[i].sock_fd == -1) {
                        init_client_session(&g_clients[i]);
                        g_clients[i].sock_fd = new_fd;
                        inet_ntop(AF_INET, &cli_addr.sin_addr, g_clients[i].ip_addr, sizeof(g_clients[i].ip_addr));
                        g_clients[i].port = ntohs(cli_addr.sin_port);

                        printf("[CONNECT] Client moi ket noi: %s:%d (FD=%d)\n",
                               g_clients[i].ip_addr, g_clients[i].port, new_fd);
                        send_line(new_fd, "WELCOME", "{\"message\":\"Ket noi thanh cong toi QuizNet C Server!\"}");
                        added = 1;
                        break;
                    }
                }
                if (!added) {
                    send_line(new_fd, "SERVER_FULL", "{\"message\":\"May chu da day ket noi!\"}");
                    close(new_fd);
                }
            }
        }

        // Kiểm tra dữ liệu đến từ các Client đang kết nối
        for (int i = 0; i < MAX_CLIENTS; i++) {
            int sd = g_clients[i].sock_fd;
            if (sd > 0 && FD_ISSET(sd, &read_fds)) {
                int bytes = read_into_buffer(&g_clients[i]);
                if (bytes <= 0) {
                    printf("[DISCONNECT] Client %s:%d (FD=%d, User=%s) da ngat ket noi.\n",
                           g_clients[i].ip_addr, g_clients[i].port, sd,
                           g_clients[i].is_logged_in ? g_clients[i].username : "Guest");
                    close(sd);
                    init_client_session(&g_clients[i]);
                } else {
                    // Tách từng dòng hoàn chỉnh (xử lý dính gói / phân mảnh)
                    while (extract_line(&g_clients[i], line_buf, sizeof(line_buf))) {
                        dispatch_command(&g_clients[i], line_buf);
                    }
                }
            }
        }
    }

    sqlite3_close(g_db);
    close(master_fd);
    return 0;
}
