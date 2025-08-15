import pytest
from flask import Flask
from backend.twilio_routes import twilio_bp

@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(twilio_bp)
    with app.test_client() as c:
        yield c

def test_sms_ok(client):
    r = client.post("/sms", data={"From": "+15555550123", "Body": "hello"})
    assert r.status_code == 200
    assert b"<Response>" in r.data

def test_voice_ok(client):
    r = client.post("/voice", data={"From": "+15555550123", "SpeechResult": "hello"})
    assert r.status_code == 200
    assert b"<Response>" in r.data
