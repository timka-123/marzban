from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.db import Session, crud, get_db
from app.models.admin import Admin
from app.models.setting import SettingResponse, SettingUpdate
from app.utils import responses

router = APIRouter(
    tags=["Settings"],
    prefix="/api",
    responses={401: responses._401, 403: responses._403},
)


@router.get("/settings", response_model=List[SettingResponse])
def list_settings(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """List all panel settings stored in the database."""
    return crud.get_all_settings(db)


@router.get("/settings/{key}", response_model=SettingResponse)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Get a single panel setting by key."""
    setting = crud.get_setting(db, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.put("/settings/{key}", response_model=SettingResponse)
def put_setting(
    key: str,
    payload: SettingUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Create or update a panel setting. Accepts any JSON-compatible value."""
    return crud.set_setting(db, key, payload.value)


@router.delete("/settings/{key}")
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Delete a panel setting. Subsequent reads fall back to ENV defaults."""
    if not crud.delete_setting(db, key):
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"detail": "deleted"}
