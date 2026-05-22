"""
test_masking.py — Verificación de la función de enmascaramiento de PII.

Criterios:
  1. La función nunca retorna el email original en texto claro.
  2. La salida es determinista (misma entrada → misma salida).
  3. Los emails malformados/nulos no lanzan excepción.
  4. La máscara parcial preserva estructura local@dominio.
  5. El SHA-256 producido por el fallback tiene longitud 64 (hex).
"""

import hashlib
from src.migrator import _mask_email


# ─── Casos positivos ──────────────────────────────────────────────────────────

class TestMaskEmailNeverReturnsPlaintext:
    """El email original nunca debe aparecer en la salida."""

    def test_common_email(self):
        email = "maria.lopez@correo.com"
        assert _mask_email(email) != email

    def test_short_local(self):
        email = "ab@correo.com"
        assert _mask_email(email) != email

    def test_single_char_local(self):
        email = "a@correo.com"
        assert _mask_email(email) != email

    def test_long_email(self):
        email = "nombre.apellido.compuesto@universidad.edu.co"
        assert _mask_email(email) != email


class TestMaskEmailDeterministic:
    """La misma entrada siempre produce la misma salida (idempotencia)."""

    def test_same_output_twice(self):
        email = "test.user@example.org"
        assert _mask_email(email) == _mask_email(email)

    def test_different_emails_differ(self):
        assert _mask_email("alice@x.com") != _mask_email("bob@x.com")


class TestMaskEmailPartialStructure:
    """La máscara parcial (Opción A) debe preservar la estructura @dominio."""

    def test_domain_preserved(self):
        email = "usuario@biblioteca.co"
        result = _mask_email(email)
        assert "@biblioteca.co" in result

    def test_first_char_preserved(self):
        email = "zorro@example.com"
        result = _mask_email(email)
        # El primer carácter del local debe mantenerse
        assert result.startswith("z")

    def test_asterisks_present(self):
        email = "usuario@correo.com"
        result = _mask_email(email)
        local_part = result.split("@")[0]
        assert "*" in local_part


# ─── Casos de borde ───────────────────────────────────────────────────────────

class TestMaskEmailEdgeCases:
    """Inputs inválidos no deben lanzar excepción."""

    def test_none_input(self):
        result = _mask_email(None)
        # Fallback SHA-256 → 64 chars hex
        assert len(result) == 64
        assert result == hashlib.sha256(b"").hexdigest()

    def test_empty_string(self):
        result = _mask_email("")
        assert len(result) == 64

    def test_no_at_sign(self):
        result = _mask_email("sinArroba")
        # Sin '@' → fallback SHA-256
        assert len(result) == 64

    def test_two_char_local(self):
        """Local de 2 chars: debe producir al menos un asterisco."""
        result = _mask_email("ab@x.com")
        local = result.split("@")[0]
        assert "*" in local
