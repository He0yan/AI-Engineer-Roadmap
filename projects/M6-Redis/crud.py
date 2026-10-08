from db import SessionLocal
from models import DeviceType,Device, MaintenanceRecord
from sqlalchemy.orm import Session, joinedload
import schemas
from typing import Optional, List
from sqlalchemy import func
from datetime import date



# ==================== DeviceType ====================
def create_device_type(db: Session, data: schemas.DeviceTypeCreate) -> DeviceType:
    obj = DeviceType(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def list_device_types(db: Session) -> List[DeviceType]:
    return db.query(DeviceType).all()

def get_device_type(db: Session, type_id: int) -> Optional[DeviceType]:
    return db.get(DeviceType, type_id)

# ==================== Device ====================
def create_device(db: Session, data: schemas.DeviceCreate) -> Device:
    obj = Device(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_devices(db: Session, skip: int = 0, limit: int = 100) -> List[Device]:
    return db.query(Device).offset(skip).limit(limit).all()


def get_device_from_db(db: Session, device_id: int) -> Optional[Device]:
    device=db.get(Device, device_id)
    return device


def get_device_by_serial(db: Session, serial_number: str) -> Optional[Device]:
    return db.query(Device).filter(Device.serial_number == serial_number).first()


def update_device_in_db(db: Session, device: Device, data: schemas.DeviceUpdate) -> Device:
    update_data = data.model_dump(exclude_unset=True)   # 只更新客户端传了的字段
    for key, value in update_data.items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    return device


def delete_device(db: Session, device: Device) -> None:
    db.delete(device)
    db.commit()

# ==================== MaintenanceRecord ====================
def create_maintenance(db: Session, device_id: int, data: schemas.MaintenanceCreate) -> MaintenanceRecord:
    payload = data.model_dump(exclude_unset=True)
    if "maintenance_date" not in payload:
        payload["maintenance_date"] = date.today()
    obj = MaintenanceRecord(device_id=device_id, **payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_maintenance(db: Session, device_id: int) -> List[MaintenanceRecord]:
    return (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.device_id == device_id)
        .order_by(MaintenanceRecord.maintenance_date.desc())
        .all()
    )

# ==================== JOIN 查询：汇总 ====================
def get_device_summary(db: Session, device_id: int):
    """返回：设备 + 类型 + 维护次数 + 最近维护日期。"""

    # 一次查询拿设备 + 类型
    device = (
        db.query(Device)
        .options(joinedload(Device.type))
        .filter(Device.id == device_id)
        .first()
    )
    if device is None:
        return None

    # 聚合维护信息
    result = (
        db.query(
            func.count(MaintenanceRecord.id).label("maintenance_count"),
            func.max(MaintenanceRecord.maintenance_date).label("last_maintenance"),
        )
        .filter(MaintenanceRecord.device_id == device_id)
        .one()
    )

    return {
        "device": device,
        "type": device.type,
        "maintenance_count": result.maintenance_count,
        "last_maintenance": result.last_maintenance,
    }