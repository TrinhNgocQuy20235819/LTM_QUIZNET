#ifndef QUESTION_H
#define QUESTION_H

#include <sqlite3.h>
#include "stream_io.h"


/**
 * Lấy danh sách câu hỏi theo bộ lọc: CMD GET_QUESTIONS|{"difficulty":"all", "category":"all"}
 */
void handle_get_questions(sqlite3 *db, ClientSession *client, const char *payload);

/**
 * Thêm câu hỏi mới (Kiểm tra quyền role == "admin"): CMD ADD_QUESTION|{...}
 */
void handle_add_question(sqlite3 *db, ClientSession *client, const char *payload);

/**
 * Lấy danh sách chủ đề câu hỏi: CMD GET_CATEGORIES|{}
 */
void handle_get_categories(sqlite3 *db, ClientSession *client);

/**
 * Lấy danh sách tài khoản sinh viên để Host chọn vào phòng thi: CMD GET_STUDENTS_LIST|{}
 */
void handle_get_students_list(sqlite3 *db, ClientSession *client, const char *payload);


#endif
