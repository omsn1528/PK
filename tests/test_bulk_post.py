"""Tests for bulk posting of selected clips using previous default upload settings."""
import os
import sys
import unittest
import time
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from studio import config, accounts, posting, scheduler, jobs, ctx, server
from fastapi.testclient import TestClient


class TestBulkPost(unittest.TestCase):
    def setUp(self):
        self.tmp_data = config.DATA_DIR / "test_bulk_post_data"
        self.tmp_data.mkdir(parents=True, exist_ok=True)
        posting._posts = []
        posting.OPEN = ("queued", "uploading", "scheduled", "uploaded_scheduled", "uploaded_private")

    def tearDown(self):
        posting._posts = []

    def test_bulk_post_default_scheduling(self):
        """Verify selected clips are queued with consecutive 12-slot IST schedules."""
        with ctx.as_user("u_test"):
            # Mock accounts
            mock_acc = {"id": "acc_yt", "platform": "youtube", "name": "My Channel"}
            with patch.object(accounts, "list_accounts", return_value=[mock_acc]), \
                 patch.object(accounts, "get", return_value=mock_acc):
                # Create test job and clips
                job_id = "job_test_1"
                clip1 = {"id": "c1", "status": "done", "duration": 30, "title": "Great Gaming Clutch", "hook": "INSANE PLAY"}
                clip2 = {"id": "c2", "status": "done", "duration": 45, "title": "Epic Boss Defeated", "hook": "UNBELIEVABLE FINISH"}
                test_job = {
                    "id": job_id, "user": "u_test", "creator": "cr_test", "clips": [clip1, clip2],
                    "options": {"upload_mode": "scheduling"}, "dir": str(self.tmp_data)
                }

                with patch.object(jobs, "get", return_value=test_job):
                    res = posting.bulk_post([(job_id, "c1"), (job_id, "c2")])
                    self.assertEqual(res["queued"], 2)
                    self.assertEqual(res["clips"], 2)
                    self.assertEqual(res["skipped"], 0)

                    posts = posting._posts
                    self.assertEqual(len(posts), 2)
                    p1 = posts[0]
                    p2 = posts[1]
                    self.assertEqual(p1["clip"], "c1")
                    self.assertEqual(p2["clip"], "c2")
                    self.assertEqual(p1["platform"], "youtube")
                    self.assertEqual(p2["platform"], "youtube")
                    self.assertEqual(p1["schedule_mode"], "scheduling")
                    self.assertEqual(p2["schedule_mode"], "scheduling")
                    self.assertEqual(p1["visibility"], "private")
                    self.assertEqual(p2["visibility"], "private")

                    # Consecutive slots: publish_at_utc must be different
                    self.assertIsNotNone(p1["publish_at_utc"])
                    self.assertIsNotNone(p2["publish_at_utc"])
                    self.assertNotEqual(p1["publish_at_utc"], p2["publish_at_utc"])
                    print("PASS: test_bulk_post_default_scheduling (consecutive slots assigned)")

    def test_bulk_post_skips_clickbait_and_duplicates(self):
        """Verify bulk post ignores clickbait and duplicate clips."""
        with ctx.as_user("u_test"):
            mock_acc = {"id": "acc_yt", "platform": "youtube", "name": "My Channel"}
            with patch.object(accounts, "list_accounts", return_value=[mock_acc]), \
                 patch.object(accounts, "get", return_value=mock_acc):
                job_id = "job_test_2"
                clip_ok = {"id": "c_ok", "status": "done", "duration": 25, "title": "Speed Funny Goal", "hook": "GOAL SPEED"}
                clip_banned = {"id": "c_bad", "status": "done", "duration": 25, "title": "Loud moment in game", "hook": "WAIT FOR IT"}
                test_job = {
                    "id": job_id, "user": "u_test", "creator": "", "clips": [clip_ok, clip_banned],
                    "options": {"upload_mode": "scheduling"}, "dir": str(self.tmp_data)
                }

                with patch.object(jobs, "get", return_value=test_job):
                    # First run: clip_ok should be queued, clip_banned skipped
                    res1 = posting.bulk_post([(job_id, "c_ok"), (job_id, "c_bad")])
                    self.assertEqual(res1["queued"], 1)
                    self.assertEqual(res1["clips"], 1)
                    self.assertEqual(res1["skipped"], 1)

                    # Second run: duplicate clip_ok should be skipped
                    res2 = posting.bulk_post([(job_id, "c_ok")])
                    self.assertEqual(res2["queued"], 0)
                    self.assertEqual(res2["skipped"], 1)
                    print("PASS: test_bulk_post_skips_clickbait_and_duplicates")

    def test_api_bulk_post_endpoint(self):
        """Verify POST /api/bulk/post FastAPI endpoint."""
        client = TestClient(server.app, base_url="http://127.0.0.1:8765")
        mock_acc = {"id": "acc_yt", "platform": "youtube", "name": "My Channel"}
        job_id = "job_test_api"
        clip1 = {"id": "c_api", "status": "done", "duration": 20, "title": "Amazing Trick", "hook": "LOOK AT THIS"}
        test_job = {
            "id": job_id, "user": "u_local", "creator": "", "clips": [clip1],
            "options": {"upload_mode": "scheduling"}, "dir": str(self.tmp_data)
        }

        headers = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
        with patch.object(accounts, "list_accounts", return_value=[mock_acc]), \
             patch.object(accounts, "get", return_value=mock_acc), \
             patch.object(jobs, "get", return_value=test_job):
            response = client.post("/api/bulk/post", json={"clips": [f"{job_id}.c_api"]}, headers=headers)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["queued"], 1)
            self.assertEqual(data["clips"], 1)
            print("PASS: test_api_bulk_post_endpoint")


if __name__ == "__main__":
    unittest.main()
