"""
APIClient

Mengirim ringkasan sesi (yang sudah melewati ScoreAggregator +
ConfidenceEngine) ke Laravel Monitor via POST /api/cv/sessions,
memakai Bearer token statis (CV_API_TOKEN).

Prinsip penting: kegagalan jaringan / server Laravel TIDAK BOLEH
menghentikan main loop computer vision. Semua exception ditangkap di
sini, hanya dicatat ke console, lalu None dikembalikan.
"""

import requests

from app.utils.config import (
    API_BASE_URL,
    API_ENDPOINT,
    API_TOKEN,
    API_TIMEOUT,
    API_MAX_RETRIES,
)


class APIClient:

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        endpoint: str = API_ENDPOINT,
        token: str = API_TOKEN,
        timeout: float = API_TIMEOUT,
        max_retries: int = API_MAX_RETRIES,
    ):
        self.url = base_url.rstrip("/") + endpoint
        self.timeout = timeout
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            print(
                "[APIClient] PERINGATAN: CV_API_TOKEN kosong. "
                "Request ke Laravel akan dikirim tanpa Authorization header."
            )

    def send_session(self, payload: dict) -> dict | None:
        """
        POST payload sesi ke Laravel. Retry sederhana (tanpa backoff)
        sebanyak `max_retries` kali kalau gagal karena masalah jaringan
        atau status 5xx. Tidak retry untuk error 4xx (client error --
        payload/token yang salah, retry tidak akan membantu).
        """

        last_error = None

        for attempt in range(1, self.max_retries + 1):

            try:
                response = self.session.post(
                    self.url,
                    json=payload,
                    timeout=self.timeout,
                )

                if 400 <= response.status_code < 500:
                    print(
                        f"[APIClient] Ditolak server ({response.status_code}): "
                        f"{response.text[:300]}"
                    )
                    return None

                response.raise_for_status()

                return response.json() if response.content else {}

            except requests.exceptions.RequestException as error:
                last_error = error
                print(
                    f"[APIClient] Percobaan {attempt}/{self.max_retries} gagal: {error}"
                )

        print(f"[APIClient] Gagal mengirim sesi {payload.get('face_id')} ke {self.url}: {last_error}")
        return None
