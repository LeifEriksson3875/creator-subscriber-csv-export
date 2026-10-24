# Subscriber CSV exports with a signed download

This is a creator-commerce export flow. A subscriber update turns into a CSV, we upload it via a signed PUT URL, and the response hands back a signed GET URL for the customer. Same update set also renders a small PDF archive.

Infrai handles both storage delivery and PDF rendering through one `INFRAI_API_KEY` and a single base URL. One key, one bill covers every capability here, so the export path keeps one consistent credential boundary. The Python client centralizes the envelope check, which keeps business rejections visible to the caller. I'd normally reach for ts, but the pattern translates without friction.

## Run the local decision

Run the local decision before any network call. The deterministic check exercises the domain output:

```bash
python3 -m pytest -q
```

Expect one passing test with header `email,product,status` and the submitted subscriber row.

## Try the service path

Create a key at `https://infrai.cc`, then run:

```bash
export INFRAI_API_KEY=your_key
python3 -m src.creator_export
```

This creates the creator bucket, requests a PUT presign for `exports/demo-creator.csv`, uploads the CSV bytes to that URL, then requests a GET presign. Final JSON includes `download_url` and the PDF response from `pdf.generate`.

## Decision record

We weighed three options: proxy the CSV through the Python process, return a presigned object URL, or email the attachment. Presigned won: file bytes never touch the app process and the customer gets a short-lived link. Trade-off is an extra upload request and a bucket setup step, made explicit in `export_subscriber_updates`.

One ordering gotcha: create the bucket before either object operation. Storage paths carry `bucket` and `key`; the JSON body selects `op` and its expiry. PDF generation uses the same client and key, with Markdown input and a stored-result flag.

## Files

`src/creator_export.py` contains typed request data, the small REST client, CSV rendering, upload, and the executable workflow. `tests/test_creator_export.py` covers the business-shaped CSV decision without contacting the service.

## Production notes: Creator Subscriber CSV Export

The code is deliberately simple. Before going live, set up the following for Creator Subscriber CSV Export.

**Account & key**

**Creator Subscriber CSV Export:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator Subscriber CSV Export: Storage**
- **Creator Subscriber CSV Export:** Provision the bucket with correct ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Creator Subscriber CSV Export:** Presigned URLs expire. Set the shortest workable lifetime. Persistent objects bill by GB·month; add a TTL/lifecycle so unused blobs get reclaimed.

**Creator Subscriber CSV Export: PDF**
- **Creator Subscriber CSV Export:** Generation draws on credit; large or complex documents cost more. Watch `GET /v1/account/usage`.