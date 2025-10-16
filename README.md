# Portfolio Bot

An intelligent AI-powered chatbot that represents you on your portfolio website. This bot uses OpenAI's GPT-4o-mini to engage with visitors, answer questions about your background, skills, and experience, and capture leads.

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

### User-Friendly Interface
- Built with Gradio for a clean, modern chat interface
- Easy to embed in any website
- Mobile-responsive design

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
OPENAI_API_KEY=your_openai_api_key_here
PUSHOVER_TOKEN=your_pushover_app_token
PUSHOVER_USER=your_pushover_user_key
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

The chatbot will launch in your browser at `http://localhost:7860`

## 📁 Project Structure

```
portfolio-bot/
├── app.py              # Main application with AI logic
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
├── .gitignore         # Git ignore rules
├── me/
│   ├── linkedin.pdf   # Your LinkedIn profile
│   └── summary.txt    # Personal summary
└── README.md          # This file
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

## 🔌 Integration

### Embedding in Your Website

The Gradio interface can be embedded in any website using an iframe or you can use the Gradio API to build a custom frontend.

### Customization

Edit `app.py` to:
- Modify the system prompt behavior
- Add new tools/functions
- Change the AI model
- Customize the chat interface theme

## 📦 Dependencies

- `openai` - OpenAI API client
- `gradio` - Web UI framework
- `pypdf` - PDF parsing for LinkedIn profile
- `requests` - HTTP requests for Pushover
- `python-dotenv` - Environment variable management

## 🔒 Security

- Never commit your `.env` file (it's in `.gitignore`)
- Keep your API keys secure
- The bot only shares information you've provided in your LinkedIn/summary
- All tool calls are logged for transparency

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
