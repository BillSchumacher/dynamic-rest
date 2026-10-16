"""Tests that write-only fields cannot be filtered or sorted on."""
import json
import os
from types import SimpleNamespace
from urllib.parse import quote

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from dynamic_rest.datastructures import FilterNode
from dynamic_rest.fields import DynamicRelationField
from dynamic_rest.filters import DynamicSortingFilter
from dynamic_rest.serializers import DynamicModelSerializer
from tests.models import Cat, Dog

if os.getenv("DATABASE_URL"):
    from tests.test_cases import ResetAPITestCase as TestCase
else:
    from tests.test_cases import APITestCase as TestCase


class WriteOnlyFieldsTestCase(TestCase):
    """Test case for write-only serializer fields."""

    def setUp(self):
        """Set up test case."""
        for name, fur_color in (("a", "red"), ("b", "gold"), ("c", "brown")):
            Dog.objects.create(name=name, fur_color=fur_color, origin="x")

    def _get(self, url, expected_status):
        """GET a URL and return the decoded JSON body."""
        response = self.client.get(url)
        self.assertEqual(expected_status, response.status_code, response.content)
        return json.loads(response.content)

    def test_filter_on_a_write_only_field_is_rejected(self):
        """Test a write-only field cannot be used to probe values."""
        complex_filter = quote(json.dumps({"fur": "red"}))
        for query in (
            "filter{fur}=red",
            "filter{fur.startswith}=r",
            "filter{fur.icontains}=o",
            "filter{-fur}=red",
            "filter{fur.in}=red&filter{fur.in}=gold",
            f"filter{{}}={complex_filter}",
        ):
            with self.subTest(query=query):
                body = self._get(f"/secret_dogs/?{query}", 400)
                self.assertIn("Invalid filter field: fur", body[0])

    def test_sort_on_a_write_only_field_is_rejected(self):
        """Test a write-only field cannot be used to order and so leak values."""
        for term in ("fur", "-fur"):
            with self.subTest(term=term):
                body = self._get(f"/secret_dogs/?sort[]={term}", 400)
                self.assertIn("Invalid filter field", body[0])

    def test_readable_fields_can_still_be_filtered_and_sorted(self):
        """Test fields that are not write-only are unaffected."""
        body = self._get("/secret_dogs/?filter{name}=b", 200)
        self.assertEqual(["b"], [dog["name"] for dog in body["secret_dogs"]])

        body = self._get("/secret_dogs/?sort[]=-name", 200)
        self.assertEqual(["c", "b", "a"], [dog["name"] for dog in body["secret_dogs"]])

    def test_write_only_fields_are_not_rendered(self):
        """Test the write-only field is still absent from responses."""
        body = self._get("/secret_dogs/", 200)
        for dog in body["secret_dogs"]:
            self.assertNotIn("fur", dog)


class HiddenHomeCatSerializer(DynamicModelSerializer):
    """Serializer whose relation to another serializer is write-only."""

    class Meta:
        """Meta class."""

        model = Cat
        name = "hidden_home_cat"
        fields = ("id", "name", "home")

    home = DynamicRelationField("tests.serializers.LocationSerializer", write_only=True)


class WriteOnlyRelationTestCase(SimpleTestCase):
    """Test case for write-only relations."""

    def test_filter_through_a_write_only_relation_is_rejected(self):
        """Test a filter cannot reach fields behind a write-only relation."""
        node = FilterNode(["home", "name"], None, "x")
        with self.assertRaises(ValidationError):
            node.generate_query_key(HiddenHomeCatSerializer())

    def test_sort_through_a_write_only_relation_is_rejected(self):
        """Test ordering cannot reach fields behind a write-only relation."""
        view = SimpleNamespace(serializer_class=HiddenHomeCatSerializer)
        ordering = DynamicSortingFilter().ordering_for("home.name", view)
        self.assertIsNone(ordering)
