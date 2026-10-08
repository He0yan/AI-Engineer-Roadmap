from pydantic import BaseModel,ConfigDict,Field
from typing import Optional
from datetime import datetime, date

# ============ DeviceType ============
class DeviceTypeBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = None


class DeviceTypeCreate(DeviceTypeBase):
    """创建类型时的请求体。"""
    pass


class DeviceTypeOut(DeviceTypeBase):
    """返回给客户端的类型信息。"""
    id: int

    model_config = ConfigDict(from_attributes=True)
 
# ============ Device ============
class DeviceBase(BaseModel):
    name: str = Field(..., max_length=100)
    serial_number: str = Field(..., max_length=100)
    type_id: int
    status: str = Field("offline", pattern="^(online|offline|maintenance)$")
    location: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass 

class DeviceUpdate(BaseModel):
    """更新设备时的请求体：所有字段可选。"""
    name: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(online|offline|maintenance)$")
    location: Optional[str] = None

class DeviceOut(DeviceBase):
    """返回给客户端的设备信息。"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DeviceWithTypeOut(DeviceOut):
    """带类型名的设备信息（用于 JOIN 场景）。"""
    type_name: str

# ============ MaintenanceRecord ============
class MaintenanceCreate(BaseModel):
    maintenance_type: str = Field(..., max_length=50)
    description: Optional[str] = None
    technician: Optional[str] = None
    maintenance_date: Optional[date] = None


class MaintenanceOut(BaseModel):
    id: int
    device_id: int
    maintenance_type: str
    description: Optional[str]
    technician: Optional[str]
    maintenance_date: date

    model_config = ConfigDict(from_attributes=True)