"""GlossaryRepository CRUD + search."""

from __future__ import annotations

import pytest


def test_create_then_get(glossary_repo):
    entry = glossary_repo.create(
        source_lang="ru",
        target_lang="tk",
        source_text="доставка",
        target_text="eltip bermek",
    )
    assert entry.id
    fetched = glossary_repo.get(entry.id)
    assert fetched is not None
    assert fetched.source_text == "доставка"
    assert fetched.target_text == "eltip bermek"


def test_create_rejects_empty_text(glossary_repo):
    with pytest.raises(ValueError):
        glossary_repo.create(
            source_lang="ru", target_lang="tk", source_text="", target_text="x"
        )


def test_list_filters_by_pair_and_query(glossary_repo):
    glossary_repo.create(source_lang="ru", target_lang="tk", source_text="доставка", target_text="eltip bermek")
    glossary_repo.create(source_lang="ru", target_lang="tk", source_text="заказ", target_text="sargyt")
    glossary_repo.create(source_lang="ru", target_lang="en", source_text="заказ", target_text="order")

    ru_tk = glossary_repo.list(source_lang="ru", target_lang="tk")
    assert {e.source_text for e in ru_tk} == {"доставка", "заказ"}

    found = glossary_repo.list(query="dostavka")
    assert found == []
    found = glossary_repo.list(query="достав")
    assert any(e.source_text == "доставка" for e in found)


def test_update(glossary_repo):
    entry = glossary_repo.create(
        source_lang="ru", target_lang="tk", source_text="курьер", target_text="kuryer"
    )
    updated = glossary_repo.update(entry.id, target_text="kurýer", note="fixed")
    assert updated is not None
    assert updated.target_text == "kurýer"
    assert updated.note == "fixed"


def test_delete(glossary_repo):
    entry = glossary_repo.create(
        source_lang="ru", target_lang="tk", source_text="склад", target_text="ammar"
    )
    assert glossary_repo.delete(entry.id) is True
    assert glossary_repo.get(entry.id) is None
    assert glossary_repo.delete(entry.id) is False


def test_find_match_case_insensitive_by_default(glossary_repo):
    glossary_repo.create(
        source_lang="ru", target_lang="tk", source_text="Доставка", target_text="eltip bermek"
    )
    hit = glossary_repo.find_match(
        source_text="доставка", source_lang="ru", target_lang="tk"
    )
    assert hit is not None and hit.target_text == "eltip bermek"


def test_find_match_respects_case_sensitive_flag(glossary_repo):
    glossary_repo.create(
        source_lang="ru",
        target_lang="tk",
        source_text="Доставка",
        target_text="eltip bermek",
        case_sensitive=True,
    )
    assert (
        glossary_repo.find_match(
            source_text="доставка", source_lang="ru", target_lang="tk"
        )
        is None
    )
    assert (
        glossary_repo.find_match(
            source_text="Доставка", source_lang="ru", target_lang="tk"
        )
        is not None
    )
