from fastapi import Request

import MySQLdb as mdb
import yaml

cfg = yaml.safe_load(open("secrets/secrets.yaml", "r"))


def get_cursor(return_connection=False):
    conn = mdb.connect(cfg["MYSQL_SERVER"], cfg["MYSQL_USERNAME"], cfg["MYSQL_PASSWORD"], "study-app-users")
    cursor = conn.cursor()
    if return_connection:
        return cursor, conn
    return cursor


def get_column_value_from_cursor(cursor, colname):
    query_result = cursor.fetchone()
    if query_result is None:
        return None
    col_idx = 0
    for desc in cursor.description:
        if desc[0] == colname:
            break
        else:
            col_idx += 1
    return query_result[col_idx]


def mysql_register_user(email, username, password):
    cursor, conn = get_cursor(return_connection=True)

    # Ensure that email is not already in database
    cursor.execute("SELECT * FROM user_credentials WHERE email=%s", (email, ))
    email_exist = cursor.fetchone()
    if email_exist:
        return {"status": "That email is already taken!"}

    # If full set of user credentials, insert
    if username != "" and password != "":
        cursor.execute("INSERT INTO user_credentials (email, username, password) VALUES (%s, %s, %s)",
                       (email, username, password))

    conn.commit()
    conn.close()
    return {"status": "OK"}


def validate_user_login(email, password):
    cursor = get_cursor()
    cursor.execute("SELECT * FROM user_credentials WHERE email=%s AND password=%s", (email, password))
    username = get_column_value_from_cursor(cursor, "username")
    if username:
        return {
            "status": "OK",
            "username": username
        }
    return {"status": "Invalid email or password"}


def insert_session_id(session_id, username):
    cursor, conn = get_cursor(return_connection=True)
    cursor.execute("SELECT * FROM user_sessions where session_id=%s", (session_id, ))
    username_check = get_column_value_from_cursor(cursor, "username")
    if username_check is None:
        cursor.execute("INSERT INTO user_sessions (session_id, username) VALUES (%s, %s)", (session_id, username))

    conn.commit()
    conn.close()


def get_username_from_request_cookies(request: Request):
    if "session_id" in request.cookies:
        session_id = request.cookies.get("session_id")
        cursor = get_cursor()
        cursor.execute("SELECT username FROM user_sessions WHERE session_id=%s", (session_id,))
        return get_column_value_from_cursor(cursor, "username")
    else:
        return None


def remove_session_id(request: Request):
    # Check if request has an associated session ID
    if "session_id" in request.cookies:
        session_id = request.cookies.get("session_id")

        # Check that the session ID actually exists
        cursor, conn = get_cursor(return_connection=True)
        cursor.execute("SELECT session_id FROM user_sessions where session_id=%s", (session_id, ))
        id_check = get_column_value_from_cursor(cursor, "session_id")
        if id_check:
            cursor.execute("DELETE FROM user_sessions WHERE session_id=%s", (session_id, ))

        conn.commit()
        conn.close()
