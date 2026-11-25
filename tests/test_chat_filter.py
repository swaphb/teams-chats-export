import json
import os
import tempfile
import unittest

from teams_chats_export import chat_matches, load_chat_patterns, render_all


def make_chat(chat_id, topic=None, members=()):
    return {"id": chat_id, "topic": topic, "members": [{"displayName": m} for m in members]}


class ChatFilterTests(unittest.TestCase):
    def test_no_patterns_matches_everything(self):
        self.assertTrue(chat_matches(make_chat("19:abc", "Anything"), None))
        self.assertTrue(chat_matches(make_chat("19:abc", "Anything"), []))

    def test_wildcard_matches_topic_case_insensitively(self):
        chat = make_chat("19:abc", "Project Phoenix Standup")
        self.assertTrue(chat_matches(chat, ["project phoenix*"]))
        self.assertFalse(chat_matches(chat, ["Lunch*"]))

    def test_matches_member_list_when_no_topic(self):
        chat = make_chat("19:abc", members=["Bob Jones", "Alice Smith"])
        self.assertTrue(chat_matches(chat, ["*Alice Smith*"]))

    def test_matches_chat_id(self):
        chat = make_chat("19:abc@thread.v2", "Topic")
        self.assertTrue(chat_matches(chat, ["19:abc@thread.v2"]))

    def test_exclude_wins_over_include(self):
        chat = make_chat("19:abc", "Team Lunch")
        self.assertFalse(chat_matches(chat, ["Team*", "!*Lunch*"]))
        self.assertTrue(chat_matches(make_chat("19:def", "Team Sync"), ["Team*", "!*Lunch*"]))

    def test_only_excludes_matches_everything_else(self):
        self.assertFalse(chat_matches(make_chat("19:abc", "Team Lunch"), ["!*Lunch*"]))
        self.assertTrue(chat_matches(make_chat("19:def", "Team Sync"), ["!*Lunch*"]))

    def test_load_patterns_skips_blanks_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "chats.txt")
            with open(path, "w") as f:
                f.write("# keep these\nProject*\n\n  !*Lunch*  \n")
            self.assertEqual(load_chat_patterns(path), ["Project*", "!*Lunch*"])

    def test_render_all_only_renders_matching_chats(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = os.path.join(tmp, "data")
            for chat in [make_chat("keep", "Project Phoenix"), make_chat("skip", "Team Lunch")]:
                os.makedirs(os.path.join(data_dir, chat["id"]))
                with open(os.path.join(data_dir, f"{chat['id']}.json"), "w") as f:
                    json.dump(chat, f)
            render_all(tmp, patterns=["Project*"])
            self.assertEqual(sorted(os.listdir(os.path.join(tmp, "html"))), ["index.html", "keep.html"])
