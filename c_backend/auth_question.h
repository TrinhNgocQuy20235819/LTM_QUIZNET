#ifndef AUTH_QUESTION_H
#define AUTH_QUESTION_H

#include <sqlite3.h>
#include "stream_io.h"

/**
 * Xử lý đăng ký tài khoản mới: CMD REGISTER|{"username":"...", "password":"..."}
 */
void handle_register(sqlite3 *db, ClientSession *client, const char *payload);

/**
 * Xử lý đăng nhập & gắn phiên vào Socket: CMD LOGIN|{"username":"...", "password":"..."}
 * Nếu tài khoản đã đăng nhập ở socket khác trong mảng all_clients -> gửi FORCE_LOGOUT đóng socket cũ.
 */
void handle_login(sqlite3 *db, ClientSession *client, ClientSession all_clients[], int max_clients, const char *payload);

/**
 * Lấy danh sách câu hỏi theo bộ lọc: CMD GET_QUESTIONS|{"difficulty":"all", "category":"all"}
 */
void handle_get_questions(sqlite3 *db, ClientSession *client, const char *payload);

/**
 * Thêm câu hỏi mới (Kiểm tra quyền role == "admin"): CMD ADD_QUESTION|{...}
 */
void handle_add_question(sqlite3 *db, ClientSession *client, const char *payload);

#endif
