# NEXZA AI Backend

This is a Flask backend server that powers NEXZA, an AI assistant for "Taqueria Mexicano Grill". It connects to a local LLM via LM Studio and integrates with Twilio for interactive SMS and voice conversations.

## Features

- **Interactive Voice AI**: Handles phone calls, transcribes user speech, gets AI responses, and speaks them back.
- **SMS Chatbot**: Responds to text messages using the AI.
- **Secure Webhooks**: All Twilio endpoints are validated to ensure requests are authentic.
- **Conversation History**: Remembers the context of SMS and voice conversations.
- **Modular & Configurable**: Code is split into logical files (`app`, `config`, `utils`) and configured via a `.env` file.

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd nexza-backend

can be config for general use/ios app compatible (Nexza)