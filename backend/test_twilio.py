import os
import pytest
from unittest.mock import patch
from backend import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    # Ensure demo is enabled for most tests
    os.environ["TWILIO_DEMO_ENABLED"] = "true"
    with app.test_client() as c:
        yield c


def test_status_endpoint(client):
    """Test the /twilio/status health check endpoint."""
    r = client.get("/twilio/status")
    assert r.status_code == 200
    data = r.get_json()
    # Our status endpoint returns {"status": "ok", "demo_enabled": <bool>}
    assert data["status"] == "ok"
    assert "demo_enabled" in data


@patch("backend.twilio_routes.get_ai_response")
def test_voice_happy_path_english(mock_get_ai_response, client):
    """Happy path for /twilio/voice with an English response."""
    mock_get_ai_response.return_value = "Hello from the AI!"

    r = client.post(
        "/twilio/voice",
        data={"From": "+15551112222", "To": "+15553334444", "SpeechResult": "Hi there"}
    )

    assert r.status_code == 200
    assert r.mimetype == "text/xml"
    text = r.data.decode("utf-8")
    assert "<Response>" in text
    # Language should default to en-US for English input
    assert 'language="en-US"' in text
    assert "Hello from the AI!" in text


@patch("backend.twilio_routes.get_ai_response")
def test_voice_happy_path_spanish(mock_get_ai_response, client):
    """Happy path for /twilio/voice with a Spanish response."""
    mock_get_ai_response.return_value = "¡Hola desde la IA!"

    r = client.post(
        "/twilio/voice",
        data={"From": "+15551112222", "To": "+15553334444", "SpeechResult": "Hola, necesito ayuda"}
    )

    assert r.status_code == 200
    assert r.mimetype == "text/xml"
    text = r.data.decode("utf-8")
    assert "<Response>" in text
    # For Spanish input we expect es-MX voice language
    assert 'language="es-MX"' in text
    assert "Hola" in text  # relaxed assertion to avoid exact punctuation differences


@patch("backend.twilio_routes.get_ai_response")
def test_sms_happy_path(mock_get_ai_response, client):
    """Happy path for /twilio/sms."""
    mock_get_ai_response.return_value = "SMS response from AI."

    r = client.post(
        "/twilio/sms",
        data={"From": "+15551112222", "To": "+15553334444", "Body": "Test message"}
    )

    assert r.status_code == 200
    assert r.mimetype == "text/xml"
    text = r.data.decode("utf-8")
    assert "<Response>" in text
    assert "<Message>" in text
    assert "SMS response from AI." in text


def test_xml_escaping(client):
    """Special characters should be escaped in TwiML response."""
    with patch("backend.twilio_routes.get_ai_response") as mock_get_ai_response:
        mock_get_ai_response.return_value = '< > & \' "'

        r = client.post("/twilio/sms", data={"Body": "test"})
        text = r.data.decode("utf-8")

        # Core entities should be escaped
        assert "&lt;" in text
        assert "&gt;" in text
        assert "&amp;" in text
        # One of apostrophe encodings should appear
        assert ("&apos;" in text) or ("&#x27;" in text)
        assert "&quot;" in text


@patch("backend.twilio_routes.get_ai_response")
def test_ai_fallback_response(mock_get_ai_response, client):
    """Routes should degrade gracefully if AI throws."""
    mock_get_ai_response.side_effect = Exception("AI boom")

    r = client.post("/twilio/voice", data={"SpeechResult": "Help me"})
    # Handler should return a TwiML fallback with 200 OK for Twilio to proceed
    assert r.status_code == 200
    text = r.data.decode("utf-8")
    assert "<Say" in text
    assert "trouble" in text.lower()  # relaxed wording check


def test_demo_disabled(client):
    """Endpoints are disabled when the feature flag is off."""
    os.environ["TWILIO_DEMO_ENABLED"] = "false"

    r_voice = client.post("/twilio/voice", data={"SpeechResult": "test"})
    r_sms = client.post("/twilio/sms", data={"Body": "test"})

    # Our routes return 503 with a simple body when disabled
    assert r_voice.status_code == 503
    assert r_sms.status_code == 503
    assert "Feature disabled" in r_voice.get_data(as_text=True)
    assert "Feature disabled" in r_sms.get_data(as_text=True)

    # Reset for other tests (not strictly necessary in isolated runs)
    os.environ["TWILIO_DEMO_ENABLED"] = "true"