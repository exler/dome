from typing import ClassVar, Self

import django_filters
from django.db.models import Q, QuerySet
from django_filters.filterset import FilterSet

from entities.models import Book, EntityBase, Game, Movie, Show


class EntityBaseFilter(FilterSet):
    search = django_filters.CharFilter(method="search_filter")
    tags = django_filters.CharFilter(method="tags_filter")

    class Meta:
        fields: ClassVar = ["search", "tags"]

    def search_filter(self: Self, queryset: QuerySet[EntityBase], name: str, value: str) -> QuerySet[EntityBase]:
        return queryset.filter(Q(name__icontains=value) | Q(aliases__icontains=value))

    def tags_filter(self: Self, queryset: QuerySet[EntityBase], name: str, value: str) -> QuerySet[EntityBase]:
        raw_values = self.data.getlist("tags")
        if not raw_values and value:
            raw_values = [item.strip() for item in value.split(",") if item.strip()]

        for tag_value in raw_values:
            queryset = queryset.filter(tags__name__iexact=tag_value)

        return queryset.distinct()


class MovieFilter(EntityBaseFilter):
    class Meta(EntityBaseFilter.Meta):
        model = Movie


class ShowFilter(EntityBaseFilter):
    class Meta(EntityBaseFilter.Meta):
        model = Show


class GameFilter(EntityBaseFilter):
    class Meta(EntityBaseFilter.Meta):
        model = Game


class BookFilter(EntityBaseFilter):
    class Meta(EntityBaseFilter.Meta):
        model = Book


class EntitySearchFilter(FilterSet):
    search = django_filters.CharFilter(method="search_filter")

    class Meta:
        fields: ClassVar = ["search"]

    def search_filter(self: Self, queryset: QuerySet[EntityBase], name: str, value: str) -> QuerySet[EntityBase]:
        return queryset.filter(Q(name__icontains=value) | Q(aliases__icontains=value))
