# -*- coding: UTF-8 -*-
"""
User MySQL handler — DB operations for user auth
"""

import logging
import uuid
from datetime import datetime, timedelta

import pymysql

from app.plugin.auth import hash_password, verify_password

from .connect import ConnectMysqlHandler

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15


class UserMysqlHandler:

    @staticmethod
    def is_user_exist(username: str) -> bool:
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                return cursor.fetchone() is not None
        except Exception as ex:
            logging.warning(f"检查用户存在失败: {ex}")
            return False
        finally:
            if connect:
                connect.close()

    @staticmethod
    def create_user(username: str, password: str) -> tuple:
        """Create a new user. Returns (success: bool, message: str)."""
        if UserMysqlHandler.is_user_exist(username):
            return False, "用户名已存在"

        user_id = str(uuid.uuid4()).replace("-", "")
        password_hash_val = hash_password(password)
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                sql = "INSERT INTO users (id, username, password_hash) VALUES (%s, %s, %s)"
                cursor.execute(sql, (user_id, username, password_hash_val))
                connect.commit()
                return True, user_id
        except Exception as ex:
            logging.warning(f"创建用户失败: {ex}")
            return False, str(ex)
        finally:
            if connect:
                connect.close()

    @staticmethod
    def verify_user(username: str, password: str) -> tuple:
        """Verify login credentials. Returns (success: bool, user_data|message: dict|str)."""
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, password_hash, email, is_active, "
                    "failed_login_attempts, locked_until FROM users WHERE username = %s",
                    (username,),
                )
                user = cursor.fetchone()
                if not user:
                    return False, "用户名或密码错误"

                # Check if account is locked
                if user.get("locked_until"):
                    try:
                        locked_until = datetime.fromisoformat(str(user["locked_until"]))
                        if datetime.now() < locked_until:
                            remaining = int((locked_until - datetime.now()).total_seconds() / 60) + 1
                            return False, f"账户已锁定，请 {remaining} 分钟后重试"
                    except ValueError:
                        pass

                # Verify password
                if not verify_password(password, user["password_hash"]):
                    # Increment failed attempts
                    attempts = (user.get("failed_login_attempts") or 0) + 1
                    if attempts >= MAX_FAILED_ATTEMPTS:
                        locked_until = (datetime.now() + timedelta(minutes=LOCK_DURATION_MINUTES)).isoformat()
                        cursor.execute(
                            "UPDATE users SET failed_login_attempts = %s, locked_until = %s WHERE id = %s",
                            (attempts, locked_until, user["id"]),
                        )
                        connect.commit()
                        return False, f"密码错误次数过多，账户已锁定 {LOCK_DURATION_MINUTES} 分钟"
                    cursor.execute("UPDATE users SET failed_login_attempts = %s WHERE id = %s", (attempts, user["id"]))
                    connect.commit()
                    return False, "用户名或密码错误"

                # Login success - reset attempts + update last_login
                cursor.execute(
                    "UPDATE users SET failed_login_attempts = 0, locked_until = NULL, "
                    "last_login = NOW() WHERE id = %s",
                    (user["id"],),
                )
                connect.commit()

                return True, {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user.get("email"),
                    "is_active": user.get("is_active", 1),
                }
        except Exception as ex:
            logging.warning(f"验证用户失败: {ex}")
            return False, str(ex)
        finally:
            if connect:
                connect.close()

    @staticmethod
    def get_user_profile(user_id: str) -> dict:
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, email, is_active, created_at, last_login FROM users WHERE id = %s", (user_id,)
                )
                user = cursor.fetchone()
                if user:
                    if isinstance(user.get("created_at"), datetime):
                        user["created_at"] = user["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(user.get("last_login"), datetime):
                        user["last_login"] = user["last_login"].strftime("%Y-%m-%d %H:%M:%S")
                return user
        except Exception as ex:
            logging.warning(f"获取用户资料失败: {ex}")
            return None
        finally:
            if connect:
                connect.close()

    @staticmethod
    def update_profile(user_id: str, email: str = None) -> tuple:
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                if email is not None:
                    cursor.execute("UPDATE users SET email = %s WHERE id = %s", (email, user_id))
                    connect.commit()
            return True, "更新成功"
        except Exception as ex:
            logging.warning(f"更新资料失败: {ex}")
            return False, str(ex)
        finally:
            if connect:
                connect.close()

    @staticmethod
    def change_password(user_id: str, old_password: str, new_password: str) -> tuple:
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    return False, "用户不存在"

                if not verify_password(old_password, user["password_hash"]):
                    return False, "原密码错误"

                new_hash = hash_password(new_password)
                cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
                connect.commit()
                return True, "密码修改成功"
        except Exception as ex:
            logging.warning(f"修改密码失败: {ex}")
            return False, str(ex)
        finally:
            if connect:
                connect.close()
