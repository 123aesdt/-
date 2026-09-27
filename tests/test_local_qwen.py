import unittest
from types import SimpleNamespace
from unittest.mock import patch

import llm


class FakeAvatarSession:
    def __init__(self):
        self.opt = SimpleNamespace(llm_provider="local_qwen", llm_model="/models/qwen")
        self.messages = []

    def put_msg_txt(self, text, datainfo):
        self.messages.append((text, datainfo))


class LocalQwenTests(unittest.TestCase):
    def test_local_qwen_answer_is_forwarded_to_avatar(self):
        avatar = FakeAvatarSession()

        with patch("llm._generate_local_qwen", return_value="这是模型生成的回答", create=True):
            llm.llm_response("这是一个问题", avatar, {"source": "test"})

        self.assertEqual(
            avatar.messages,
            [("这是模型生成的回答", {"source": "test"})],
        )


if __name__ == "__main__":
    unittest.main()
