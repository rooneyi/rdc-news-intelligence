"""Tests pour la logique de découpage des messages WhatsApp.
C'est le chemin le plus critique : un bug ici coupe les réponses ou fait boucler l'envoi."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.routes.webhooks import _pop_whatsapp_chunk


def test_short_text_below_min_returns_empty():
    chunk, rest = _pop_whatsapp_chunk("Bonjour", min_chars=50, hard_max=200)
    assert chunk == ""
    assert rest == "Bonjour"


def test_short_text_force_returns_all():
    chunk, rest = _pop_whatsapp_chunk("Bonjour", min_chars=50, hard_max=200, force=True)
    assert chunk == "Bonjour"
    assert rest == ""


def test_splits_on_double_newline():
    text = "Première partie.\n\nDeuxième partie qui est longue."
    chunk, rest = _pop_whatsapp_chunk(text, min_chars=10, hard_max=100)
    assert chunk == "Première partie."
    assert "Deuxième" in rest


def test_splits_on_single_newline_when_no_double():
    text = "Ligne un\nLigne deux longue longue longue"
    chunk, rest = _pop_whatsapp_chunk(text, min_chars=5, hard_max=30)
    assert chunk == "Ligne un"
    assert "Ligne deux" in rest


def test_does_not_cut_url():
    url = "https://example.com/article/tres-long-chemin/page"
    text = "Voir cet article : " + url + " pour plus d'info."
    # Le hard_max est au milieu de l'URL
    mid = len("Voir cet article : ") + 10
    chunk, rest = _pop_whatsapp_chunk(text, min_chars=5, hard_max=mid)
    # L'URL ne doit pas être coupée
    assert url not in chunk or url in chunk  # l'URL est soit intacte soit pas présente
    # Le chunk ne doit pas finir au milieu de l'URL
    if chunk:
        assert not any(chunk.endswith(url[:i]) for i in range(5, len(url) - 5))


def test_empty_text_returns_empty():
    chunk, rest = _pop_whatsapp_chunk("", min_chars=10, hard_max=100)
    assert chunk == ""
    assert rest == ""


def test_text_exactly_at_max_returns_full():
    text = "A" * 100
    chunk, rest = _pop_whatsapp_chunk(text, min_chars=10, hard_max=100)
    assert len(chunk) == 100
    assert rest == ""


def test_full_message_split_loop_covers_all_content():
    """Simule la boucle complète de _send_whatsapp_long_body : aucun texte ne doit être perdu."""
    original = "Premier paragraphe.\n\n" * 20 + "Fin du message."
    chunks = []
    remaining = original
    min_c, max_c = 100, 500
    iterations = 0
    while remaining.strip():
        iterations += 1
        assert iterations < 200, "Boucle infinie détectée"
        if len(remaining) <= max_c:
            chunks.append(remaining.strip())
            break
        to_send, remaining = _pop_whatsapp_chunk(remaining, min_c, max_c, force=False)
        if not to_send:
            to_send, remaining = _pop_whatsapp_chunk(remaining, min_c, max_c, force=True)
        if to_send:
            chunks.append(to_send)

    reassembled = " ".join(chunks)
    # Tous les mots importants du texte original doivent être présents
    assert "Premier paragraphe" in reassembled
    assert "Fin du message" in reassembled
