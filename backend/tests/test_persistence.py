import os

import pytest
from sqlalchemy import select

from app.db import SessionLocal, initialize_database
from app.models import ChatSession, Message


@pytest.mark.asyncio
async def test_session_messages_are_scoped_to_their_session() -> None:
    if os.getenv("RUN_DATABASE_TESTS") != "1":
        pytest.skip("Set RUN_DATABASE_TESTS=1 against the compose PostgreSQL service.")
    await initialize_database()
    async with SessionLocal() as db:
        first = ChatSession(title="First")
        second = ChatSession(title="Second")
        db.add_all([first, second])
        await db.flush()
        db.add_all([
            Message(session_id=first.id, role="user", content="first message", source_refs=[], receipt={}),
            Message(session_id=second.id, role="user", content="second message", source_refs=[], receipt={}),
        ])
        await db.commit()
        messages = (await db.scalars(select(Message).where(Message.session_id == first.id))).all()
        assert [message.content for message in messages] == ["first message"]
        await db.delete(first)
        await db.delete(second)
        await db.commit()
