from io import BytesIO

import requests


class OpenLibraryClient:
    BASE_API_URL = "https://openlibrary.org"
    BASE_COVERS_URL = "https://covers.openlibrary.org"

    def __init__(self) -> None:
        self.session = requests.Session()

    def search(self, query: str) -> dict:
        url = f"{self.BASE_API_URL}/search.json"
        params = {
            "title": query,
            "language": "eng",
            "fields": "key,author_name,cover_i,first_publish_year,publish_date,subject,id_goodreads",
            "limit": 1,
        }

        response = self.session.get(url, params=params, timeout=5)
        return response.json()

    def get_work_details(self, work_key: str) -> dict:
        url = f"{self.BASE_API_URL}{work_key}.json"

        response = self.session.get(url, timeout=5)
        return response.json()

    def get_cover_image(self, cover_id: int, size: str = "L") -> BytesIO:
        url = f"{self.BASE_COVERS_URL}/b/id/{cover_id}-{size}.jpg"

        response = self.session.get(url, timeout=5)
        return BytesIO(response.content)


open_library_client = OpenLibraryClient()
