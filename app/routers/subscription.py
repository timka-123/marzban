import base64
import re
from app.utils.notification import NewDevice, Notification, notify
from distutils.version import LooseVersion
from typing import Optional, Tuple
import logging

from fastapi import APIRouter, Depends, Header, Path, Request, Response
from fastapi.responses import HTMLResponse

from app.db import Session, crud, get_db
from app.dependencies import get_validated_sub, validate_dates
from app.models.user import SubscriptionUserResponse, UserResponse
from app.subscription.share import encode_title, generate_subscription
from app.templates import render_template
from config import (
    HWID_DEVICE_LIMIT_ENABLED,
    HWID_FALLBACK_DEVICE_LIMIT,
    HWID_MAX_DEVICES_ANNOUNCE,
    SUB_ANNOUNCE,
    SUB_ANNOUNCE,
    SUB_PROFILE_TITLE,
    SUB_SUPPORT_URL,
    SUB_UPDATE_INTERVAL,
    SUBSCRIPTION_PAGE_TEMPLATE,
    USE_CUSTOM_JSON_DEFAULT,
    USE_CUSTOM_JSON_FOR_HAPP,
    USE_CUSTOM_JSON_FOR_STREISAND,
    USE_CUSTOM_JSON_FOR_NPVTUNNEL,
    USE_CUSTOM_JSON_FOR_V2RAYN,
    USE_CUSTOM_JSON_FOR_V2RAYNG,
    XRAY_SUBSCRIPTION_PATH,
)

client_config = {
    "clash-meta": {"config_format": "clash-meta", "media_type": "text/yaml", "as_base64": False, "reverse": False},
    "mihomo": {"config_format": "mihomo", "media_type": "text/yaml", "as_base64": False, "reverse": False},
    "sing-box": {"config_format": "sing-box", "media_type": "application/json", "as_base64": False, "reverse": False},
    "clash": {"config_format": "clash", "media_type": "text/yaml", "as_base64": False, "reverse": False},
    "v2ray": {"config_format": "v2ray", "media_type": "text/plain", "as_base64": True, "reverse": False},
    "outline": {"config_format": "outline", "media_type": "application/json", "as_base64": False, "reverse": False},
    "v2ray-json": {"config_format": "v2ray-json", "media_type": "application/json", "as_base64": False,
                   "reverse": False}
}

router = APIRouter(tags=['Subscription'], prefix=f'/{XRAY_SUBSCRIPTION_PATH}')


def check_hwid(
    db: Session,
    dbuser,
    hwid: Optional[str],
    platform: Optional[str],
    os_version: Optional[str],
    device_model: Optional[str],
    user_agent: Optional[str],
) -> Tuple[bool, str]:
    """
    Check whether HWID device limit allows this request.

    Returns (allowed, reason) where reason is one of:
      'disabled'          — HWID enforcement is off globally
      'bypass'            — per-user limit is 0 (always allow)
      'no_hwid'           — client did not send X-HWID header
      'known_device'      — device already registered, allow
      'new_device'        — new device registered, allow
      'limit_reached'     — device limit exceeded, block
      'device_banned'     — device is banned for this user, block
    """
    if not HWID_DEVICE_LIMIT_ENABLED:
        return True, 'disabled'

    existing = (
        crud.get_user_device_for_user(db, dbuser.id, hwid) if hwid else None
    )
    if existing and existing.banned:
        return False, 'device_banned'

    if dbuser.hwid_device_limit == 0:
        if hwid:
            crud.upsert_user_device(db, dbuser.id, hwid, platform, os_version, device_model, user_agent)
        return True, 'bypass'

    if not hwid:
        return True, 'no_hwid'

    if existing:
        crud.upsert_user_device(db, dbuser.id, hwid, platform, os_version, device_model, user_agent)
        return True, 'known_device'

    limit = dbuser.hwid_device_limit if dbuser.hwid_device_limit is not None else HWID_FALLBACK_DEVICE_LIMIT
    count = crud.count_user_devices(db, dbuser.id)
    if count >= limit:
        return False, 'limit_reached'

    crud.insert_user_device(db, dbuser.id, hwid, platform, os_version, device_model, user_agent)
    notify(NewDevice(
        hwid=hwid,
        device_os=platform,  # todo: review it again
        os_version=os_version,
        device_model=device_model,
        user_agent=user_agent,
        action=Notification.Type.new_device,
        username=dbuser.username
    ))
    return True, 'new_device'


def build_hwid_headers(allowed: bool, reason: str) -> dict:
    headers = {}

    if reason == 'no_hwid':
        headers['x-hwid-not-supported'] = 'true'

    if HWID_DEVICE_LIMIT_ENABLED:
        headers['x-hwid-active'] = 'true'
    if not allowed:
        if reason == 'limit_reached':
            headers['x-hwid-max-devices-reached'] = 'true'
            if HWID_MAX_DEVICES_ANNOUNCE:
                headers['announce'] = base64.b64encode(
                    HWID_MAX_DEVICES_ANNOUNCE.encode()
                ).decode()
        elif reason == 'device_banned':
            headers['x-hwid-device-banned'] = 'true'
            headers['announce'] = "This HWID is banned"
    return headers


def get_subscription_user_info(user: UserResponse) -> dict:
    """Retrieve user subscription information including upload, download, total data, and expiry."""
    return {
        "upload": 0,
        "download": user.used_traffic,
        "total": user.data_limit if user.data_limit is not None else 0,
        "expire": user.expire if user.expire is not None else 0,
    }


@router.get("/{token}/")
@router.get("/{token}", include_in_schema=False)
def user_subscription(
    request: Request,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_sub),
    user_agent: str = Header(default=""),
    x_hwid: Optional[str] = Header(default=None, alias="x-hwid"),
    x_device_os: Optional[str] = Header(default=None, alias="x-device-os"),
    x_ver_os: Optional[str] = Header(default=None, alias="x-ver-os"),
    x_device_model: Optional[str] = Header(default=None, alias="x-device-model"),
):
    """Provides a subscription link based on the user agent (Clash, V2Ray, etc.)."""
    user: UserResponse = UserResponse.model_validate(dbuser)

    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header:
        return HTMLResponse(
            render_template(
                SUBSCRIPTION_PAGE_TEMPLATE,
                {"user": user}
            )
        )

    allowed, reason = check_hwid(db, dbuser, x_hwid, x_device_os, x_ver_os, x_device_model, user_agent)
    logging.info(allowed, reason)
    hwid_headers = build_hwid_headers(allowed, reason)
    if not allowed:
        return Response(content="", media_type="text/plain", headers=hwid_headers)

    crud.update_user_sub(db, dbuser, user_agent)
    response_headers = {
        "announce": SUB_ANNOUNCE,
        "content-disposition": f'attachment; filename="{user.username}"',
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "announce": SUB_ANNOUNCE,
        "profile-title": encode_title(SUB_PROFILE_TITLE),
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        ),
        **hwid_headers,
    }

    if re.match(r'^([Mm]ihomo|[Cc]lash[-\.]?[Mm]eta|[Cc]lash-verge|[Ff][Ll][Cc]lash)|[Aa]toll', user_agent):
        conf = generate_subscription(user=user, config_format="mihomo", as_base64=False, reverse=False)
        return Response(content=conf, media_type="text/yaml", headers=response_headers)

    elif re.match(r'^([Cc]lash|[Ss]tash)', user_agent):
        conf = generate_subscription(user=user, config_format="clash", as_base64=False, reverse=False)
        return Response(content=conf, media_type="text/yaml", headers=response_headers)

    elif re.match(r'^(SFA|SFI|SFM|SFT|[Kk]aring|[Hh]iddify[Nn]ext)|.*sing[-b]?ox.*', user_agent, re.IGNORECASE):
        conf = generate_subscription(user=user, config_format="sing-box", as_base64=False, reverse=False)
        return Response(content=conf, media_type="application/json", headers=response_headers)

    elif re.match(r'^(SS|SSR|SSD|SSS|Outline|Shadowsocks|SSconf)', user_agent):
        conf = generate_subscription(user=user, config_format="outline", as_base64=False, reverse=False)
        return Response(content=conf, media_type="application/json", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYN) and re.match(r'^v2rayN/(\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayN/(\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("6.40"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYNG) and re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.8.29"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        elif LooseVersion(version_str) >= LooseVersion("1.8.18"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=True)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif re.match(r'^[Ss]treisand', user_agent):
        if USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_STREISAND:
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_HAPP) and re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.11.0"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_NPVTUNNEL:
        if "ktor-client" in user_agent:
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    else:
        conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False)
        return Response(content=conf, media_type="text/plain", headers=response_headers)


@router.get("/{token}/info", response_model=SubscriptionUserResponse)
def user_subscription_info(
    dbuser: UserResponse = Depends(get_validated_sub),
):
    """Retrieves detailed information about the user's subscription."""
    return dbuser


@router.get("/{token}/usage")
def user_get_usage(
    dbuser: UserResponse = Depends(get_validated_sub),
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db)
):
    """Fetches the usage statistics for the user within a specified date range."""
    start, end = validate_dates(start, end)

    usages = crud.get_user_usages(db, dbuser, start, end)

    return {"usages": usages, "username": dbuser.username}


@router.get("/{token}/{client_type}")
def user_subscription_with_client_type(
    request: Request,
    dbuser: UserResponse = Depends(get_validated_sub),
    client_type: str = Path(..., regex="sing-box|clash-meta|mihomo|clash|outline|v2ray|v2ray-json"),
    db: Session = Depends(get_db),
    user_agent: str = Header(default=""),
    x_hwid: Optional[str] = Header(default=None, alias="x-hwid"),
    x_device_os: Optional[str] = Header(default=None, alias="x-device-os"),
    x_ver_os: Optional[str] = Header(default=None, alias="x-ver-os"),
    x_device_model: Optional[str] = Header(default=None, alias="x-device-model"),
):
    """Provides a subscription link based on the specified client type (e.g., Clash, V2Ray)."""
    user: UserResponse = UserResponse.model_validate(dbuser)

    allowed, reason = check_hwid(db, dbuser, x_hwid, x_device_os, x_ver_os, x_device_model, user_agent)
    hwid_headers = build_hwid_headers(allowed, reason)
    logging.info(allowed, reason)
    if not allowed:
        return Response(content="", media_type="text/plain", headers=hwid_headers)

    response_headers = {
        "announce": SUB_ANNOUNCE,
        "content-disposition": f'attachment; filename="{user.username}"',
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "announce": SUB_ANNOUNCE,
        "profile-title": encode_title(SUB_PROFILE_TITLE),
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        ),
        **hwid_headers,
    }

    config = client_config.get(client_type)
    conf = generate_subscription(user=user,
                                 config_format=config["config_format"],
                                 as_base64=config["as_base64"],
                                 reverse=config["reverse"])

    return Response(content=conf, media_type=config["media_type"], headers=response_headers)
