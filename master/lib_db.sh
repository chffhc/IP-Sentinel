#!/bin/bash
# SQLite helper functions for IP-Sentinel Master.
# Static schema/PRAGMA statements may use db_exec. Runtime data must use db_query
# with SQLite CLI parameters to avoid SQL injection through Telegram callbacks.

db_exec() {
    printf ".timeout 5000\n%s\n" "$1" | sqlite3 "$DB_FILE"
}

sqlite_literal() {
    local value="${1-}"
    value=${value//\'/\'\'}
    printf "'%s'" "$value"
}

db_query() {
    local sql="$1"
    shift
    {
        printf ".timeout 5000\n"
        printf ".parameter init\n"
        # Avoid feeding untrusted values to `.parameter set @pN VALUE` directly:
        # sqlite3's dot-command parser can split on spaces/semicolons before SQL
        # parsing. Populate the same temp.sqlite_parameters table with escaped
        # SQL literals instead, then execute the parameterized statement.
        printf "DELETE FROM temp.sqlite_parameters;\n"
        local idx=1
        local param
        for param in "$@"; do
            printf "INSERT INTO temp.sqlite_parameters(key, value) VALUES('@p%d', %s);\n" "$idx" "$(sqlite_literal "$param")"
            idx=$((idx + 1))
        done
        printf "%s\n" "$sql"
    } | sqlite3 "$DB_FILE"
}
