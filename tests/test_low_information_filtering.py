"""
Unit tests for low-information filtering and multi-language detection.
Verifies that promotional boilerplate, short slogans, and foreign language leakage are rejected.
"""

import pytest
from evidence.extractor import detect_language, is_low_information, EvidenceExtractor


def test_is_low_information_detects_boilerplate():
    # Promotional and cookie boilerplate
    assert is_low_information("Cookie policy and consent settings. All rights reserved.")
    assert is_low_information("Sign up for our newsletter to get daily updates!")
    assert is_low_information("Share this post on Facebook, Twitter, and LinkedIn.")
    assert is_low_information("Leave a comment or reply below.")
    assert is_low_information("Trending now: 10 fun facts you won't believe!")
    assert is_low_information("Subscribe now for 50% discount code.")
    assert is_low_information("Credit: NASA's Goddard Space Flight Center (modified).")
    assert is_low_information("Photo credit: European Space Agency / STScI.")
    assert is_low_information("Short phrase.")  # Too short


def test_is_low_information_accepts_substantive_prose():
    # Substantive factual prose
    text1 = "The James Webb Space Telescope uses a 6.5-meter primary mirror composed of 18 hexagonal gold-plated beryllium segments."
    assert not is_low_information(text1)

    text2 = "Researchers observed water vapor, carbon dioxide, and sulfur dioxide in the atmosphere of the exoplanet WASP-39b."
    assert not is_low_information(text2)


def test_detect_language_accuracy():
    english_text = "The James Webb Space Telescope was launched on December 25, 2021 from Kourou, French Guiana on an Ariane 5 rocket."
    assert detect_language(english_text) == "en"

    spanish_text = "El telescopio espacial James Webb es un observatorio espacial desarrollado a través de la colaboración entre varios países."
    assert detect_language(spanish_text) == "es"

    french_text = "Le télescope spatial James Webb est un observatoire développé par la NASA avec la participation de l'Agence spatiale européenne."
    assert detect_language(french_text) == "fr"


def test_extractor_filters_foreign_passages_when_target_is_english():
    extractor = EvidenceExtractor()
    html = """
    <html>
      <body>
        <main>
          <h1>Observaciones del Telescopio</h1>
          <p>The James Webb Space Telescope conducts infrared astronomy with four high-sensitivity scientific instruments.</p>
          <p>El telescopio espacial James Webb orbita alrededor del punto de Lagrange L2 a un millón y medio de kilómetros de la Tierra.</p>
        </main>
      </body>
    </html>
    """
    ev = extractor.extract_from_html(html, url="https://example.org/telescope", target_language="en")

    # Only English passage should be retained
    assert len(ev.passages) == 1
    assert "infrared astronomy" in ev.passages[0].text
    assert "orbita alrededor" not in ev.passages[0].text

