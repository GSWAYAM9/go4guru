import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildClassroomWsUrl } from "@/lib/api-client";
import { AuthProvider, useAuth } from "@/lib/auth-context";

const mockRefresh = vi.fn();
const mockLogout = vi.fn();

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    refreshAuthSession: (...args: unknown[]) => mockRefresh(...args),
    logoutAccount: (...args: unknown[]) => mockLogout(...args),
  };
});

function AuthProbe() {
  const { token, user, initializing } = useAuth();
  return (
    <div>
      <span data-testid="init-state">{initializing ? "loading" : "ready"}</span>
      <span data-testid="token-state">{token ? "present" : "empty"}</span>
      <span data-testid="user-email">{user?.email ?? "none"}</span>
    </div>
  );
}

describe("Phase 11 Frontend Security Hardening", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
  });

  it("keeps access JWT strictly in React memory and purges legacy sessionStorage keys", async () => {
    window.sessionStorage.setItem(
      "go4guru_access_session_v1",
      JSON.stringify({ access_token: "stale.legacy.jwt" })
    );
    mockRefresh.mockResolvedValue({
      access_token: "fresh.memory.only.jwt",
      token_type: "bearer",
      expires_in: 900,
      mfa_required: false,
      user: {
        id: "u-1",
        email: "student@go4guru.in",
        display_name: "Aarav",
        roles: ["student"],
        permissions: ["practice:attempt"],
        tenant_id: null,
        is_minor: false,
        mfa_enabled: false,
      },
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("init-state").textContent).toBe("ready");
    });
    expect(screen.getByTestId("token-state").textContent).toBe("present");
    expect(screen.getByTestId("user-email").textContent).toBe("student@go4guru.in");
    expect(window.sessionStorage.getItem("go4guru_access_session_v1")).toBeNull();
    expect(window.sessionStorage.length).toBe(0);
    expect(window.localStorage.length).toBe(0);
  });

  it("omits bearer tokens from classroom WebSocket URLs", () => {
    const url = buildClassroomWsUrl("sess-123");
    expect(url).toMatch(/\/ws\/v1\/classroom\/sess-123$/);
    expect(url).not.toContain("token=");
    expect(url).not.toContain("?");
  });
});
