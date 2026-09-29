from fastapi import FastAPI,Depends, HTTPException, status
from typing import List, Optional
import schemas
import crud
from sqlalchemy.orm import Session
from db import get_db, engine, Base


app=FastAPI(title="Industrial_ai")

#创建device_type对象
@app.post('/device_types',response_model=schemas.DeviceTypeOut)
def create_device_type(payload: schemas.DeviceTypeCreate,db: Session = Depends(get_db)):
    return crud.create_device_type(db, payload)

@app.get("/device-types", response_model=List[schemas.DeviceTypeOut])
def list_device_types(db: Session = Depends(get_db)):
    return crud.list_device_types(db)


# ==================== Devices ====================
@app.post("/devices", response_model=schemas.DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(payload: schemas.DeviceCreate, db: Session = Depends(get_db)):
    # 检查类型是否存在
    if crud.get_device_type(db, payload.type_id) is None:
        raise HTTPException(status_code=400, detail="type_id 不存在")
    # 检查序列号是否重复
    if crud.get_device_by_serial(db, payload.serial_number) is not None:
        raise HTTPException(status_code=400, detail="serial_number 已存在")
    return crud.create_device(db, payload)


@app.get("/devices", response_model=List[schemas.DeviceOut])
def list_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.list_devices(db, skip=skip, limit=limit)


@app.get("/devices/{device_id}", response_model=schemas.DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return device


@app.put("/devices/{device_id}", response_model=schemas.DeviceOut)
def update_device(device_id: int, payload: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return crud.update_device(db, device, payload)


@app.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    crud.delete_device(db, device)


# ==================== Maintenance ====================
@app.post("/devices/{device_id}/maintenance",
          response_model=schemas.MaintenanceOut,
          status_code=status.HTTP_201_CREATED)
def create_maintenance(device_id: int, payload: schemas.MaintenanceCreate, db: Session = Depends(get_db)):
    if crud.get_device(db, device_id) is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return crud.create_maintenance(db, device_id, payload)


@app.get("/devices/{device_id}/maintenance", response_model=List[schemas.MaintenanceOut])
def list_maintenance(device_id: int, db: Session = Depends(get_db)):
    if crud.get_device(db, device_id) is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return crud.list_maintenance(db, device_id)


# ==================== 汇总（需要 JOIN） ====================
@app.get("/devices/{device_id}/summary", response_model=schemas.DeviceSummary)
def get_device_summary(device_id: int, db: Session = Depends(get_db)):
    summary = crud.get_device_summary(db, device_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return summary