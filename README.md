# Portfolio Bot

An intelligent AI-powered chatbot that represents you on your portfolio website. This bot uses OpenAI's GPT-4o-mini to engage with visitors, answer questions about your background, skills, and experience, and capture leads.

**Now with REST API support!** Easily integrate the bot into your custom frontend applications.

## 🎯 What It Does

Portfolio Bot creates an interactive chat experience on your portfolio website where the AI acts as you, answering questions about your:
- Professional background and experience
- Skills and expertise
- Career history (from LinkedIn)
- Personal interests

The bot intelligently:
- **Captures Leads**: Records visitor contact information when they express interest
- **Tracks Unknown Questions**: Logs questions it can't answer so you can improve the knowledge base
- **Sends Real-time Notifications**: Uses Pushover to notify you instantly when someone wants to connect
- **Stays In Character**: Represents you professionally based on your LinkedIn profile and custom summary

## 🚀 Features

### REST API
- Full REST API for frontend integration
- Session management for conversation continuity
- CORS enabled for cross-origin requests
- JSON responses for easy parsing
- Multiple endpoints for different functionalities

### AI-Powered Conversations
- Uses OpenAI GPT-4o-mini for natural, context-aware responses
- Trained on your LinkedIn profile and personal summary
- Maintains professional tone while being engaging
- Mirrors the visitor's language automatically and defaults to Norwegian when uncertain

### Lead Capture System
- Automatically detects when visitors want to connect
- Records email addresses and names
- Stores conversation context for follow-up
- Instant notifications via Pushover

### Knowledge Management
- Records questions the bot couldn't answer
- Helps you identify gaps in your portfolio information
- Continuous improvement through feedback

### Frontend Ready
- Use the included HTML example (`examples/frontend-example.html`)
- Integrates seamlessly with React, Vue, or any SPA
- Customize the chat experience to match your brand

### Resilient by Default
- Structured JSON logging for easier monitoring
- OpenAI and Pushover calls guarded by timeouts and error handling
- Built-in per-session rate limiting with friendly user notifications
- Optional PostgreSQL archive of every visitor/assistant message (enable via `DATABASE_URL`)
- Optional log forwarding webhook for real-time alerting (set LOG_FORWARD_URL)
- /api/health reports database/session status for external monitoring

## 📋 Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Pushover account (for notifications)
- Your LinkedIn profile exported as PDF
- A brief personal summary
- Redis instance (optional, for expiring session storage)
- (Optional) PostgreSQL database if you want to persist chat transcripts (`DATABASE_URL`)

## 🛠️ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/borgar90/portfolio-bot.git
cd portfolio-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory with:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here
PUSHOVER_TOKEN=your_pushover_app_token
PUSHOVER_USER=your_pushover_user_key

# Optional
API_HOST=0.0.0.0               # Bind address for the WSGI server
API_PORT=5000                  # API server port (default: 5000)
LOG_LEVEL=INFO                 # Logging level for structured events
RATE_LIMIT_MAX_REQUESTS=8      # Requests allowed per session within the window
RATE_LIMIT_WINDOW_SECONDS=60   # Window size in seconds for rate limiting
OPENAI_TIMEOUT_SECONDS=30      # Timeout for OpenAI responses
PUSHOVER_TIMEOUT_SECONDS=5     # Timeout for Pushover notifications
WSGI_THREADS=4                 # Waitress worker threads
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/portfolio_bot   # Optional: persistent chat storage
REDIS_URL=redis://redis:6379/0      # Optional: Redis-backed session store with TTL
SESSION_TTL_SECONDS=3600            # Expiry window for chat sessions (minimum 60s, Redis or in-memory fallback)
LOG_FORWARD_URL=https://logs.example.com/collect  # Optional webhook/collector for structured log forwarding
LOG_FORWARD_TIMEOUT=2               # Timeout (seconds) for log forwarding
```

With `DATABASE_URL` configured, the app automatically creates a `conversation_messages` table (if needed) and records every unauthenticated visitor utterance and assistant reply, including language hints and rate-limit flags. If the variable is omitted, the API still works but skips persistence.

## Local Smoke Test

1. Create a virtual environment and install dependencies: `pip install -r requirements.txt`.
2. Export the required environment variables (or copy `.env`) including `OPENAI_API_KEY`, `PUSHOVER_TOKEN`, and `PUSHOVER_USER`.
3. To exercise persistence locally, ensure Postgres and Redis are available (`docker network create devnet` once, then `docker compose up --build`).
4. For a quick check without Docker, run `python app.py` in one shell and `python examples/test_api.py` in another.
5. Optional: verify Pushover notifications with `python examples/test_pushover.py --message "Test from portfolio-bot"`.

When `REDIS_URL` is supplied the app stores session state in Redis with automatic expiration (default 1 hour). Without Redis it falls back to an in-memory store with the same TTL logic.

**How to get these:**
- **OpenAI API Key**: Sign up at [OpenAI Platform](https://platform.openai.com/)
- **Pushover**: Create an account at [Pushover.net](https://pushover.net/) and create an application

### 4. Prepare Your Profile Data

Place these files in the `me/` directory:
- `linkedin.pdf` - Export your LinkedIn profile as PDF
- `summary.txt` - Write a brief personal summary (see example below)

**Example `summary.txt`:**
```
My name is [Your Name]. I'm a [your profession/roles]. I'm originally from [location].
I love [interests/hobbies]. [Any other relevant personal information].
```

### 5. Run the Application

```bash
python app.py
```

- Waitress WSGI server listens on `http://localhost:5000` by default
- Override bind host/port with `API_HOST` / `API_PORT`

## 🌐 API Usage

The bot includes a full REST API for frontend integration. See [API.md](API.md) for complete documentation.

### Quick Start Example

```javascript
// Send a message
const response = await fetch('http://localhost:5000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "What is your background?",
    session_id: "unique-session-id"  // Optional
  })
});

  const data = await response.json();
  console.log(data.message);  // Bot's response
  console.log(data.session_id);  // Save for next request
  console.log(data.rate_limited); // true when the per-session limit is hit
```

### Available Endpoints

- `GET /api/health` - Check API status
- `POST /api/chat` - Send a message and get response
- `GET /api/session/{id}` - Get conversation history
- `DELETE /api/session/{id}` - Clear session
- `GET /api/info` - Get bot information
- Every `/api/chat` response includes a `rate_limited` flag so frontends can pause gracefully

### Example Frontend

See `examples/frontend-example.html` for a complete working example with a beautiful chat interface.

### Test the API

```bash
python examples/test_api.py
```

## 📁 Project Structure

```
portfolio-bot/
├── app.py                          # Main application with AI logic and API
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (not in git)
├── .gitignore                     # Git ignore rules
├── README.md                      # This file
├── API.md                         # Complete API documentation
├── me/
│   ├── linkedin.pdf              # Your LinkedIn profile
│   └── summary.txt               # Personal summary
└── examples/
    ├── frontend-example.html     # Beautiful chat UI example
    └── test_api.py               # API testing script
```

## 🔧 How It Works

1. **Initialization**: The bot loads your LinkedIn PDF and summary text to build context
2. **System Prompt**: Creates a comprehensive prompt that instructs the AI to act as you
3. **Chat Loop**: When a visitor asks a question:
   - The message is sent to OpenAI with full context
   - The AI can call tools (functions) to record information
   - Responses are generated naturally based on your profile
4. **Tool Calls**: 
   - `record_user_details`: Captures email and notes when visitors want to connect
   - `record_unknown_question`: Logs unanswerable questions for improvement
5. **Notifications**: Pushover sends instant alerts to your phone when leads are captured
6. **API Server**: Flask REST API serves requests from your frontend with session management

## 🔌 Integration

### Option 1: Using the REST API (Recommended)

Integrate with any frontend framework (React, Vue, Angular, vanilla JS, etc.):

```javascript
// Simple integration example
class PortfolioBotClient {
  constructor(apiUrl = 'http://localhost:5000/api') {
    this.apiUrl = apiUrl;
    this.sessionId = localStorage.getItem('bot_session') || null;
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
    localStorage.setItem('bot_session', this.sessionId);
    return data;
  }
}

// Usage
const bot = new PortfolioBotClient();
const response = await bot.sendMessage("Hello!");
console.log(response.message);
```

### Option 2: Use the HTML Starter

Open `examples/frontend-example.html` in your browser while the API is running. This file shows how to:
- Render a polished chat experience
- Persist sessions via `localStorage`
- Display typing indicators and status messages
- Call your API endpoint via `fetch`

### Customization

Edit `app.py` to:
- Modify the system prompt behavior
- Add new tools/functions
- Change the AI model
- Customize API endpoints
- Add authentication/rate limiting

### Generate Profile Summary from GitHub

Keep `me/summary.txt` in sync with your public GitHub activity using the helper script:

```bash
python scripts/github_summary.py --username <your_github_username>
```

Options:
- `--tokenEnv GITHUB_TOKEN` (or `--token <value>`) to avoid rate limits
- `--output me/summary.txt` (default) to control destination
- `--max-repos 8` to change how many highlighted repositories are listed

The script queries the GitHub REST API, summarises your repos/languages, and rewrites `me/summary.txt`, which the bot already loads on startup.

## 📦 Dependencies

- `openai` - OpenAI API client
- `pypdf` - PDF parsing for LinkedIn profile
- `requests` - HTTP requests for Pushover notifications
- `python-dotenv` - Environment variable management
- `flask` - REST API server
- `flask-cors` - Cross-origin resource sharing for API
- `apig-wsgi` - Bridges the Flask app to AWS Lambda

## 🔒 Security

- Never commit your `.env` file (it's in `.gitignore`)
- Keep your API keys secure
- The bot only shares information you've provided in your LinkedIn/summary
- All tool calls are logged for transparency
- Consider adding authentication for production API deployment
- Sessions are stored in memory (implement Redis/database for production)

## ☁️ Deploy to AWS Lambda with SAM

The existing Flask API can be deployed to AWS Lambda + API Gateway without rewriting it. The repo now includes `template.yaml`, which provisions the Lambda function and HTTP endpoint.

### 1. Prerequisites

- Install AWS CLI (`pip install awscli --upgrade`) and configure credentials: `aws configure`
- Install AWS SAM CLI: `pip install aws-sam-cli`
- (Optional) Install Docker for building in a containerized environment

### 2. Configure Secrets

The Lambda function expects secrets in AWS Secrets Manager:

| Secret | Keys | Used for |
|--------|------|----------|
| `openai-key` | `api_key` | OpenAI API key |
| `pushover-credentials` | `token`, `user` | Pushover notification credentials |

Create the secrets in the AWS console and note their ARNs.

### 3. Deploy with SAM

```bash
# From the repository root
sam build
sam deploy --guided
```

During `sam deploy` provide:
- **Stack Name**: e.g. `portfolio-bot`
- **AWS Region**: e.g. `eu-north-1`
- **OpenAISecretArn** and **PushoverSecretArn**: enter the ARNs from Secrets Manager
- Accept IAM role creation when prompted

Deployment outputs the API Gateway invoke URL, for example:

```
https://abcd1234.execute-api.eu-north-1.amazonaws.com/Prod/
```

Use that URL as the base for your frontend (`/api/chat`, `/api/info`, etc.).

### 4. Local testing

You can still run the API locally:

```bash
python app.py
```

This runs the same Flask app that Lambda invokes via `apig-wsgi`, served locally through Waitress.

## 🎨 Future Enhancements

Potential improvements:
- Build analytics/dashboard views on stored conversations
- Support multiple languages
- Add voice interaction
- Integration with CRM systems
- A/B testing for different conversation styles

## 📝 License

This project is open source and available for personal or commercial use.

## 👤 Author

Created by Borgar Flaen Stensrud

## 🤝 Contributing

Feel free to fork, improve, and submit pull requests!

## Compliance Checklist (TODO)

- Define and document chat retention and deletion policy
- Publish a privacy notice covering stored conversations
- Provide a process for data export or removal on request

## Docker (local + devnet)

1. Ensure the shared network exists (one-time): `docker network create devnet`.
2. Copy or update `.env` with your secrets. Override `DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/portfolio_bot` and set `REDIS_URL=redis://redis:6379/0` for the compose stack.
3. Build and start the stack: `docker compose up --build`.

The compose file provisions the Waitress API container, Postgres 16, and Redis 7 with health checks. All services join the external `devnet` network so they can talk to other containers on the same bridge. The API is served on `http://localhost:5000` by default.

To stop the stack: `docker compose down` (add `-v` if you want to wipe the Postgres volume).

## Monitoring & Alerting

- Logs are structured JSON on stdout; ship them with a log forwarder (filebeat, CloudWatch agent) or set `LOG_FORWARD_URL` to mirror events to a webhook.
- `/api/health` returns overall status plus database/session details. Treat a non-200 response as degraded and alert accordingly.
- Error events (`openai_error`, `pushover_error`, `message_store_write_failed`, etc.) use `log_event` and are forwarded through the webhook for alerting.

## Documentation Sign-off

Prepared and reviewed on 2025-10-23 by Borgar Flaen Stensrud (BFS Company). Content inspired by learnings from the Edward Donner course on Agentic AI @ udemy.com.
