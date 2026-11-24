import unittest

from teams_chats_export import get_jinja_env, render_message_body


class HtmlSecurityTests(unittest.TestCase):
    def render_body(self, content, attachments=None):
        return str(render_message_body(
            {"body": {"content": content}, "attachments": attachments or []}, "", ""
        ))

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


if __name__ == '__main__':
    unittest.main()
