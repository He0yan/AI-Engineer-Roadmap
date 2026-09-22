from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Device Management API V1")

# ========================
# 1. 内存数据库（模拟 M5 的 PostgreSQL）
# ========================
devices_db = {}  # 格式：{1001: {"id": 1001, "name": "Pump-A", ...}}
current_id = 1000  # 用于自增生成 id

# ========================
# 2. Pydantic 模型
# ========================
class DeviceCreate(BaseModel):
    name: str
    device_type: str
    location: str

class DeviceUpdate(BaseModel):
    name: str | None = None
    device_type: str | None = None
    location: str | None = None

class DeviceResponse(BaseModel):
    id: int
    name: str
    device_type: str
    location: str
    status: str

@app.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(device: DeviceCreate):
    global current_id
    current_id += 1
    
    # 构建内部数据
    new_device = {
        "id": current_id,
        "name": device.name,
        "device_type": device.device_type,
        "location": device.location,
        "status": "offline"  # 新设备默认离线
    }
    
    # 存入内存数据库
    devices_db[current_id] = new_device
    return new_device

@app.get("/devices", response_model=list[DeviceResponse])
def get_devices(location: str | None = None, device_type: str | None = None):
    # 获取所有设备
    result = list(devices_db.values())
    
    # 如果带了查询参数，进行过滤
    if location:
        result = [d for d in result if d["location"] == location]
    if device_type:
        result = [d for d in result if d["device_type"] == device_type]
        
    return result

@app.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device(device_id: int):
    if device_id not in devices_db:
        # 提前预告 Day 6 的异常处理
        raise HTTPException(status_code=404, detail="Device not found")
    return devices_db[device_id]

@app.put("/devices/{device_id}", response_model=DeviceResponse)
def update_device(device_id: int, device: DeviceUpdate):
    if device_id not in devices_db:
        raise HTTPException(status_code=404, detail="Device not found")
    
    stored_device = devices_db[device_id]
    
    # 只更新客户端传过来的字段
    if device.name is not None:
        stored_device["name"] = device.name
    if device.device_type is not None:
        stored_device["device_type"] = device.device_type
    if device.location is not None:
        stored_device["location"] = device.location
        
    return stored_device

@app.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int):
    if device_id not in devices_db:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # 从内存中删除
    del devices_db[device_id]
    return None  # 204 状态码不返回 Body

@app.get("/devices/{device_id}/status")
def get_device_status(device_id: int):
    if device_id not in devices_db:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {
        "id": device_id,
        "status": devices_db[device_id]["status"],
        "last_seen": "2026-09-22T10:00:00Z"  # 模拟真实时间
    }

