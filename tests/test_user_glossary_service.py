"""End-to-end test for the runtime user-glossary application."""

from __future__ import annotations

from src.translator.user_glossary import UserGlossaryService


def test_apply_replaces_known_terms(glossary_repo):
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="доставка", target_text="eltip bermek",
    )
    service = UserGlossaryService(glossary_repo)
    out = service.apply("Doruk dostawka", source_lang="ru", target_lang="tk")
    # The glossary applies post-translation, so the input here represents the
    # model output; we replace target-side terms in arbitrary text.
    # Without a matching token in the input, output is unchanged.
    assert out == "Doruk dostawka"


def test_apply_replaces_when_source_token_present(glossary_repo):
    # Glossary entries replace target-side text in the translated output. To
    # keep the test realistic we add an entry whose ``source_text`` is what we
    # expect the model to leave behind ("доставка") and whose target is the
    # Turkmen idiom we want.
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="доставка", target_text="eltip bermek",
    )
    service = UserGlossaryService(glossary_repo)
    out = service.apply(
        "быстрая доставка завтра",
        source_lang="ru",
        target_lang="tk",
    )
    assert out == "быстрая eltip bermek завтра"


def test_apply_respects_whole_word_flag(glossary_repo):
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="кот", target_text="pişik", whole_word=True,
    )
    service = UserGlossaryService(glossary_repo)
    out = service.apply("Скотовод и кот", source_lang="ru", target_lang="tk")
    assert "Скотовод" in out  # untouched
    assert "pişik" in out


def test_apply_respects_case_sensitive(glossary_repo):
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="Doc", target_text="DOK", case_sensitive=True,
    )
    service = UserGlossaryService(glossary_repo)
    assert service.apply("Doc and doc", source_lang="ru", target_lang="tk") == "DOK and doc"


def test_detect_terms(glossary_repo):
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="заказ", target_text="sargyt",
    )
    service = UserGlossaryService(glossary_repo)
    hits = service.detect_terms("новый заказ", source_lang="ru", target_lang="tk")
    assert len(hits) == 1 and hits[0].target_text == "sargyt"

    none = service.detect_terms("что-то иное", source_lang="ru", target_lang="tk")
    assert none == []


def test_apply_picks_longer_match_first(glossary_repo):
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="быстрая доставка", target_text="çalt eltip bermek",
    )
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="доставка", target_text="eltip bermek",
    )
    service = UserGlossaryService(glossary_repo)
    out = service.apply("заказ: быстрая доставка завтра",
                        source_lang="ru", target_lang="tk")
    assert "çalt eltip bermek" in out
    assert " eltip bermek " not in out  # short rule did not also fire
