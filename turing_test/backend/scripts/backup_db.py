#!/usr/bin/env python3
"""
数据库备份脚本

将 SQLite 数据库备份到外部存储（如 S3、WebDAV 等）或发送到指定 URL。

使用方法:
    python backup_db.py

环境变量:
    BACKUP_S3_BUCKET: S3 桶名（可选）
    BACKUP_S3_KEY: S3 对象键（可选）
    BACKUP_WEBHOOK_URL: Webhook URL，用于发送备份文件（可选）
    BACKUP_LOCAL_PATH: 本地备份路径（可选）
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

# 获取项目根目录
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>")

DB_PATH = Path("data/turing.db")
BACKUP_DIR = Path("data/backups")


def create_backup() -> Path:
    """创建数据库备份"""
    if not DB_PATH.exists():
        logger.error(f"数据库文件不存在：{DB_PATH}")
        raise FileNotFoundError(f"数据库文件不存在：{DB_PATH}")
    
    # 创建备份目录
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成备份文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"turing_backup_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_filename
    
    # 复制文件
    shutil.copy2(DB_PATH, backup_path)
    logger.info(f"备份已创建：{backup_path}")
    
    return backup_path


def upload_to_s3(backup_path: Path):
    """上传到 S3 兼容存储"""
    bucket = os.getenv("BACKUP_S3_BUCKET")
    key = os.getenv("BACKUP_S3_KEY", f"backups/{backup_path.name}")
    
    if not bucket:
        logger.warning("未设置 BACKUP_S3_BUCKET，跳过 S3 上传")
        return
    
    try:
        import boto3
        from botocore.config import Config
        
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=Config(signature_version='s3v4'),
        )
        
        with open(backup_path, 'rb') as f:
            s3.upload_fileobj(f, bucket, key)
        
        logger.info(f"备份已上传到 S3: s3://{bucket}/{key}")
    except ImportError:
        logger.error("boto3 未安装，无法上传到 S3: pip install boto3")
    except Exception as e:
        logger.error(f"S3 上传失败：{e}")


def send_to_webhook(backup_path: Path):
    """发送备份到 Webhook URL"""
    webhook_url = os.getenv("BACKUP_WEBHOOK_URL")
    
    if not webhook_url:
        logger.warning("未设置 BACKUP_WEBHOOK_URL，跳过 Webhook 发送")
        return
    
    try:
        import requests
        
        with open(backup_path, 'rb') as f:
            files = {'file': (backup_path.name, f, 'application/octet-stream')}
            response = requests.put(webhook_url, files=files, timeout=60)
            response.raise_for_status()
        
        logger.info(f"备份已发送到 Webhook: {webhook_url}")
    except ImportError:
        logger.error("requests 未安装：pip install requests")
    except Exception as e:
        logger.error(f"Webhook 发送失败：{e}")


def cleanup_old_backups(keep_count: int = 3):
    """清理旧备份，只保留最近的 N 个"""
    if not BACKUP_DIR.exists():
        return
    
    backups = sorted(BACKUP_DIR.glob("turing_backup_*.db"), reverse=True)
    
    if len(backups) > keep_count:
        for old_backup in backups[keep_count:]:
            old_backup.unlink()
            logger.info(f"已删除旧备份：{old_backup}")


def main():
    """主函数"""
    logger.info("开始数据库备份...")
    
    try:
        # 创建备份
        backup_path = create_backup()
        
        # 上传到 S3
        upload_to_s3(backup_path)
        
        # 发送到 Webhook
        send_to_webhook(backup_path)
        
        # 清理旧备份
        cleanup_old_backups(keep_count=3)
        
        logger.info("备份完成")
    except Exception as e:
        logger.error(f"备份失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
