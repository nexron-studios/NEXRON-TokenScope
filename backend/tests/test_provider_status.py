from __future__ import annotations

import unittest

from app.providers.base import status_from_http


class StatusFromHttpTests(unittest.TestCase):
    def test_a_forbidden_html_page_is_reported_as_a_block(self) -> None:
        status, message = status_from_http(403, content_type="text/html; charset=utf-8")

        self.assertEqual(status, "unreachable")
        self.assertIn("blockiert", message)

    def test_a_forbidden_json_answer_still_blames_the_token(self) -> None:
        status, message = status_from_http(403, content_type="application/json")

        self.assertEqual(status, "unauthorized")
        self.assertIn("neu anmelden", message)

    def test_an_unknown_content_type_keeps_the_previous_verdict(self) -> None:
        status, _ = status_from_http(401)

        self.assertEqual(status, "unauthorized")


if __name__ == "__main__":
    unittest.main()
