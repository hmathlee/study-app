from fastapi import Request

import MySQLdb as mdb
import yaml
import random
import string
import os
import base64


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
    user_id = get_column_value_from_cursor(cursor, "id")
    if user_id:
        return {
            "status": "OK",
            "user_id": user_id
        }
    return {"status": "Invalid email or password"}


def insert_session_id(session_id, user_id):
    cursor, conn = get_cursor(return_connection=True)
    cursor.execute("SELECT * FROM user_sessions where session_id=%s", (session_id, ))
    user_id_check = get_column_value_from_cursor(cursor, "user_id")
    if user_id_check is None:
        cursor.execute("INSERT INTO user_sessions (session_id, user_id) VALUES (%s, %s)", (session_id, user_id))

    conn.commit()
    conn.close()


def set_response_cookie(response, user_id):
    # Generate session ID
    session_id_bytes = os.urandom(16)
    session_id = base64.urlsafe_b64encode(session_id_bytes).decode("utf-8")
    response.set_cookie("session_id", session_id)
    insert_session_id(session_id, user_id)

    return response


def get_user_id_from_request_cookies(request: Request):
    if "session_id" in request.cookies:
        session_id = request.cookies.get("session_id")
        cursor = get_cursor()
        cursor.execute("SELECT * FROM user_sessions WHERE session_id=%s", (session_id,))
        return get_column_value_from_cursor(cursor, "user_id")
    else:
        return None


def get_gcs_user_id(user_id):
    if user_id:
        user_id = "study-app-user-" + user_id
    else:
        user_id = "study-app-" + user_id
    return user_id


def get_user_credential_from_request_cookies(request: Request, attr: str):
    user_id = get_user_id_from_request_cookies(request)
    if user_id:
        cursor = get_cursor()
        cursor.execute("SELECT * FROM user_credentials where id=%s", (user_id, ))
        return get_column_value_from_cursor(cursor, attr)
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


if __name__ == "__main__":
    pass