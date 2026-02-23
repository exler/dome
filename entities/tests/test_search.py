from typing import Iterable, Self
from unittest import expectedFailure

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import RequestFactory, TestCase
from django.urls import reverse

from entities.factories import BookFactory, GameFactory, MovieFactory, ShowFactory
from entities.models import EntityBase, MovieTag
from entities.views import EntitiesSearchView

User = get_user_model()


class SearchTestCase(TestCase):
    @classmethod
    def setUpTestData(cls: type[Self]) -> None:
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(username="testuser", password="12345")  # noqa: S106

        MovieFactory(name="The Matrix")
        MovieFactory(name="The Matrix Reloaded")
        ShowFactory(name="Dexter")
        ShowFactory(name="The IT Crowd")
        GameFactory(name="The Witcher 3: Wild Hunt")
        GameFactory(name="Ghost of Tsushima")
        BookFactory(name="Atomic Habits")
        BookFactory(name="The Invincible")

    def _make_search_query(self: Self, query: str) -> str:
        request = self.factory.get(reverse("entities:entities-search"), query_params={"search": query})
        request.user = self.user

        queryset = EntitiesSearchView(request=request).get_queryset()
        return queryset

    def _assert_results_desired(self: Self, queryset: QuerySet[EntityBase], expected_results: Iterable[str]) -> None:
        self.assertCountEqual([x.name for x in queryset], expected_results)

    def test_search_exact_match(self: Self) -> None:
        queryset = self._make_search_query("The Witcher 3: Wild Hunt")
        self._assert_results_desired(queryset, ["The Witcher 3: Wild Hunt"])

    def test_search_partial_match(self: Self) -> None:
        queryset = self._make_search_query("Matrix")
        self._assert_results_desired(queryset, ["The Matrix Reloaded", "The Matrix"])

    # Fuzzy search not implemented yet
    # def test_search_typo(self: Self) -> None:
    #     queryset = self._make_search_query("Dextre")
    #     self._assert_results_desired(queryset, ["Dexter"])

    def test_search_no_results(self: Self) -> None:
        queryset = self._make_search_query("Non-existent")
        self._assert_results_desired(queryset, [])

    def test_search_multiple_entity_types(self: Self) -> None:
        queryset = self._make_search_query("The")
        types = {type(x) for x in queryset}
        self.assertTrue(len(types) > 1)

    def test_search_by_alias(self: Self) -> None:
        MovieFactory(name="Justice", aliases=["Napad"])
        queryset = self._make_search_query("Napad")
        self._assert_results_desired(queryset, ["Justice"])

    @expectedFailure
    def test_search_by_polish_name_and_alias(self) -> None:
        MovieFactory(name="Za duży na bajki")
        MovieFactory(name="Too Old for Fairy Tales 2", aliases=["Za duży na bajki 2"])

        queryset = self._make_search_query("Za duży")
        self._assert_results_desired(queryset, ["Za duży na bajki", "Too Old for Fairy Tales 2"])


class TagFilterTestCase(TestCase):
    @classmethod
    def setUpTestData(cls: type[Self]) -> None:
        cls.user = User.objects.create_user(username="taguser", password="12345")  # noqa: S106
        cls.tag_action = MovieTag.objects.create(name="Action")
        cls.tag_sci_fi = MovieTag.objects.create(name="Sci-Fi")
        cls.tag_drama = MovieTag.objects.create(name="Drama")

        cls.movie_both = MovieFactory(name="Both Tags")
        cls.movie_both.tags.add(cls.tag_action, cls.tag_sci_fi)

        cls.movie_one = MovieFactory(name="One Tag")
        cls.movie_one.tags.add(cls.tag_action)

        cls.movie_other = MovieFactory(name="Other Tag")
        cls.movie_other.tags.add(cls.tag_drama)

    def test_tag_filter_requires_all_selected_tags(self: Self) -> None:
        response = self.client.get(reverse("entities:entities-list", args=["movies"]), {"tags": ["Action", "Sci-Fi"]})
        self.assertEqual(response.status_code, 200)
        results = [obj.name for obj in response.context["page_obj"]]
        self.assertCountEqual(results, ["Both Tags"])
