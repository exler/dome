from django.urls import path

from entities.views import EntitiesDetailView, EntitiesListView, EntitiesSearchView

app_name = "entities"

urlpatterns = [
    path("search/", EntitiesSearchView.as_view(), name="entities-search"),
    path("<str:entity_type>/", EntitiesListView.as_view(), name="entities-list"),
    path("<str:entity_type>/<int:pk>/", EntitiesDetailView.as_view(), name="entities-detail"),
    path("<str:entity_type>/<int:pk>/<slug:slug>/", EntitiesDetailView.as_view(), name="entities-detail-slug"),
]
