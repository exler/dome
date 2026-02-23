from itertools import chain
from typing import Any, Self

from django.contrib.contenttypes.models import ContentType
from django.db.models import OuterRef, QuerySet, Subquery
from django.urls import reverse
from django.views.generic import DetailView, ListView
from django_filters.filterset import FilterSet
from django_filters.views import FilterView

from dome.common.mixins import ElidedPaginationMixin
from entities.filters import EntitySearchFilter
from entities.mappings import ENTITY_MODEL_TO_FILTER_MAPPING
from entities.mixins import DynamicEntityMixin
from entities.models import Book, EntityBase, Game, Movie, Show
from tracking.models import TrackingObject


class EntitiesListView(ElidedPaginationMixin, DynamicEntityMixin, FilterView):
    """
    View for rendering a list of entities of a type passed in the URL.
    """

    template_name = "entities/entities_list.html"

    paginate_by = 20

    def get_filterset_class(self: Self) -> type[FilterSet]:
        return ENTITY_MODEL_TO_FILTER_MAPPING[self.model]

    def get_queryset(self: Self) -> QuerySet[EntityBase]:
        """
        Get queryset based on entity type passed in URL.
        Annotate with tracking status if user is authenticated.
        """
        queryset = super().get_queryset()

        if self.request.user.is_authenticated:
            # Get content type for this entity model
            content_type = ContentType.objects.get_for_model(self.model)

            # Subquery to get tracking status for each entity
            tracking_status = TrackingObject.objects.filter(
                user=self.request.user, content_type=content_type, object_id=OuterRef("pk")
            ).values("status")[:1]

            queryset = queryset.annotate(tracking_status=Subquery(tracking_status))

        return queryset

    def get_context_data(self: Self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        tag_model = self.model._meta.get_field("tags").related_model
        context["tag_options"] = list(tag_model.objects.order_by("name").values_list("name", flat=True))
        selected_tags = self.request.GET.getlist("tags")
        if not selected_tags:
            raw_value = self.request.GET.get("tags", "")
            selected_tags = [item.strip() for item in raw_value.split(",") if item.strip()]
        context["selected_tags"] = selected_tags
        context["search_query"] = self.request.GET.get("search", "")
        return context


class EntitiesDetailView(DynamicEntityMixin, DetailView):
    template_name = "entities/entities_detail.html"

    def get_queryset(self: Self) -> QuerySet[EntityBase]:
        """
        Get queryset based on entity type passed in URL.
        """

        return super().get_queryset()

    def get_context_data(self: Self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            try:
                tracking_obj = TrackingObject.objects.get(
                    object_id=self.object.id,
                    content_type=ContentType.objects.get_for_model(self.object),
                    user=self.request.user,
                )
            except TrackingObject.DoesNotExist:
                tracking_obj = None
        else:
            tracking_obj = None

        context["tracking_obj"] = tracking_obj
        context["edit_url"] = reverse(
            f"admin:entities_{context['entity_type_normalized']}_change", args=[self.object.id]
        )
        return context


class EntitiesSearchView(ListView):
    template_name = "entities/entities_search.html"

    def _prepare_queryset(self, model: type[EntityBase]) -> QuerySet[EntityBase]:
        filtered_qs = EntitySearchFilter(
            self.request.GET,
            queryset=model.objects.all(),
        ).qs

        # Add tracking status if user is authenticated
        if self.request.user.is_authenticated:
            content_type = ContentType.objects.get_for_model(model)
            tracking_status = TrackingObject.objects.filter(
                user=self.request.user, content_type=content_type, object_id=OuterRef("pk")
            ).values("status")[:1]

            filtered_qs = filtered_qs.annotate(tracking_status=Subquery(tracking_status))

        # Remove any ordering before combining
        return filtered_qs.order_by()

    def get_queryset(self) -> QuerySet[EntityBase]:
        """
        Overriding `get_queryset` with filters because it is not possible
        to use `.annotate` (required for the ranking) after `.union`.
        """

        if not self.request.GET.get("search"):
            # If no search query is provided, just return an empty list
            # to focus on rendering the page
            return []

        # Get querysets for each model type
        movie_qs = self._prepare_queryset(Movie)
        show_qs = self._prepare_queryset(Show)
        game_qs = self._prepare_queryset(Game)
        book_qs = self._prepare_queryset(Book)

        # Combine all querysets - note: cannot use union() with full models
        # so we'll chain them instead
        combined = list(chain(movie_qs, show_qs, game_qs, book_qs))

        return combined

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        return context
