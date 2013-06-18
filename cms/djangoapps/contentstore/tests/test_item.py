"""Tests for items views."""
import json

from lxml import etree
from django.core.urlresolvers import reverse

from contentstore.tests.test_course_settings import CourseTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.django import modulestore
from xmodule.contentstore.django import contentstore
from xmodule.contentstore.content import StaticContent
from xmodule.exceptions import NotFoundError


class DeleteItem(CourseTestCase):
    """Tests for '/delete_item' url."""
    def setUp(self):
        """ Creates the test course with a static page in it. """
        super(DeleteItem, self).setUp()
        self.course = CourseFactory.create(org='mitX', number='333', display_name='Dummy Course')

    def test_delete_static_page(self):
        # Add static tab
        data = {
            'parent_location': 'i4x://mitX/333/course/Dummy_Course',
            'template': 'i4x://edx/templates/static_tab/Empty'
        }

        resp = self.client.post(reverse('clone_item'), data)
        self.assertEqual(resp.status_code, 200)

        # Now delete it. There was a bug that the delete was failing (static tabs do not exist in draft modulestore).
        resp = self.client.post(reverse('delete_item'), resp.content, "application/json")
        self.assertEqual(resp.status_code, 200)


class ImportSubtitles(CourseTestCase):
    """Tests for '/import_subtitles' url."""
    def setUp(self):
        """Create initial data."""
        super(ImportSubtitles, self).setUp()

        # Add video module
        data = {
            'parent_location': 'i4x://MITx/999/course/Robot_Super_Course',
            'template': 'i4x://edx/templates/video/default'
        }
        resp = self.client.post(reverse('clone_item'), data)
        self.item_location = json.loads(resp.content).get('id')

        data = '<video youtube="0.75:JMD_ifUUfsU,1.0:hI10vDNYz4M,1.25:AKqURZnYqpk,1.50:DYpADpL7jAY" />'
        modulestore().update_item(self.item_location, data)

        self.item = modulestore().get_item(self.item_location)

        self.assertTrue(self.item_location)
        self.assertEqual(resp.status_code, 200)

    def get_youtube_ids(self):
        """Return youtube speeds and ids."""
        xmltree = etree.fromstring(self.item.data)
        youtube = xmltree.get('youtube')
        return dict([
            (float(i.split(':')[0]), i.split(':')[1])
            for i in youtube.split(',')
        ])

    def test_default_video_module(self):
        # Check assets status before importing subtitles.
        for youtube_id in self.get_youtube_ids().values():
            filename = 'subs_{0}.srt.sjson'.format(youtube_id)
            content_location = StaticContent.compute_location(
                'MITx', '999', filename)
            self.assertRaises(NotFoundError, contentstore().find, content_location)

        # Import subtitles.
        resp = self.client.post(
            reverse('import_subtitles'), {'id': self.item_location})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'success')

        # Check assets status after importing subtitles.
        for youtube_id in self.get_youtube_ids().values():
            filename = 'subs_{0}.srt.sjson'.format(youtube_id)
            content_location = StaticContent.compute_location(
                'MITx', '999', filename)
            self.assertTrue(contentstore().find(content_location))

    def test_fail_data_without_id(self):
        resp = self.client.post(
            reverse('import_subtitles'), {})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

    def test_fail_data_with_bad_location(self):
        resp = self.client.post(
            reverse('import_subtitles'), {'id': 'BAD_LOCATION'})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

        resp = self.client.post(
            reverse('import_subtitles'),
            {'id': '{0}_{1}'.format(self.item_location, 'BAD_LOCATION')}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

    def test_fail_for_non_video_module(self):
        # Video module: setup
        data = {
            'parent_location': 'i4x://MITx/999/course/Robot_Super_Course',
            'template': 'i4x://edx/templates/video/default'
        }
        resp = self.client.post(reverse('clone_item'), data)
        item_location = json.loads(resp.content).get('id')
        data = '<video youtube="0.75:JMD_ifUUfsU,1.0:hI10vDNYz4M" />'
        modulestore().update_item(item_location, data)

        # Video module: testing
        resp = self.client.post(
            reverse('import_subtitles'), {'id': item_location})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'success')

        # Video module: teardown
        for youtube_id in ['JMD_ifUUfsU', 'hI10vDNYz4M']:
            filename = 'subs_{0}.srt.sjson'.format(youtube_id)
            content_location = StaticContent.compute_location(
                'MITx', '999', filename)
            content = contentstore().find(content_location)
            contentstore().delete(content.get_id())

        # # Videoalpha module: setup
        # data = {
        #     'parent_location': 'i4x://MITx/999/course/Robot_Super_Course',
        #     'template': 'i4x://edx/templates/videoalpha/default'
        # }
        # resp = self.client.post(reverse('clone_item'), data)
        # item_location = json.loads(resp.content).get('id')
        # data = '<videoalpha youtube="0.75:JMD_ifUUfsU,1.0:hI10vDNYz4M" />'
        # modulestore().update_item(item_location, data)

        # # Videoalpha module: testing
        # resp = self.client.post(
        #     reverse('import_subtitles'), {'id': item_location})
        # self.assertEqual(resp.status_code, 200)
        # self.assertEqual(
        #     json.loads(resp.content).get('status'), 'success')

        # # Videoalpha module: teardown
        # for youtube_id in ['JMD_ifUUfsU', 'hI10vDNYz4M']:
        #     filename = 'subs_{0}.srt.sjson'.format(youtube_id)
        #     content_location = StaticContent.compute_location(
        #         'MITx', '999', filename)
        #     content = contentstore().find(content_location)
        #     contentstore().delete(content.get_id())

        # HTML Announcement module: setup
        data = {
            'parent_location': 'i4x://MITx/999/course/Robot_Super_Course',
            'template': 'i4x://edx/templates/html/Announcement'
        }
        resp = self.client.post(reverse('clone_item'), data)
        item_location = json.loads(resp.content).get('id')

        # HTML Announcement module: testing
        resp = self.client.post(
            reverse('import_subtitles'), {'id': item_location})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

    def test_fail_bad_xml(self):
        data = '<<<video youtube="0.75:JMD_ifUUfsU,1.25:AKqURZnYqpk,1.50:DYpADpL7jAY" />'
        modulestore().update_item(self.item_location, data)

        # Import subtitles.
        resp = self.client.post(
            reverse('import_subtitles'), {'id': self.item_location})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

    def test_fail_miss_youtube_attr(self):
        data = '<video youtube="" />'
        modulestore().update_item(self.item_location, data)

        # Import subtitles.
        resp = self.client.post(
            reverse('import_subtitles'), {'id': self.item_location})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

        data = '<video />'
        modulestore().update_item(self.item_location, data)

        # Import subtitles.
        resp = self.client.post(
            reverse('import_subtitles'), {'id': self.item_location})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

    def test_fail_bad_youtube_attr(self):
        data = '<video youtube=":JMD_ifUUfsU,1.25:AKqURZnYqpk,1.50:DYpADpL7jAY" />'
        modulestore().update_item(self.item_location, data)

        # Import subtitles.
        resp = self.client.post(
            reverse('import_subtitles'), {'id': self.item_location})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

    def test_fail_youtube_ids_unavailable(self):
        data = '<video youtube="0.75:JMD_ifUUfsU,1.25:AKqURZnYqpk,1.50:DYpADpL7jAY" />'
        modulestore().update_item(self.item_location, data)

        # Import subtitles.
        resp = self.client.post(
            reverse('import_subtitles'), {'id': self.item_location})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get('status'), 'fail')

    def tearDown(self):
        super(ImportSubtitles, self).tearDown()

        # Remove all subtitles for current module.
        for youtube_id in self.get_youtube_ids().values():
            filename = 'subs_{0}.srt.sjson'.format(youtube_id)
            content_location = StaticContent.compute_location(
                'MITx', '999', filename)
            try:
                content = contentstore().find(content_location)
                contentstore().delete(content.get_id())
            except NotFoundError:
                pass
