from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db import Session, crud, get_db
from app.dependencies import get_validated_user
from app.models.admin import Admin
from app.utils import responses

router = APIRouter(tags=["User Devices"], prefix="/api", responses={401: responses._401})


class UserDeviceResponse(BaseModel):
    hwid: str
    user_id: int
    platform: Optional[str] = None
    os_version: Optional[str] = None
    device_model: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    banned: bool = False
    last_seen: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class UserDevicesResponse(BaseModel):
    devices: List[UserDeviceResponse]
    total: int


@router.get(
    "/user/{username}/devices",
    response_model=UserDevicesResponse,
    responses={403: responses._403, 404: responses._404},
)
def get_user_devices(
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """List all registered devices for a user."""
    devices = crud.get_user_devices(db, dbuser.id)
    return UserDevicesResponse(
        devices=[UserDeviceResponse.model_validate(d) for d in devices],
        total=len(devices),
    )


@router.delete(
    "/user/{username}/devices/{hwid}",
    responses={403: responses._403, 404: responses._404},
)
def delete_user_device(
    hwid: str,
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Delete a specific device by HWID for a user."""
    deleted = crud.delete_user_device(db, dbuser.id, hwid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"detail": "Device deleted"}


@router.delete(
    "/user/{username}/devices",
    responses={403: responses._403, 404: responses._404},
)
def delete_all_user_devices(
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Delete all registered devices for a user."""
    count = crud.delete_all_user_devices(db, dbuser.id)
    return {"detail": f"Deleted {count} device(s)"}


@router.post(
    "/user/{username}/devices/{hwid}/ban",
    response_model=UserDeviceResponse,
    responses={403: responses._403, 404: responses._404},
)
def ban_user_device(
    hwid: str,
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Ban a specific device by HWID for a user."""
    device = crud.ban_user_device(db, dbuser.id, hwid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return UserDeviceResponse.model_validate(device)


@router.post(
    "/user/{username}/devices/{hwid}/unban",
    response_model=UserDeviceResponse,
    responses={403: responses._403, 404: responses._404},
)
def unban_user_device(
    hwid: str,
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Unban a specific device by HWID for a user."""
    device = crud.unban_user_device(db, dbuser.id, hwid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return UserDeviceResponse.model_validate(device)


@router.post(
    "/user/{username}/devices/ban",
    responses={403: responses._403, 404: responses._404},
)
def ban_all_user_devices(
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Ban all registered devices for a user."""
    count = crud.ban_all_user_devices(db, dbuser.id)
    return {"detail": f"Banned {count} device(s)"}


@router.post(
    "/user/{username}/devices/unban",
    responses={403: responses._403, 404: responses._404},
)
def unban_all_user_devices(
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Unban all registered devices for a user."""
    count = crud.unban_all_user_devices(db, dbuser.id)
    return {"detail": f"Unbanned {count} device(s)"}
