import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HomePage from "@/app/page";
import { FoundationStatus } from "@/components/foundation-status";
import { MathText } from "@/components/math-text";
import { AuthProvider } from "@/lib/auth-context";

describe("Go4Guru LandingPage & Core Components", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Go4Guru by GO4GURU Inc. hero, logo, and interactive sections", () => {
    render(
      <AuthProvider>
        <HomePage />
      </AuthProvider>
    );

    expect(
      screen.getByRole("heading", { level: 1, name: /Learn deeply\.\s*Master it for real\./i })
    ).toBeInTheDocument();
    expect(screen.getAllByAltText(/Go4Guru logo/i).length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Go4Guru by GO4GURU Inc\./i)
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: /go4guru\.com/i }).length
    ).toBeGreaterThan(0);
  });

  it("switches workspace showcase tabs, adaptive check-in answers, currency pricing, and FAQ items", () => {
    render(
      <AuthProvider>
        <HomePage />
      </AuthProvider>
    );

    // Switch Inside Go4Guru tab
    fireEvent.click(screen.getByRole("tab", { name: "Revision & Mistakes" }));
    expect(
      screen.getByText(/Every slip turns into a scheduled review card\./i)
    ).toBeInTheDocument();

    // Toggle adaptive check-in to misconception option
    fireEvent.click(screen.getByRole("radio", { name: /Carbon dioxide/i }));
    expect(
      screen.getByText(/Saved to your Mistake Book\./i)
    ).toBeInTheDocument();

    // Switch currency from USD to INR and billing cycle to Yearly
    fireEvent.click(screen.getByRole("button", { name: /India · INR/i }));
    expect(screen.getByText("₹1,899")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Yearly/i }));
    expect(screen.getByText("₹1,599")).toBeInTheDocument();

    // Expand an FAQ item
    const toursBtn = screen.getByRole("button", {
      name: /International Educational Tours\?/i,
    });
    expect(toursBtn).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toursBtn);
    expect(toursBtn).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByText(/upcoming tour itineraries/i)
    ).toBeInTheDocument();
  });

  it("FoundationStatus renders truthful error banner when backend API is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("Failed to fetch")
    );

    render(<FoundationStatus />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /NETWORK_UNREACHABLE/i
      );
    });
  });

  it("renders KaTeX math safely without executing script tags in prose", () => {
    const { container } = render(
      <MathText text={'Solve $x^2 + 1 = 5$ <script>alert("xss")</script>'} />
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector(".katex")).not.toBeNull();
    expect(container.textContent).toContain('<script>alert("xss")</script>');
  });
});
