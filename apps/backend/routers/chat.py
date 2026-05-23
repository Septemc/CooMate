from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import Conversation, Message, User, get_db
from models.schemas import ChatRequest, ConversationOut, ConversationSummary, MessageOut, GenerateOptionsRequest, GenerateOptionsResponse, StepOptionOut
from llm_client import stream_chat, parse_steps, _build_messages, generate_step_options

router = APIRouter(prefix="/api", tags=["chat"])


def _get_user_from_request(request: Request, db: Session) -> User:
    """Extract user from auth header, or create/find guest user."""
    from auth import get_current_user_optional
    user = get_current_user_optional(request, db)
    if user is None:
        # Fallback: find or create default guest
        guest = db.query(User).filter(User.username == "guest").first()
        if not guest:
            guest = User(
                id=str(uuid.uuid4()),
                username="guest",
                name="游客",
                password_hash="",
                is_guest=True,
            )
            db.add(guest)
            db.commit()
            db.refresh(guest)
        return guest
    return user


@router.post("/chat")
async def chat(req: ChatRequest, request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_request(request, db)

    # Get or create conversation
    if req.conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == req.conversation_id,
            Conversation.user_id == user.id,
        ).first()
        if not conv:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title="新对话",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # Store user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)

    # Update title on first message
    msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
    if msg_count == 0:
        conv.title = req.message[:30] + ("..." if len(req.message) > 30 else "")
    db.commit()

    # Build history for LLM (last 20 messages)
    history_msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_msgs[-21:-1]]

    conv_id = conv.id

    async def generate():
        full_text = ""
        async for chunk in stream_chat(_build_messages(history, req.message), req.action):
            full_text += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

        # Parse steps and store assistant message
        steps = parse_steps(full_text)
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            role="assistant",
            content=full_text,
            steps=steps,
        )
        db.add(assistant_msg)
        conv.updated_at = time.time()
        db.commit()

        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'steps': steps}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/chat/generate-options", response_model=GenerateOptionsResponse)
async def generate_options(req: GenerateOptionsRequest):
    try:
        options = await generate_step_options(req.step_title, req.step_content, req.user_context)
        return GenerateOptionsResponse(
            options=[StepOptionOut(key=o["key"], label=o["label"]) for o in options]
        )
    except Exception as e:
        return GenerateOptionsResponse(
            options=[
                StepOptionOut(key="A", label="我愿意直面这个问题"),
                StepOptionOut(key="B", label="我还没完全想清楚"),
                StepOptionOut(key="C", label="我想换个角度看看"),
            ]
        )


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_request(request, db)
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        ConversationSummary(
            id=c.id,
            title=c.title,
            updated_at=c.updated_at.timestamp() if c.updated_at else 0,
        )
        for c in convs
    ]


@router.get("/conversations/{conv_id}", response_model=ConversationOut)
async def get_conversation(conv_id: str, request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_request(request, db)
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
        .all()
    )
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                steps=m.steps,
                timestamp=m.created_at.timestamp() if m.created_at else 0,
            )
            for m in msgs
        ],
        created_at=conv.created_at.timestamp() if conv.created_at else 0,
        updated_at=conv.updated_at.timestamp() if conv.updated_at else 0,
    )


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_request(request, db)
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id,
    ).first()
    if conv:
        db.delete(conv)
        db.commit()
    return {"ok": True}
