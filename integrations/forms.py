from django import forms
from django.core.files import File

from integrations.importers import IMPORTER_MAPPING, GoodreadsImporter, SimklImporter


class ImportTrackingDataForm(forms.Form):
    import_format = forms.ChoiceField(
        choices=(
            (GoodreadsImporter.IMPORTER_NAME, "Goodreads (.csv)"),
            (SimklImporter.IMPORTER_NAME, "Simkl (.csv)"),
        )
    )
    import_file = forms.FileField()

    def clean_import_file(self) -> File:
        importer_class = IMPORTER_MAPPING[self.cleaned_data["import_format"]]
        importer_class.validate_file(self.cleaned_data["import_file"])
        return self.cleaned_data["import_file"]
