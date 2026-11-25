#include "auth_question.h"
#include "cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void handle_register(sqlite3 *db, ClientSession *client, const char *payload) {
    cJSON *root = cJSON_Parse(payload);
    if (!root) {
        send_line(client->sock_fd, "REGISTER_ERR", "{\"message\":\"Dinh dang JSON khong hop le\"}");
        return;
    }

    cJSON *j_user = cJSON_GetObjectItemCaseSensitive(root, "username");
    cJSON *j_pass = cJSON_GetObjectItemCaseSensitive(root, "password");

    if (!cJSON_IsString(j_user) || !cJSON_IsString(j_pass) ||
        strlen(j_user->valuestring) < 2 || strlen(j_pass->valuestring) < 3) {
        send_line(client->sock_fd, "REGISTER_ERR", "{\"message\":\"Username >= 2 ky tu, Password >= 3 ky tu\"}");
        cJSON_Delete(root);
        return;
    }

    const char *sql = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'student');";
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        send_line(client->sock_fd, "REGISTER_ERR", "{\"message\":\"Loi truy van CSDL\"}");
        cJSON_Delete(root);
        return;
    }

    sqlite3_bind_text(stmt, 1, j_user->valuestring, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, j_pass->valuestring, -1, SQLITE_STATIC);

    int rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc == SQLITE_DONE) {
        send_line(client->sock_fd, "REGISTER_OK", "{\"message\":\"Dang ky thanh cong! Hay dang nhap.\"}");
        printf("[AUTH] Dang ky tai khoan moi: %s (%s:%d)\n", j_user->valuestring, client->ip_addr, client->port);
    } else {
        send_line(client->sock_fd, "REGISTER_ERR", "{\"message\":\"Ten dang nhap da ton tai!\"}");
    }

    cJSON_Delete(root);
}

void handle_login(sqlite3 *db, ClientSession *client, ClientSession all_clients[], int max_clients, const char *payload) {
    cJSON *root = cJSON_Parse(payload);
    if (!root) {
        send_line(client->sock_fd, "LOGIN_ERR", "{\"message\":\"JSON khong hop le\"}");
        return;
    }

    cJSON *j_user = cJSON_GetObjectItemCaseSensitive(root, "username");
    cJSON *j_pass = cJSON_GetObjectItemCaseSensitive(root, "password");

    if (!cJSON_IsString(j_user) || !cJSON_IsString(j_pass)) {
        send_line(client->sock_fd, "LOGIN_ERR", "{\"message\":\"Thieu username hoac password\"}");
        cJSON_Delete(root);
        return;
    }

    const char *sql = "SELECT id, username, role FROM users WHERE username = ? AND password_hash = ?;";
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        send_line(client->sock_fd, "LOGIN_ERR", "{\"message\":\"Loi truy van CSDL\"}");
        cJSON_Delete(root);
        return;
    }

    sqlite3_bind_text(stmt, 1, j_user->valuestring, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, j_pass->valuestring, -1, SQLITE_STATIC);

    if (sqlite3_step(stmt) == SQLITE_ROW) {
        int uid = sqlite3_column_int(stmt, 0);
        const char *uname = (const char *)sqlite3_column_text(stmt, 1);
        const char *urole = (const char *)sqlite3_column_text(stmt, 2);

        // Kiểm tra & đá phiên cũ nếu tài khoản này đang online ở socket khác
        for (int i = 0; i < max_clients; i++) {
            if (all_clients[i].sock_fd != -1 &&
                all_clients[i].sock_fd != client->sock_fd &&
                all_clients[i].is_logged_in &&
                strcmp(all_clients[i].username, uname) == 0) {
                printf("[SESSION] Phat hien dang nhap trung lap '%s' -> Dong socket cu FD=%d\n",
                       uname, all_clients[i].sock_fd);
                send_line(all_clients[i].sock_fd, "FORCE_LOGOUT",
                          "{\"message\":\"Tai khoan da dang nhap tu thiet bi khac!\"}");
                close(all_clients[i].sock_fd);
                init_client_session(&all_clients[i]);
            }
        }

        // Gắn thông tin phiên vào ClientSession hiện tại
        client->is_logged_in = 1;
        client->user_id = uid;
        strncpy(client->username, uname, MAX_USERNAME - 1);
        strncpy(client->role, urole, MAX_ROLE - 1);

        cJSON *res = cJSON_CreateObject();
        cJSON_AddStringToObject(res, "username", client->username);
        cJSON_AddStringToObject(res, "role", client->role);
        cJSON_AddStringToObject(res, "ip", client->ip_addr);
        cJSON_AddNumberToObject(res, "port", client->port);

        char *res_str = cJSON_PrintUnformatted(res);
        send_line(client->sock_fd, "LOGIN_OK", res_str);
        printf("[AUTH] Dang nhap thanh cong: %s (role=%s) tai %s:%d (FD=%d)\n",
               client->username, client->role, client->ip_addr, client->port, client->sock_fd);

        free(res_str);
        cJSON_Delete(res);
    } else {
        send_line(client->sock_fd, "LOGIN_ERR", "{\"message\":\"Sai ten dang nhap hoac mat khau!\"}");
    }

    sqlite3_finalize(stmt);
    cJSON_Delete(root);
}

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

void handle_get_students_list(sqlite3 *db, ClientSession *client) {
    if (!client->is_logged_in) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Vui long dang nhap truoc!\"}");
        return;
    }

    const char *sql = "SELECT id, username FROM users WHERE role = 'student' ORDER BY username ASC;";
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Loi truy van danh sach sinh vien\"}");
        return;
    }

    cJSON *arr = cJSON_CreateArray();
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        cJSON *u = cJSON_CreateObject();
        cJSON_AddNumberToObject(u, "id", sqlite3_column_int(stmt, 0));
        cJSON_AddStringToObject(u, "username", (const char *)sqlite3_column_text(stmt, 1));
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
}
