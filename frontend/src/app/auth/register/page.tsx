"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bot, ArrowRight, Sparkles } from "lucide-react";
import { auth } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { storeTokens } from "@/lib/utils";

export default function RegisterPage() {
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm) { setError("Passwords do not match"); return; }
    setLoading(true);
    setError("");
    try {
      const tokens = await auth.register(form.email, form.password, form.name);
      storeTokens(tokens.access_token, tokens.refresh_token);
      setTokens(tokens.access_token, tokens.refresh_token);
      setUser(await auth.me());
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const inputBase =
    "w-full px-3.5 py-2.5 rounded-xl text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition-all";

  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    e.target.style.borderColor = "hsl(var(--primary) / 0.5)";
    e.target.style.boxShadow = "0 0 0 3px hsl(var(--primary) / 0.08)";
  };
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    e.target.style.borderColor = "hsl(var(--border))";
    e.target.style.boxShadow = "none";
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
      style={{ background: "hsl(var(--background))" }}
    >
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full pointer-events-none"
        style={{ background: "radial-gradient(ellipse, hsl(217 91% 60% / 0.08) 0%, transparent 70%)" }}
      />

      <div className="w-full max-w-sm relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex flex-col items-center gap-4">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{
                background: "linear-gradient(135deg, hsl(217 91% 60% / 0.15), hsl(217 91% 60% / 0.05))",
                border: "1px solid hsl(217 91% 60% / 0.3)",
                boxShadow: "0 0 40px hsl(217 91% 60% / 0.12)",
              }}
            >
              <Bot className="h-8 w-8" style={{ color: "hsl(var(--primary))" }} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground tracking-tight">Get Started</h1>
              <p className="text-sm text-muted-foreground mt-1 flex items-center justify-center gap-1.5">
                <Sparkles className="h-3 w-3" style={{ color: "hsl(var(--primary))" }} />
                Create your ChatbotMCP account
              </p>
            </div>
          </div>
        </div>

        {/* Card */}
        <div
          className="rounded-2xl p-7"
          style={{
            background: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            boxShadow: "0 24px 64px hsl(0 0% 0% / 0.3)",
          }}
        >
          <h2 className="text-base font-semibold text-foreground mb-1">Create account</h2>
          <p className="text-xs text-muted-foreground mb-6">Free to start, no credit card needed</p>

          {error && (
            <div
              className="mb-5 p-3 rounded-xl text-xs flex items-center gap-2"
              style={{
                background: "hsl(var(--destructive) / 0.08)",
                color: "hsl(var(--destructive))",
                border: "1px solid hsl(var(--destructive) / 0.2)",
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "hsl(var(--destructive))" }} />
              {error}
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-4">
            {[
              { label: "Full name", key: "name", type: "text", placeholder: "John Smith", required: false },
              { label: "Email address", key: "email", type: "email", placeholder: "you@company.com", required: true },
              { label: "Password", key: "password", type: "password", placeholder: "Min. 8 characters", required: true, minLength: 8 },
              { label: "Confirm password", key: "confirm", type: "password", placeholder: "Repeat password", required: true },
            ].map(({ label, key, type, placeholder, required, minLength }) => (
              <div key={key}>
                <label className="text-[10px] font-semibold text-muted-foreground mb-1.5 block uppercase tracking-widest">
                  {label}
                </label>
                <input
                  type={type}
                  placeholder={placeholder}
                  value={form[key as keyof typeof form]}
                  onChange={set(key as keyof typeof form)}
                  required={required}
                  minLength={minLength}
                  className={inputBase}
                  style={{ background: "hsl(var(--secondary))", border: "1px solid hsl(var(--border))" }}
                  onFocus={handleFocus}
                  onBlur={handleBlur}
                />
              </div>
            ))}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary-glow w-full flex items-center justify-center gap-2 py-2.5 mt-2"
              style={{
                color: "hsl(var(--primary-foreground))",
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin"
                       style={{ borderColor: "hsl(var(--primary-foreground)) transparent transparent" }} />
                  Creating account…
                </>
              ) : (
                <>
                  Create account
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-border text-center">
            <p className="text-xs text-muted-foreground">
              Already have an account?{" "}
              <Link
                href="/auth/login"
                className="font-semibold transition-colors"
                style={{ color: "hsl(var(--primary))" }}
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
