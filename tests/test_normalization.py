from src.normalization import normalize_text, normalize_identifier


def test_normalize_text_removes_accents_and_case():
    assert normalize_text("  Corazón de Fuego ") == "corazon de fuego"


def test_normalize_identifier_removes_formatting():
    assert normalize_identifier("T-123.456.789-0") == "T1234567890"
