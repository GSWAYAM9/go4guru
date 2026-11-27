"""Pure-stdlib Phase 11 production hardening & security invariant unit tests."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

_HARDENING_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "src" / "core" / "hardening.py"
)
_SPEC = importlib.util.spec_from_file_location("go4guru_hardening", _HARDENING_PATH)
assert _SPEC and _SPEC.loader
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["go4guru_hardening"] = _MOD
_SPEC.loader.exec_module(_MOD)

FixedWindowRateLimiter = _MOD.FixedWindowRateLimiter
PLATFORM_PHASE = _MOD.PLATFORM_PHASE
build_api_security_headers = _MOD.build_api_security_headers
is_origin_allowed = _MOD.is_origin_allowed
is_safe_audio_cache_filename = _MOD.is_safe_audio_cache_filename
validate_production_config_invariants = _MOD.validate_production_config_invariants


class Phase11HardeningUnitTests(unittest.TestCase):
    def test_platform_phase_is_phase_11(self) -> None:
        self.assertEqual(PLATFORM_PHASE, "phase_11_production_readiness")

    def test_production_config_rejects_insecure_defaults(self) -> None:
        violations = validate_production_config_invariants(
            app_env="production",
            debug=True,
            jwt_secret="dev-only-change-before-deploy-minimum-32-chars",
            database_url="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/go4guru",
            cookie_secure=False,
            cors_allowed_origins=["http://localhost:3000"],
            trusted_hosts=["*", ""],
        )
        joined = " | ".join(violations)
        self.assertIn("JWT_SECRET_KEY", joined)
        self.assertIn("DEBUG=true", joined)
        self.assertIn("postgres:postgres", joined)
        self.assertIn("trusted_hosts", joined)
        self.assertIn("COOKIE_SECURE=true", joined)
        self.assertIn("https://", joined)
        self.assertIn("localhost", joined)

    def test_production_config_accepts_hardened_configuration(self) -> None:
        violations = validate_production_config_invariants(
            app_env="production",
            debug=False,
            jwt_secret="prod-9b6d3c7e8f1a2b4c5d6e7f8a9b0c1d2e3f4a5b6c",
            database_url="postgresql+asyncpg://go4guru_app:strong_pwd@pg-prod.internal:5432/go4guru",
            cookie_secure=True,
            cors_allowed_origins=["https://app.go4guru.in"],
            trusted_hosts=["api.go4guru.in"],
        )
        self.assertEqual(violations, [])

    def test_origin_allowlist_blocks_spoofed_and_wildcard_origins(self) -> None:
        allowed = ["https://app.go4guru.in", "http://localhost:3000/"]
        self.assertTrue(is_origin_allowed("https://app.go4guru.in", allowed))
        self.assertTrue(is_origin_allowed("https://app.go4guru.in/", allowed))
        self.assertTrue(is_origin_allowed("http://localhost:3000", allowed))
        self.assertFalse(is_origin_allowed("https://app.go4guru.in.evil.com", allowed))
        self.assertFalse(is_origin_allowed("https://evil.example", allowed))
        self.assertFalse(is_origin_allowed(None, allowed))
        self.assertFalse(is_origin_allowed("https://anything.test", ["*"]))

    def test_audio_cache_filename_blocks_path_traversal_and_non_mp3(self) -> None:
        self.assertTrue(is_safe_audio_cache_filename("a1b2c3d4e5f60718.mp3"))
        self.assertTrue(is_safe_audio_cache_filename("voice_seg-01.mp3"))
        self.assertFalse(is_safe_audio_cache_filename("../homework/secret.pdf"))
        self.assertFalse(is_safe_audio_cache_filename("sub/dir/clip.mp3"))
        self.assertFalse(is_safe_audio_cache_filename("..\\clip.mp3"))
        self.assertFalse(is_safe_audio_cache_filename("clip.mp3.html"))
        self.assertFalse(is_safe_audio_cache_filename(".hidden.mp3"))
        self.assertFalse(is_safe_audio_cache_filename(""))

    def test_security_headers_include_csp_and_env_gated_hsts(self) -> None:
        dev_headers = build_api_security_headers("development")
        self.assertEqual(
            dev_headers["Content-Security-Policy"],
            "default-src 'none'; frame-ancestors 'none'",
        )
        self.assertEqual(dev_headers["X-Frame-Options"], "DENY")
        self.assertNotIn("Strict-Transport-Security", dev_headers)

        prod_headers = build_api_security_headers("production")
        self.assertEqual(
            prod_headers["Strict-Transport-Security"],
            "max-age=31536000; includeSubDomains",
        )

    def test_fixed_window_rate_limiter_blocks_brute_force_and_resets_after_window(self) -> None:
        limiter = FixedWindowRateLimiter(max_buckets=32)
        t0 = 1000.0
        for idx in range(5):
            dec = limiter.check("rl:auth_login:10.0.0.1:user@test.in", limit=5, window_seconds=60, now=t0 + idx)
            self.assertTrue(dec.allowed)
            self.assertEqual(dec.remaining, 4 - idx)
            self.assertEqual(dec.retry_after_seconds, 0)

        blocked = limiter.check("rl:auth_login:10.0.0.1:user@test.in", limit=5, window_seconds=60, now=t0 + 10)
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.remaining, 0)
        self.assertEqual(blocked.retry_after_seconds, 50)

        # Separate account/IP bucket remains isolated
        other = limiter.check("rl:auth_login:10.0.0.2:other@test.in", limit=5, window_seconds=60, now=t0 + 10)
        self.assertTrue(other.allowed)

        # Original bucket recovers after window elapses
        recovered = limiter.check("rl:auth_login:10.0.0.1:user@test.in", limit=5, window_seconds=60, now=t0 + 61)
        self.assertTrue(recovered.allowed)
        self.assertEqual(recovered.current_count, 1)


if __name__ == "__main__":
    unittest.main()
