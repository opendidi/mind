"""
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2025-08-19 15:12:24
"""

# -*- coding: UTF-8 -*-

import json
import logging
import os
import time
import uuid
from datetime import datetime

import pymysql
import pymysql.cursors

import app.util.file as PanoFile
from app.plugin.minio import minio_cdn_url
from app.plugin.minio.app.controller import MinioUtil
from app.util.log_config import setup_logging

from .connect import ConnectMysqlHandler

dirname = os.path.dirname(os.path.abspath(__name__))

# 获取操作系统类型
platform = os.name

if platform == "nt":
    logger = setup_logging(log_file=dirname + "\\app\\log\\MaterialMysqlHandler.log")


def extract_path_segment(url, start_segment="/pano/", levels=2):
    """Extract a path segment from a material URL.

    Supports both legacy /pano/ paths and current MinIO /mind/ paths.
    Falls back to extracting the bucket-relative directory prefix when
    the expected segment delimiter is not found.
    """
    # Try the configured segment first
    parts = url.split(start_segment)
    if len(parts) >= 2:
        path = parts[1]
        result = "/".join(path.split("/")[:levels])
        return result + "/"

    # Fallback: URL format is http://host/bucket/dir/.../file.ext
    # Extract the bucket-relative directory prefix
    # e.g. http://cdn/mind/123456/file.png → mind/123456/
    try:
        scheme_split = url.split("://", 1)[1] if "://" in url else url
        path_parts = scheme_split.split("/")
        # Skip host:port (index 0), then take bucket + first dir level
        if len(path_parts) >= 3:
            bucket = path_parts[1]  # "mind"
            first_dir = path_parts[2]  # "123456" (timestamp)
            return f"{bucket}/{first_dir}/"
        elif len(path_parts) >= 2:
            return path_parts[1] + "/"
    except (IndexError, ValueError):
        pass

    # Last resort: return the dirname portion of the URL path
    import os
    from urllib.parse import urlparse

    parsed = urlparse(url)
    dirname = os.path.dirname(parsed.path)
    return (dirname.lstrip("/") + "/") if dirname else ""


class MaterialMysqlHandler:

    def query_list(material_data, user_id):
        page_num = material_data.get("current")
        page_size = material_data.get("page_size")
        keyword = material_data.get("keyword")
        type = material_data.get("type")
        folder = material_data.get("folder")
        parent_id = material_data.get("parent_id")
        sort_order = material_data.get("sort_order")
        params = [user_id]
        connect = None
        try:
            # 计算起始记录的偏移量
            offset = (int(page_num) - 1) * int(page_size)
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                sql = """
          SELECT
            id, name, url, file_path, thumb_path, size, extension,
            created_at, description, parent_id, type, `lock`
          FROM
            material
          WHERE
            del = 0
            AND user_id = %s
        """
                if type is not None:
                    sql += "AND type = %s "
                    params.append(type)
                if folder is not None:
                    sql += "AND name = %s "
                    params.append(folder)
                if parent_id is not None:
                    sql += "AND parent_id = %s "
                    params.append(parent_id)
                if keyword is not None:
                    sql += "AND name LIKE %s "
                    params.append("%" + keyword + "%")
                # 添加动态排序
                if sort_order is not None:
                    # 防止SQL注入，只允许特定排序方向
                    order = "DESC" if sort_order.upper() == "DESC" else "ASC"
                    # 默认排序
                    sql += f"ORDER BY created_at {order} "
                else:
                    # 如果没有指定排序方向，默认降序
                    sql += "ORDER BY created_at DESC "
                sql += "LIMIT {} OFFSET {}".format(page_size, offset)
                cursor.execute(sql, tuple(params))
                results = cursor.fetchall()
                # 格式化时间
                for row in results:
                    # 检查 created_at 的类型
                    if isinstance(row["created_at"], str):
                        row["created_at"] = datetime.strptime(row["created_at"], "%a, %d %b %Y %H:%M:%S %Z").strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    elif isinstance(row["created_at"], datetime):
                        row["created_at"] = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")

                params_count = [user_id]

                count_sql = """
          SELECT COUNT(*) as total FROM material WHERE del = 0 AND user_id = %s
        """
                if parent_id is not None:
                    count_sql += "AND parent_id = %s "
                    params_count.append(parent_id)
                if keyword is not None:
                    count_sql += "AND name LIKE %s "
                    params_count.append("%" + keyword + "%")
                cursor.execute(count_sql, tuple(params_count))
                total = cursor.fetchone()["total"]

                return {
                    "list": results,
                    "total": int(total),
                    "current": int(page_num),
                    "page_size": int(page_size),
                }
        except Exception as e:
            logging.error(f"Material MySQL query_list 错误：{e}")
        finally:
            # 关闭数据库连接
            if connect:
                connect.close()

    def find_material_by_id(id, user_id=None):
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                if user_id:
                    sql = """
            SELECT
              id, name, url, file_path, thumb_path, size, extension,
              created_at,
              description,
              parent_id,
              type,
              `lock`,
              `path`
            FROM
              material
            WHERE
              id = %s and del = 0 and user_id = %s
          """
                    cursor.execute(sql, (id, user_id))
                else:
                    sql = """
            SELECT
              id, name, url, file_path, thumb_path, size, extension,
              created_at,
              description,
              parent_id,
              type,
              `lock`,
              `path`
            FROM
              material
            WHERE
              id = %s and del = 0
          """
                    cursor.execute(sql, (id,))
                # 获取所有记录列表
                return cursor.fetchone()
        except Exception as ex:
            logging.warning(ex)
        finally:
            if connect:
                connect.close()

    """
    查询所有目录文件数据
  """

    def foldertree(user_id):
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            params = [user_id]
            with connect.cursor() as cursor:
                sql = """
          SELECT
            id, name, url, file_path, thumb_path, type, size, extension,
            created_at,
            description,
            parent_id,
            `lock`,
            `path`
          FROM
            material
          WHERE
            del = 0
          AND
            type = 'dir'
          AND
            user_id = %s
        """
                cursor.execute(sql, tuple(params))
                results = cursor.fetchall()
                # 格式化时间
                for row in results:
                    # 检查 created_at 的类型
                    if isinstance(row["created_at"], str):
                        row["created_at"] = datetime.strptime(row["created_at"], "%a, %d %b %Y %H:%M:%S %Z").strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    elif isinstance(row["created_at"], datetime):
                        row["created_at"] = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                return [dict(row) for row in results]
        except Exception as ex:
            logging.warning(ex)
        finally:
            if connect:
                connect.close()

    """
    创建文件夹数据
    name: 文件夹名称
  """

    def create_dir(material_data, user_id):
        connect = None
        try:
            id = str(uuid.uuid4()).replace("-", "")
            name = material_data.get("name")
            parent_id = material_data.get("parent_id")
            path = name  # 默认路径为当前目录名
            if parent_id:
                parent = MaterialMysqlHandler.find_material_by_id(parent_id, user_id)
                if parent and parent.get("path"):
                    path = f"{parent['path']}/{material_data['name']}"
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                sql = """
          INSERT INTO `material` (`id`, `name`, `type`, `parent_id`, `path`, `user_id`) VALUES (%s, %s, %s, %s, %s, %s)
        """
                # 执行 SQL 语句
                cursor.execute(sql, (id, name, "dir", parent_id, path, user_id))
                # 提交事务
                connect.commit()
                return True
        except Exception as ex:
            logging.warning(ex)
            return False
        finally:
            if connect:
                connect.close()

    def update_material(material_data, user_id):
        # 文件列表
        file_list = material_data.get("file_list")
        # 绝对路径
        root_path = material_data.get("root_path")
        # 父级id
        parent_id = material_data.get("parent_id", 0)
        # 时间戳
        timestamp = material_data.get("timestamp")
        # 用于存放每条插入记录的成功信息
        success_info = []
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                # 获取上传的文件
                for file in file_list:
                    filename = file.filename
                    if file and PanoFile.allowed_file(filename):
                        # 每个文件生成唯一 ID（修复：之前 id 在循环外导致多文件共享同一 UUID）
                        fid = str(uuid.uuid4()).replace("-", "")
                        # 把图片存储到临时目录
                        file.save(os.path.join(root_path, filename))

                        path = ""
                        if platform == "nt":
                            path = root_path + "\\" + filename
                        elif platform == "posix":
                            path = root_path + "/" + filename

                        # 把全景图上传到阿里云
                        oss_path = str(timestamp) + "/" + filename

                        MinioUtil.upload_pano_file(path, oss_path)

                        # 获取文件后缀
                        file_name_with_extension = os.path.basename(path)

                        file_name = os.path.splitext(file_name_with_extension)[0]

                        # 获取文件后缀并去掉前面的点
                        file_extension = os.path.splitext(path)[1][1:]

                        # 存储完整文件名（含扩展名），供 copy/scissors 等操作通过文件名查找 MinIO 对象
                        name = file_name_with_extension
                        url = f"http://{minio_cdn_url}/mind/{oss_path}"
                        thumb_path = ""
                        size = MinioUtil.get_object_size(oss_path)
                        extension = file_extension

                        sql = """
              INSERT INTO `material` (`id`, `name`, `url`, `thumb_path`, `size`, `extension`, `type`, `parent_id`, `user_id`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

                        # 执行 SQL 语句
                        cursor.execute(sql, (fid, name, url, thumb_path, size, extension, "", parent_id, user_id))

                        # 收集成功信息（修复：lastrowid 对 UUID 主键恒为 0，改为返回实际文件信息）
                        success_info.append({"id": fid, "name": name, "url": url, "size": size, "extension": extension})
                        # 提交事务
                        connect.commit()

                if len(success_info) > 0:
                    return success_info
                else:
                    return None
        except Exception as ex:
            logging.warning(ex)
            return None
        finally:
            if connect:
                connect.close()

    """
    url: 文件存储路径
    thumb_path: 全景图缩略图
    extension: 文件后缀
  """

    def install_material(material_data, user_id):
        id = str(uuid.uuid4()).replace("-", "")
        url = material_data.get("url")
        thumb_path = material_data.get("thumb_path")
        size = material_data.get("size")
        extension = material_data.get("extension")
        type = material_data.get("type")
        parent_id = material_data.get("parent_id")
        name = os.path.basename(url)
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                sql = """
          INSERT INTO `material` (`id`, `name`, `url`, `thumb_path`, `size`, `extension`, `type`, `parent_id`, `user_id`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
                cursor.execute(sql, (id, name, url, thumb_path, size, extension, type, parent_id, user_id))
                connect.commit()
                return cursor.rowcount
        except Exception as ex:
            logging.warning(ex)
            return False
        finally:
            if connect:
                connect.close()

    """
    删除素材数据
  """

    def delete_material(material_data, user_id):
        id = material_data.get("id")
        is_del = material_data.get("del")
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                sql = """
          UPDATE `material` SET del = %s WHERE id = %s AND user_id = %s
        """
                cursor.execute(sql, (is_del, id, user_id))
                connect.commit()
                return cursor.lastrowid
        except Exception as ex:
            logging.warning(ex)
        finally:
            if connect:
                connect.close()

    def modify(id, user_id, **kwargs):
        if not id:
            logging.warning("ID 不能为空")
            return False
        if not kwargs:
            logging.warning("没有可更新的字段")
            return False
        connect = None
        try:
            connect = ConnectMysqlHandler.connect_mysql()
            with connect.cursor() as cursor:
                for key in kwargs:
                    # 如果值是字典
                    if isinstance(kwargs[key], dict):
                        # 转成 JSON 字符串
                        kwargs[key] = json.dumps(kwargs[key], ensure_ascii=False)
                update_fields = [f"{key} = %s" for key in kwargs.keys()]
                values = list(kwargs.values())

                sql = f"UPDATE material SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s"
                values.append(id)
                values.append(user_id)

                cursor.execute(sql, values)
                connect.commit()

                if cursor.rowcount == 0:
                    return False, "未找到匹配的 ID 或数据未变更"
                return True, cursor.rowcount
        except Exception as ex:
            logging.warning(f"数据增加失败：{ex}")
        finally:
            if connect:
                connect.close()

    def scissors_file(id, folder, user_id):
        done = MaterialMysqlHandler.copy_file(id, folder, user_id)
        if done:
            MaterialMysqlHandler.delete_material({"id": id, "del": 1}, user_id)
            return True
        else:
            return False

    def copy_file(id, folder, user_id):
        connect = None
        try:
            # 根据ID查询文件信息
            info = MaterialMysqlHandler.find_material_by_id(id, user_id)
            if not info:
                return False

            file_name = info["name"]
            connect = ConnectMysqlHandler.connect_mysql()

            # 从 URL 直接解析 MinIO 源目录前缀（不再全量扫描 bucket）
            # URL 格式: http://cdn/mind/timestamp/filename.ext → 源前缀: timestamp/
            source_prefix = MinioUtil.parse_source_prefix(info["url"])
            if not source_prefix:
                logging.warning("copy_file: 无法从 URL 解析源路径前缀: url=%s", info["url"])
                return False

            # 复制源目录下所有对象到新位置（全景图含 tile/配置等附属文件）
            timestamp = int(time.time())
            target_prefix = f"krpano/{timestamp}/"
            logging.info("copy_file: 复制目录 %s → %s (folder=%s)", source_prefix, target_prefix, folder)
            ok = MinioUtil.copy_directory_prefix(source_prefix, target_prefix)
            if not ok:
                logging.warning("copy_file: MinIO 目录复制失败 %s → %s", source_prefix, target_prefix)
                return False

            # 构建新 URL：将源前缀替换为目标前缀
            new_url = info["url"].replace(source_prefix, target_prefix, 1)
            data = {
                "name": file_name,
                "url": new_url,
                "thumb_path": "",
                "size": MinioUtil.get_object_size(target_prefix + file_name),
                "extension": os.path.splitext(file_name)[1][1:],
                "type": "panorama",
                "parent_id": folder,
            }
            done = MaterialMysqlHandler.install_material(data, user_id)
            return bool(done)
        except Exception as ex:
            logging.warning(ex)
            return False
        finally:
            if connect:
                connect.close()
