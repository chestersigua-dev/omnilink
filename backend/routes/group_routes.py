import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Group, Device
from backend.auth import get_current_user
from backend.adapters import get_adapter

router = APIRouter(prefix="/api/groups", tags=["Custom Groups & Orchestration"])

class CreateGroupRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    device_ids: Optional[List[int]] = []

class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class AssignDevicesRequest(BaseModel):
    device_ids: List[int]

class BatchControlRequest(BaseModel):
    action: str # "turn_all_on", "turn_all_off", "set_level"
    parameter: Optional[str] = "level"
    value: Optional[int] = 50

@router.get("")
def list_user_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    groups = db.query(Group).filter(Group.user_id == current_user.id).all()
    return [g.to_dict() for g in groups]

@router.post("")
def create_group(
    req: CreateGroupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = Group(
        name=req.name,
        description=req.description or "",
        user_id=current_user.id
    )
    if req.device_ids:
        devices = db.query(Device).filter(
            Device.id.in_(req.device_ids),
            Device.user_id == current_user.id
        ).all()
        group.devices = devices

    db.add(group)
    db.commit()
    db.refresh(group)
    return group.to_dict()

@router.get("/{group_id}")
def get_group_details(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group.to_dict()

@router.put("/{group_id}")
def update_group(
    group_id: int,
    req: UpdateGroupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if req.name is not None:
        group.name = req.name
    if req.description is not None:
        group.description = req.description

    db.commit()
    db.refresh(group)
    return group.to_dict()

@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    db.delete(group)
    db.commit()
    return {"message": "Group removed successfully"}

@router.put("/{group_id}/devices")
def assign_devices_to_group(
    group_id: int,
    req: AssignDevicesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign or replace the set of devices belonging to this group."""
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    devices = db.query(Device).filter(
        Device.id.in_(req.device_ids),
        Device.user_id == current_user.id
    ).all()
    group.devices = devices

    db.commit()
    db.refresh(group)
    return group.to_dict()

@router.post("/{group_id}/batch-control")
async def batch_control_group(
    group_id: int,
    req: BatchControlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dispatches parallel asynchronous commands to all devices in the group.
    """
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if not group.devices:
        return {
            "group_id": group_id,
            "action": req.action,
            "dispatched_count": 0,
            "message": "Group has no assigned devices"
        }

    action = req.action.lower().strip()
    tasks = []

    async def _dispatch_to_device(dev: Device):
        adapter = get_adapter(dev.brand)
        dev_dict = dev.to_dict()
        try:
            if action == "turn_all_on":
                res = await adapter.turn_on(dev_dict)
                dev.power_state = True
                dev.is_online = res.get("is_online", True)
                return {"device_id": dev.id, "success": True, "res": res}
            elif action == "turn_all_off":
                res = await adapter.turn_off(dev_dict)
                dev.power_state = False
                dev.is_online = res.get("is_online", True)
                return {"device_id": dev.id, "success": True, "res": res}
            elif action == "set_level":
                val = req.value if req.value is not None else 50
                res = await adapter.set_level(dev_dict, req.parameter or "level", val)
                dev.level = res.get("level", val)
                dev.is_online = res.get("is_online", True)
                return {"device_id": dev.id, "success": True, "res": res}
            else:
                return {"device_id": dev.id, "success": False, "error": f"Unknown action {action}"}
        except Exception as e:
            return {"device_id": dev.id, "success": False, "error": str(e)}

    # Run asynchronous parallel actions to all group members
    results = await asyncio.gather(*[_dispatch_to_device(d) for d in group.devices])
    
    db.commit()
    db.refresh(group)

    return {
        "group_id": group_id,
        "group_name": group.name,
        "action": action,
        "dispatched_count": len(results),
        "results": results,
        "group": group.to_dict()
    }
