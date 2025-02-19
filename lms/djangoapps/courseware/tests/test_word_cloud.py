"""Word cloud integration tests using mongo modulestore."""


import pytest

import json
from operator import itemgetter

# noinspection PyUnresolvedReferences
from xmodule.tests.helpers import override_descriptor_system  # pylint: disable=unused-import
from xmodule.x_module import STUDENT_VIEW

from .helpers import BaseTestXmodule


@pytest.mark.usefixtures("override_descriptor_system")
class TestWordCloud(BaseTestXmodule):
    """Integration test for Word Cloud Block."""
    CATEGORY = "word_cloud"

    def _get_resource_url(self, item):
        """
        Creates a resource URL for a given asset that is compatible with this old XModule testing stuff.
        """
        display_name = self.item_descriptor.display_name.replace(' ', '_')
        return "resource/i4x://{}/{}/word_cloud/{}/{}".format(
            self.course.id.org, self.course.id.course, display_name, item
        )

    def _get_users_state(self):
        """Return current state for each user:

        {username: json_state}
        """
        # check word cloud response for every user
        users_state = {}

        for user in self.users:
            response = self.clients[user.username].post(self.get_url('get_state'))
            users_state[user.username] = json.loads(response.content.decode('utf-8'))

        return users_state

    def _post_words(self, words):
        """Post `words` and return current state for each user:

        {username: json_state}
        """
        users_state = {}

        for user in self.users:
            response = self.clients[user.username].post(
                self.get_url('submit'),
                {'student_words[]': words},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            users_state[user.username] = json.loads(response.content.decode('utf-8'))

        return users_state

    def _check_response(self, response_contents, correct_jsons):
        """Utility function that compares correct and real responses."""
        for username, content in response_contents.items():

            # Used in debugger for comparing objects.
            # self.maxDiff = None

            # We should compare top_words for manually,
            # because they are unsorted.
            keys_to_compare = set(content.keys()).difference({'top_words'})
            self.assertDictEqual(
                {k: content[k] for k in keys_to_compare},
                {k: correct_jsons[username][k] for k in keys_to_compare})

            # comparing top_words:
            top_words_content = sorted(
                content['top_words'],
                key=itemgetter('text')
            )
            top_words_correct = sorted(
                correct_jsons[username]['top_words'],
                key=itemgetter('text')
            )
            self.assertListEqual(top_words_content, top_words_correct)

    def test_initial_state(self):
        """Inital state of word cloud is correct. Those state that
        is sended from server to frontend, when students load word
        cloud page.
        """
        users_state = self._get_users_state()

        assert ''.join({content['status'] for (_, content) in users_state.items()}) == 'success'

        # correct initial data:
        correct_initial_data = {
            'status': 'success',
            'student_words': {},
            'total_count': 0,
            'submitted': False,
            'top_words': {},
            'display_student_percents': False
        }

        for _, response_content in users_state.items():
            assert response_content == correct_initial_data

    def test_post_words(self):
        """Students can submit data succesfully.
        Word cloud data properly updates after students submit.
        """
        input_words = [
            "small",
            "BIG",
            " Spaced ",
            " few words",
        ]

        correct_words = [
            "small",
            "big",
            "spaced",
            "few words",
        ]

        users_state = self._post_words(input_words)

        assert ''.join({content['status'] for (_, content) in users_state.items()}) == 'success'

        correct_state = {}
        for index, user in enumerate(self.users):

            correct_state[user.username] = {
                'status': 'success',
                'submitted': True,
                'display_student_percents': True,
                'student_words': {word: 1 + index for word in correct_words},
                'total_count': len(input_words) * (1 + index),
                'top_words': [
                    {
                        'text': word, 'percent': 100 / len(input_words),
                        'size': (1 + index)
                    }
                    for word in correct_words
                ]
            }

        self._check_response(users_state, correct_state)

    def test_collective_users_submits(self):
        """Test word cloud data flow per single and collective users submits.

            Make sures that:

            1. Inital state of word cloud is correct. Those state that
            is sended from server to frontend, when students load word
            cloud page.

            2. Students can submit data succesfully.

            3. Next submits produce "already voted" error. Next submits for user
            are not allowed by user interface, but techically it possible, and
            word_cloud should properly react.

            4. State of word cloud after #3 is still as after #2.
        """

        # 1.
        users_state = self._get_users_state()

        assert ''.join({content['status'] for (_, content) in users_state.items()}) == 'success'

        # 2.
        # Invcemental state per user.
        users_state_after_post = self._post_words(['word1', 'word2'])

        assert ''.join({content['status'] for (_, content) in users_state_after_post.items()}) == 'success'

        # Final state after all posts.
        users_state_before_fail = self._get_users_state()

        # 3.
        users_state_after_post = self._post_words(
            ['word1', 'word2', 'word3'])

        assert ''.join({content['status'] for (_, content) in users_state_after_post.items()}) == 'fail'

        # 4.
        current_users_state = self._get_users_state()
        self._check_response(users_state_before_fail, current_users_state)

    def test_unicode(self):
        input_words = [" this is unicode Юникод"]
        correct_words = ["this is unicode юникод"]

        users_state = self._post_words(input_words)

        assert ''.join({content['status'] for (_, content) in users_state.items()}) == 'success'

        for user in self.users:
            self.assertListEqual(
                list(users_state[user.username]['student_words'].keys()),
                correct_words)

    def test_handle_ajax_incorrect_dispatch(self):
        responses = {
            user.username: self.clients[user.username].post(
                self.get_url('whatever'),
                {},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            for user in self.users
        }

        status_codes = {response.status_code for response in responses.values()}
        assert status_codes.pop() == 200

        for user in self.users:
            self.assertDictEqual(
                json.loads(responses[user.username].content.decode('utf-8')),
                {
                    'status': 'fail',
                    'error': 'Unknown Command!'
                }
            )

    def test_word_cloud_constructor(self):
        """
        Make sure that all parameters extracted correctly from xml.
        """
        fragment = self.runtime.render(self.item_descriptor, STUDENT_VIEW)
        expected_context = {
            'ajax_url': self.item_descriptor.ajax_url,
            'display_name': self.item_descriptor.display_name,
            'instructions': self.item_descriptor.instructions,
            'element_class': self.item_descriptor.location.block_type,
            'element_id': self.item_descriptor.location.html_id(),
            'num_inputs': 5,  # default value
            'submitted': False,  # default value,
        }

        assert fragment.content == self.runtime.render_template('word_cloud.html', expected_context)
