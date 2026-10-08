from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db import Base

class DeviceType(Base):
    __tablename__ = "device_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)

    # 关系：一个类型有多台设备
    devices = relationship("Device", back_populates="type")

    def __repr__(self):
        return f"<DeviceType(id={self.id}, name={self.name})>"

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    serial_number = Column(String(100), nullable=False, unique=True)
    type_id = Column(Integer, ForeignKey("device_types.id"), nullable=False)
    status = Column(String(20), nullable=False, default="offline")
    location = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('online','offline','maintenance')", name="devices_status_check"),
    )

    # 关系
    type = relationship("DeviceType", back_populates="devices")
    maintenance_records = relationship("MaintenanceRecord", back_populates="device")

    def __repr__(self):
        return f"<Device(id={self.id}, name={self.name}, status={self.status})>"

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    maintenance_type = Column(String(50), nullable=False)
    description = Column(Text)
    technician = Column(String(100))
    maintenance_date = Column(Date, nullable=False, server_default=func.current_date())

    device = relationship("Device", back_populates="maintenance_records")

    def __repr__(self):
        return f"<MaintenanceRecord(id={self.id}, device_id={self.device_id})>"


