# -*- coding: UTF-8 -*-
"""
Chat MySQL handler — DB operations for conversation persistence
"""
import logging
import json
import uuid
import pymysql
from datetime import datetime
from .connect import ConnectMysqlHandler


class ChatMysqlHandler:

    @staticmethod
    def list_conversations(user_id: str, limit: int = 50, offset: int = 0, keyword: str = None) -> list:
        """List conversations for a user (without message content)."""
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = """
                    SELECT id, title, pinned, created_at, updated_at
                    FROM conversations
                    WHERE user_id = %s
                """
                params = [user_id]
                if keyword:
                    sql += " AND title LIKE %s"
                    params.append(f"%{keyword}%")
                sql += " ORDER BY pinned DESC, updated_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as ex:
            logging.warning(f"查询对话列表失败: {ex}")
            return []
        finally:
            if connect:
                connect.close()

    @staticmethod
    def get_conversation(conv_id: str, user_id: str) -> dict | None:
        """Load a single conversation with full messages."""
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM conversations WHERE id = %s AND user_id = %s",
                    (conv_id, user_id),
                )
                row = cursor.fetchone()
                if row:
                    row['messages'] = json.loads(row['messages']) if isinstance(row.get('messages'), str) else (row.get('messages') or [])
                return row
        except Exception as ex:
            logging.warning(f"查询对话失败: {ex}")
            return None
        finally:
            if connect:
                connect.close()

    @staticmethod
    def save_conversation(user_id: str, data: dict) -> tuple:
        """Insert or update a conversation. Returns (success: bool, message: str)."""
        conv_id = data.get('id') or str(uuid.uuid4()).replace('-', '')
        title = data.get('title', '新对话')
        messages = json.dumps(data.get('messages', []), ensure_ascii=False)
        pinned = 1 if data.get('pinned') else 0

        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                # Check if exists
                cursor.execute("SELECT id FROM conversations WHERE id = %s", (conv_id,))
                exists = cursor.fetchone()

                if exists:
                    sql = """
                        UPDATE conversations
                        SET title = %s, messages = %s, pinned = %s, updated_at = %s
                        WHERE id = %s AND user_id = %s
                    """
                    cursor.execute(sql, (title, messages, pinned, datetime.now(), conv_id, user_id))
                else:
                    sql = """
                        INSERT INTO conversations (id, user_id, title, messages, pinned, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (conv_id, user_id, title, messages, pinned, datetime.now(), datetime.now()))

                connect.commit()
                return True, conv_id
        except Exception as ex:
            logging.warning(f"保存对话失败: {ex}")
            return False, str(ex)
        finally:
            if connect:
                connect.close()

    @staticmethod
    def delete_conversation(conv_id: str, user_id: str) -> bool:
        """Delete a conversation."""
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM conversations WHERE id = %s AND user_id = %s",
                    (conv_id, user_id),
                )
                connect.commit()
                return cursor.rowcount > 0
        except Exception as ex:
            logging.warning(f"删除对话失败: {ex}")
            return False
        finally:
            if connect:
                connect.close()

    @staticmethod
    def update_feedback(conv_id: str, user_id: str, msg_id: str, feedback: str) -> bool:
        """Update feedback on a specific message within a conversation."""
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT messages FROM conversations WHERE id = %s AND user_id = %s",
                    (conv_id, user_id),
                )
                row = cursor.fetchone()
                if not row:
                    return False

                msgs = json.loads(row['messages']) if isinstance(row['messages'], str) else (row.get('messages') or [])
                for m in msgs:
                    if m.get('id') == msg_id:
                        m['feedback'] = feedback
                        break

                with connect.cursor() as update_cursor:
                    update_cursor.execute(
                        "UPDATE conversations SET messages = %s, updated_at = %s WHERE id = %s AND user_id = %s",
                        (json.dumps(msgs, ensure_ascii=False), datetime.now(), conv_id, user_id),
                    )
                connect.commit()
                return True
        except Exception as ex:
            logging.warning(f"更新反馈失败: {ex}")
            return False
        finally:
            if connect:
                connect.close()
