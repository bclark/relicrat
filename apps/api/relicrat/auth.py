"""Single-owner bearer sessions. The web gateway alone translates HTTP-only cookies.

Auth uses independent transactions so a failed domain write cannot undo logout,
login throttling, or session issuance. No cookie/query authentication is accepted.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import math
import re
import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from relicrat.credentials import owner_config, verify_password
from relicrat.database import session_factory
from relicrat.models import OwnerLoginGuard, OwnerSession

router = APIRouter(prefix='/api/v1/auth', tags=['owner access'])
TOKEN = re.compile(r'^Bearer ([A-Za-z0-9_-]{43})$')
TTL = timedelta(hours=12)
WINDOW = timedelta(minutes=15)


def now():
    return datetime.now(timezone.utc)


def token_hash(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def authenticate(header):
    _, fingerprint = owner_config()
    match = TOKEN.fullmatch(header or '')
    if not match:
        raise HTTPException(401, 'Sign in to continue', headers={'WWW-Authenticate': 'Bearer'})
    with session_factory()() as db:
        session = db.scalar(select(OwnerSession).where(
            OwnerSession.token_hash == token_hash(match[1]), OwnerSession.credential_fingerprint == fingerprint,
            OwnerSession.expires_at > now(), OwnerSession.revoked_at.is_(None)))
        if session is None:
            raise HTTPException(401, 'Session expired or ended. Sign in again', headers={'WWW-Authenticate': 'Bearer'})
        return {'id': session.id, 'expires_at': session.expires_at}


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    password: str = Field(min_length=1, max_length=256)


@router.post('/login')
def login(payload: Login):
    try:
        encoded, fingerprint = owner_config()
        with session_factory()() as db:
            guard = db.scalar(select(OwnerLoginGuard).where(OwnerLoginGuard.id == 1).with_for_update())
            if guard is None:
                raise ValueError('Missing owner guard')
            instant = now()
            if guard.blocked_until and guard.blocked_until > instant:
                raise HTTPException(429, 'Too many failed attempts. Try again later',
                                    headers={'Retry-After': str(math.ceil((guard.blocked_until - instant).total_seconds()))})
            if guard.window_started_at <= instant - WINDOW:
                guard.failures = 0
                guard.window_started_at = instant
                guard.blocked_until = None
            if not verify_password(payload.password, encoded):
                guard.failures += 1
                if guard.failures >= 5:
                    guard.blocked_until = instant + WINDOW
                db.commit()
                raise HTTPException(401, 'Password not recognized')
            guard.failures = 0
            guard.window_started_at = instant
            guard.blocked_until = None
            # Bounded retention of expired/revoked access state, never domain data.
            db.execute(delete(OwnerSession).where(or_(OwnerSession.expires_at < instant - timedelta(days=1),
                                                    OwnerSession.revoked_at < instant - timedelta(days=1))))
            token = secrets.token_urlsafe(32)
            session = OwnerSession(token_hash=token_hash(token), credential_fingerprint=fingerprint, expires_at=instant + TTL)
            db.add(session)
            db.commit()
            return {'token': token, 'expires_at': session.expires_at, 'max_age': int(TTL.total_seconds())}
    except (ValueError, SQLAlchemyError):
        raise HTTPException(503, 'Owner access is unavailable') from None


@router.get('/session')
def session_info(request: Request):
    return {'authenticated': True, 'expires_at': request.state.owner_session['expires_at']}


@router.post('/logout')
def logout(request: Request):
    try:
        with session_factory()() as db:
            session = db.get(OwnerSession, request.state.owner_session['id'])
            if session is not None:
                session.revoked_at = now()
                db.commit()
        return {'authenticated': False}
    except SQLAlchemyError:
        raise HTTPException(503, 'Sign out could not be confirmed') from None


class OwnerBoundary:
    """Authorize before reading protected bodies; cap unauthenticated login bytes."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        async def private_send(message):
            if message['type'] == 'http.response.start':
                headers = [(k, v) for k, v in message.get('headers', []) if k.lower() not in (b'cache-control', b'x-content-type-options')]
                message['headers'] = headers + [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]
            await send(message)
        if scope['path'] == '/health' and scope['method'] == 'GET':
            return await self.app(scope, receive, private_send)
        if scope['path'] == '/api/v1/auth/login' and scope['method'] == 'POST':
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                if len(body) + len(chunk) > 2048:
                    return await JSONResponse({'detail': 'Login request is too large'}, status_code=413)(scope, receive, private_send)
                body.extend(chunk)
                if not message.get('more_body', False):
                    break
            delivered = False
            async def buffered_receive():
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await self.app(scope, buffered_receive, private_send)
        try:
            owner = await run_in_threadpool(authenticate, Headers(scope=scope).get('authorization'))
        except HTTPException as error:
            return await JSONResponse({'detail': error.detail}, status_code=error.status_code, headers=error.headers)(scope, receive, private_send)
        except (ValueError, SQLAlchemyError):
            return await JSONResponse({'detail': 'Owner access is unavailable'}, status_code=503)(scope, receive, private_send)
        scope.setdefault('state', {})['owner_session'] = owner
        return await self.app(scope, receive, private_send)
