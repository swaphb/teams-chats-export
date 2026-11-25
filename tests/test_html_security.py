import json
import os
import tempfile
import unittest

from teams_chats_export import get_hosted_content_filename, get_jinja_env, render_message_body


class HtmlSecurityTests(unittest.TestCase):
    def render_body(self, content, attachments=None, chat_dir="", remote_images=False):
        return str(render_message_body(
            {"id": "m1", "body": {"content": content}, "attachments": attachments or []}, chat_dir, "", remote_images
        ))

    def write_hosted_content(self, chat_dir, hosted_content_id, data):
        with open(os.path.join(chat_dir, get_hosted_content_filename("m1", hosted_content_id)), "wb") as f:
            f.write(data)

    def test_message_html_is_sanitized_but_formatting_survives(self):
        result = self.render_body('<p><strong>Hello</strong><img src="x" onerror="alert(1)"><a href="javascript:alert(1)">link</a><script>alert(1)</script></p>')
        self.assertIn('<strong>Hello</strong>', result)
        self.assertNotIn('onerror', result)
        self.assertNotIn('javascript:', result)
        self.assertNotIn('<script', result)

    def test_attachment_fields_are_escaped(self):
        attachment = {"id": "1", "contentType": "reference", "contentUrl": "javascript:alert(1)", "name": "<img src=x onerror=alert(1)>"}
        result = self.render_body('<attachment id="1"></attachment>', [attachment])
        self.assertNotIn('href=', result)
        self.assertIn('&lt;img', result)
        self.assertNotIn('<img', result)

    def test_template_escapes_chat_metadata(self):
        result = get_jinja_env().get_template('index.jinja').render(chats=[{"filename": "chat.html", "chat_name": "<script>alert(1)</script>"}])
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('<script>', result)

    def test_safe_links_and_embedded_images_survive(self):
        result = self.render_body('<p><a href="https://example.org/">link</a><img src="data:image/png;base64,YQ=="></p>')
        self.assertIn('href="https://example.org/"', result)
        self.assertIn('src="data:image/png;base64,YQ=="', result)

    def test_extra_formatting_survives(self):
        result = self.render_body('<h2>Title</h2><hr><p>x<sup>2</sup><strike>old</strike></p>')
        self.assertIn('<h2>Title</h2>', result)
        self.assertIn('<hr>', result)
        self.assertIn('<sup>2</sup>', result)
        self.assertIn('<strike>old</strike>', result)

    def test_remote_images_are_linked_by_default(self):
        result = self.render_body('<p><img alt="cat <b>gif</b>" src="https://example.org/a.gif?x=1&amp;y=2" width="40"></p>')
        self.assertNotIn('<img', result)
        self.assertIn('<a href="https://example.org/a.gif?x=1&amp;y=2">Image: cat &lt;b&gt;gif&lt;/b&gt;</a>', result)

    def test_remote_images_load_when_enabled(self):
        result = self.render_body('<p><img src="https://example.org/a.gif" width="40" height="bad"></p>', remote_images=True)
        self.assertIn('src="https://example.org/a.gif"', result)
        self.assertIn('width="40"', result)
        self.assertNotIn('height=', result)

    def test_graph_hosted_image_is_embedded(self):
        with tempfile.TemporaryDirectory() as chat_dir:
            self.write_hosted_content(chat_dir, "hc1", b"a")
            url = "https://graph.microsoft.com/v1.0/chats/c1/messages/m1/hostedContents/hc1/$value"
            result = self.render_body(f'<p><img src="{url}" alt="pic"></p>', chat_dir=chat_dir)
        self.assertIn('src="data:image/png;base64,YQ=="', result)
        self.assertIn('data-hosted-content-id="hc1"', result)
        self.assertNotIn('graph.microsoft.com', result)

    def test_code_snippet_content_is_escaped(self):
        hosted_content_id = "hc2"
        content = {"codeSnippetUrl": f"https://graph.microsoft.com/v1.0/chats/c1/messages/m1/hostedContents/{hosted_content_id}/$value"}
        attachment = {"id": "1", "contentType": "application/vnd.microsoft.card.codesnippet", "content": json.dumps(content)}
        with tempfile.TemporaryDirectory() as chat_dir:
            self.write_hosted_content(chat_dir, hosted_content_id, b"<script>alert(1)</script>")
            result = self.render_body('<attachment id="1"></attachment>', [attachment], chat_dir)
        self.assertIn('<pre><code>&lt;script&gt;alert(1)&lt;/script&gt;</code></pre>', result)
        self.assertNotIn('<script', result)

    def test_message_reference_fields_are_escaped(self):
        ref = {"messageSender": {"user": {"displayName": "<b>Eve</b>"}}, "messagePreview": "<img src=x onerror=alert(1)>"}
        attachment = {"id": "1", "contentType": "messageReference", "content": json.dumps(ref)}
        result = self.render_body('<attachment id="1"></attachment>', [attachment])
        self.assertIn('<blockquote class="message-reference"', result)
        self.assertIn('&lt;b&gt;Eve&lt;/b&gt;', result)
        self.assertNotIn('<img', result)

    def test_chat_template_escapes_metadata(self):
        payload = "<script>alert(1)</script>"
        chat = {"id": "c1", "topic": payload, "chatType": payload}
        messages = [
            {"obj": {"id": "1", "from": {"user": {"displayName": payload}}, "createdDateTime": payload}, "content": None, "createdDateTime": 0},
            {"obj": {"id": "2", "eventDetail": {"@odata.type": payload}, "createdDateTime": ""}, "content": None, "createdDateTime": 0},
        ]
        result = get_jinja_env().get_template('chat.jinja').render(chat=chat, messages=messages, member_list_str=payload)
        self.assertNotIn(payload, result)
        self.assertEqual(result.count('&lt;script&gt;'), 7)


if __name__ == '__main__':
    unittest.main()
