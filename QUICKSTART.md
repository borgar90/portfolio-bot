# Quick Start Guide - Portfolio Bot API

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Then edit with your keys
```

## Running the Server

### Both API + Gradio (Default)
```bash
python app.py
```
- API: http://localhost:5000
- Gradio UI: http://localhost:7860

### API Only
```bash
set MODE=api
python app.py
```

### Gradio Only
```bash
set MODE=gradio
python app.py
```

## Quick API Test

### Using cURL
```bash
# Health check
curl http://localhost:5000/api/health

# Send a message
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello! What is your background?\"}"
```

### Using Python Script
```bash
python examples/test_api.py
```

### Using the Web UI
Open `examples/frontend-example.html` in your browser (requires API server running).

## Integration in Your Frontend

### React Example
```jsx
import { useState, useEffect } from 'react';

function ChatBot() {
  const [sessionId, setSessionId] = useState(
    localStorage.getItem('bot_session')
  );
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const sendMessage = async (message) => {
    const response = await fetch('http://localhost:5000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId })
    });
    
    const data = await response.json();
    setSessionId(data.session_id);
    localStorage.setItem('bot_session', data.session_id);
    
    setMessages([...messages, 
      { role: 'user', content: message },
      { role: 'assistant', content: data.message }
    ]);
  };

  return (
    <div>
      {/* Your chat UI here */}
    </div>
  );
}
```

### Vue Example
```vue
<template>
  <div class="chat">
    <div v-for="msg in messages" :key="msg.id">
      {{ msg.content }}
    </div>
    <input v-model="input" @keyup.enter="sendMessage" />
  </div>
</template>

<script>
export default {
  data() {
    return {
      messages: [],
      input: '',
      sessionId: localStorage.getItem('bot_session')
    }
  },
  methods: {
    async sendMessage() {
      const response = await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: this.input,
          session_id: this.sessionId
        })
      });
      
      const data = await response.json();
      this.sessionId = data.session_id;
      localStorage.setItem('bot_session', data.session_id);
      
      this.messages.push(
        { role: 'user', content: this.input },
        { role: 'assistant', content: data.message }
      );
      this.input = '';
    }
  }
}
</script>
```

### Vanilla JavaScript
```javascript
class ChatAPI {
  constructor() {
    this.apiUrl = 'http://localhost:5000/api';
    this.sessionId = localStorage.getItem('bot_session');
  }

  async sendMessage(message) {
    const response = await fetch(`${this.apiUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: this.sessionId
      })
    });

    const data = await response.json();
    this.sessionId = data.session_id;
    localStorage.setItem('bot_session', data.session_id);
    return data;
  }

  async getHistory() {
    if (!this.sessionId) return null;
    
    const response = await fetch(
      `${this.apiUrl}/session/${this.sessionId}`
    );
    return response.json();
  }

  clearSession() {
    if (this.sessionId) {
      fetch(`${this.apiUrl}/session/${this.sessionId}`, {
        method: 'DELETE'
      });
      localStorage.removeItem('bot_session');
      this.sessionId = null;
    }
  }
}

// Usage
const chat = new ChatAPI();
const result = await chat.sendMessage("Hello!");
console.log(result.message);
```

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Check API status |
| POST | `/api/chat` | Send message, get response |
| GET | `/api/session/{id}` | Get conversation history |
| DELETE | `/api/session/{id}` | Clear session |
| GET | `/api/info` | Get bot information |

## Environment Variables

```env
# Required
OPENAI_API_KEY=your_key_here
PUSHOVER_TOKEN=your_token
PUSHOVER_USER=your_user_key

# Optional
API_PORT=5000          # Default: 5000
MODE=both              # Options: api, gradio, both
```

## Production Deployment

For production, consider:

1. **Add Authentication**: JWT tokens, API keys
2. **Rate Limiting**: Prevent abuse
3. **Persistent Storage**: Use Redis or database for sessions
4. **HTTPS**: Use SSL certificates
5. **Error Handling**: Better error messages and logging
6. **Monitoring**: Add health checks and metrics
7. **Scaling**: Use gunicorn or similar WSGI server

Example with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

**API not starting:**
- Check if port 5000 is available
- Verify all environment variables are set
- Check Python version (3.8+)

**CORS errors:**
- CORS is enabled by default
- For production, configure specific origins in app.py

**Session not persisting:**
- Sessions are in-memory only
- Implement database/Redis for production

**OpenAI errors:**
- Verify API key is valid
- Check account has credits
- Review rate limits

## Next Steps

1. Customize the system prompt in `app.py`
2. Add your own LinkedIn PDF and summary
3. Modify the frontend example to match your brand
4. Deploy to production (Heroku, AWS, etc.)
5. Monitor and improve based on user interactions

For complete documentation, see [API.md](API.md)
