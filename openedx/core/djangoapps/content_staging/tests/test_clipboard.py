"""
Tests for the clipboard functionality
"""
from textwrap import dedent
from xml.etree import ElementTree

from rest_framework.test import APIClient
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from xmodule.modulestore.tests.factories import ToyCourseFactory


CLIPBOARD_ENDPOINT = "/api/content-staging/v1/clipboard/"


class ClipboardTestCase(ModuleStoreTestCase):
    """
    Test Clipboard functionality
    """

    def test_empty_clipboard(self):
        """
        When a user has no content on their clipboard, we get an empty 200 response
        """
        client = APIClient()
        client.login(username=self.user.username, password=self.user_password)
        response = client.get(CLIPBOARD_ENDPOINT)
        # We don't consider this a 404 error, it's a 200 with an empty response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "content": None,
            "source_usage_key": "",
            "source_context_title": ""
        })

    def _setup_course(self):
        """ Set up the "Toy Course" and an APIClient for testing clipboard functionality. """
        # Setup:
        course_key = ToyCourseFactory.create().id  # See xmodule/modulestore/tests/sample_courses.py
        client = APIClient()
        client.login(username=self.user.username, password=self.user_password)

        # Initial conditions: clipboard is empty:
        response = client.get(CLIPBOARD_ENDPOINT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content"], None)

        return (course_key, client)

    def test_copy_video(self):
        """
        Test copying a video from the course
        """
        course_key, client = self._setup_course()

        # Copy the video
        video_key = course_key.make_usage_key("video", "sample_video")
        response = client.post(CLIPBOARD_ENDPOINT, {"usage_key": str(video_key)}, format="json")

        # Validate the response:
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["source_usage_key"], str(video_key))
        self.assertEqual(response_data["source_context_title"], "Toy Course")
        self.assertEqual(response_data["content"], {**response_data["content"], **{
            "block_type": "video",
            # To ensure API stability, we are hard-coding these expected values:
            "purpose": "clipboard",
            "status": "ready",
            "display_name": "default",  # Weird name but that's what defined in the toy course
        }})
        # Test the actual OLX in the clipboard:
        olx_url = response_data["content"]["olx_url"]
        olx_response = client.get(olx_url)
        self.assertEqual(olx_response.status_code, 200)
        self.assertEqual(olx_response.get("Content-Type"), "application/vnd.openedx.xblock.v1.video+xml")
        self.assertXmlEqual(
            olx_response.content.decode(),
            """
            <video
                url_name="sample_video"
                display_name="default"
                youtube="0.75:JMD_ifUUfsU,1.00:OEoXaMPEzfM,1.25:AKqURZnYqpk,1.50:DYpADpL7jAY"
                youtube_id_0_75="JMD_ifUUfsU"
                youtube_id_1_0="OEoXaMPEzfM"
                youtube_id_1_25="AKqURZnYqpk"
                youtube_id_1_5="DYpADpL7jAY"
            />
            """
        )

        # Now if we GET the clipboard again, the GET response should exactly equal the last POST response:
        self.assertEqual(client.get(CLIPBOARD_ENDPOINT).json(), response_data)

    def test_copy_html(self):
        """
        Test copying an HTML from the course
        """
        course_key, client = self._setup_course()

        # Copy the video
        html_key = course_key.make_usage_key("html", "toyhtml")
        response = client.post(CLIPBOARD_ENDPOINT, {"usage_key": str(html_key)}, format="json")

        # Validate the response:
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["source_usage_key"], str(html_key))
        self.assertEqual(response_data["source_context_title"], "Toy Course")
        self.assertEqual(response_data["content"], {**response_data["content"], **{
            "block_type": "html",
            # To ensure API stability, we are hard-coding these expected values:
            "purpose": "clipboard",
            "status": "ready",
            "display_name": "Text",  # Has no display_name set so we fallback to this default
        }})
        # Test the actual OLX in the clipboard:
        olx_url = response_data["content"]["olx_url"]
        olx_response = client.get(olx_url)
        self.assertEqual(olx_response.status_code, 200)
        self.assertEqual(olx_response.get("Content-Type"), "application/vnd.openedx.xblock.v1.html+xml")
        # For HTML, we really want to be sure that the OLX is serialized in this exact format (using CDATA), so we check
        # the actual string directly rather than using assertXmlEqual():
        self.assertEqual(olx_response.content.decode(), dedent("""
            <html url_name="toyhtml" display_name="Text"><![CDATA[
            <a href='/static/handouts/sample_handout.txt'>Sample</a>
            ]]></html>
        """).lstrip())

        # Now if we GET the clipboard again, the GET response should exactly equal the last POST response:
        self.assertEqual(client.get(CLIPBOARD_ENDPOINT).json(), response_data)

    def test_copy_several_things(self):
        """
        Test that the clipboard only holds one thing at a time.
        """
        course_key, client = self._setup_course()

        # Copy the video and validate the response:
        video_key = course_key.make_usage_key("video", "sample_video")
        response = client.post(CLIPBOARD_ENDPOINT, {"usage_key": str(video_key)}, format="json")
        self.assertEqual(response.status_code, 200)
        video_clip_data = response.json()
        self.assertEqual(video_clip_data["source_usage_key"], str(video_key))
        self.assertEqual(video_clip_data["content"]["block_type"], "video")
        old_olx_url = video_clip_data["content"]["olx_url"]
        self.assertEqual(client.get(old_olx_url).status_code, 200)

        # Now copy some HTML:
        html_key = course_key.make_usage_key("html", "toyhtml")
        response = client.post(CLIPBOARD_ENDPOINT, {"usage_key": str(html_key)}, format="json")
        self.assertEqual(response.status_code, 200)

        # Now check the clipboard:
        response = client.get(CLIPBOARD_ENDPOINT)
        html_clip_data = response.json()
        self.assertEqual(html_clip_data["source_usage_key"], str(html_key))
        self.assertEqual(html_clip_data["content"]["block_type"], "html")

        # The OLX link from the video will no longer work:
        self.assertEqual(client.get(old_olx_url).status_code, 404)

    def test_no_course_permission(self):
        """
        Test that a user without read access cannot copy items in a course
        """
        course_key = ToyCourseFactory.create().id
        nonstaff_client = APIClient()
        nonstaff_username, nonstaff_password = self.create_non_staff_user()
        nonstaff_client.login(username=nonstaff_username, password=nonstaff_password)

        # Try copying the video as a non-staff user:
        html_key = course_key.make_usage_key("html", "toyhtml")
        with self.allow_transaction_exception():
            response = nonstaff_client.post(CLIPBOARD_ENDPOINT, {"usage_key": str(html_key)}, format="json")
            self.assertEqual(response.status_code, 403)
        response = nonstaff_client.get(CLIPBOARD_ENDPOINT)
        self.assertEqual(response.json()["content"], None)

    def test_no_stealing_clipboard_content(self):
        """
        Test that a user cannot see another user's clipboard
        """
        course_key, client = self._setup_course()
        nonstaff_client = APIClient()
        nonstaff_username, nonstaff_password = self.create_non_staff_user()
        nonstaff_client.login(username=nonstaff_username, password=nonstaff_password)

        # The regular user copies something to their clipboard:
        html_key = course_key.make_usage_key("html", "toyhtml")
        response = client.post(CLIPBOARD_ENDPOINT, {"usage_key": str(html_key)}, format="json")
        # Then another user tries to get the OLX:
        olx_url = response.json()["content"]["olx_url"]
        response = nonstaff_client.get(olx_url)
        self.assertEqual(response.status_code, 403)

    def assertXmlEqual(self, xml_str_a: str, xml_str_b: str) -> bool:
        """ Assert that the given XML strings are equal, ignoring attribute order and some whitespace variations. """
        self.assertEqual(ElementTree.canonicalize(xml_str_a), ElementTree.canonicalize(xml_str_b))
