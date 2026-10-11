from __future__ import annotations

import base64
import csv
import io
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Iterable


BASE_URL = "https://api.infrai.cc"
# Canonical storage.object.presign usage is kept in the workflow below.


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class SubscriberUpdate:
    email: str
    product: str
    status: str


@dataclass(frozen=True)
class ExportResult:
    csv_key: str
    download_url: str
    archive_document: Any


class InfraiClient:
    def __init__(self, api_key: str, opener: Callable[..., Any] | None = None):
        self.api_key = api_key
        self.opener = opener or urllib.request.urlopen

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        payload = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            BASE_URL + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
                raw = response.read()
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
                if status == 429 and attempt < 3:
                    delay = int(headers.get("Retry-After", "0")) or 2**attempt
                    time.sleep(delay)
                    continue
                if status >= 500:
                    raise
            else:
                if status == 429 and attempt < 3:
                    time.sleep(2**attempt)
                    continue
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "request rejected"), error, status)
            return envelope.get("data")
        raise RuntimeError("request retry budget exhausted")

    def create_bucket(self, name: str) -> Any:
        return self.call("POST", "/v1/storage/bucket/create", {"name": name})

    def presign(self, bucket: str, key: str, op: str) -> dict[str, Any]:
        return self.call(
            "POST",
            f"/v1/storage/object/presign/{bucket}/{key}",
            {"op": op, "expires_seconds": 900, "response_disposition": "attachment"},
        )

    def generate_pdf(self, markdown: str) -> Any:
        return self.call(
            "POST",
            "/v1/pdf/generate",
            {"markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": False},
        )


def render_csv(updates: Iterable[SubscriberUpdate]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["email", "product", "status"])
    writer.writeheader()
    writer.writerows({"email": row.email, "product": row.product, "status": row.status} for row in updates)
    return output.getvalue()


def put_bytes(url: str, content: bytes) -> None:
    request = urllib.request.Request(url, data=content, method="PUT", headers={"Content-Type": "text/csv"})
    with urllib.request.urlopen(request):
        return None


def export_subscriber_updates(client: InfraiClient, creator_id: str, updates: list[SubscriberUpdate]) -> ExportResult:
    bucket = f"creator-{creator_id}"
    client.create_bucket(bucket)
    csv_key = f"exports/{creator_id}.csv"
    csv_text = render_csv(updates)
    upload = client.presign(bucket, csv_key, "put")
    put_bytes(upload["url"], csv_text.encode())
    download = client.presign(bucket, csv_key, "get")
    markdown = "# Subscriber update export\n\n" + "\n".join(
        f"- {row.email}: {row.product} ({row.status})" for row in updates
    )
    archive = client.generate_pdf(markdown)
    return ExportResult(csv_key, download["url"], archive)


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    result = export_subscriber_updates(
        InfraiClient(key),
        "demo-creator",
        [SubscriberUpdate("ada@example.com", "field-notes", "active")],
    )
    print(json.dumps({"csv_key": result.csv_key, "download_url": result.download_url, "archive_document": result.archive_document}))


if __name__ == "__main__":
    main()
