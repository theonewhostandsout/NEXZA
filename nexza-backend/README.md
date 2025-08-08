# NEXZA Backend

## Overview
The NEXZA Backend is a Flask-based API server powering the NEXZA AI Assistant platform. 
It handles AI query processing, file management, and communication with external APIs (such as Twilio). 
Designed for modularity and speed, it can be deployed locally or in the cloud.

## Features
- **AI Query Processing**: Integrates with large language models (local or API-based).
- **Document Search**: Supports retrieval-augmented generation (RAG) for contextual answers.
- **Telephony Integration**: Works with Twilio for SMS and call handling.
- **Configurable**: Environment variables stored securely in `.env`.

## Requirements
- Python 3.11+
- See `requirements.txt` for dependencies.

## Setup
1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/nexza-backend.git
    cd nexza-backend
    ```
2. Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    venv\Scripts\activate   # Windows
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Create a `.env` file based on `.env.example` and populate your API keys.

5. Run the application:
    ```bash
    flask run
    ```

## Project Structure
- `app.py` - Entry point for the backend.
- `config.py` - Configuration management.
- `utils.py` - Utility functions.
- `filesystem_manager.py` - File storage and retrieval logic.
- `requirements.txt` - Python dependencies.

## Security
All secrets should be placed in `.env`. Never commit your `.env` file.

## License
MIT License
