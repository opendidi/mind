# -*- coding: UTF-8 -*-
"""
MinIO 配置项 — 从环境变量读取，不再硬编码。
"""

import os

# 桶名称
minio_bucket_name = os.environ.get('MINIO_BUCKET_NAME', 'mind')
# ip+端口
minio_endpoint = os.environ.get('MINIO_ENDPOINT', '127.0.0.1:9000')
# cdn地址
minio_cdn_url = os.environ.get('MINIO_CDN_URL', os.environ.get('MINIO_ENDPOINT', '127.0.0.1:9000'))
# access_key
minio_access_key = os.environ.get('MINIO_ACCESS_KEY', '')
# secret_key
minio_secret_key = os.environ.get('MINIO_SECRET_KEY', '')
# 是否使用SSL
minio_secure = os.environ.get('MINIO_SECURE', 'false').lower() == 'true'
