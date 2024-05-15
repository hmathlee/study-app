from fastapi import Request
from google.cloud import storage
import MySQLdb as mdb

import os
import yaml
import base64

# Config
cfg = yaml.safe_load(open("secrets/secrets.yaml", "r"))

# GCS
storage_client = storage.Client.from_service_account_json("secrets/profound-saga-420500-b3f6a7d4835f.json")


def get_cursor(return_connection=False):
    conn = mdb.connect(cfg["MYSQL_SERVER"], cfg["MYSQL_USERNAME"], cfg["MYSQL_PASSWORD"], "study-app-users")
    cursor = conn.cursor()
    if return_connection:
        return cursor, conn
    return cursor


def set_response_cookie(response, user_id):
    # Generate session ID
    session_id_bytes = os.urandom(16)
    session_id = base64.urlsafe_b64encode(session_id_bytes).decode("utf-8")
    response.set_cookie("session_id", session_id)

    # Insert session ID. In the (small) chance that a duplicate session ID is generated, regenerate until unique
    duplicate_session_id = True
    while duplicate_session_id:
        cursor, conn = get_cursor(return_connection=True)
        cursor.execute("SELECT * FROM user_sessions where session_id=%s", (session_id, ))

        # If no results are returned for the session ID, create a new session
        q = cursor.fetchone()
        if q is None:
            cursor.execute("INSERT INTO user_sessions (session_id, user_id) VALUES (%s, %s)", (session_id, user_id))
            conn.commit()
            conn.close()
            duplicate_session_id = False

    return response


def get_user_credential_from_request_cookies(request: Request, attr: str):
    # Get user ID from request cookies
    session_id = request.cookies.get("session_id")
    cursor = get_cursor()
    cursor.execute("SELECT user_id FROM user_sessions WHERE session_id=%s", (session_id,))
    user_id = cursor.fetchone()

    if user_id is None:
        return None
    else:
        user_id = user_id[0]

    # Get attribute from row keyed by user ID
    cursor.execute("SELECT * FROM user_credentials where id=%s", (user_id, ))
    q = cursor.fetchone()

    if q is None:
        # Special case: if we're just looking for ID, return the ID
        if attr == "id":
            return user_id
        else:
            return None

    names = [desc[0] for desc in cursor.description]
    return str(q[names.index(attr)])


def remove_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    cursor, conn = get_cursor(return_connection=True)
    cursor.execute("DELETE FROM user_sessions WHERE session_id=%s", (session_id, ))
    conn.commit()
    conn.close()


def remove_temp_bucket(temp_bucket):
    buckets = storage_client.list_buckets()
    buckets = [bucket.name for bucket in buckets]
    if temp_bucket in buckets:
        b = storage_client.get_bucket(temp_bucket)
        blobs = b.list_blobs()
        for blob in blobs:
            blob.delete()
        b.delete()


if __name__ == "__main__":
    pass
