#ifndef DB_INIT_H
#define DB_INIT_H

#include <sqlite3.h>

/**
 * Tự động tạo các bảng còn thiếu, nâng cấp cột mới (Migration)
 * và nạp tài khoản mẫu để đồng bộ DB giữa các thành viên.
 */
void init_database_schema(sqlite3 *db);

#endif