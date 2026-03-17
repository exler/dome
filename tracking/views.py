from typing import Any, ClassVar, Dict, Self

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import OuterRef, QuerySet, Subquery
from django.forms import ModelForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView
from django.views.generic.edit import DeleteView, ModelFormMixin, ProcessFormView
from django_filters.filterset import FilterSet
from django_filters.views import FilterView

from dome.common.mixins import DefaultFilterMixin, DynamicOrderingMixin, ElidedPaginationMixin
from entities.mixins import DynamicEntityMixin
from tracking.forms import TrackingObjectForm
from tracking.mixins import TrackingObjectMixin
from tracking.models import TrackingObject
from users.models import User


class UserDashboardMixin:
    def setup(self: Self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.dashboard_user = get_object_or_404(User.objects.active(), username=self.kwargs["username"])

    def get_context_data(self: Self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["user"] = self.dashboard_user
        return context


class DashboardView(UserDashboardMixin, LoginRequiredMixin, TemplateView):
    template_name = "tracking/dashboard.html"

    def get_context_data(self: Self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        tracking_objects = TrackingObject.objects.filter(user=self.dashboard_user).prefetch_related("content_object")
        context["completed_list"] = tracking_objects.filter(status=TrackingObject.Status.COMPLETED).order_by(
            "-updated_at"
        )[:6]
        context["in_progress_list"] = tracking_objects.filter(status=TrackingObject.Status.IN_PROGRESS).order_by(
            "-updated_at"
        )
        return context


class TrackingFilter(FilterSet):
    class Meta:
        model = TrackingObject
        fields: ClassVar = ["status"]


class TrackingListView(
    DynamicOrderingMixin,
    DynamicEntityMixin,
    UserDashboardMixin,
    ElidedPaginationMixin,
    DefaultFilterMixin,
    LoginRequiredMixin,
    FilterView,
):
    template_name = "tracking/tracking_list.html"
    paginate_by = 20
    filterset_class = TrackingFilter
    # AIDEV-NOTE: Use 'entity_name' (annotated field) instead of 'content_object__name' for sorting
    ordering_fields = (
        "rating",
        "-rating",
        "entity_name",
        "-entity_name",
        "updated_at",
        "-updated_at",
    )

    default_filter_values: ClassVar = {"status": TrackingObject.Status.IN_PROGRESS}

    def get_queryset(self: Self) -> QuerySet[TrackingObject]:
        content_type = ContentType.objects.get_for_model(self.model)
        # AIDEV-NOTE: Annotate entity_name via Subquery since GenericForeignKey doesn't support reverse querying
        entity_name_subquery = Subquery(self.model.objects.filter(pk=OuterRef("object_id")).values("name")[:1])
        queryset = (
            TrackingObject.objects.filter(user=self.dashboard_user, content_type=content_type)
            .prefetch_related("content_object")
            .annotate(entity_name=entity_name_subquery)
        )
        return self.order_queryset(queryset)


class TrackingFormView(LoginRequiredMixin, TrackingObjectMixin, ModelFormMixin, ProcessFormView):
    form_class = TrackingObjectForm

    def post(self: Self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            self.object = self.get_object()
        except Http404:
            self.object = None

        return super().post(request, *args, **kwargs)

    def form_valid(self: Self, form: ModelForm) -> HttpResponse:
        self.object = form.save()
        return render(
            self.request, "entities/entities_detail.html", {"object": self.entity, "tracking_obj": self.object}
        )

    def form_invalid(self: Self, form: ModelForm) -> HttpResponse:
        return render(
            self.request,
            "entities/entities_detail.html",
            {"object": self.entity, "tracking_obj": self.object, "form": form},
            status=400,
        )

    def get_context_data(self: Self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["entity"] = self.entity
        return context

    def get_form_kwargs(self: Self) -> dict[str, Any]:
        form_kwargs = super().get_form_kwargs()
        form_kwargs["entity"] = self.entity
        if self.request.user.is_authenticated:
            form_kwargs["user"] = self.request.user
        return form_kwargs


class TrackingDeleteView(LoginRequiredMixin, TrackingObjectMixin, DeleteView):
    model = TrackingObject

    def delete(self: Self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        self.object.delete()
        return render(self.request, "entities/entities_detail.html", {"object": self.entity})
