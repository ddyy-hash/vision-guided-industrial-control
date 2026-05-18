import sqlite3
import json
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from .device_scanner import DeviceInfo, DeviceStatus, DeviceType

logger = logging.getLogger(__name__)

class DeviceStorageService:
    def __init__(self, db_path: str = "devices.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS devices (
                        device_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        device_type TEXT NOT NULL,
                        connection_info TEXT NOT NULL,
                        status TEXT NOT NULL,
                        last_seen REAL,
                        discovered_time REAL,
                        metadata TEXT,
                        created_time REAL NOT NULL,
                        updated_time REAL NOT NULL
                    )
                    CREATE TABLE IF NOT EXISTS connection_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        connection_time REAL NOT NULL,
                        disconnect_time REAL,
                        status TEXT NOT NULL,
                        error_message TEXT,
                        FOREIGN KEY (device_id) REFERENCES devices (device_id)
                    )
                    CREATE TABLE IF NOT EXISTS device_configs (
                        device_id TEXT PRIMARY KEY,
                        config_data TEXT NOT NULL,
                        created_time REAL NOT NULL,
                        updated_time REAL NOT NULL,
                        FOREIGN KEY (device_id) REFERENCES devices (device_id)
                    )
                    INSERT OR REPLACE INTO devices
                    (device_id, name, device_type, connection_info, status,
                     last_seen, discovered_time, metadata, created_time, updated_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_time FROM devices WHERE device_id = ?), ?), ?)
                    SELECT device_id, name, device_type, connection_info, status,
                           last_seen, discovered_time, metadata
                    FROM devices WHERE device_id = ?
                    SELECT device_id, name, device_type, connection_info, status,
                           last_seen, discovered_time, metadata
                    FROM devices
                    ORDER BY discovered_time DESC
                        INSERT INTO connection_history
                        (device_id, connection_time, status, error_message)
                        VALUES (?, ?, ?, ?)
                        UPDATE connection_history
                        SET disconnect_time = ?, status = ?, error_message = ?
                        WHERE id = (
                            SELECT id FROM connection_history
                            WHERE device_id = ? AND disconnect_time IS NULL
                            ORDER BY connection_time DESC
                            LIMIT 1
                        )
                    SELECT connection_time, disconnect_time, status, error_message
                    FROM connection_history
                    WHERE device_id = ?
                    ORDER BY connection_time DESC
                    LIMIT ?
                    INSERT OR REPLACE INTO device_configs
                    (device_id, config_data, created_time, updated_time)
                    VALUES (?, ?, COALESCE((SELECT created_time FROM device_configs WHERE device_id = ?), ?), ?)
                    SELECT DISTINCT d.device_id, d.name, d.device_type, d.connection_info,
                           d.status, d.last_seen, d.discovered_time, d.metadata
                    FROM devices d
                    JOIN connection_history ch ON d.device_id = ch.device_id
                    WHERE ch.connection_time > ?
                    ORDER BY ch.connection_time DESC
                ''', (cutoff_time,))

                devices = []
                for row in cursor.fetchall():
                    device = self._row_to_device_info(row)
                    if device:
                        devices.append(device)

                return devices

        except Exception as e:
            logger.error(f"获取最近连接设备失败: {e}")
            return []

    def _row_to_device_info(self, row) -> Optional[DeviceInfo]:
        """Convert a database row into a DeviceInfo object."""
        try:
            device_info = DeviceInfo(
                device_id=row[0],
                name=row[1],
                device_type=DeviceType(row[2]),
                connection_info=row[3],
                status=DeviceStatus(row[4])
            )
            device_info.last_seen = row[5]
            device_info.discovered_time = row[6]
            if row[7]:
                device_info.metadata = json.loads(row[7])

            return device_info

        except Exception as e:
            logger.error(f"转换设备信息失败: {e}")
            return None

    def cleanup_old_history(self, days: int = 30):
        """Remove stale connection history records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cutoff_time = time.time() - (days * 24 * 60 * 60)

                cursor.execute('DELETE FROM connection_history WHERE connection_time < ?', (cutoff_time,))

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"清理了 {deleted_count} 条旧的连接历史记录")
                return deleted_count

        except Exception as e:
            logger.error(f"清理连接历史失败: {e}")
            return 0

_device_storage = None

def get_device_storage() -> DeviceStorageService:
    """Return the global device storage service instance."""
    global _device_storage
    if _device_storage is None:
        _device_storage = DeviceStorageService()
    return _device_storage
