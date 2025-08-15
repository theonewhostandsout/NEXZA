import pytest
from flask import Flask
from backend.twilio_routes import twilio_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(twilio_bp, url_prefix="/twilio")
    return app

@pytest.fixture
def client():
    app = create_app()
    with app.test_client() as client:
        yield client

def test_twilio_voice(client):
    resp = client.post('/twilio/voice', data={'SpeechResult': 'hello'})
    assert b'<Response><Say>' in resp.data

def test_twilio_sms(client):
    resp = client.post('/twilio/sms', data={'Body': 'hi'})
    assert resp.data.strip() != b''
