"""Tests for the API."""
import datetime
import json
import os
from urllib.parse import quote, quote_plus

from django.db import connection
from django.test import override_settings
from rest_framework.exceptions import ErrorDetail

from tests.models import Cat, Group, Location, Permission, Profile, User
from tests.serializers import NestedEphemeralSerializer, PermissionSerializer
from tests.setup import create_fixture

if os.getenv("DATABASE_URL"):
    from tests.test_cases import ResetAPITestCase as TestCase
else:
    from tests.test_cases import APITestCase as TestCase
UNICODE_STRING = "\u2764\ufe0f"  # unicode heart
UNICODE_URL_STRING = quote_plus(UNICODE_STRING)


def sort_values(data: dict) -> dict:
    """A hack to fix ordering in responses."""
    for key, value in data.items():
        for key_value in value:
            for k, v in key_value.items():
                if isinstance(v, list):
                    key_value[k] = sorted(v)
        if "id" in data[key][0]:
            data[key] = sorted(value, key=lambda x: x["id"])
        else:
            data[key] = sorted(value, key=lambda x: x["name"])
    return data


@override_settings(DYNAMIC_REST={"ENABLE_LINKS": False})
class TestUsersAPI(TestCase):
    """Test users API."""

    def setUp(self):
        """Set up."""
        self.fixture = create_fixture()
        self.maxDiff = None  # pylint: disable=invalid-name

    def _get_json(self, url, expected_status=200):
        """Get JSON from URL."""
        response = self.client.get(url)
        self.assertEqual(expected_status, response.status_code)
        return json.loads(response.content.decode("utf-8"))

    def test_get(self):
        """Test get."""
        with self.assertNumQueries(1):
            # 1 for User, 0 for Location
            response = self.client.get("/users/")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 1, "location": 1, "name": "0"},
                    {"id": 2, "location": 1, "name": "1"},
                    {"id": 3, "location": 2, "name": "2"},
                    {"id": 4, "location": 3, "name": "3"},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_trailing_slash_does_not_redirect(self):
        """Test get with trailing slash does not redirect."""
        response = self.client.get("/users/1")
        self.assertEqual(200, response.status_code)

    def test_get_with_include(self):
        """Test get with include."""
        with self.assertNumQueries(2):
            # 2 queries: 1 for User, 1 for Group, 0 for Location
            response = self.client.get("/users/?include[]=groups")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 1, "groups": [1, 2], "location": 1, "name": "0"},
                    {"id": 2, "groups": [1, 2], "location": 1, "name": "1"},
                    {"id": 3, "groups": [1, 2], "location": 2, "name": "2"},
                    {"id": 4, "groups": [1, 2], "location": 3, "name": "3"},
                ]
            },
            sort_values(json.loads(response.content.decode("utf-8"))),
        )

        with self.assertNumQueries(2):
            # 2 queries: 1 for User, 1 for Group
            response = self.client.get("/groups/?include[]=members")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "groups": [
                    {"id": 1, "members": [1, 2, 3, 4], "name": "0"},
                    {"id": 2, "members": [1, 2, 3, 4], "name": "1"},
                ]
            },
            sort_values(json.loads(response.content.decode("utf-8"))),
        )

    def test_get_with_exclude(self):
        """Test get with exclude."""
        with self.assertNumQueries(1):
            response = self.client.get("/users/?exclude[]=name")
        query = connection.queries[-1]["sql"]
        self.assertFalse("name" in query, query)
        self.assertFalse("*" in query, query)

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 1, "location": 1},
                    {"id": 2, "location": 1},
                    {"id": 3, "location": 2},
                    {"id": 4, "location": 3},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_nested_has_one_sideloading_disabled(self):
        """Test get with nested has one sideloading disabled."""
        with self.assertNumQueries(2):
            response = self.client.get("/users/?include[]=location.&sideloading=false")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 1, "location": {"id": 1, "name": "0"}, "name": "0"},
                    {"id": 2, "location": {"id": 1, "name": "0"}, "name": "1"},
                    {"id": 3, "location": {"id": 2, "name": "1"}, "name": "2"},
                    {"id": 4, "location": {"id": 3, "name": "2"}, "name": "3"},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_nested_has_one(self):
        """Test get with nested has one."""
        with self.assertNumQueries(2):
            response = self.client.get("/users/?include[]=location.")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "locations": [
                    {"id": 1, "name": "0"},
                    {"id": 2, "name": "1"},
                    {"id": 3, "name": "2"},
                ],
                "users": [
                    {"id": 1, "location": 1, "name": "0"},
                    {"id": 2, "location": 1, "name": "1"},
                    {"id": 3, "location": 2, "name": "2"},
                    {"id": 4, "location": 3, "name": "3"},
                ],
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_nested_has_many(self):
        """Test get with nested has many."""
        with self.assertNumQueries(2):
            # 2 queries: 1 for User, 1 for Group
            response = self.client.get("/users/?include[]=groups.")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "groups": [{"id": 1, "name": "0"}, {"id": 2, "name": "1"}],
                "users": [
                    {"groups": [1, 2], "id": 1, "location": 1, "name": "0"},
                    {"groups": [1, 2], "id": 2, "location": 1, "name": "1"},
                    {"groups": [1, 2], "id": 3, "location": 2, "name": "2"},
                    {"groups": [1, 2], "id": 4, "location": 3, "name": "3"},
                ],
            },
            sort_values(json.loads(response.content.decode("utf-8"))),
        )

    def test_get_with_nested_include(self):
        """Test get with nested include."""
        with self.assertNumQueries(3):
            # 3 queries: 1 for User, 1 for Group, 1 for Permissions
            response = self.client.get("/users/?include[]=groups.permissions")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "groups": [
                    {"id": 1, "name": "0", "permissions": [1]},
                    {"id": 2, "name": "1", "permissions": [2]},
                ],
                "users": [
                    {"groups": [1, 2], "id": 1, "location": 1, "name": "0"},
                    {"groups": [1, 2], "id": 2, "location": 1, "name": "1"},
                    {"groups": [1, 2], "id": 3, "location": 2, "name": "2"},
                    {"groups": [1, 2], "id": 4, "location": 3, "name": "3"},
                ],
            },
            sort_values(json.loads(response.content.decode("utf-8"))),
        )

    def test_get_with_nested_exclude(self):
        """Test get with nested exclude."""
        with self.assertNumQueries(2):
            # 2 queries: 1 for User, 1 for Group
            response = self.client.get("/users/?exclude[]=groups.name")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "groups": [{"id": 1}, {"id": 2}],
                "users": [
                    {"groups": [1, 2], "id": 1, "location": 1, "name": "0"},
                    {"groups": [1, 2], "id": 2, "location": 1, "name": "1"},
                    {"groups": [1, 2], "id": 3, "location": 2, "name": "2"},
                    {"groups": [1, 2], "id": 4, "location": 3, "name": "3"},
                ],
            },
            sort_values(json.loads(response.content.decode("utf-8"))),
        )

    def test_get_with_nested_exclude_all(self):
        """Test get with nested exclude all."""
        with self.assertNumQueries(2):
            # 2 queries: 1 for User, 1 for Group
            url = "/users/?exclude[]=groups.*&include[]=groups.name"
            response = self.client.get(url)
        self.assertEqual(200, response.status_code, response.content.decode("utf-8"))
        self.assertEqual(
            {
                "groups": [{"name": "0"}, {"name": "1"}],
                "users": [
                    {"groups": [1, 2], "id": 1, "location": 1, "name": "0"},
                    {"groups": [1, 2], "id": 2, "location": 1, "name": "1"},
                    {"groups": [1, 2], "id": 3, "location": 2, "name": "2"},
                    {"groups": [1, 2], "id": 4, "location": 3, "name": "3"},
                ],
            },
            sort_values(json.loads(response.content.decode("utf-8"))),
        )

    def test_get_with_exclude_all_and_include_field(self):
        """Test get with exclude all and include field."""
        with self.assertNumQueries(1):
            url = "/users/?exclude[]=*&include[]=id"
            response = self.client.get(url)
        self.assertEqual(200, response.status_code, response.content.decode("utf-8"))
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual({"id"}, set(data["users"][0].keys()))

    def test_get_with_exclude_all_and_include_relationship(self):
        """Test get with exclude all and include relationship."""
        with self.assertNumQueries(2):
            url = "/users/?exclude[]=*&include[]=groups."
            response = self.client.get(url)
        self.assertEqual(200, response.status_code, response.content.decode("utf-8"))
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual({"groups"}, set(data["users"][0].keys()))
        self.assertTrue("groups" in data)

    def test_get_one_with_include(self):
        """Test get one with include."""
        with self.assertNumQueries(2):
            # 2 queries: 1 for User, 1 for Group
            response = self.client.get("/users/1/?include[]=groups.")
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(data.get("groups", [])), 2)

    def test_get_with_filter(self):
        """Test get with filter."""
        with self.assertNumQueries(1):
            # verify that extra [] are stripped out of the key
            response = self.client.get("/users/?filter{name}[]=1")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 2, "location": 1, "name": "1"},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_filter_no_match(self):
        """Test get with filter no match."""
        with self.assertNumQueries(1):
            response = self.client.get("/users/?filter{name}[]=foo")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"users": []}, json.loads(response.content.decode("utf-8")))

    def test_get_with_filter_unicode_no_match(self):
        """Test get with filter unicode no match."""
        with self.assertNumQueries(1):
            response = self.client.get("/users/?filter{name}[]=%s" % UNICODE_URL_STRING)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"users": []}, json.loads(response.content.decode("utf-8")))
        with self.assertNumQueries(1):
            response = self.client.get("/users/?filter{name}[]=%s" % UNICODE_STRING)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"users": []}, json.loads(response.content.decode("utf-8")))

    def test_get_with_filter_unicode(self):
        """Test get with filter unicode."""
        User.objects.create(name=UNICODE_STRING, last_name="Unicode")
        with self.assertNumQueries(1):
            response = self.client.get("/users/?filter{name}[]=%s" % UNICODE_URL_STRING)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(json.loads(response.content.decode("utf-8"))["users"]))
        with self.assertNumQueries(1):
            response = self.client.get("/users/?filter{name}[]=%s" % UNICODE_STRING)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(json.loads(response.content.decode("utf-8"))["users"]))

    def test_get_with_filter_in(self):
        """Test get with filter in."""
        url = "/users/?filter{name.in}=1&filter{name.in}=2"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 2, "location": 1, "name": "1"},
                    {"id": 3, "location": 2, "name": "2"},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )
        url = "/users/?filter{name.in}=[1,2]"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 2, "location": 1, "name": "1"},
                    {"id": 3, "location": 2, "name": "2"},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_complex_filter(self):
        """Test get with complex filter."""
        # same filter as the above case
        f = {".or": [{"name": "1"}, {".and": [{"name": "2"}, {"location": 2}]}]}
        f = quote(json.dumps(f))
        url = f"/users/?filter{{}}={f}"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 2, "location": 1, "name": "1"},
                    {"id": 3, "location": 2, "name": "2"},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_filter_exclude(self):
        """Test get with filter exclude."""
        url = "/users/?filter{-name}=1"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 1, "location": 1, "name": "0"},
                    {"id": 3, "location": 2, "name": "2"},
                    {"id": 4, "location": 3, "name": "3"},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_filter_relation_field(self):
        """Test get with filter relation field."""
        url = "/users/?filter{location.name}=1"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "users": [
                    {"id": 3, "location": 2, "name": "2"},
                ]
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_filter_and_include_relationship(self):
        """Test get with filter and include relationship."""
        url = "/users/?include[]=groups.&filter{groups|name}=1"
        with self.assertNumQueries(2):
            # 2 queries: 1 for User, 1 for Group
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "groups": [{"id": 2, "name": "1"}],
                "users": [
                    {"groups": [2], "id": 1, "location": 1, "name": "0"},
                    {"groups": [2], "id": 2, "location": 1, "name": "1"},
                    {"groups": [2], "id": 3, "location": 2, "name": "2"},
                    {"groups": [2], "id": 4, "location": 3, "name": "3"},
                ],
            },
            json.loads(response.content.decode("utf-8")),
        )

    def test_get_with_filter_and_source_rewrite(self):
        """Test filtering on fields where source is different."""
        url = "/locations/?filter{address}=here&include[]=address"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(data["locations"]), 1)

    def test_get_with_filter_and_query_injection(self):
        """Test viewset with query injection."""
        url = "/users/?name=1"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(data["users"]), 1)
        self.assertEqual(data["users"][0]["name"], "1")

    def test_get_with_include_one_to_many(self):
        """Test o2m without related_name set."""
        url = "/locations/?filter{id}=1&include[]=users"
        with self.assertNumQueries(2):
            # 2 queries: 1 for locations, 1 for location-users
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(data["locations"]), 1)
        self.assertEqual(len(data["locations"][0]["users"]), 2)

    def test_get_with_count_field(self):
        """Test get with count field."""
        url = "/locations/?filter{id}=1&include[]=users&include[]=user_count"
        with self.assertNumQueries(2):
            # 2 queries: 1 for locations, 1 for location-users
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(data["locations"]), 1)
        self.assertEqual(len(data["locations"][0]["users"]), 2)
        self.assertEqual(data["locations"][0]["user_count"], 2)

    def test_get_with_queryset_injection(self):
        """Test get with queryset injection."""
        url = "/users/?location=1"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(data["users"]), 2)

    def test_get_with_include_invalid(self):
        """Test get with include invalid."""
        for bad_data in ("name..", "groups..name", "foo", "groups.foo"):
            response = self.client.get(f"/users/?include[]={bad_data}")
            self.assertEqual(400, response.status_code)

    def test_post(self):
        """Test post."""
        data = {
            "name": "test",
            "last_name": "last",
            "location": 1,
            "display_name": "test last",  # Read only, should be ignored.
        }
        response = self.client.post(
            "/users/", json.dumps(data), content_type="application/json"
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")),
            {
                "user": {
                    "id": 5,
                    "name": "test",
                    "permissions": [],
                    "favorite_pet": None,
                    "favorite_pet_id": None,
                    "groups": [],
                    "location": 1,
                    "last_name": "last",
                    "display_name": None,
                    "thumbnail_url": None,
                    "number_of_cats": 1,
                    "profile": None,
                    "date_of_birth": None,
                    "is_dead": False,
                }
            },
        )

    def test_put(self):
        """Test put."""
        group = Group.objects.create(name="test group")
        data = {"name": "updated"}
        response = self.client.put(
            f"/groups/{group.pk}/", json.dumps(data), content_type="application/json"
        )
        self.assertEqual(200, response.status_code)
        updated_group = Group.objects.get(pk=group.pk)
        self.assertEqual(updated_group.name, data["name"])

    def test_get_with_default_queryset(self):
        """Test get with default queryset."""
        url = "/groups/?filter{id}=1&include[]=loc1users"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertEqual(sorted([1, 2]), content["groups"][0]["loc1users"])

    def test_get_with_default_lambda_queryset(self):
        """Test get with default lambda queryset."""
        url = "/groups/?filter{id}=1&include[]=loc1users_lambda"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertEqual(sorted([1, 2]), content["groups"][0]["loc1users_lambda"])

    def test_get_with_default_queryset_filtered(self):
        """Test get with default queryset filtered.

        Make sure filter can be added to relational fields with default
        filters.
        """
        url = (
            "/groups/?filter{id}=1&include[]=loc1users"
            "&filter{loc1users|id.in}=3"
            "&filter{loc1users|id.in}=1"
        )
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertEqual([1], content["groups"][0]["loc1users"])

    def test_get_with_filter_nested_rewrites(self):
        """Test get with filter nested rewrites.

        Test filter for members.id which needs to be rewritten as users.id
        """
        user = User.objects.create(name="test user")
        group = Group.objects.create(name="test group")
        user.groups.add(group)

        url = "/groups/?filter{members.id}=%s&include[]=members" % user.pk
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(content["groups"]))
        self.assertEqual(group.pk, content["groups"][0]["id"])

        url = (
            "/users/?filter{groups.members.id}=%s" "&include[]=groups.members" % user.pk
        )
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(1, len(content["users"]))

    def test_get_with_filter_nonexistent_field(self):
        """Test get with filter nonexistent field."""
        # Filtering on non-existent field should return 400
        url = "/users/?filter{foobar}=1"
        response = self.client.get(url)
        self.assertEqual(400, response.status_code)

    def test_get_with_filter_invalid_data(self):
        """Test get with filter invalid data."""
        User.objects.create(name="test", date_of_birth=datetime.datetime.utcnow())
        url = "/users/?filter{date_of_birth.gt}=0&filter{date_of_birth.lt}=0"
        response = self.client.get(url)
        self.assertEqual(400, response.status_code)

        self.assertEqual(
            [
                ErrorDetail(
                    string="“0” value has an invalid date format. "
                    "It must be in YYYY-MM-DD format.",
                    code="invalid",
                )
            ],
            response.data,
        )

    def test_get_with_filter_deferred(self):
        """Test get with filter deferred."""
        # Filtering deferred field should work
        grp = Group.objects.create(name="test group")
        user = self.fixture.users[0]
        user.groups.add(grp)

        url = "/users/?filter{groups.id}=%s" % grp.pk
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(1, len(content["users"]))
        self.assertEqual(user.pk, content["users"][0]["id"])

    def test_get_with_filter_outer_joins(self):
        """Test get with filter outer joins.

        Test that the API does not return duplicate results
        when the underlying SQL query would return dupes.
        """
        user = User.objects.create(name="test")
        group_a = Group.objects.create(name="A")
        group_b = Group.objects.create(name="B")
        user.groups.add(group_a, group_b)
        response = self.client.get(
            "/users/?filter{groups.name.in}=A&filter{groups.name.in}=B"
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(1, len(content["users"]), content)

    def test_get_with_filter_isnull(self):
        """Test for .isnull filters."""
        # User with location=None
        User.objects.create(name="name", last_name="lname", location=None)

        # Count Users where location is not null
        expected = User.objects.filter(location__isnull=False).count()

        url = "/users/?filter{location.isnull}=0"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, len(content["users"]))

        url = "/users/?filter{location.isnull}=False"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, len(content["users"]))

        url = "/users/?filter{location.isnull}=1"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(content["users"]))

        url = "/users/?filter{-location.isnull}=True"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, len(content["users"]))

    def test_get_with_nested_source_fields(self):
        """Test get with nested source fields."""
        u1 = User.objects.create(name="test1", last_name="user")
        Profile.objects.create(
            user=u1, display_name="foo", thumbnail_url="http://thumbnail.url"
        )

        url = (
            "/users/?filter{id}=%s&include[]=display_name"
            "&include[]=thumbnail_url" % u1.pk
        )
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(content["users"][0]["display_name"])
        self.assertIsNotNone(content["users"][0]["thumbnail_url"])

    def test_get_with_nested_source_fields_count(self):
        """Test get with nested source fields count."""
        loc = Location.objects.create(name="test location")
        u1 = User.objects.create(name="test1", last_name="user", location=loc)
        Profile.objects.create(user=u1, display_name="foo")
        u2 = User.objects.create(name="test2", last_name="user", location=loc)
        Profile.objects.create(user=u2, display_name="moo")

        # Test prefetching to pull profile.display_name into UserSerializer
        url = "/users/?include[]=display_name" "&include[]=thumbnail_url"

        with self.assertNumQueries(2):
            response = self.client.get(url)
            self.assertEqual(200, response.status_code)

        # Test prefetching of user.location.name into ProfileSerializer
        url = "/profiles/?include[]=user_location_name"
        with self.assertNumQueries(3):
            response = self.client.get(url)
            self.assertEqual(200, response.status_code)
            content = json.loads(response.content.decode("utf-8"))
            self.assertIsNotNone(content["profiles"][0]["user_location_name"])

    def test_get_with_dynamic_method_field(self):
        """Test get with dynamic method field."""
        url = "/users/?include[]=number_of_cats"
        with self.assertNumQueries(3):
            response = self.client.get(url)
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                {
                    "users": [
                        {
                            "id": 1,
                            "location": 1,
                            "name": "0",
                            "number_of_cats": 1,
                        },
                        {
                            "id": 2,
                            "location": 1,
                            "name": "1",
                            "number_of_cats": 1,
                        },
                        {
                            "id": 3,
                            "location": 2,
                            "name": "2",
                            "number_of_cats": 1,
                        },
                        {
                            "id": 4,
                            "location": 3,
                            "name": "3",
                            "number_of_cats": 0,
                        },
                    ]
                },
                json.loads(response.content.decode("utf-8")),
            )

    def test_get_with_request_filters_and_requires(self):
        """This tests conflicting external and internal prefetch requirements.

        `location.cats` is an external requirement that points
        to the `Location.cat_set` model relationship.

        `user.number_of_cats` is an internal requirement that points
        to the same relationship.

        The prefetch tree produced by this call merges the two together
        into a single prefetch:
        {
           'location': {
              'cat_set': {}
            }
        }
        """
        url = (
            "/users/?"
            "include[]=number_of_cats&"
            "include[]=location.cats.&"
            "filter{location.cats|name.icontains}=1"
        )
        with self.assertNumQueries(3):
            response = self.client.get(url)
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                {
                    "cats": [{"id": 2, "name": "1"}],
                    "locations": [
                        {"name": "0", "id": 1, "cats": []},
                        {"name": "1", "id": 2, "cats": [2]},
                        {"name": "2", "id": 3, "cats": []},
                    ],
                    "users": [
                        {
                            "id": 1,
                            "location": 1,
                            "name": "0",
                            "number_of_cats": 0,
                        },
                        {
                            "id": 2,
                            "location": 1,
                            "name": "1",
                            "number_of_cats": 0,
                        },
                        {
                            "id": 3,
                            "location": 2,
                            "name": "2",
                            "number_of_cats": 1,
                        },
                        {
                            "id": 4,
                            "location": 3,
                            "name": "3",
                            "number_of_cats": 0,
                        },
                    ],
                },
                json.loads(response.content.decode("utf-8")),
            )

    def test_implicit_vs_explicit_prefetch(self):
        """Test implicit vs explicit prefetch.

        LocationSerializer has a built-in filter to hide Atlantis.

        UserSerializer can explicitly include Location, and it can also
        implicitly require Location through the `number_of_cats` field.
        This test ensures that LocationSerializer.filter_queryset() is
        being respected regardless of whether `User.location` is being
        included implicitly or explicitly.
        """
        atlantis = Location.objects.create(name="Atlantis")
        atlantian = User.objects.create(
            name="Atlantian", last_name="Human", location=atlantis
        )
        Cat.objects.create(
            name="Gato",
            home=atlantis,
            backup_home=self.fixture.locations[0],
        )

        url = (
            f"/users/{atlantian.pk}/?" "include[]=number_of_cats&" "include[]=location."
        )
        response1 = self._get_json(url)

        url = (
            f"/users/{atlantian.pk}/?" "include[]=number_of_cats&" "exclude[]=location"
        )
        response2 = self._get_json(url)

        # Atlantis is hidden, therefore its cats are also hidden
        self.assertEqual(response1["user"]["number_of_cats"], 0)
        self.assertEqual(
            response1["user"]["number_of_cats"], response2["user"]["number_of_cats"]
        )

    def test_boolean_filters_on_boolean_field(self):
        """Test boolean filters on boolean field."""
        # create one dead user
        User.objects.create(name="Dead", last_name="Mort", is_dead=True)

        # set up test specs
        tests = {
            True: ["true", "True", "1", "okies"],
            False: ["false", "False", "0", ""],
        }

        # run through test scenarios
        for expected_value, test_values in tests.items():
            for test_value in test_values:
                url = "/users/?include[]=is_dead&filter{is_dead}=%s" % test_value
                data = self._get_json(url)

                expected = {expected_value}
                actual = {o["is_dead"] for o in data["users"]}
                self.assertEqual(
                    expected,
                    actual,
                    f"Boolean filter '{test_value}' failed. "
                    f"Expected={expected} Actual={actual}",
                )

    def test_sort_relation_field(self):
        """Test sort relation field."""
        url = "/users/?sort[]=location.name"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual([1, 1, 2, 3], [row["location"] for row in data["users"]])

    def test_sort_relation_field_reverse(self):
        """Test sort relation field reverse."""
        url = "/users/?sort[]=-location.name"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual([3, 2, 1, 1], [row["location"] for row in data["users"]])

    def test_sort_relation_field_many(self):
        """Test sort relation field many."""
        url = "/locations/?sort[]=friendly_cats.name"
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        ids = [row["id"] for row in data["locations"]]
        # no duplicates
        self.assertEqual(len(ids), len(set(ids)))


@override_settings(DYNAMIC_REST={"ENABLE_LINKS": False})
class TestLocationsAPI(TestCase):
    """Test Locations API."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_options(self):
        """Test options."""
        response = self.client.options("/locations/")
        self.assertEqual(200, response.status_code)
        actual = json.loads(response.content.decode("utf-8"))
        expected = {
            "description": "Location viewset.",
            "name": "Location List",
            "parses": [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
            ],
            "properties": {
                "name": {
                    "default": None,
                    "label": "Name",
                    "nullable": False,
                    "read_only": False,
                    "required": True,
                    "type": "string",
                },
                "address": {
                    "default": None,
                    "immutable": False,
                    "label": "Address",
                    "nullable": False,
                    "read_only": False,
                    "required": False,
                    "type": "field",
                },
                "id": {
                    "default": None,
                    "label": "ID",
                    "nullable": False,
                    "read_only": True,
                    "required": False,
                    "type": "integer",
                },
                "user_count": {
                    "default": None,
                    "immutable": False,
                    "label": "User count",
                    "nullable": False,
                    "read_only": False,
                    "required": False,
                    "type": "field",
                },
                "users": {
                    "default": None,
                    "immutable": False,
                    "label": "Users",
                    "nullable": True,
                    "read_only": False,
                    "related_to": "users",
                    "required": False,
                    "type": "many",
                },
                "cats": {
                    "default": None,
                    "immutable": False,
                    "label": "Cats",
                    "nullable": True,
                    "read_only": False,
                    "related_to": "cats",
                    "required": False,
                    "type": "many",
                },
                "bad_cats": {
                    "default": None,
                    "immutable": False,
                    "label": "Bad cats",
                    "nullable": True,
                    "read_only": False,
                    "related_to": "cats",
                    "required": False,
                    "type": "many",
                },
                "friendly_cats": {
                    "default": None,
                    "immutable": False,
                    "label": "Friendly cats",
                    "nullable": True,
                    "read_only": False,
                    "related_to": "cats",
                    "required": False,
                    "type": "many",
                },
            },
            "renders": ["application/json", "text/html"],
            "resource_name": "location",
            "resource_name_plural": "locations",
        }
        # Django 1.7 and 1.9 differ in their interpretation of
        # "nullable" when it comes to inverse relationship fields.
        # Ignore the values for the purposes of this comparison.
        for field in ["cats", "friendly_cats", "bad_cats", "users"]:
            del actual["properties"][field]["nullable"]
            del expected["properties"][field]["nullable"]
        actual.pop("features")
        self.assertEqual(
            json.loads(json.dumps(expected)), json.loads(json.dumps(actual))
        )

    def test_get_with_filter_by_user(self):
        """Test get with filter by user."""
        url = "/locations/?filter{users}=1"
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(1, len(content["locations"]))

    def test_get_with_filter_rewrites(self):
        """Tests various filter rewrite scenarios."""
        urls = [
            "/locations/?filter{cats}=1",
            "/locations/?filter{friendly_cats}=1",
            "/locations/?filter{bad_cats}=1",
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(200, response.status_code)


@override_settings(DYNAMIC_REST={"ENABLE_LINKS": False})
class TestAlternateLocationsAPI(TestCase):
    """Test extra_drest_filters view attribute."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()

    def test_extra_drest_filter_combines_with_drest_filters(self):
        """Test that extra_drest_filters combines with drest filters."""
        # sanity check: standard filter returns 1 result
        r = self.client.get("/alternate_locations/?filter{users.last_name}=1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data.get("locations", [])), 1, r.data)
        location = r.data["locations"][0]
        self.assertEqual(location["name"], "0")

        # using the custom filter gives same result
        r = self.client.get("/alternate_locations/?user_name=0")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["locations"]), 1)
        location = r.data["locations"][0]
        self.assertEqual(location["name"], "0")

        # now combine filters, such that no user could satisfy both
        # verify that we get no locations back
        r = self.client.get(
            "/alternate_locations/?user_name=0&filter{users.last_name}=1"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["locations"]), 0)

    def test_separate_filter_doesnt_combine_with_drest_filters(self):
        """Test that separate_filter doesn't combine with drest filters."""
        # This establishes that doing a naive `.filter` results
        # in multiple joins, giving an unexpected result:
        # the Location has 2 users, each satisfying one of the
        # two filters.
        r = self.client.get(
            "/alternate_locations/?user_name_separate=0" "&filter{users.last_name}=1"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["locations"]), 1)
        location = r.data["locations"][0]
        self.assertEqual(location["name"], "0")


class TestRelationsAPI(TestCase):
    """Test auto-generated relation endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()

    def test_generated_relation_fields(self):
        """Test generated relation fields."""
        # Links for single-relations is currently disabled.
        # See WithDynamicSerializerMixin.get_link_fields()
        r = self.client.get("/users/1/location/")
        self.assertEqual(404, r.status_code)

        r = self.client.get("/users/1/permissions/")
        self.assertFalse("groups" in r.data["permissions"][0])
        self.assertEqual(200, r.status_code)

        r = self.client.get("/users/1/groups/")
        self.assertEqual(200, r.status_code)

        # Not a relation field
        r = self.client.get("/users/1/name/")
        self.assertEqual(404, r.status_code)

    def test_location_users_relations_identical_to_sideload(self):
        """Test location users relations identical to side-load."""
        r1 = self.client.get("/locations/1/?include[]=users.")
        self.assertEqual(200, r1.status_code)
        r1_data = json.loads(r1.content.decode("utf-8"))

        r2 = self.client.get("/locations/1/users/")
        self.assertEqual(200, r2.status_code)
        r2_data = json.loads(r2.content.decode("utf-8"))

        self.assertEqual(r2_data["users"], r1_data["users"])

    def test_relation_includes(self):
        """Test relation includes."""
        r = self.client.get("/locations/1/users/?include[]=location.")
        self.assertEqual(200, r.status_code)

        content = json.loads(r.content.decode("utf-8"))
        self.assertTrue("locations" in content)

    def test_relation_includes_context(self):
        """Test relation includes context."""
        r = self.client.get("/locations/1/users/?include[]=number_of_cats")
        self.assertEqual(200, r.status_code)

        # Note: the DynamicMethodField for `number_of_cats` checks to
        # ensure context is set, and raises if not. If the request
        # succeeded and `number_of_cats` is returned, it means that check
        # passed.
        self.assertTrue("number_of_cats" in r.data["users"][0])

    def test_relation_excludes(self):
        """Test relation excludes."""
        r = self.client.get("/locations/1/users/?exclude[]=location")
        self.assertEqual(200, r.status_code)
        content = json.loads(r.content.decode("utf-8"))

        self.assertFalse("location" in content["users"][0])

    def test_relation_filter_returns_error(self):
        """Test relation filter returns error."""
        r = self.client.get("/locations/1/users/?filter{name}=foo")
        self.assertEqual(400, r.status_code)


class TestUserLocationsAPI(TestCase):
    """Test API on serializer with embedded fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()

    def test_get_embedded(self):
        """Test get embedded."""
        with self.assertNumQueries(3):
            url = "/v1/user_locations/1/"
            response = self.client.get(url)

        self.assertEqual(200, response.status_code)
        content = json.loads(response.content.decode("utf-8"))
        groups = content["user_location"]["groups"]
        location = content["user_location"]["location"]
        self.assertEqual(content["user_location"]["location"]["name"], "0")
        self.assertTrue(isinstance(groups[0], dict))
        self.assertTrue(isinstance(location, dict))

    def test_get_embedded_force_sideloading(self):
        """Test get embedded force sideloading."""
        with self.assertNumQueries(3):
            url = "/v1/user_locations/1/?sideloading=true"
            response = self.client.get(url)

        self.assertEqual(200, response.status_code)
        content = json.loads(response.content.decode("utf-8"))
        groups = content["user_location"]["groups"]
        location = content["user_location"]["location"]
        self.assertEqual(content["locations"][0]["name"], "0")
        self.assertFalse(isinstance(groups[0], dict))
        self.assertFalse(isinstance(location, dict))


class TestLinks(TestCase):
    """Test links."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()

        home = Location.objects.create()
        hunting_ground = Location.objects.create()
        self.cat = Cat.objects.create(name="foo", home=home, backup_home=hunting_ground)
        self.cat.hunting_grounds.add(hunting_ground)

    def test_deferred_relations_have_links(self):
        """Test deferred relations have links."""
        r = self.client.get("/v2/cats/1/")
        self.assertEqual(200, r.status_code)
        content = json.loads(r.content.decode("utf-8"))

        cat = content["cat"]
        self.assertTrue("links" in cat)

        # 'home' has link=None set so should not have a link object
        self.assertTrue("home" not in cat["links"])

        # test for default link (auto-generated relation endpoint)
        # Note that the pluralized name is used rather than the full prefix.
        self.assertEqual(cat["links"]["foobar"], "/v2/cats/1/foobar/")

        # test for dynamically generated link URL
        cat1 = Cat.objects.get(pk=1)
        self.assertEqual(
            cat["links"]["backup_home"],
            f"/locations/{cat1.backup_home.pk}/?include[]=address",
        )

    @override_settings(DYNAMIC_REST={"ENABLE_HOST_RELATIVE_LINKS": False})
    def test_relative_links(self):
        """Test relative links."""
        r = self.client.get("/v2/cats/1/")
        self.assertEqual(200, r.status_code)
        content = json.loads(r.content.decode("utf-8"))

        cat = content["cat"]
        self.assertTrue("links" in cat)

        # test that links urls become resource-relative urls when
        # host-relative urls are turned off.
        self.assertEqual(cat["links"]["foobar"], "foobar/")

    def test_including_empty_relation_hides_link(self):
        """Test including empty relation hides link."""
        r = self.client.get("/v2/cats/1/?include[]=foobar")
        self.assertEqual(200, r.status_code)
        content = json.loads(r.content.decode("utf-8"))

        # 'foobar' is included but empty, so don't return a link
        cat = content["cat"]
        self.assertFalse(cat["foobar"])
        self.assertFalse("foobar" in cat["links"])

    def test_including_non_empty_many_relation_has_link(self):
        """Test including non-empty many relation has link."""
        r = self.client.get(f"/v2/cats/{self.cat.pk}/?include[]=foobar")
        self.assertEqual(200, r.status_code)
        content = json.loads(r.content.decode("utf-8"))
        cat = content["cat"]
        self.assertTrue("foobar" in cat)
        self.assertTrue("foobar" in cat["links"])

    def test_no_links_for_included_single_relations(self):
        """Test no links for included single relations."""
        url = f"/v2/cats/{self.cat.pk}/?include[]=home"
        r = self.client.get(url)
        self.assertEqual(200, r.status_code)
        content = json.loads(r.content.decode("utf-8"))

        cat = content["cat"]
        self.assertTrue("home" in cat)
        self.assertFalse("home" in cat["links"])

    def test_sideloading_relation_hides_link(self):
        """Test sideloading relation hides link."""
        url = f"/v2/cats/{self.cat.pk}/?include[]=foobar."
        r = self.client.get(url)
        self.assertEqual(200, r.status_code)
        content = json.loads(r.content.decode("utf-8"))

        cat = content["cat"]
        self.assertTrue("foobar" in cat)
        self.assertTrue("locations" in content)  # check for sideload
        self.assertFalse("foobar" in cat["links"])  # no link

    def test_one_to_one_dne(self):
        """Test one to one dne."""
        user = User.objects.create(name="foo", last_name="bar")

        url = f"/users/{user.pk}/profile/"
        r = self.client.get(url)
        self.assertEqual(200, r.status_code)
        # Check error message to differentiate from a routing error 404
        content = json.loads(r.content.decode("utf-8"))
        self.assertEqual({}, content)

    def test_ephemeral_object_link(self):
        """Test ephemeral object link."""

        class FakeCountObject(object):
            """Fake count object."""

            pk = 1
            values = []

        class FakeNested(object):
            """Fake nested."""

            value_count = FakeCountObject()

        szr = NestedEphemeralSerializer()
        data = szr.to_representation(FakeNested())
        self.assertEqual(data, {"value_count": 1}, data)

    def test_meta_read_only_relation_field(self):
        """Test meta read only relation field.

        Test for making a DynamicRelationField read-only by adding
        it to Meta.read_only_fields.
        """
        data = {
            "name": "test ro",
            "last_name": "last",
            "location": 1,
            "profile": "bogus value",  # Read only relation field
        }
        response = self.client.post(
            "/users/", json.dumps(data), content_type="application/json"
        )
        # Note: if 'profile' isn't getting ignored, this will return
        # a 404 since a matching Profile object isn't found.
        self.assertEqual(201, response.status_code)

    def test_no_links_when_excluded(self):
        """Test no links when excluded."""
        r = self.client.get("/v2/cats/1/?exclude_links")
        self.assertEqual(200, r.status_code)
        content = json.loads(r.content.decode("utf-8"))

        cat = content["cat"]
        self.assertFalse("links" in cat)

    @override_settings(
        DYNAMIC_REST={
            "ENABLE_LINKS": True,
            "DEFER_MANY_RELATIONS": True,
        }
    )
    def test_auto_deferral(self):
        """Test auto deferral."""
        perm = Permission.objects.create(name="test", code=1)
        perm.groups.add(self.fixture.groups[0])

        # Check serializers
        fields = PermissionSerializer().get_all_fields()
        self.assertIs(fields["users"].deferred, False)
        self.assertIs(fields["groups"].deferred, None)

        url = f"/permissions/{perm.pk}/"
        r = self.client.get(url)
        data = json.loads(r.content.decode("utf-8"))
        self.assertFalse("groups" in data["permission"])

        # users shouldn't be deferred because `deferred=False` is
        # explicitly set on the field.
        self.assertTrue("users" in data["permission"])


class TestDogsAPI(TestCase):
    """Tests for sorting and pagination."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()

    def test_sort_exclude_count(self):
        """Test sort exclude count."""
        # page 1
        url = "/dogs/?sort[]=name&exclude_count=1&per_page=4"
        # 1 query - one for getting dogs, 0 for count
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        expected_data = [
            {
                "id": 2,
                "name": "Air-Bud",
                "origin": "Air Bud 4: Seventh Inning Fetch",
                "fur": "gold",
            },
            {
                "id": 1,
                "name": "Clifford",
                "origin": "Clifford the big red dog",
                "fur": "red",
            },
            {
                "id": 4,
                "name": "Pluto",
                "origin": "Mickey Mouse",
                "fur": "brown and white",
            },
            {"id": 3, "name": "Spike", "origin": "Rugrats", "fur": "brown"},
        ]
        expected_meta = {"page": 1, "per_page": 4, "more_pages": True}
        actual_response = json.loads(response.content.decode("utf-8"))
        actual_data = actual_response.get("dogs")
        actual_meta = actual_response.get("meta")
        self.assertEqual(expected_data, actual_data)
        self.assertEqual(expected_meta, actual_meta)

        # page 2
        url = f"{url}&page=2"
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        expected_data = [
            {"id": 5, "name": "Spike", "origin": "Tom and Jerry", "fur": "light-brown"}
        ]
        expected_meta = {"page": 2, "per_page": 4, "more_pages": False}
        actual_response = json.loads(response.content.decode("utf-8"))
        actual_data = actual_response.get("dogs")
        actual_meta = actual_response.get("meta")
        self.assertEqual(expected_data, actual_data)
        self.assertEqual(expected_meta, actual_meta)

    def test_sort_implied_all(self):
        """Test sort implied all."""
        url = "/dogs/?sort[]=name"
        # 2 queries - one for getting dogs, one for the meta (count)
        with self.assertNumQueries(2):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        expected_response = [
            {
                "id": 2,
                "name": "Air-Bud",
                "origin": "Air Bud 4: Seventh Inning Fetch",
                "fur": "gold",
            },
            {
                "id": 1,
                "name": "Clifford",
                "origin": "Clifford the big red dog",
                "fur": "red",
            },
            {
                "id": 4,
                "name": "Pluto",
                "origin": "Mickey Mouse",
                "fur": "brown and white",
            },
            {"id": 3, "name": "Spike", "origin": "Rugrats", "fur": "brown"},
            {"id": 5, "name": "Spike", "origin": "Tom and Jerry", "fur": "light-brown"},
        ]
        actual_response = json.loads(response.content.decode("utf-8")).get("dogs")
        self.assertEqual(expected_response, actual_response)

    def test_sort_reverse(self):
        """Test sort reverse."""
        url = "/dogs/?sort[]=-name"
        # 2 queries - one for getting dogs, one for the meta (count)
        with self.assertNumQueries(2):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        expected_response = [
            {"id": 3, "name": "Spike", "origin": "Rugrats", "fur": "brown"},
            {"id": 5, "name": "Spike", "origin": "Tom and Jerry", "fur": "light-brown"},
            {
                "id": 4,
                "name": "Pluto",
                "origin": "Mickey Mouse",
                "fur": "brown and white",
            },
            {
                "id": 1,
                "name": "Clifford",
                "origin": "Clifford the big red dog",
                "fur": "red",
            },
            {
                "id": 2,
                "name": "Air-Bud",
                "origin": "Air Bud 4: Seventh Inning Fetch",
                "fur": "gold",
            },
        ]
        actual_response = json.loads(response.content.decode("utf-8")).get("dogs")
        self.assertEqual(expected_response, actual_response)

    def test_sort_multiple(self):
        """Test sort multiple."""
        url = "/dogs/?sort[]=-name&sort[]=-origin"
        # 2 queries - one for getting dogs, one for the meta (count)
        with self.assertNumQueries(2):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        expected_response = [
            {"id": 5, "name": "Spike", "origin": "Tom and Jerry", "fur": "light-brown"},
            {"id": 3, "name": "Spike", "origin": "Rugrats", "fur": "brown"},
            {
                "id": 4,
                "name": "Pluto",
                "origin": "Mickey Mouse",
                "fur": "brown and white",
            },
            {
                "id": 1,
                "name": "Clifford",
                "origin": "Clifford the big red dog",
                "fur": "red",
            },
            {
                "id": 2,
                "name": "Air-Bud",
                "origin": "Air Bud 4: Seventh Inning Fetch",
                "fur": "gold",
            },
        ]
        actual_response = json.loads(response.content.decode("utf-8")).get("dogs")
        self.assertEqual(expected_response, actual_response)

    def test_sort_rewrite(self):
        """Test sort rewrite."""
        url = "/dogs/?sort[]=fur"
        # 2 queries - one for getting dogs, one for the meta (count)
        with self.assertNumQueries(2):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        expected_response = [
            {"id": 3, "name": "Spike", "origin": "Rugrats", "fur": "brown"},
            {
                "id": 4,
                "name": "Pluto",
                "origin": "Mickey Mouse",
                "fur": "brown and white",
            },
            {
                "id": 2,
                "name": "Air-Bud",
                "origin": "Air Bud 4: Seventh Inning Fetch",
                "fur": "gold",
            },
            {"id": 5, "name": "Spike", "origin": "Tom and Jerry", "fur": "light-brown"},
            {
                "id": 1,
                "name": "Clifford",
                "origin": "Clifford the big red dog",
                "fur": "red",
            },
        ]
        actual_response = json.loads(response.content.decode("utf-8")).get("dogs")
        self.assertEqual(expected_response, actual_response)

    def test_sort_invalid(self):
        """Test sort invalid."""
        url = "/horses?sort[]=borigin"
        response = self.client.get(url)

        # expected server to throw a 400 if an incorrect
        # sort field is specified
        self.assertEqual(400, response.status_code)


class TestHorsesAPI(TestCase):
    """Tests for sorting on default fields and limit sorting fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()

    def test_sort_custom_default(self):
        """Test sort custom default."""
        url = "/horses"
        # 1 query - one for getting horses
        # (the viewset as features specified, so no meta is returned)
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        # expect the default for horses to be sorted by -name
        expected_response = {
            "horses": [
                {"id": 2, "name": "Secretariat", "origin": "Kentucky"},
                {"id": 1, "name": "Seabiscuit", "origin": "LA"},
            ]
        }
        actual_response = json.loads(response.content.decode("utf-8"))
        self.assertEqual(expected_response, actual_response)

    def test_sort_with_field_not_allowed(self):
        """Test sort with field not allowed."""
        url = "/horses?sort[]=origin"
        response = self.client.get(url)

        # if `ordering_fields` are specified in the viewset, only allow sorting
        # based off those fields. If a field is listed in the url that is not
        # specified, return a 400
        self.assertEqual(400, response.status_code)


class TestZebrasAPI(TestCase):
    """Tests for sorting on when ordering_fields is __all__."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()

    def test_sort_explicit_all(self):
        """Test sort explicit all."""
        url = "/zebras?sort[]=-name"
        # 1 query - one for getting zebras
        # (the viewset as features specified, so no meta is returned)
        with self.assertNumQueries(1):
            response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        # expect sortable on any field on horses because __all__ is specified
        expected_response = {
            "zebras": [
                {"id": 2, "name": "Ted", "origin": "africa"},
                {"id": 1, "name": "Ralph", "origin": "new york"},
            ]
        }
        actual_response = json.loads(response.content.decode("utf-8"))
        self.assertEqual(expected_response, actual_response)


class TestBrowsableAPI(TestCase):
    """Tests for Browsable API directory."""

    def test_get_root(self):
        """Test get root."""
        response = self.client.get("/?format=api")
        content = response.content.decode("utf-8")
        self.assertIn("directory", content)
        self.assertIn("/horses", content)
        self.assertIn("/zebras", content)
        self.assertIn("/users", content)

    def test_get_list(self):
        """Test get list."""
        response = self.client.get("/users/?format=api")
        content = response.content.decode("utf-8")
        self.assertIn("directory", content)
        self.assertIn("/horses", content)
        self.assertIn("/zebras", content)
        self.assertIn("/users", content)


class TestCatsAPI(TestCase):
    """Tests for nested resources."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixture = create_fixture()
        home_id = self.fixture.locations[0].id
        backup_home_id = self.fixture.locations[1].id
        parent = Cat.objects.create(
            name="Parent", home_id=home_id, backup_home_id=backup_home_id
        )
        self.kitten = Cat.objects.create(
            name="Kitten", home_id=home_id, backup_home_id=backup_home_id, parent=parent
        )

    def test_additional_sideloads(self):
        """Test additional side-loads."""
        response = self.client.get(f"/cats/{self.kitten.id}?include[]=parent.")
        content = json.loads(response.content.decode("utf-8"))
        self.assertTrue("cat" in content)
        self.assertTrue("+cats" in content)
        self.assertEqual(content["cat"]["name"], "Kitten")
        self.assertEqual(content["+cats"][0]["name"], "Parent")

    def test_allows_whitespace(self):
        """Test allows whitespace."""
        data = {
            "name": "  Zahaklu  ",
            "home": self.kitten.home_id,
            "backup_home": self.kitten.backup_home_id,
            "parent": self.kitten.parent_id,
        }
        response = self.client.post(
            "/cats/",
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(201, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["cat"]["name"], "  Zahaklu  ")

    def test_immutable_field(self):
        """Make sure immutable 'parent' field can be set on POST."""
        parent_id = self.kitten.parent_id
        kitten_name = "New Kitten"
        data = {
            "name": kitten_name,
            "home": self.kitten.home_id,
            "backup_home": self.kitten.backup_home_id,
            "parent": parent_id,
        }
        response = self.client.post(
            "/cats/", json.dumps(data), content_type="application/json"
        )
        self.assertEqual(201, response.status_code)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["cat"]["parent"], parent_id)
        self.assertEqual(data["cat"]["name"], kitten_name)

        # Try to change immutable data in a PATCH request...
        patch_data = {
            "parent": self.kitten.pk,
            "name": "Renamed Kitten",
        }
        response = self.client.patch(
            f'/cats/{data["cat"]["id"]}/',
            json.dumps(patch_data),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content.decode("utf-8"))

        # ... and it should not have changed:
        self.assertEqual(data["cat"]["parent"], parent_id)
        self.assertEqual(data["cat"]["name"], kitten_name)


class TestFilters(TestCase):
    """Tests for filters."""

    def test_unparseable_int(self):
        """Test unparseable int."""
        url = "/users/?filter{pk}=123x"
        response = self.client.get(url)
        self.assertEqual(400, response.status_code)
