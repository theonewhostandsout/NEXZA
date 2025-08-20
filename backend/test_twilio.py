import pytest
import os
from unittest.mock import patch
from backend import app

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    app.config["TWILIO_DEMO_ENABLED"] = "true"
    app.config["TWILIO_VALIDATE_SIGNATURE"] = False # Disable validation for tests
    os.environ["TWILIO_DEMO_ENABLED"] = "true"

    with app.test_client() as client:
        yield client

def test_status_endpoint(client):
    """Test the /twilio/status health check endpoint."""
    response = client.get("/twilio/status")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "ok"
    assert "Twilio demo is running" in json_data["message"]

@patch('backend.twilio_routes.get_ai_response')
def test_voice_happy_path_english(mock_get_ai_response, client):
    """Test the happy path for /twilio/voice with an English response."""
    mock_get_ai_response.return_value = ("Hello from the AI!", "en")

    response = client.post("/twilio/voice", data={
        "From": "+15551112222",
        "To": "+15553334444",
        "SpeechResult": "Hi there"
    })

    assert response.status_code == 200
    assert response.mimetype == "text/xml"
    response_text = response.data.decode('utf-8')
    assert '<Response>' in response_text
    assert '<Say voice="en-US">' in response_text
    assert 'Hello from the AI!' in response_text

@patch('backend.twilio_routes.get_ai_response')
def test_voice_happy_path_spanish(mock_get_ai_response, client):
    """Test the happy path for /twilio/voice with a Spanish response."""
    mock_get_ai_response.return_value = ("Hola desde la IA!", "es")

    response = client.post("/twilio/voice", data={
        "From": "+15551112222",
        "To": "+15553334444",
        "SpeechResult": "Hola"
    })

    assert response.status_code == 200
    assert response.mimetype == "text/xml"
    response_text = response.data.decode('utf-8')
    assert '<Response>' in response_text
    assert '<Say voice="es-MX">' in response_text
    assert 'Hola desde la IA!' in response_text

@patch('backend.twilio_routes.get_ai_response')
def test_sms_happy_path(mock_get_ai_response, client):
    """Test the happy path for /twilio/sms."""
    mock_get_ai_response.return_value = ("SMS response from AI.", "en")

    response = client.post("/twilio/sms", data={
        "From": "+15551112222",
        "To": "+15553334444",
        "Body": "Test message"
    })

    assert response.status_code == 200
    assert response.mimetype == "text/xml"
    response_text = response.data.decode('utf-8')
    assert '<Response>' in response_text
    assert '<Message>' in response_text
    assert 'SMS response from AI.' in response_text

def test_xml_escaping(client):
    """Test if special characters are properly escaped in TwiML response."""
    with patch('backend.twilio_routes.get_ai_response') as mock_get_ai_response:
        mock_get_ai_response.return_value = ("< > & ' \"", "en")

        response = client.post("/twilio/sms", data={"Body": "test"})
        response_text = response.data.decode('utf-8')

        assert '&lt; &gt; &amp; &#x27; &quot;' in response_text

@patch('backend.twilio_routes.get_ai_response')
def test_ai_fallback_response(mock_get_ai_response, client):
    """Test if the fallback response is used when the AI fails."""
    # Simulate an exception in the AI client
    mock_get_ai_response.side_effect = Exception("AI go boom")

    response = client.post("/twilio/voice", data={"SpeechResult": "Help me"})

    assert response.status_code == 200 # The error handler should catch the exception and return 200 OK for Twilio
    response_text = response.data.decode('utf-8')
    # Check that the generic fallback message is in the response
    assert "Sorry, I&#x27;m having trouble connecting right now. Please call back later." in response_text

def test_language_detection():
    """Test the language detection utility function."""
    from backend.ai_client import detect_language
    assert detect_language("hola, cómo estás?") == "es"
    assert detect_language("hello, how are you?") == "en"
    assert detect_language("This is a test.") == "en"
    assert detect_language("Me gustaría un coche nuevo.") == "es"
    assert detect_language("") == "en" # Empty string should default to English
    assert detect_language(None) == "en" # None should default to English

def test_demo_disabled(client):
    """Test that the endpoints are disabled when the feature flag is off."""
    os.environ["TWILIO_DEMO_ENABLED"] = "false"

    voice_response = client.post("/twilio/voice", data={"SpeechResult": "test"})
    assert "This feature is not enabled." in voice_response.data.decode('utf-8')

    sms_response = client.post("/twilio/sms", data={"Body": "test"})
    assert "This feature is not enabled." in sms_response.data.decode('utf-8')

    # Reset the env var
    os.environ["TWILIO_DEMO_ENABLED"] = "true"
