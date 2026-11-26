#include "db_init.h"
#include <stdio.h>
#include <string.h>

// Hàm phụ: Kiểm tra xem 1 cột đã tồn tại trong bảng chưa (tránh lỗi khi ALTER TABLE nhiều lần)
static int column_exists(sqlite3 *db, const char *table_name, const char *col_name) {
    char sql[256];
    snprintf(sql, sizeof(sql), "PRAGMA table_info(%s);", table_name);
    sqlite3_stmt *stmt = NULL;
    int found = 0;

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            const char *name = (const char *)sqlite3_column_text(stmt, 1);
            if (name && strcmp(name, col_name) == 0) {
                found = 1;
                break;
            }
        }
        sqlite3_finalize(stmt);
    }
    return found;
}

void init_database_schema(sqlite3 *db) {
    char *err_msg = NULL;

    // 1. Bật khóa ngoại và chế độ WAL (cho phép đọc/ghi song song khi demo)
    sqlite3_exec(db, "PRAGMA foreign_keys = ON;", NULL, NULL, NULL);
    sqlite3_exec(db, "PRAGMA journal_mode = WAL;", NULL, NULL, NULL);

    // 2. Tạo đầy đủ 6 bảng chuẩn của dự án nếu chưa tồn tại
    const char *schema_sql =
        "CREATE TABLE IF NOT EXISTS users ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  username TEXT UNIQUE NOT NULL,"
        "  password_hash TEXT NOT NULL,"
        "  role TEXT NOT NULL DEFAULT 'student',"
        "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ");"
        "CREATE TABLE IF NOT EXISTS questions ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  content TEXT NOT NULL,"
        "  option_a TEXT NOT NULL, option_b TEXT NOT NULL,"
        "  option_c TEXT NOT NULL, option_d TEXT NOT NULL,"
        "  correct_answer TEXT NOT NULL,"
        "  difficulty TEXT NOT NULL,"
        "  category TEXT NOT NULL,"
        "  explanation TEXT,"
        "  created_by TEXT DEFAULT 'admin',"
        "  purpose TEXT NOT NULL DEFAULT 'practice',"
        "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ");"
        "CREATE TABLE IF NOT EXISTS exam_rooms ("
        "  room_code TEXT PRIMARY KEY,"
        "  room_name TEXT NOT NULL,"
        "  host_name TEXT NOT NULL,"
        "  duration_minutes INTEGER NOT NULL,"
        "  num_questions INTEGER NOT NULL,"
        "  easy_count INTEGER DEFAULT 0,"
        "  medium_count INTEGER DEFAULT 0,"
        "  hard_count INTEGER DEFAULT 0,"
        "  status TEXT NOT NULL DEFAULT 'waiting',"
        "  question_ids_json TEXT,"
        "  room_type TEXT DEFAULT 'exam',"
        "  scheduled_start_time TIMESTAMP,"
        "  allowed_users_json TEXT DEFAULT '[]',"
        "  is_public BOOLEAN DEFAULT 0,"
        "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        "  started_at TIMESTAMP,"
        "  ended_at TIMESTAMP"
        ");"
        "CREATE TABLE IF NOT EXISTS room_participants ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  room_code TEXT NOT NULL,"
        "  user_name TEXT NOT NULL,"
        "  joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        "  submitted_at TIMESTAMP,"
        "  is_submitted BOOLEAN DEFAULT 0,"
        "  score REAL DEFAULT 0,"
        "  correct_count INTEGER DEFAULT 0,"
        "  total_questions INTEGER DEFAULT 0,"
        "  answers_json TEXT,"
        "  FOREIGN KEY (room_code) REFERENCES exam_rooms(room_code) ON DELETE CASCADE,"
        "  UNIQUE(room_code, user_name)"
        ");"
        "CREATE TABLE IF NOT EXISTS exam_history ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  user_name TEXT NOT NULL,"
        "  exam_type TEXT NOT NULL,"
        "  room_code TEXT,"
        "  title TEXT NOT NULL,"
        "  total_questions INTEGER NOT NULL,"
        "  correct_count INTEGER NOT NULL,"
        "  score REAL NOT NULL,"
        "  duration_seconds INTEGER NOT NULL,"
        "  completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        "  details_json TEXT"
        ");"
        "CREATE TABLE IF NOT EXISTS activity_logs ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        "  username TEXT,"
        "  ip_port TEXT,"
        "  socket_fd INTEGER,"
        "  event TEXT NOT NULL,"
        "  status TEXT,"
        "  details TEXT"
        ");"
        "CREATE TABLE IF NOT EXISTS students ("
        "  user_id INTEGER PRIMARY KEY,"
        "  student_code TEXT UNIQUE,"
        "  full_name TEXT,"
        "  class_name TEXT,"
        "  course TEXT,"
        "  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
        ");";

    if (sqlite3_exec(db, schema_sql, NULL, NULL, &err_msg) != SQLITE_OK) {
        fprintf(stderr, "[DB INIT ERROR] %s\n", err_msg);
        sqlite3_free(err_msg);
    }

    // 3. Tự động nâng cấp (Migration) nếu bảng cũ thiếu cột mới
    if (!column_exists(db, "questions", "created_by"))
        sqlite3_exec(db, "ALTER TABLE questions ADD COLUMN created_by TEXT DEFAULT 'admin';", NULL, NULL, NULL);

    if (!column_exists(db, "questions", "purpose")) {
        sqlite3_exec(db, "ALTER TABLE questions ADD COLUMN purpose TEXT NOT NULL DEFAULT 'practice';", NULL, NULL, NULL);
        // Tự động chuyển các câu có ID chẵn sang kho 'exam' (chỉ chạy đúng 1 lần khi nâng cấp)
        // Giúp hệ thống có sẵn ~15 câu cho Thi chính thức và ~16 câu cho Luyện tập để test ngay!
        sqlite3_exec(db, "UPDATE questions SET purpose = 'exam' WHERE id % 2 = 0;", NULL, NULL, NULL);
    }

    if (!column_exists(db, "exam_rooms", "room_type"))
        sqlite3_exec(db, "ALTER TABLE exam_rooms ADD COLUMN room_type TEXT DEFAULT 'exam';", NULL, NULL, NULL);

    if (!column_exists(db, "exam_rooms", "scheduled_start_time"))
        sqlite3_exec(db, "ALTER TABLE exam_rooms ADD COLUMN scheduled_start_time TIMESTAMP;", NULL, NULL, NULL);

    if (!column_exists(db, "exam_rooms", "allowed_users_json"))
        sqlite3_exec(db, "ALTER TABLE exam_rooms ADD COLUMN allowed_users_json TEXT DEFAULT '[]';", NULL, NULL, NULL);

    if (!column_exists(db, "exam_rooms", "is_public"))
        sqlite3_exec(db, "ALTER TABLE exam_rooms ADD COLUMN is_public BOOLEAN DEFAULT 0;", NULL, NULL, NULL);

    // 4. Nạp sẵn các tài khoản mẫu cho 3 vai trò RBAC (chỉ thêm nếu chưa có)
    const char *seed_users_sql =
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('admin', 'admin123', 'admin');"
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('giangvien1', '123', 'teacher');"
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('sinhvien1', '123', 'student');"
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('sinhvien2', '123', 'student');";
    sqlite3_exec(db, seed_users_sql, NULL, NULL, NULL);

    // 5. Nạp hồ sơ mẫu vào bảng students (nếu chưa có)
    const char *seed_students_sql =
        "INSERT OR IGNORE INTO students (user_id, student_code, full_name, class_name, course) "
        "SELECT id, 'B21DCCN001', 'Nguyen Van A', 'D21CQCN01', 'K21' FROM users WHERE username = 'sinhvien1';"
        "INSERT OR IGNORE INTO students (user_id, student_code, full_name, class_name, course) "
        "SELECT id, 'B21DCCN002', 'Tran Thi B', 'D21CQCN02', 'K21' FROM users WHERE username = 'sinhvien2';";
    sqlite3_exec(db, seed_students_sql, NULL, NULL, NULL);

    printf("[DB] Da kiem tra va dong bo cau truc 6 bang & tai khoan mau thanh cong!\n");
}