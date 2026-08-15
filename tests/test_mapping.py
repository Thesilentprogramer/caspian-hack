from __future__ import annotations

import time

import pytest

from privacy_guard._mapping import MappingStore
from privacy_guard.types import MappingExpired


def test_round_trip_encrypts_and_decrypts() -> None:
    store = MappingStore()
    mid = store.create()
    store.put(mid, "[EMAIL_AAAA]", "ada@example.com")
    assert store.get_all(mid) == {"[EMAIL_AAAA]": "ada@example.com"}


def test_values_are_not_stored_as_plaintext() -> None:
    store = MappingStore()
    mid = store.create()
    store.put(mid, "[API_KEY_BBBB]", "sk_live_abc123")
    blob = store._maps[mid].values["[API_KEY_BBBB]"]
    assert b"sk_live_abc123" not in blob


def test_instances_do_not_share_mappings() -> None:
    a = MappingStore()
    mid = a.create()
    a.put(mid, "[EMAIL_X]", "a@b.com")
    b = MappingStore()
    with pytest.raises(MappingExpired):
        b.get_all(mid)


def test_unknown_mapping_id_expires() -> None:
    store = MappingStore()
    with pytest.raises(MappingExpired):
        store.get_all("missing")


def test_ttl_expiry_with_injected_clock() -> None:
    clock = {"now": 100.0}

    def now() -> float:
        return clock["now"]

    store = MappingStore(ttl_seconds=10, clock=now)
    mid = store.create()
    store.put(mid, "[IP_ADDRESS_1]", "192.168.1.105")
    assert store.get_all(mid)["[IP_ADDRESS_1]"] == "192.168.1.105"
    clock["now"] = 111.0
    with pytest.raises(MappingExpired):
        store.get_all(mid)
    assert len(store) == 0


def test_len_drops_expired() -> None:
    clock = {"now": 0.0}
    store = MappingStore(ttl_seconds=5, clock=lambda: clock["now"])
    store.create()
    assert len(store) == 1
    clock["now"] = 6.0
    assert len(store) == 0


def test_store_survives_within_ttl() -> None:
    clock = {"now": time.monotonic()}
    store = MappingStore(ttl_seconds=60, clock=lambda: clock["now"])
    mid = store.create()
    store.put(mid, "[PHONE_1]", "555-0100")
    clock["now"] += 30
    assert store.get_all(mid)["[PHONE_1]"] == "555-0100"
