"""Проверка подписи Viber-вебхука."""
import hashlib
import hmac
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app


def test_verify_viber_signature():
    os.environ["VIBER_TOKEN"] = "token123"
    body = b'{"event":"message","message":{"text":"hi"}}'
    sig = hmac.new(b"token123", body, hashlib.sha256).hexdigest()
    assert app._verify_viber_signature(sig, body) is True
    assert app._verify_viber_signature("bad", body) is False
    assert app._verify_viber_signature("", body) is False

    os.environ.pop("VIBER_TOKEN", None)
    assert app._verify_viber_signature(sig, body) is False


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Все тесты пройдены.")
