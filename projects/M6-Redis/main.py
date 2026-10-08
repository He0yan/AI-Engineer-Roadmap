import json
from fastapi import FastAPI, Depends, HTTPException
from redis import Redis

from redis_client import get_redis
from crud import get_device_from_db,update_device_in_db
from db import get_db
from sqlalchemy.orm import Session
from schemas import DeviceUpdate

app = FastAPI()

@app.get("/devices/{device_id}")
def get_device(
    device_id: int,
    r: Redis = Depends(get_redis),
    db:Session=Depends(get_db)
):
    key = f"device:{device_id}"

    # 1. 先查 Redis
    try:
        cached = r.get(key)
    except Exception as e:
        # Redis 挂了，降级到数据库
        print(f"Redis error: {e}")
        cached = None

    if cached is not None:
        return {
            "source": "cache",
            "data": json.loads(cached),
        }

    # 2. Cache Miss，查 PostgreSQL
    device = get_device_from_db(db,device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    device= {
        "id": device.id,
        "name": device.name,
        "status": device.status  
    }
    # 3. 写回 Redis，TTL 60 秒
    try:
        r.set(key, json.dumps(device), ex=60)
    except Exception as e:
        # 写缓存失败不影响主流程
        print(f"Redis set error: {e}")

    return {
        "source": "database",
        "data": device,
    }

@app.put("/devices/{device_id}")
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    r: Redis = Depends(get_redis),
    db:Session=Depends(get_db)
):
    key = f"device:{device_id}"

    # 1. 更新 PostgreSQL
    device = get_device_from_db(db, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    device = update_device_in_db(db,device, payload)
    

    # 2. 删除 Redis 缓存
    try:
        r.delete(key)
    except Exception as e:
        print(f"Redis delete error: {e}")

    # 3. 返回最新数据
    return {"source": "database", "data": device}