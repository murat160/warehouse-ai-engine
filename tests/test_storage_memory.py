"""TranslationMemoryRepository CRUD + exact match."""

from __future__ import annotations


def test_upsert_inserts_and_updates(tm_repo):
    inserted = tm_repo.upsert(
        source_lang="ru",
        target_lang="tk",
        source_text="быстрая доставка",
        target_text="çalt eltip bermek",
    )
    assert inserted.id

    updated = tm_repo.upsert(
        source_lang="ru",
        target_lang="tk",
        source_text="БЫСТРАЯ доставка",  # same after normalise
        target_text="çalt eltip beriş",
    )
    # Same row was updated, not duplicated.
    assert updated.id == inserted.id
    assert updated.target_text == "çalt eltip beriş"

    listed = tm_repo.list(source_lang="ru", target_lang="tk")
    assert len(listed) == 1


def test_find_exact_normalises_input(tm_repo):
    tm_repo.upsert(
        source_lang="ru",
        target_lang="tk",
        source_text="быстрая доставка",
        target_text="çalt eltip bermek",
    )
    hit = tm_repo.find_exact(
        source_text="  Быстрая  Доставка  ",
        source_lang="ru",
        target_lang="tk",
    )
    assert hit is not None
    assert hit.target_text == "çalt eltip bermek"

    # Different language pair must miss.
    assert (
        tm_repo.find_exact(
            source_text="быстрая доставка", source_lang="ru", target_lang="en"
        )
        is None
    )


def test_search_by_query(tm_repo):
    tm_repo.upsert(
        source_lang="ru", target_lang="tk",
        source_text="быстрая доставка", target_text="çalt eltip bermek",
    )
    tm_repo.upsert(
        source_lang="ru", target_lang="tk",
        source_text="спасибо за заказ", target_text="sargydyňyz üçin sag boluň",
    )
    hits = tm_repo.list(query="достав")
    assert len(hits) == 1
    assert "доставка" in hits[0].source_text


def test_delete(tm_repo):
    entry = tm_repo.upsert(
        source_lang="ru", target_lang="tk",
        source_text="привет", target_text="salam",
    )
    assert tm_repo.delete(entry.id) is True
    assert tm_repo.get(entry.id) is None
    assert tm_repo.delete(entry.id) is False
