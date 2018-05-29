'''
Unit tests for pychal - Python Challonge API

Examples for runnins these tests:
 - python tests.py -v
 - CHALLONGE_USER=username CHALLONGE_KEY=your.api.key python ./tests.py -v
'''
import datetime
import os
import random
import string
import unittest
import requests
import tzlocal
import challonge


USERNAME = None
API_KEY = None


def _get_random_name():
    '''Create random string for challonge tourney name'''
    return "pychal_" + "".join(
        random.choice(string.ascii_lowercase) for _ in range(0, 15)
        )


class APITestCase(unittest.TestCase):
    '''Test Challonge API Methods'''
    # pylint: disable=invalid-name

    def test_set_credentials(self):
        '''Set API Credentials'''
        # pylint: disable=protected-access
        challonge.set_credentials(USERNAME, API_KEY)
        self.assertEqual(challonge.api._credentials['user'], USERNAME)
        self.assertEqual(challonge.api._credentials['api_key'], API_KEY)

    def test_get_credentials(self):
        '''Get API Credentials'''
        # pylint: disable=protected-access
        challonge.api._credentials['user'] = USERNAME
        challonge.api._credentials['api_key'] = API_KEY
        self.assertEqual(challonge.get_credentials(), (USERNAME, API_KEY))

    def test_get_local_timezone(self):
        '''Get TimeZone'''
        tz = challonge.get_timezone()
        local_tz = tzlocal.get_localzone()
        self.assertEqual(tz, local_tz)

    def test_set_get_timezone(self):
        '''Set TimeZone'''
        test_tz = 'Asia/Seoul'
        challonge.set_timezone(test_tz)
        tz = challonge.get_timezone()
        self.assertEqual(str(tz), test_tz)

    def test_call(self):
        '''Verify tournaments call does not return empty'''
        challonge.set_credentials(USERNAME, API_KEY)
        self.assertNotEqual(challonge.fetch("GET", "tournaments"), '')


class TournamentsTestCase(unittest.TestCase):
    '''Test Challonge Tournament Methods'''
    # map/filter on lambda could be replaced by comprehension
    # pylint: disable=deprecated-lambda

    # pylint: disable=invalid-name

    def setUp(self):
        challonge.set_credentials(USERNAME, API_KEY)
        self.random_name = _get_random_name()

        self.t = challonge.tournaments.create(self.random_name,
                                              self.random_name)

    def tearDown(self):
        challonge.tournaments.destroy(self.t['id'])

    def test_index(self):
        '''Tournaments Index'''
        ts = challonge.tournaments.index()
        ts = list(filter(lambda x: x['id'] == self.t['id'], ts))
        self.assertEqual(len(ts), 1)
        self.assertEqual(self.t, ts[0])

    def test_index_filter_by_state(self):
        '''Tournaments Index Filtered by Tournament State'''
        ts = challonge.tournaments.index(state="pending")
        ts = list(filter(lambda x: x['id'] == self.t['id'], ts))
        self.assertEqual(len(ts), 1)
        self.assertEqual(self.t, ts[0])

        ts = challonge.tournaments.index(state="in_progress")
        ts = list(filter(lambda x: x['id'] == self.t['id'], ts))
        self.assertEqual(ts, [])

    def test_index_filter_by_created(self):
        '''Tournaments Index Filtered by Tournament Creation Date'''
        ts = challonge.tournaments.index(
            created_after=datetime.datetime.now().date() -
            datetime.timedelta(days=1))
        ts = filter(lambda x: x['id'] == self.t['id'], ts)
        self.assertTrue(self.t['id'] in map(lambda x: x['id'], ts))

    def test_show(self):
        '''Tournaments: Show'''
        self.assertEqual(challonge.tournaments.show(self.t['id']), self.t)

    def test_update_name(self):
        '''Tournaments: Update Name'''
        challonge.tournaments.update(self.t['id'], name="Test!")

        t = challonge.tournaments.show(self.t['id'])

        self.assertEqual(t['name'], "Test!")
        t.pop("name")
        self.t.pop("name")

        self.assertTrue(t['updated_at'] >= self.t['updated_at'])
        t.pop("updated_at")
        self.t.pop("updated_at")

        self.assertEqual(t, self.t)

    def test_update_private(self):
        '''Tournaments: Set to Private'''
        challonge.tournaments.update(self.t['id'], private=True)

        t = challonge.tournaments.show(self.t['id'])

        self.assertEqual(t['private'], True)

    def test_update_type(self):
        '''Tournaments: Update Type'''
        challonge.tournaments.update(self.t['id'],
                                     tournament_type="round robin")

        t = challonge.tournaments.show(self.t['id'])

        self.assertEqual(t['tournament_type'], "round robin")

    def test_start(self):
        '''Tournaments: Start'''
        # we have to add participants in order to start()
        self.assertRaises(
            challonge.ChallongeException,
            challonge.tournaments.start,
            self.t['id'])

        self.assertEqual(self.t['started_at'], None)

        challonge.participants.create(self.t['id'], "#1")
        challonge.participants.create(self.t['id'], "#2")

        challonge.tournaments.start(self.t['id'])

        t = challonge.tournaments.show(self.t['id'])
        self.assertNotEqual(t['started_at'], None)

    def test_finalize(self):
        '''Tournaments: Finalize'''
        challonge.participants.create(self.t['id'], "#1")
        challonge.participants.create(self.t['id'], "#2")

        challonge.tournaments.start(self.t['id'])
        ms = challonge.matches.index(self.t['id'])
        self.assertEqual(ms[0]['state'], "open")

        challonge.matches.update(
            self.t['id'],
            ms[0]['id'],
            scores_csv="3-2,4-1,2-2",
            winner_id=ms[0]['player1_id'])

        challonge.tournaments.finalize(self.t['id'])
        t = challonge.tournaments.show(self.t['id'])

        self.assertNotEqual(t['completed_at'], None)

    def test_reset(self):
        '''Tournaments: Reset'''
        # have to add participants in order to start()
        challonge.participants.create(self.t['id'], "#1")
        challonge.participants.create(self.t['id'], "#2")

        challonge.tournaments.start(self.t['id'])

        # we can't add participants to a started tournament...
        self.assertRaises(
            challonge.ChallongeException,
            challonge.participants.create,
            self.t['id'],
            "name")

        challonge.tournaments.reset(self.t['id'])

        # but we can add participants to a reset tournament
        p = challonge.participants.create(self.t['id'], "name")

        challonge.participants.destroy(self.t['id'], p['id'])


class ParticipantsTestCase(unittest.TestCase):
    '''Test Challonge Participants Methods'''
    # pylint: disable=invalid-name

    def setUp(self):
        challonge.set_credentials(USERNAME, API_KEY)
        self.t_name = _get_random_name()
        self.ps_names = [_get_random_name(), _get_random_name()]
        self.t = challonge.tournaments.create(self.t_name, self.t_name)
        self.ps = challonge.participants.bulk_add(
            self.t['id'],
            self.ps_names)

    def tearDown(self):
        challonge.tournaments.destroy(self.t['id'])

    def test_index(self):
        '''Participants: Index'''
        ps = challonge.participants.index(self.t['id'])
        self.assertEqual(len(ps), 2)

        self.assertTrue(self.ps[0] == ps[0] or self.ps[0] == ps[1])
        self.assertTrue(self.ps[1] == ps[0] or self.ps[1] == ps[1])

    def test_show(self):
        '''Participants: Show'''
        p1 = challonge.participants.show(self.t['id'], self.ps[0]['id'])
        self.assertEqual(p1['id'], self.ps[0]['id'])

    def test_create(self):
        '''Participants: Create'''
        new_player = challonge.participants.create(self.t['id'],
                                                   _get_random_name())
        res = challonge.participants.show(self.t['id'], new_player['id'])
        self.assertEqual(res, new_player)

    def test_create_with_number_names(self):
        '''Participants: Create Player with only Numbers in the Name'''
        player_with_only_numbers = "".join(
            [str(random.randint(0, 9)) for _ in range(0, 9)]
            )
        new_player = challonge.participants.create(self.t['id'],
                                                   player_with_only_numbers)
        res = challonge.participants.show(self.t['id'], new_player['id'])
        self.assertEqual(res['name'], player_with_only_numbers)

    def test_update(self):
        '''Participants: Update'''
        challonge.participants.update(self.t['id'],
                                      self.ps[0]['id'], misc="Test!")
        p1 = challonge.participants.show(self.t['id'], self.ps[0]['id'])

        self.assertEqual(p1['misc'], "Test!")
        self.ps[0].pop("misc")
        p1.pop("misc")

        self.assertTrue(p1['updated_at'] >= self.ps[0]['updated_at'])
        self.ps[0].pop("updated_at")
        p1.pop("updated_at")

        self.assertEqual(self.ps[0], p1)

    @unittest.skip("Skipping because of API Issues")
    def test_check_in_and_undo_check_in(self):
        '''Participants: Player Check-In and Undo'''
        timezone = challonge.get_timezone()
        # Get the local time plus 30 minutes.
        test_date = (datetime.datetime.now(tz=timezone) +
                     datetime.timedelta(minutes=30))

        challonge.tournaments.update(
            self.t["id"],
            check_in_duration=30,
            start_at=test_date)

        challonge.participants.check_in(self.t["id"], self.ps[0]["id"])
        challonge.participants.check_in(self.t["id"], self.ps[1]["id"])

        p1 = challonge.participants.show(self.t["id"], self.ps[0]["id"])
        p2 = challonge.participants.show(self.t["id"], self.ps[1]["id"])

        self.assertTrue(p1["checked_in"])
        self.assertTrue(p2["checked_in"])

        # # check the undo process
        challonge.participants.undo_check_in(self.t["id"], self.ps[0]["id"])
        challonge.participants.undo_check_in(self.t["id"], self.ps[0]["id"])

        p1 = challonge.participants.show(self.t["id"], self.ps[0]["id"])
        p2 = challonge.participants.show(self.t["id"], self.ps[0]["id"])

        self.assertFalse(p1["checked_in"])
        self.assertFalse(p2["checked_in"])

    def test_destroy_before_tournament_start(self):
        '''
        Participants: delete participant prior to start of the tournament
        '''
        challonge.participants.destroy(self.t['id'], self.ps[0]['id'])
        p = challonge.participants.index(self.t['id'])
        self.assertEqual(len(p), 1)

    def test_destroy_after_tournament_start(self):
        '''
        Participants: delete participant after the start of the tournament
        '''
        challonge.tournaments.start(self.t['id'])
        challonge.participants.destroy(self.t['id'], self.ps[1]['id'])
        p2 = challonge.participants.show(self.t['id'], self.ps[1]['id'])
        self.assertFalse(p2['active'])

    def test_randomize(self):
        '''
        randomize has a 50% chance of actually being different than
        current seeds, so we're just verifying that the method runs at all
        '''
        challonge.participants.randomize(self.t['id'])


class MatchesTestCase(unittest.TestCase):
    '''Test Challonge Matches Methods'''
    # pylint: disable=invalid-name

    def setUp(self):
        challonge.set_credentials(USERNAME, API_KEY)
        self.t_name = _get_random_name()

        self.t = challonge.tournaments.create(self.t_name, self.t_name)
        self.ps = challonge.participants.bulk_add(
            self.t['id'],
            [_get_random_name(), _get_random_name()])
        challonge.tournaments.start(self.t['id'])

    def tearDown(self):
        challonge.tournaments.destroy(self.t['id'])

    def test_index(self):
        '''Matches: Index'''
        ms = challonge.matches.index(self.t['id'])

        self.assertEqual(len(ms), 1)
        m = ms[0]

        ps = set((self.ps[0]['id'], self.ps[1]['id']))
        self.assertEqual(ps, set((m['player1_id'], m['player2_id'])))
        self.assertEqual(m['state'], "open")

    def test_show(self):
        '''Matches: Show'''
        ms = challonge.matches.index(self.t['id'])
        for m in ms:
            self.assertEqual(m, challonge.matches.show(self.t['id'], m['id']))

    def test_update_reopen(self):
        '''Matches: Update Reopen'''
        ms = challonge.matches.index(self.t['id'])
        m = ms[0]
        self.assertEqual(m['state'], "open")

        challonge.matches.update(
            self.t['id'],
            m['id'],
            scores_csv="3-2,4-1,2-2",
            winner_id=m['player1_id'])

        m = challonge.matches.show(self.t['id'], m['id'])
        self.assertEqual(m['state'], "complete")

        challonge.matches.reopen(self.t['id'], m['id'])
        m = challonge.matches.show(self.t['id'], m['id'])
        self.assertEqual(m['state'], "open")


class AttachmentsTestCase(unittest.TestCase):
    '''Test Challonge Attachments Methods'''
    # pylint: disable=invalid-name

    def setUp(self):
        challonge.set_credentials(USERNAME, API_KEY)
        self.t_name = _get_random_name()

        self.t = challonge.tournaments.create(
            self.t_name,
            self.t_name,
            accept_attachments=True)

        self.ps = challonge.participants.bulk_add(
            self.t['id'],
            [_get_random_name(), _get_random_name()])
        challonge.tournaments.start(self.t['id'])
        self.match = challonge.matches.index(self.t['id'])[0]

    def tearDown(self):
        challonge.tournaments.destroy(self.t['id'])

    def test_index(self):
        '''Attachments: Create and Index'''
        challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            url="http://test.com")

        challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            url="http://test2.com")

        a = challonge.attachments.index(self.t['id'], self.match['id'])
        self.assertEqual(len(a), 2)

    def test_create_url(self):
        '''Attachments: Create URL'''
        a = challonge.attachments.create(self.t['id'], self.match['id'],
                                         url="http://test.com")
        self.assertEqual(a['url'], "http://test.com")

    def test_create_description(self):
        '''Attachments: Create Description'''
        a = challonge.attachments.create(self.t['id'], self.match['id'],
                                         description="test text!")
        self.assertEqual(a['description'], "test text!")

    def test_create_url_with_description(self):
        '''Attachments: Create URL with Description'''
        a = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            url="http://test.com",
            description="just a test")

        self.assertEqual(a['url'], "http://test.com")
        self.assertEqual(a['description'], "just a test")

    @unittest.skip("Skipping because of API Issues")
    def test_create_file(self):
        '''Attachments: Create File'''
        # Note: This site seems very slow.
        image = requests.get('http://lorempixel.com/300/300/')
        a1 = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            asset=image)

        a2 = challonge.attachments.show(self.t['id'], self.match['id'],
                                        a1['id'])

        self.assertEqual(a1['asset'], a2['asset'])

    @unittest.skip("Skipping because of API Issues")
    def test_create_file_with_description(self):
        '''Attachments: Create File with Description'''
        # Note: This site seems very slow.
        image = requests.get('http://lorempixel.com/300/300/')
        a1 = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            asset=image,
            description="just a test")

        a2 = challonge.attachments.show(self.t['id'], self.match['id'],
                                        a1['id'])

        self.assertEqual(a1['asset'], a2['asset'])

    def test_update_url(self):
        '''Attachments: Update URL'''
        a = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            url="http://test.com")

        challonge.attachments.update(
            self.t['id'],
            self.match['id'],
            a['id'],
            url="https://newtest.com")

        a = challonge.attachments.show(self.t['id'], self.match['id'],
                                       a['id'])
        self.assertEqual(a['url'], "https://newtest.com")

    def test_update_description(self):
        '''Attachments: Update Description'''
        a = challonge.attachments.create(self.t['id'], self.match['id'],
                                         description="test text!")
        challonge.attachments.update(
            self.t['id'],
            self.match['id'],
            a['id'],
            description="This is an updated test!")

        a = challonge.attachments.show(self.t['id'], self.match['id'], a['id'])
        self.assertEqual(a['description'], "This is an updated test!")

    def test_update_url_with_description(self):
        '''Attachments: Update URL with Description'''
        a = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            url="http://test.com",
            description="hello there!")

        challonge.attachments.update(
            self.t['id'],
            self.match['id'],
            a['id'],
            url="http://newtest.com",
            description="added a new url!")
        a = challonge.attachments.show(self.t['id'], self.match['id'], a['id'])

        self.assertEqual(a['url'], "http://newtest.com")
        self.assertEqual(a['description'], "added a new url!")

    @unittest.skip("Skipping because of API Issues")
    def test_update_file(self):
        '''Attachments: Update File'''
        # Note: This site seems very slow.
        image = requests.get('http://lorempixel.com/300/300/')
        a1 = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            asset=image)

        # Note: This site seems very slow.
        image = requests.get('http://lorempixel.com/300/300/')
        challonge.attachments.update(
            self.t['id'],
            self.match['id'],
            a1['id'],
            asset=image)

        a2 = challonge.attachments.show(self.t['id'], self.match['id'],
                                        a1['id'])

        self.assertNotEqual(a1['asset'], a2['asset'])

    @unittest.skip("Skipping because of API Issues")
    def test_update_file_with_description(self):
        '''Attachments: Update File with Description'''
        # Note: This site seems very slow.
        image = requests.get('http://lorempixel.com/300/300/')
        a1 = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            asset=image,
            description="just a test")

        # Note: This site seems very slow.
        image = requests.get('http://lorempixel.com/300/300/')
        challonge.attachments.update(
            self.t['id'],
            self.match['id'],
            a1['id'],
            asset=image,
            description='just a second test')

        a2 = challonge.attachments.show(self.t['id'], self.match['id'],
                                        a1['id'])

        self.assertNotEqual(a1['asset'], a2['asset'])
        self.assertNotEqual(a1['description'], a2['description'])

    @unittest.skip("Skipping because of API Issues")
    def test_update_file_only_description(self):
        '''Attachments: Create File with Only Description'''
        # Note: This site seems very slow.
        image = requests.get('http://lorempixel.com/300/300/')
        a1 = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            asset=image,
            description="just a test")

        # Note: This site seems very slow.
        image = requests.get('http://lorempixel.com/300/300/')
        challonge.attachments.update(
            self.t['id'],
            self.match['id'],
            a1['id'],
            description='just a second test')

        a2 = challonge.attachments.show(self.t['id'], self.match['id'],
                                        a1['id'])

        self.assertEqual(a1['asset'], a2['asset'])
        self.assertNotEqual(a1['description'], a2['description'])

    def test_destroy(self):
        '''Attachments: Create and Destroy'''
        a = challonge.attachments.create(
            self.t['id'],
            self.match['id'],
            url="http://test.com",
            description="just a test")

        challonge.attachments.destroy(self.t['id'], self.match['id'], a['id'])
        a = challonge.attachments.index(self.t['id'], self.match['id'])

        self.assertEqual(a, [])


if __name__ == "__main__":
    USERNAME = os.environ.get("CHALLONGE_USER")
    API_KEY = os.environ.get("CHALLONGE_KEY")
    if not USERNAME or not API_KEY:
        raise RuntimeError("You must add CHALLONGE_USER and CHALLONGE_KEY \
            to your environment variables to run the test suite")

    unittest.main()
