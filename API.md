# Portfolio Bot API Documentation

## Base URL
```
http://localhost:5000/api
```

## Endpoints

### 1. Health Check
Check if the API is running.

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "Portfolio Bot API",
  "timestamp": "2025-10-16T10:30:00.000000"
}
```

---

### 2. Chat
Send a message to the bot and get a response.

**Endpoint:** `POST /api/chat`

**Request Body:**
```json
{
  "message": "What is your background?",
  "session_id": "optional-unique-session-id",
  "history": []
}
```

**Parameters:**
- `message` (required): The user's message/question
- `session_id` (optional): Unique identifier for the conversation session. If not provided, a new one will be generated.
- `history` (optional): Array of previous messages in the conversation. If not provided, session history will be used.

**Response:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "message": "I'm an entrepreneur, software engineer, informatician and physicist...",
  "timestamp": "2025-10-16T10:30:00.000000"
}
```

---

### 3. Get Session
Retrieve conversation history for a session.

**Endpoint:** `GET /api/session/{session_id}`

**Response:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "history": [
    {
      "role": "user",
      "content": "What is your background?"
    },
    {
      "role": "assistant",
      "content": "I'm an entrepreneur, software engineer..."
    }
  ],
  "created_at": "2025-10-16T10:25:00.000000",
  "last_interaction": "2025-10-16T10:30:00.000000"
}
```

---

### 4. Delete Session
Clear conversation history for a session.

**Endpoint:** `DELETE /api/session/{session_id}`

**Response:**
```json
{
  "message": "Session deleted successfully"
}
```

---

### 5. Get Bot Info
Get information about the bot.

**Endpoint:** `GET /api/info`

**Response:**
```json
{
  "name": "Ed Donner",
  "description": "AI-powered chatbot representing Ed Donner",
  "capabilities": [
    "Answer questions about background and experience",
    "Capture lead information",
    "Record unanswered questions"
  ]
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error description"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (missing required parameters)
- `404` - Not Found (session doesn't exist)
- `500` - Internal Server Error

---

## CORS

The API has CORS enabled, allowing requests from any origin. This makes it easy to integrate with frontend applications.

---

## Session Management

Sessions are stored in memory and will be lost when the server restarts. For production use, consider implementing persistent storage (database, Redis, etc.).

**Best Practices:**
- Generate a unique `session_id` on the client side (e.g., UUID)
- Store the `session_id` in browser localStorage or sessionStorage
- Send the same `session_id` with each request to maintain conversation context
- Clear session when user starts a new conversation

---

## Example Usage

### JavaScript/Fetch
```javascript
async function sendMessage(message, sessionId = null) {
  const response = await fetch('http://localhost:5000/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId
    })
  });
  
  const data = await response.json();
  return data;
}

// Usage
const result = await sendMessage("What are your skills?");
console.log(result.message);
console.log(result.session_id); // Save this for subsequent requests
```

### Python/Requests
```python
import requests

def send_message(message, session_id=None):
    url = "http://localhost:5000/api/chat"
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    
    response = requests.post(url, json=payload)
    return response.json()

# Usage
result = send_message("What is your background?")
print(result['message'])
print(result['session_id'])  # Save this for subsequent requests
```

### cURL
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about yourself"}'
```

---

## Configuration

The API can be configured using environment variables in your `.env` file:

```env
# API server port (default: 5000)
API_PORT=5000

# Run mode: "api", "gradio", or "both" (default: both)
MODE=both
```

**Run Modes:**
- `api` - Only start the Flask API server
- `gradio` - Only start the Gradio interface
- `both` - Start both (API on port 5000, Gradio on port 7860)
