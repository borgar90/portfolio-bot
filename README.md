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

## 📋 Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Pushover account (for notifications)
- Your LinkedIn profile exported as PDF
- A brief personal summary

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
API_PORT=5000              # API server port (default: 5000)
MODE=both                  # Run mode: "api", "gradio", or "both" (default: both)
```

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

- Default port: `5000` (override with `API_PORT` environment variable)
- Base URL: `http://localhost:5000`

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
```

### Available Endpoints

- `GET /api/health` - Check API status
- `POST /api/chat` - Send a message and get response
- `GET /api/session/{id}` - Get conversation history
- `DELETE /api/session/{id}` - Clear session
- `GET /api/info` - Get bot information

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

This uses the same Flask app that Lambda invokes via `apig-wsgi`.

## 🎨 Future Enhancements

Potential improvements:
- Add database for storing conversations
- Implement analytics dashboard
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
