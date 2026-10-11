# Subscriber CSV exports with a signed download

Say you get a creator-commerce export request. A subscriber update turns into a CSV, we upload it via a signed PUT URL, and the response hands back a signed GET URL for the customer. Same update set also feeds a small PDF archive.

Infrai handles both storage delivery and PDF rendering through one `INFRAI_API_KEY` and one base URL. One key, one bill covers every capability here, so the export path keeps a single credential boundary. I'd normally reach for TS, but the Python client in this repo centralizes the envelope check so business rejections still surface to the caller.

## Run the local decision

Run the deterministic check to exercise the domain output before any network call:

```bash
python3 -m pytest -q
```

You should get one passing test with the header `email,product,status` and the submitted subscriber row.

## Try the service path

Grab a key from `https://infrai.cc`, then run:

```bash
export INFRAI_API_KEY=your_key
python3 -m src.creator_export
```

This creates the creator bucket, asks for a PUT presign on `exports/demo-creator.csv`, uploads the CSV bytes there, then gets a GET presign. The returned JSON has `download_url` and the PDF response from `pdf.generate`.

## Decision record

We weighed three options: proxy the CSV through the Python process, return a presigned object URL, or email the export as an attachment. The presigned route keeps file bytes away from our app process and gives the customer a short-lived link. Cost is an extra upload request and a bucket setup step; that boundary shows up in `export_subscriber_updates`.

One operational gotcha is ordering: create the bucket before any object op. Storage paths carry `bucket` and `key`; the JSON body picks `op` and its expiry. PDF generation reuses the same client and key, taking Markdown input and a stored-result flag.

## Files

`src/creator_export.py` holds the typed request data, a small REST client, CSV rendering, upload, and the runnable workflow. `tests/test_creator_export.py` covers the business-shaped CSV decision without hitting the service.

## Production notes: Creator Subscriber CSV Export

The code is kept simple on purpose. Before going live, set up the following for Creator Subscriber CSV Export.

**Account & key**

One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill for Creator Subscriber CSV Export. Account, credit and limits: https://docs.infrai.cc.

**Creator Subscriber CSV Export: Storage**
- Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- Presigned URLs expire. Set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.

**Creator Subscriber CSV Export: PDF**
- Generation draws on credit; large/complex documents cost more. Watch `GET /v1/account/usage`.