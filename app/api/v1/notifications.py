import asyncio
import contextlib
import logging
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.dependency import get_current_user
from app.models.user import User
from app.realtime import channel_for
from app.redis_client import get_async_redis
from app.schemas.notification import (
    MarkAllReadOut,
    NotificationFilters,
    NotificationOut,
    NotificationPage,
    UnreadCountOut,
    WsTicketOut,
)
from app.security import decode_ws_ticket
from app.services import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])

WS_POLICY_VIOLATION = 1008
WS_INTERNAL_ERROR = 1011


@router.get("/notifications", response_model=NotificationPage)
def list_notifications(
    filters: Annotated[NotificationFilters, Query()],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.list_notifications(db, user, filters)


@router.get("/notifications/unread-count", response_model=UnreadCountOut)
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return notification_service.unread_count(db, user)


@router.post("/notifications/read-all", response_model=MarkAllReadOut)
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return notification_service.mark_all_read(db, user)


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return notification_service.mark_read(db, notification_id, user)


@router.post("/ws/ticket", response_model=WsTicketOut)
def ws_ticket(user: User = Depends(get_current_user)):
    # a browser cannot send the Authorization header with a WebSocket, and a token in the URL ends up in logs:
    # so the client trades its token for a short-lived one-time ticket first
    return notification_service.issue_ws_ticket(user)


@router.websocket("/ws")
async def notifications_socket(websocket: WebSocket, ticket: str = Query(min_length=1)):
    # browsers always send Origin: refuse pages we do not know (cross-site WebSocket hijacking)
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in config.ALLOWED_ORIGINS:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    try:
        claims = decode_ws_ticket(ticket)
    except jwt.PyJWTError:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    # one-time use: SET NX succeeds only for the first connection with this ticket
    client = get_async_redis()
    try:
        first_use = await client.set(f"ws_ticket:{claims['jti']}", "1", nx=True, ex=config.WS_TICKET_TTL_SECONDS)
    except RedisError:
        logger.exception("Valkey is unavailable, websocket refused")
        await websocket.close(code=WS_INTERNAL_ERROR)
        return
    if not first_use:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    await websocket.accept()
    await _serve(websocket, client, channel_for(claims["uid"]))


async def _serve(websocket: WebSocket, client, channel: str) -> None:
    try:
        async with client.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            # "connected" is sent only after the subscription: whatever is published later arrives here,
            # whatever happened earlier the client fetches over REST (it can dedupe by notification id)
            await websocket.send_json({"type": "connected"})

            tasks = [
                asyncio.create_task(_forward(websocket, pubsub)),
                asyncio.create_task(_listen(websocket)),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                error = task.exception()
                if error is not None and not isinstance(error, WebSocketDisconnect):
                    logger.warning("Websocket closed after an error: %r", error)
    except RedisError:
        logger.exception("Valkey error while serving a websocket")
    with contextlib.suppress(RuntimeError, WebSocketDisconnect):
        await websocket.close()


async def _forward(websocket: WebSocket, pubsub) -> None:
    async for message in pubsub.listen():
        if message["type"] == "message":
            await websocket.send_text(message["data"])


async def _listen(websocket: WebSocket) -> None:
    while True:
        text = await websocket.receive_text()
        if text == "ping":
            await websocket.send_json({"type": "pong"})
