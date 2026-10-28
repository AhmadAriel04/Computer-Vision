"""
CVClient

Client komunikasi antara Computer Vision dengan
BSI Survey Monitor Laravel.

Endpoint:
    POST /api/cv/sessions

Authentication:
    X-CV-Token

Catatan:
    CVClient hanya bertugas mengirim hasil session.
    Penentuan apakah session membutuhkan konfirmasi
    dilakukan oleh Laravel berdasarkan confidence threshold.
"""

import time

import requests

from app.utils.config import (
    API_BASE_URL,
    API_ENDPOINT,
    API_TOKEN,
    API_TIMEOUT,
    API_MAX_RETRIES,
)


class CVClient:

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        endpoint: str = API_ENDPOINT,
        token: str = API_TOKEN,
        timeout: float = API_TIMEOUT,
        max_retries: int = API_MAX_RETRIES,
    ):

        self.url = (
            base_url.rstrip("/")
            + endpoint
        )

        self.timeout = timeout

        self.max_retries = max(
            1,
            int(max_retries)
        )

        self.session = requests.Session()

        self.session.headers.update({

            "Accept": "application/json",

            "Content-Type": "application/json",

        })

        if token:

            self.session.headers["X-CV-Token"] = token

        else:

            print(
                "[CVClient] PERINGATAN: "
                "CV_API_TOKEN belum diatur."
            )

    # ==========================================================
    # SEND SESSION
    # ==========================================================

    def send_session(
        self,
        payload: dict,
    ) -> dict | None:
        """
        Mengirim hasil session ke Laravel.

        Return:
            dict response Laravel jika berhasil.
            None jika gagal.

        Error jaringan tidak akan menghentikan
        main loop Computer Vision.
        """

        session_uid = payload.get(
            "session_uid",
            "unknown"
        )

        for attempt in range(
            1,
            self.max_retries + 1
        ):

            try:

                print(
                    f"[CVClient] Mengirim session "
                    f"{session_uid} "
                    f"(percobaan "
                    f"{attempt}/{self.max_retries})..."
                )

                response = self.session.post(

                    self.url,

                    json=payload,

                    timeout=self.timeout,
                )

                # --------------------------------------------------
                # Client error
                # --------------------------------------------------

                if 400 <= response.status_code < 500:

                    print(
                        f"[CVClient] Server menolak request "
                        f"HTTP {response.status_code}: "
                        f"{response.text[:500]}"
                    )

                    return None

                # --------------------------------------------------
                # Server error
                # --------------------------------------------------

                if response.status_code >= 500:

                    print(
                        f"[CVClient] Server error "
                        f"HTTP {response.status_code}"
                    )

                    if attempt < self.max_retries:

                        time.sleep(0.5)

                        continue

                    return None

                # --------------------------------------------------
                # Success
                # --------------------------------------------------

                response.raise_for_status()

                if not response.content:

                    return {}

                data = response.json()

                print(
                    f"[CVClient] Session "
                    f"{session_uid} berhasil dikirim."
                )

                return data

            except requests.exceptions.RequestException as error:

                print(
                    f"[CVClient] Gagal mengirim session "
                    f"{session_uid}: {error}"
                )

                if attempt < self.max_retries:

                    time.sleep(0.5)

                    continue

                return None

            except ValueError as error:

                print(
                    f"[CVClient] Response Laravel "
                    f"bukan JSON yang valid: {error}"
                )

                return None

        return None