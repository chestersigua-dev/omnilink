import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Device
from backend.auth import get_current_user
from backend.scanner import scan_network
from backend.adapters import get_adapter

router = APIRouter(prefix="/api/iot", tags=["IoT Devices & Discovery"])

class AddDeviceRequest(BaseModel):
    device_uid: str
    name: str
    brand: str
    model: Optional[str] = ""
    device_type: Optional[str] = "generic"
    ip_address: Optional[str] = "127.0.0.1"
    mac_address: Optional[str] = ""
    port: Optional[int] = 0
    protocol: Optional[str] = ""
    power_state: Optional[bool] = False
    level: Optional[int] = 50
    state_metadata: Optional[Dict[str, Any]] = None

class UpdateDeviceRequest(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    power_state: Optional[bool] = None

class DeviceControlRequest(BaseModel):
    action: str # "turn_on", "turn_off", "set_level", "get_status"
    parameter: Optional[str] = "level" # "brightness", "volume", "temperature", "speed"
    value: Optional[int] = None

@router.get("/scan")
async def scan_iot_devices(
    force_simulation: Optional[bool] = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scan subnet via mDNS and SSDP broadcast.
    Returns list of discovered units, annotating whether they are already added to user's dashboard.
    """
    discovered = await scan_network(force_simulation=force_simulation)
    
    # Check which devices are already registered by the user
    user_device_uids = {
        d.device_uid for d in db.query(Device.device_uid).filter(Device.user_id == current_user.id).all()
    }

    results = []
    for item in discovered:
        dev_copy = dict(item)
        dev_copy["is_registered"] = item["device_uid"] in user_device_uids
        results.append(dev_copy)

    return {
        "count": len(results),
        "devices": results,
        "mode": "simulation" if force_simulation else "auto"
    }

@router.get("/devices")
def get_user_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all devices owned by the authenticated user."""
    devices = db.query(Device).filter(Device.user_id == current_user.id).all()
    return [d.to_dict() for d in devices]

@router.post("/devices")
def add_device(
    req: AddDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a discovered or manual device to user's system."""
    # Check if already added
    existing = db.query(Device).filter(
        Device.user_id == current_user.id,
        Device.device_uid == req.device_uid
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device '{req.name}' is already added to your dashboard"
        )

    device = Device(
        device_uid=req.device_uid,
        name=req.name,
        brand=req.brand.lower(),
        model=req.model or "",
        device_type=req.device_type or "generic",
        ip_address=req.ip_address or "127.0.0.1",
        mac_address=req.mac_address or "",
        port=req.port or 0,
        protocol=req.protocol or "",
        power_state=req.power_state if req.power_state is not None else False,
        level=req.level if req.level is not None else 50,
        user_id=current_user.id
    )
    if req.state_metadata:
        device.set_state_dict(req.state_metadata)

    db.add(device)
    db.commit()
    db.refresh(device)
    return device.to_dict()

@router.get("/devices/{device_id}")
def get_device_details(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id, Device.user_id == current_user.id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device.to_dict()

@router.put("/devices/{device_id}")
def update_device_info(
    device_id: int,
    req: UpdateDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id, Device.user_id == current_user.id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    if req.name is not None:
        device.name = req.name
    if req.power_state is not None:
        device.power_state = req.power_state
    if req.level is not None:
        device.level = max(0, min(100, req.level))

    db.commit()
    db.refresh(device)
    return device.to_dict()

@router.delete("/devices/{device_id}")
def delete_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id, Device.user_id == current_user.id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    db.delete(device)
    db.commit()
    return {"message": "Device removed from dashboard successfully"}

@router.post("/devices/{device_id}/control")
async def control_device(
    device_id: int,
    req: DeviceControlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unified multi-brand control endpoint dispatching commands to the specific adapter.
    """
    device = db.query(Device).filter(Device.id == device_id, Device.user_id == current_user.id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    adapter = get_adapter(device.brand)
    dev_dict = device.to_dict()

    action = req.action.lower().strip()
    result_log = {}

    if action == "turn_on":
        res = await adapter.turn_on(dev_dict)
        device.power_state = True
        device.is_online = res.get("is_online", True)
        result_log = res
    elif action == "turn_off":
        res = await adapter.turn_off(dev_dict)
        device.power_state = False
        device.is_online = res.get("is_online", True)
        result_log = res
    elif action == "set_level":
        val = req.value if req.value is not None else 50
        res = await adapter.set_level(dev_dict, req.parameter or "level", val)
        device.level = res.get("level", val)
        device.is_online = res.get("is_online", True)
        result_log = res
    elif action == "get_status":
        res = await adapter.get_status(dev_dict)
        device.power_state = res.get("power_state", device.power_state)
        device.level = res.get("level", device.level)
        device.is_online = res.get("is_online", True)
        result_log = res
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {req.action}")

    db.commit()
    db.refresh(device)

    return {
        "success": True,
        "device": device.to_dict(),
        "adapter_execution": result_log
    }

@router.post("/devices/{device_id}/sync")
async def sync_device_status(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refreshes live state from adapter."""
    device = db.query(Device).filter(Device.id == device_id, Device.user_id == current_user.id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    adapter = get_adapter(device.brand)
    res = await adapter.get_status(device.to_dict())
    device.power_state = res.get("power_state", device.power_state)
    device.level = res.get("level", device.level)
    device.is_online = res.get("is_online", True)

    db.commit()
    db.refresh(device)
    return device.to_dict()
