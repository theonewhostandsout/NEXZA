import pytest
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c

def test_sms_ok(client):
    r = client.post("/sms", data={"From": "+15555550123", "Body": "hello"})
    assert r.status_code == 200
    assert b"<Response>" in r.data

def test_voice_ok(client):
    r = client.post("/voice", data={"From": "+15555550123", "SpeechResult": "hello"})
    assert r.status_code == 200
    assert b"<Response>" in r.data
