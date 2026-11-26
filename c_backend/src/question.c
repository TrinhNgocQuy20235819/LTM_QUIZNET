#include "question.h"
#include "cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>


void handle_get_questions(sqlite3 *db, ClientSession *client, const char *payload) {
    if (!client->is_logged_in) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Vui long dang nhap truoc!\"}");
        return;
    }

    cJSON *root = cJSON_Parse(payload);
    const char *difficulty = "all";
    const char *category = "all";

    if (root) {
        cJSON *j_diff = cJSON_GetObjectItemCaseSensitive(root, "difficulty");
        cJSON *j_cat = cJSON_GetObjectItemCaseSensitive(root, "category");
        if (cJSON_IsString(j_diff) && strlen(j_diff->valuestring) > 0) difficulty = j_diff->valuestring;
        if (cJSON_IsString(j_cat) && strlen(j_cat->valuestring) > 0) category = j_cat->valuestring;
    }

    const char *sql =
        "SELECT id, content, option_a, option_b, option_c, option_d, difficulty, category "
        "FROM questions "
        "WHERE (? = 'all' OR difficulty = ?) AND (? = 'all' OR category = ?) "
        "ORDER BY id DESC LIMIT 100;";

    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Loi truy van cau hoi\"}");
        if (root) cJSON_Delete(root);
        return;
    }

    sqlite3_bind_text(stmt, 1, difficulty, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, difficulty, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, category, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, category, -1, SQLITE_STATIC);

    cJSON *arr = cJSON_CreateArray();
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        cJSON *q = cJSON_CreateObject();
        cJSON_AddNumberToObject(q, "id", sqlite3_column_int(stmt, 0));
        cJSON_AddStringToObject(q, "content", (const char *)sqlite3_column_text(stmt, 1));
        cJSON_AddStringToObject(q, "option_a", (const char *)sqlite3_column_text(stmt, 2));
        cJSON_AddStringToObject(q, "option_b", (const char *)sqlite3_column_text(stmt, 3));
        cJSON_AddStringToObject(q, "option_c", (const char *)sqlite3_column_text(stmt, 4));
        cJSON_AddStringToObject(q, "option_d", (const char *)sqlite3_column_text(stmt, 5));
        cJSON_AddStringToObject(q, "difficulty", (const char *)sqlite3_column_text(stmt, 6));
        cJSON_AddStringToObject(q, "category", (const char *)sqlite3_column_text(stmt, 7));
        cJSON_AddItemToArray(arr, q);
    }
    sqlite3_finalize(stmt);

    cJSON *res = cJSON_CreateObject();
    cJSON_AddNumberToObject(res, "total", cJSON_GetArraySize(arr));
    cJSON_AddItemToObject(res, "questions", arr);

    char *res_str = cJSON_PrintUnformatted(res);
    send_line(client->sock_fd, "QUESTIONS_LIST", res_str);

    free(res_str);
    cJSON_Delete(res);
    if (root) cJSON_Delete(root);
}

void handle_add_question(sqlite3 *db, ClientSession *client, const char *payload) {
    if (!client->is_logged_in) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Chua dang nhap!\"}");
        return;
    }
    // Kiểm soát quyền truy cập (Access Control)
    if (strcmp(client->role, "admin") != 0) {
        send_line(client->sock_fd, "FORBIDDEN", "{\"message\":\"Chi Admin moi co quyen them cau hoi!\"}");
        return;
    }

    cJSON *root = cJSON_Parse(payload);
    if (!root) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"JSON khong hop le\"}");
        return;
    }

    const char *content = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "content"));
    const char *opt_a = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "option_a"));
    const char *opt_b = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "option_b"));
    const char *opt_c = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "option_c"));
    const char *opt_d = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "option_d"));
    const char *correct = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "correct_answer"));
    const char *diff = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "difficulty"));
    const char *cat = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "category"));
    const char *expl = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "explanation"));

    if (!content || !opt_a || !opt_b || !opt_c || !opt_d || !correct || !diff || !cat) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Thieu thong tin cau hoi\"}");
        cJSON_Delete(root);
        return;
    }

    const char *sql =
        "INSERT INTO questions (content, option_a, option_b, option_c, option_d, correct_answer, difficulty, category, explanation) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);";
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, content, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 2, opt_a, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 3, opt_b, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 4, opt_c, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 5, opt_d, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 6, correct, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 7, diff, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 8, cat, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 9, expl ? expl : "", -1, SQLITE_STATIC);

        if (sqlite3_step(stmt) == SQLITE_DONE) {
            send_line(client->sock_fd, "ADD_QUESTION_OK", "{\"message\":\"Da them cau hoi moi vao CSDL!\"}");
        } else {
            send_line(client->sock_fd, "ERROR", "{\"message\":\"Khong the luu cau hoi\"}");
        }
        sqlite3_finalize(stmt);
    }

    cJSON_Delete(root);
}

void handle_get_categories(sqlite3 *db, ClientSession *client) {
    if (!client->is_logged_in) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Vui long dang nhap truoc!\"}");
        return;
    }

    const char *sql = "SELECT DISTINCT category FROM questions ORDER BY category ASC;";
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Loi truy van danh muc\"}");
        return;
    }

    cJSON *arr = cJSON_CreateArray();
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        const char *cat = (const char *)sqlite3_column_text(stmt, 0);
        if (cat) {
            cJSON_AddItemToArray(arr, cJSON_CreateString(cat));
        }
    }
    sqlite3_finalize(stmt);

    cJSON *res = cJSON_CreateObject();
    cJSON_AddItemToObject(res, "categories", arr);

    char *res_str = cJSON_PrintUnformatted(res);
    send_line(client->sock_fd, "CATEGORIES_LIST", res_str);

    free(res_str);
    cJSON_Delete(res);
}

void handle_get_students_list(sqlite3 *db, ClientSession *client, const char *payload) {
    if (!client->is_logged_in) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Vui long dang nhap truoc!\"}");
        return;
    }

    // Chỉ Giảng viên và Admin mới được phép lấy danh sách sinh viên
    if (strcmp(client->role, "teacher") != 0 && strcmp(client->role, "admin") != 0) {
        send_line(client->sock_fd, "FORBIDDEN", "{\"message\":\"Sinh vien khong co quyen xem danh sach sinh vien!\"}");
        return;
    }

    cJSON *root = cJSON_Parse(payload);
    const char *class_filter = "all";
    const char *course_filter = "all";

    if (root) {
        const char *c_val = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "class_name"));
        const char *k_val = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "course"));
        if (c_val && strlen(c_val) > 0) class_filter = c_val;
        if (k_val && strlen(k_val) > 0) course_filter = k_val;
    }

    const char *sql =
        "SELECT u.id, u.username, IFNULL(s.student_code, ''), IFNULL(s.full_name, u.username), "
        "       IFNULL(s.class_name, ''), IFNULL(s.course, '') "
        "FROM users u "
        "LEFT JOIN students s ON u.id = s.user_id "
        "WHERE u.role = 'student' "
        "  AND (? = 'all' OR s.class_name = ?) "
        "  AND (? = 'all' OR s.course = ?) "
        "ORDER BY u.username ASC;";

    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Loi truy van danh sach sinh vien\"}");
        if (root) cJSON_Delete(root);
        return;
    }

    sqlite3_bind_text(stmt, 1, class_filter, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, class_filter, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, course_filter, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, course_filter, -1, SQLITE_STATIC);

    cJSON *arr = cJSON_CreateArray();
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        cJSON *u = cJSON_CreateObject();
        cJSON_AddNumberToObject(u, "id", sqlite3_column_int(stmt, 0));
        cJSON_AddStringToObject(u, "username", (const char *)sqlite3_column_text(stmt, 1));
        cJSON_AddStringToObject(u, "student_code", (const char *)sqlite3_column_text(stmt, 2));
        cJSON_AddStringToObject(u, "full_name", (const char *)sqlite3_column_text(stmt, 3));
        cJSON_AddStringToObject(u, "class_name", (const char *)sqlite3_column_text(stmt, 4));
        cJSON_AddStringToObject(u, "course", (const char *)sqlite3_column_text(stmt, 5));
        cJSON_AddItemToArray(arr, u);
    }
    sqlite3_finalize(stmt);

    cJSON *res = cJSON_CreateObject();
    cJSON_AddNumberToObject(res, "total", cJSON_GetArraySize(arr));
    cJSON_AddItemToObject(res, "students", arr);

    char *res_str = cJSON_PrintUnformatted(res);
    send_line(client->sock_fd, "STUDENTS_LIST", res_str);

    free(res_str);
    cJSON_Delete(res);
    if (root) cJSON_Delete(root);
}
