import requests
from django.conf import settings


class KnowBe4Client:
    def __init__(self):
        self.base_url = settings.KNOWBE4_API_URL
        self.headers = {
            "Authorization": f"Bearer {settings.KNOWBE4_API_KEY}",
            "Content-Type": "application/json",
        }

    def get_enrollments_delta(self, since: str) -> list:
        resp = requests.get(
            f"{self.base_url}/v1/training/enrollments",
            headers=self.headers,
            params={"since": since},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_phishing_results(self, since: str) -> list:
        resp = requests.get(
            f"{self.base_url}/v1/phishing/security-tests",
            headers=self.headers,
            params={"since": since},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def provision_user(self, user, groups: list[str]) -> dict:
        payload = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "groups": groups,
        }
        resp = requests.post(
            f"{self.base_url}/v1/users",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def deprovision_user(self, email: str) -> None:
        resp = requests.patch(
            f"{self.base_url}/v1/users/{email}",
            headers=self.headers,
            json={"status": "archived"},
            timeout=30,
        )
        resp.raise_for_status()

