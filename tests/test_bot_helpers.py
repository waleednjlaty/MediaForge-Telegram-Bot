from app.referral import parse_ref


def test_parse_ref():
    assert parse_ref("/start ref_12345") == 12345
    assert parse_ref("/start") is None
    assert parse_ref("/start ref_bad") is None
