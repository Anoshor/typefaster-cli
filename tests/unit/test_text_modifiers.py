"""Unit tests for MonkeyType-style text modifiers."""

from __future__ import annotations

from typefaster.domain.text_modifiers import apply_modifiers


def test_no_modifiers_is_identity() -> None:
    text = "The Quick, Brown Fox! 42."
    assert apply_modifiers(text, lowercase=False, words_only=False) == text


def test_lowercase_only() -> None:
    out = apply_modifiers("The Quick, Brown Fox! 42.", lowercase=True, words_only=False)
    assert out == "the quick, brown fox! 42."


def test_words_only_strips_punct_and_digits_and_lowercases() -> None:
    out = apply_modifiers("The Quick, Brown Fox! 42.", lowercase=False, words_only=True)
    assert out == "the quick brown fox"


def test_words_only_collapses_whitespace() -> None:
    out = apply_modifiers("a,,,  b\t\tc", lowercase=False, words_only=True)
    assert out == "a b c"


def test_words_only_implies_lowercase_even_without_flag() -> None:
    out = apply_modifiers("HELLO WORLD", lowercase=False, words_only=True)
    assert out == "hello world"


def test_empty_result_falls_back_to_original() -> None:
    # All-digits/punctuation would empty under words_only; never return "".
    original = "1234 5678 !!!"
    assert apply_modifiers(original, lowercase=False, words_only=True) == original
