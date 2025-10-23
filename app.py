"""Portfolio bot API server with multilingual support, Redis-backed sessions, and
PostgreSQL transcript archiving.

Author: Borgar Flaen Stensrud / BFS Company
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import requests
import redis
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from flask import Flask, request, Response
from flask_cors import CORS
from apig_wsgi import make_lambda_handler

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
    text,
)
from sqlalchemy.exc import SQLAlchemyError

load_dotenv(override=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL, format="%(message)s")
logger = logging.getLogger("portfolio_bot")

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "8"))
PUSHOVER_TIMEOUT_SECONDS = float(os.getenv("PUSHOVER_TIMEOUT_SECONDS", "5"))
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
LOG_FORWARD_URL = os.getenv("LOG_FORWARD_URL")
LOG_FORWARD_TIMEOUT = float(os.getenv("LOG_FORWARD_TIMEOUT", "2"))

# Initialize Flask app
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
CORS(app)  # Enable CORS for frontend integration

NORWEGIAN_KEYWORDS = {
    "hei",
    "hva",
    "hvordan",
    "takk",
    "v\u00e6r",
    "bes\u00f8kende",
    "kontakt",
    "erfaring",
    "ferdigheter",
    "bakgrunn",
}

ENGLISH_KEYWORDS = {
    "hello",
    "what",
    "how",
    "thanks",
    "please",
    "contact",
    "background",
    "experience",
    "skills",
    "portfolio",
}


def forward_log(payload: dict):
    """Send structured logs to optional webhook for centralized monitoring."""
    if not LOG_FORWARD_URL:
        return
    try:
        requests.post(LOG_FORWARD_URL, json=payload, timeout=LOG_FORWARD_TIMEOUT)
    except requests.RequestException as exc:
        logger.debug("log_forward_failed %s", exc)


def log_event(event_type, **details):
    """Record an event with ISO timestamp and forward it if a collector is configured."""
    payload = {"event": event_type, "timestamp": datetime.now(timezone.utc).isoformat()}
    payload.update(details)
    logger.info(json.dumps(payload, default=str, ensure_ascii=False))
    forward_log(payload)


class SessionStore:
    """Maintain per-session chat context with Redis TTL fallback to in-memory cache."""

    def __init__(self, redis_url: str | None, ttl_seconds: int):
        self.ttl = max(ttl_seconds, 60)
        self.redis = None
        self._cache = {}
        if redis_url:
            try:
                self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
                log_event("session_store_ready", backend="redis")
            except redis.RedisError as exc:
                log_event("session_store_error", error=str(exc))
                self.redis = None
                log_event("session_store_fallback", reason="redis_connection_failed")
                log_event("session_store_in_memory", reason="redis_connection_failed")
        else:
            log_event("session_store_in_memory", reason="missing_redis_url")

    def _key(self, session_id: str) -> str:
        return f"portfolio_bot:session:{session_id}"

    def _purge_expired(self):
        if self.redis:
            return
        now = time.time()
        expired = [sid for sid, record in self._cache.items() if record["expires"] < now]
        for sid in expired:
            self._cache.pop(sid, None)

    def get(self, session_id: str):
        if self.redis:
            raw = self.redis.get(self._key(session_id))
            if not raw:
                return None
            self.redis.expire(self._key(session_id), self.ttl)
            return json.loads(raw)
        self._purge_expired()
        record = self._cache.get(session_id)
        if not record:
            return None
        record["expires"] = time.time() + self.ttl
        return json.loads(json.dumps(record["data"]))  # return a shallow copy

    def set(self, session_id: str, data: dict):
        """Persist chat state and refresh its TTL."""
        payload = json.loads(json.dumps(data, ensure_ascii=False))
        if self.redis:
            self.redis.set(self._key(session_id), json.dumps(payload, ensure_ascii=False), ex=self.ttl)
        else:
            self._cache[session_id] = {"data": payload, "expires": time.time() + self.ttl}

    def delete(self, session_id: str):
        """Remove a session, clearing any stored context."""
        if self.redis:
            self.redis.delete(self._key(session_id))
        else:
            self._cache.pop(session_id, None)

    def touch(self, session_id: str):
        """Extend the TTL without mutating the stored payload."""
        if self.redis:
            self.redis.expire(self._key(session_id), self.ttl)
        else:
            record = self._cache.get(session_id)
            if record:
                record["expires"] = time.time() + self.ttl

    def health(self):
        """Report backend health for monitoring surfaces."""
        if self.redis:
            try:
                self.redis.ping()
                return {"status": "ok", "backend": "redis"}
            except redis.RedisError as exc:
                return {"status": "error", "backend": "redis", "error": str(exc)}
        self._purge_expired()
        return {"status": "in_memory", "backend": "memory", "active_sessions": len(self._cache)}


class MessageStore:
    """Persist messages to the backing SQL database for analytics and auditing."""

    def __init__(self, database_url: str | None):
        self.engine = None
        self.table = None
        if not database_url:
            log_event("message_store_disabled", reason="missing_database_url")
            return

        try:
            self.engine = create_engine(database_url, pool_pre_ping=True, future=True)
            metadata = MetaData()
            self.table = Table(
                "conversation_messages",
                metadata,
                Column("id", String(36), primary_key=True),
                Column("session_id", String(64), nullable=False, index=True),
                Column("role", String(16), nullable=False),
                Column("content", Text, nullable=False),
                Column("language", String(8)),
                Column("rate_limited", Boolean, nullable=False, default=False),
                Column("created_at", DateTime(timezone=True), nullable=False),
            )
            metadata.create_all(self.engine)
            log_event(
                "message_store_ready",
                backend=self.engine.url.get_backend_name(),
                database=self.engine.url.database,
            )
        except SQLAlchemyError as exc:
            log_event("message_store_error", error=str(exc))
            self.engine = None
            self.table = None

    def store(self, session_id: str, role: str, content: str, language: str | None = None, rate_limited: bool = False):
        """Insert a single message row into the conversation log."""
        if self.engine is None or self.table is None:
            return False

        try:
            with self.engine.begin() as conn:
                conn.execute(
                    insert(self.table),
                    {
                        "id": str(uuid.uuid4()),
                        "session_id": session_id,
                        "role": role,
                        "content": content,
                        "language": language,
                        "rate_limited": rate_limited,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
            return True
        except SQLAlchemyError as exc:
            log_event("message_store_write_failed", error=str(exc))
            return False

    def health(self):
        """Report backend health for monitoring surfaces."""
        if self.engine is None or self.table is None:
            return {"status": "disabled", "backend": None}
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ok", "backend": self.engine.url.get_backend_name()}
        except SQLAlchemyError as exc:
            log_event("message_store_health_error", error=str(exc))
            return {"status": "error", "backend": self.engine.url.get_backend_name(), "error": str(exc)}


session_store = SessionStore(REDIS_URL, SESSION_TTL_SECONDS)
message_store = MessageStore(DATABASE_URL)


def detect_language_preference(text):
    """Infer whether the visitor is likely speaking Norwegian or English."""
    lowered = text.lower()
    if any(ch in lowered for ch in ("\u00e6", "\u00f8", "\u00e5")):
        return "no"
    if any(keyword in lowered for keyword in NORWEGIAN_KEYWORDS):
        return "no"
    if any(keyword in lowered for keyword in ENGLISH_KEYWORDS):
        return "en"
    return "no"


def rate_limit_message(language_code):
    """Produce a per-language advisory when the rate limit triggers."""
    if language_code == "en":
        return "I'd love to keep chatting, but I can only respond to a few messages per minute per visitor. Please try again in a moment."
    return "Jeg svarer gjerne, men jeg er begrenset til noen f\u00e5 meldinger per minutt per bes\u00f8kende. Pr\u00f8v igjen om et lite \u00f8yeblikk."


def fallback_error_message(language_code):
    """Provide a friendly explanation if OpenAI is unreachable."""
    if language_code == "en":
        return "Sorry, I ran into an issue reaching the service. Please try again shortly."
    return "Beklager, jeg st\u00f8tte p\u00e5 et problem med tjenesten min. Kan du pr\u00f8ve igjen om litt?"


def check_rate_limit(session_id, session, language_code):
    """Return flag + message when a session exceeds its quota within the rate window."""
    if RATE_LIMIT_MAX_REQUESTS <= 0:
        return False, None

    if not session:
        return False, None

    now = time.time()
    timestamps = session.setdefault("request_timestamps", [])
    timestamps = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW_SECONDS]

    if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        session["request_timestamps"] = timestamps
        log_event(
            "rate_limited",
            session_id=session_id,
            count=len(timestamps),
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        return True, rate_limit_message(language_code)

    timestamps.append(now)
    session["request_timestamps"] = timestamps
    return False, None


def push(text):
    token = os.getenv("PUSHOVER_TOKEN")
    user_key = os.getenv("PUSHOVER_USER")
    if not token or not user_key:
        log_event("pushover_skipped", reason="missing_credentials")
        return False

    try:
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": token,
                "user": user_key,
                "message": text,
            },
            timeout=PUSHOVER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        log_event("pushover_delivered", characters=len(text))
        return True
    except requests.RequestException as exc:
        log_event("pushover_error", error=str(exc), preview=text[:120])
        return False


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    log_event("record_user_details", email=email, name=name)
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    log_event("record_unknown_question", question_preview=question[:120])
    return {"recorded": "ok"}


def json_response(payload, status=200):
    """Return a UTF-8 encoded JSON response with consistent headers."""
    return Response(
        json.dumps(payload, ensure_ascii=False),
        status=status,
        mimetype="application/json; charset=utf-8"
    )

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]


class Me:
    """Encapsulates persona data and LLM interaction helpers."""

    def __init__(self):
        """Load personal knowledge sources and configure OpenAI client."""
        self.openai = OpenAI(timeout=OPENAI_TIMEOUT_SECONDS, max_retries=OPENAI_MAX_RETRIES)
        self.name = "Borgar Flaen Stensrud"
        reader = PdfReader("me/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()


    def handle_tool_call(self, tool_calls):
        """Route tool calls emitted by the model to local helper functions."""
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            log_event("tool_invoked", tool=tool_name)
            tool = globals().get(tool_name)
            if not tool:
                log_event("tool_missing", tool=tool_name)
                result = {}
            else:
                result = tool(**arguments)
            results.append({"role": "tool","content": json.dumps(result, ensure_ascii=False),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        """Build the long-form system prompt with persona context."""
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. \
Always respond in the same language the user uses, defaulting to Norwegian when you are unsure which language they prefer. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def chat(self, message, history):
        """Simplified chat helper for non-API callers."""
        result = self.chat_api(message, history, language_hint=detect_language_preference(message))
        return result["response"]
    
    def chat_api(self, message, history=None, language_hint="no"):
        """API version of chat that handles history as a list of message objects"""
        if history is None:
            history = []
        
        messages = [{"role": "system", "content": self.system_prompt()}] + list(history) + [{"role": "user", "content": message}]
        done = False
        response = None
        while not done:
            try:
                response = self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tools,
                    timeout=OPENAI_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                log_event("openai_error", error=str(exc))
                updated_history = list(history)
                updated_history.append({"role": "user", "content": message})
                fallback = fallback_error_message(language_hint or "no")
                updated_history.append({"role": "assistant", "content": fallback})
                return {
                    "response": fallback,
                    "updated_history": updated_history,
                    "error": "openai_unavailable"
                }
            if response.choices[0].finish_reason=="tool_calls":
                msg = response.choices[0].message
                tool_calls = msg.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(msg)
                messages.extend(results)
            else:
                done = True
        
        usage = getattr(response, "usage", None)
        if usage:
            log_event(
                "chat_completion",
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )
        else:
            log_event("chat_completion", input_tokens=None, output_tokens=None, total_tokens=None)

        return {
            "response": response.choices[0].message.content,
            "updated_history": messages[1:]  # Exclude system prompt
        }


# Initialize the bot
me = Me()


# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    db_status = message_store.health()
    session_status = session_store.health()
    overall = "healthy"
    if db_status.get("status") == "error" or session_status.get("status") == "error":
        overall = "unhealthy"
    response = {
        "status": overall,
        "service": "Portfolio Bot API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "session_store": session_status,
    }
    status_code = 200 if overall == "healthy" else 503
    return json_response(response, status=status_code)


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint
    Expected JSON body:
    {
        "message": "user message",
        "session_id": "optional-session-id",
        "history": [] // optional conversation history
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return json_response({"error": "Message is required"}, status=400)
        
        message = data['message']
        session_id = data.get('session_id', str(uuid.uuid4()))
        history = data.get('history', [])
        language = detect_language_preference(message)

        session = session_store.get(session_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        if not session:
            session = {
                "created_at": now_iso,
                "history": [],
                "request_timestamps": [],
                "last_interaction": now_iso,
            }
        else:
            session_store.touch(session_id)
            session.setdefault("history", [])
            session.setdefault("request_timestamps", [])

        if history:
            history_list = list(history)
            session["history"] = history_list
        else:
            history_list = list(session.get("history", []))

        session["last_interaction"] = now_iso
        message_store.store(session_id, "user", message, language=language)

        log_event(
            "chat_request",
            session_id=session_id,
            language=language,
            history_length=len(history_list),
        )

        limited, limit_message = check_rate_limit(session_id, session, language)
        session_store.set(session_id, session)
        if limited:
            updated_history = history_list + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": limit_message},
            ]
            session["history"] = updated_history
            session["last_interaction"] = datetime.now(timezone.utc).isoformat()
            session_store.set(session_id, session)
            log_event("chat_rate_limited", session_id=session_id, language=language)
            message_store.store(session_id, "assistant", limit_message, language=language, rate_limited=True)
            return json_response({
                "session_id": session_id,
                "message": limit_message,
                "timestamp": session["last_interaction"],
                "rate_limited": True
            })
        
        # Get response from bot
        result = me.chat_api(message, history_list, language_hint=language)
        
        # Update session history
        session["history"] = result['updated_history']
        session["last_interaction"] = datetime.now(timezone.utc).isoformat()
        session_store.set(session_id, session)
        log_event(
            "chat_response",
            session_id=session_id,
            language=language,
            rate_limited=False,
            error=result.get("error")
        )

        message_store.store(session_id, "assistant", result['response'], language=language)
        
        response_body = {
            "session_id": session_id,
            "message": result['response'],
            "timestamp": session["last_interaction"],
            "rate_limited": False,
        }
        return json_response(response_body)
    
    except Exception as e:
        log_event("chat_endpoint_error", error=str(e), session_id=data.get("session_id") if 'data' in locals() and isinstance(data, dict) else None)
        return json_response({"error": str(e)}, status=500)


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session history"""
    session = session_store.get(session_id)
    if not session:
        return json_response({"error": "Session not found"}, status=404)
    session_store.touch(session_id)
    return json_response({
        "session_id": session_id,
        "history": session.get('history', []),
        "created_at": session.get('created_at'),
        "last_interaction": session.get('last_interaction')
    })


@app.route('/api/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Clear session history"""
    session = session_store.get(session_id)
    if session:
        session_store.delete(session_id)
        return json_response({"message": "Session deleted successfully"})
    return json_response({"error": "Session not found"}, status=404)


@app.route('/api/info', methods=['GET'])
def get_info():
    """Get bot information"""
    return json_response({
        "name": me.name,
        "description": f"AI-powered chatbot representing {me.name}",
        "capabilities": [
            "Answer questions about background and experience",
            "Capture lead information",
            "Record unanswered questions"
        ]
    })


# AWS Lambda handler via API Gateway -> WSGI bridge
lambda_handler = make_lambda_handler(app)


if __name__ == "__main__":
    from waitress import serve

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 5000))
    threads = int(os.getenv("WSGI_THREADS", "4"))

    log_event("wsgi_server_starting", host=host, port=port, threads=threads, server="waitress")
    serve(app, host=host, port=port, threads=threads)
