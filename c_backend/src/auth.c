#include "auth.h"
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
        sqlite3_int64 new_uid = sqlite3_last_insert_rowid(db);

        const char *s_code = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "student_code"));
        const char *f_name = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "full_name"));
        const char *c_name = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "class_name"));
        const char *course = cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root, "course"));

        const char *sql_st = "INSERT INTO students (user_id, student_code, full_name, class_name, course) VALUES (?, ?, ?, ?, ?);";
        sqlite3_stmt *stmt_st = NULL;
        if (sqlite3_prepare_v2(db, sql_st, -1, &stmt_st, NULL) == SQLITE_OK) {
            sqlite3_bind_int64(stmt_st, 1, new_uid);
            if (s_code && strlen(s_code) > 0) sqlite3_bind_text(stmt_st, 2, s_code, -1, SQLITE_STATIC);
            else sqlite3_bind_null(stmt_st, 2);
            sqlite3_bind_text(stmt_st, 3, f_name ? f_name : j_user->valuestring, -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt_st, 4, c_name ? c_name : "", -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt_st, 5, course ? course : "", -1, SQLITE_STATIC);
            sqlite3_step(stmt_st);
            sqlite3_finalize(stmt_st);
        }

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

void handle_logout(ClientSession *client) {
    if (!client->is_logged_in) {
        send_line(client->sock_fd, "ERROR", "{\"message\":\"Ban chua dang nhap!\"}");
        return;
    }

    printf("[AUTH] Dang xuat: %s (%s:%d, FD=%d)\n",
           client->username, client->ip_addr, client->port, client->sock_fd);

    client->is_logged_in = 0;
    client->user_id = -1;
    memset(client->username, 0, sizeof(client->username));
    memset(client->role, 0, sizeof(client->role));

    send_line(client->sock_fd, "LOGOUT_OK", "{\"message\":\"Dang xuat thanh cong!\"}");
}