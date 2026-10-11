from src.creator_export import SubscriberUpdate, render_csv


def test_csv_export_contains_business_fields_and_header():
    text = render_csv([SubscriberUpdate("member@example.com", "starter-kit", "active")])
    assert text.splitlines() == [
        "email,product,status",
        "member@example.com,starter-kit,active",
    ]
