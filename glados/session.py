import json
import asyncio
from typing import Optional
from queue import Queue
from threading import Thread
from datetime import datetime, timezone
from .util.langchain import count_tokens
from .backend.db import use_db

# max recent tokens of session by model
MAX_TOKENS = {
    "gpt-3.5-turbo": 3000,
    "gpt-3.5-turbo-1106": 3000,
    "gpt-4-1106-preview": 7000,
    "gpt-4-vision-preview": 7000,
}

TOKENIZERS = {
    "gpt-3.5-turbo": "gpt3",
    "gpt-3.5-turbo-1106": "gpt3",
    "gpt-4-1106-preview": "gpt4",
    "gpt-4-vision-preview": "gpt4",
}


def random_session_id():
    return str(datetime.now(timezone.utc).timestamp())


class Session:
    def __init__(
        self,
        session_id: Optional[str] = None,
        *,
        model: str = "gpt-3.5-turbo",
        system_prompt: Optional[str] = None,
        user: Optional[str] = None,
    ):
        self.id = session_id or random_session_id()
        self.last_updated = datetime.now(timezone.utc)
        self.model = model
        self.user = user
        self.messages = []
        if system_prompt is not None:
            self(system_prompt, role="system")

    def append(self, message: dict):
        self.messages.append(message)
        self.last_updated = datetime.now(timezone.utc)

        # remove old messages
        total_tokens = 0
        for i, m in enumerate(reversed(self.messages)):
            message = json.dumps(
                m, indent=0, separators=(",", ":")
            )  # XXX: I don't know how to count tokens of a message interactively
            num_tokens = count_tokens(message, model=self.model)
            total_tokens += num_tokens
            if total_tokens > MAX_TOKENS.get(self.model, 3000):
                del self.messages[-i:]
                break

        return self[...]

    def __call__(self, content: str | list | dict, **kwargs):
        if isinstance(content, (str, list)):
            message = {"role": "user", "content": content}
        elif isinstance(content, dict):
            message = content
        else:
            raise TypeError("content must be str, list or dict")
        message.update(**kwargs)
        return self.append(message)

    def __getitem__(self, key):
        if key is Ellipsis:  # session[...]
            # returns recent up to 2000 tokens of message
            return self.messages  # XXX: implement
        elif isinstance(key, slice):  # TODO: implement
            # returns recent up to 2000 tokens of message
            if isinstance(key.start, int):  # session[1000:...]
                ...
                # return recent ~ key.start tokens
        elif isinstance(key, int):
            return self.messages[key]

    def invoke(self, client, **kwargs):
        """invoke a chat"""
        return client.chat.completions.create(
            model=self.model,
            messages=self[...],
            max_tokens=2000,
            user=self.user,
            **kwargs,
        )

    def condense(self, client):
        """make a condensed version of session"""
        recent_conversation = "\n".join(
            f"<{message['role']}> {message['content']}" for message in self.messages
        )
        prompt = (
            "This is recent conversation with AI assistant: \n\n"
            f"{recent_conversation}\n\n"
            "Please summarize the conversation in a few paragraphs."
            "Most recent messages are more important than older ones."
            "Please include as many as important keywords in your summary."
            "Use the most common language of the conversation."
        )
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a programming interface, outputs JSON.",
                },
                {"role": "user", "text": prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
            output_type="json_object",
        )
        self.messages = [
            {
                "role": "user",
                "content": "Please summarize the recent conversation",
            },
            {"role": "assistant", "content": result.choices[0].content},
        ]

    def retrive(self, session_id: str):
        """retrieve session snapshot"""
        ...

    @classmethod
    def from_snapshot(cls, snapshot: dict): ...

    def to_dict(self):
        """convert session to dict"""
        return {
            "session_id": self.id,
            "last_updated": self.last_updated.isoformat(),
            "model": self.model,
            "user": self.user,
            "messages": self.messages,
        }


class SessionManager:
    sessions = {}
    queue = Queue()
    pid = None

    def start(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.run())
        finally:
            loop.close()

    async def run(self):
        """run session manager"""
        db = use_db()
        while True:
            colname, doc = self.queue.get()
            col = db.get_collection(colname)
            await col.insert_one(doc)
            self.queue.task_done()

    # @classmethod
    # def get_instance(cls):
    #     if cls.pid is None:
    #         self.pid = Thread(target=self.start)
    #         self.pid.start()

    #         cls.pid = Thread(target=cls.run)
    #         cls.pid.start()
    #     return cls

    @staticmethod
    async def save_session(self, session_id: str):
        """persist session snapshot"""
        db = use_db()
        col = db.get_collection("sessions")

        session = SessionManager.sessions.get(session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")
            return

        await col.insert_one(
            {
                "session_id": session.id,
                "last_updated": session.last_updated,
                "model": session.model,
                "user": session.user,
                "messages": session.messages,
            }
        )

    @staticmethod
    def get_session(session_id) -> Session:
        """Get a session. if not exists, create one."""
        # gabage collection if number of sessions exceeds 100 for saving memory
        if len(SessionManager.sessions) > 100:
            sorted_sessions = sorted(
                SessionManager.sessions.items(),
                key=lambda item: item[1].last_updated,
                reverse=True,
            )
            # delete sessions except for 100 most recent sessions
            for k, _ in sorted_sessions[100:]:
                SessionManager.clear_session(k)

        if session_id not in SessionManager.sessions:
            SessionManager.sessions[session_id] = Session(session_id)

        return SessionManager.sessions[session_id]

    @staticmethod
    def end_session(session_id):
        """End a session and store snapshot."""
        ...

    @staticmethod
    def resume_session(session_id, subject: str):
        """Resume a session. if session is not in memory, retrieve from snapshot."""
        # TODO
        # get embeddings of subject
        # search for similar session
        # if found, retrieve session
        # if needed, summarize session conversation
        # make a new session from snapshot
        # return session
        ...

    @staticmethod
    def clear_session(session_id):
        """Clear a session if exists."""
        if session_id in SessionManager.sessions:
            del SessionManager.sessions[session_id]
