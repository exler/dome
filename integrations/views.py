from datetime import datetime
from typing import Self

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import FormView, View

from integrations.exporters import Exporter
from integrations.forms import ImportTrackingDataForm
from integrations.importers import IMPORTER_MAPPING


class ImportTrackingDataView(LoginRequiredMixin, FormView):
    template_name = "integrations/import_tracking_data.html"

    form_class = ImportTrackingDataForm

    success_url = reverse_lazy("integrations:import-tracking-data")

    def form_valid(self: Self, form: ImportTrackingDataForm) -> HttpResponse:
        importer_class = IMPORTER_MAPPING[form.cleaned_data["import_format"]]
        importer = importer_class(self.request.user, form.cleaned_data["import_file"])
        importer.run()

        messages.add_message(self.request, messages.SUCCESS, "Your tracking data has been imported.")

        return super().form_valid(form)


class ExportTrackingDataView(LoginRequiredMixin, View):
    def get(self: Self, request: HttpRequest) -> HttpResponse:
        exporter = Exporter(request.user, f"dome_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        return exporter.get_streaming_response()
