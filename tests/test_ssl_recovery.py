"""Test download resilience and retry mechanisms on network / SSL drops."""
import sys
sys.path.insert(0, ".")

from unittest.mock import MagicMock, patch
from studio import media


def check(name, got, expected=True):
    if got != expected:
        raise AssertionError(f"FAIL: {name} (expected {expected!r}, got {got!r})")
    print(f"  OK: {name}")


# 1. Test resilient download retries on SSL error and recovers
attempts = []


class FakeYDL:
    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def download(self, urls):
        attempts.append(dict(self.opts))
        if len(attempts) == 1:
            raise RuntimeError("ERROR: [download] Got error: [SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]")
        # Succeeded on attempt 2


with patch.object(media, "_ydl", side_effect=lambda opts: FakeYDL(opts)):
    media._download_resilient("https://www.youtube.com/watch?v=dummy", {"format": "best"}, max_tries=3)

check("Download retried after initial SSL failure", len(attempts) == 2)
check("First attempt had concurrent fragment downloads", attempts[0].get("concurrent_fragment_downloads", 2) == 2)
check("Retry fell back to 1 fragment download to prevent SSL collisions", attempts[1]["concurrent_fragment_downloads"] == 1)

print("\nSSL recovery tests passed successfully!")
