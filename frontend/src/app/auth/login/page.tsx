"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bot, ArrowRight, Eye, EyeOff, Sparkles } from "lucide-react";
import { auth } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { storeTokens } from "@/lib/utils";

export default function LoginPage() {
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const tokens = await auth.login(email, password);
      storeTokens(tokens.access_token, tokens.refresh_token);
      setTokens(tokens.access_token, tokens.refresh_token);
      setUser(await auth.me());
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
      style={{ background: "hsl(var(--background))" }}
    >
      {/* Background effects */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full pointer-events-none"
        style={{
          background: "radial-gradient(ellipse, hsl(217 91% 60% / 0.08) 0%, transparent 70%)",
        }}
      />
      <div
        className="absolute bottom-0 right-0 w-[400px] h-[300px] rounded-full pointer-events-none"
        style={{
          background: "radial-gradient(ellipse, hsl(158 64% 42% / 0.04) 0%, transparent 70%)",
        }}
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
                boxShadow: "0 0 40px hsl(217 91% 60% / 0.12), 0 0 0 1px hsl(217 91% 60% / 0.08)",
              }}
            >
              <Bot className="h-8 w-8" style={{ color: "hsl(var(--primary))" }} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground tracking-tight">ChatbotMCP</h1>
              <p className="text-sm text-muted-foreground mt-1 flex items-center justify-center gap-1.5">
                <Sparkles className="h-3 w-3" style={{ color: "hsl(var(--primary))" }} />
                AI Command Center
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
            boxShadow: "0 24px 64px hsl(0 0% 0% / 0.3), 0 1px 0 hsl(var(--border))",
          }}
        >
          <h2 className="text-base font-semibold text-foreground mb-1">Welcome back</h2>
          <p className="text-xs text-muted-foreground mb-6">Sign in to your account to continue</p>

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

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-[10px] font-semibold text-muted-foreground mb-1.5 block uppercase tracking-widest">
                Email address
              </label>
              <input
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full px-3.5 py-2.5 rounded-xl text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition-all"
                style={{
                  background: "hsl(var(--secondary))",
                  border: "1px solid hsl(var(--border))",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "hsl(var(--primary) / 0.5)";
                  e.target.style.boxShadow = "0 0 0 3px hsl(var(--primary) / 0.08)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "hsl(var(--border))";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            <div>
              <label className="text-[10px] font-semibold text-muted-foreground mb-1.5 block uppercase tracking-widest">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition-all"
                  style={{
                    background: "hsl(var(--secondary))",
                    border: "1px solid hsl(var(--border))",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "hsl(var(--primary) / 0.5)";
                    e.target.style.boxShadow = "0 0 0 3px hsl(var(--primary) / 0.08)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "hsl(var(--border))";
                    e.target.style.boxShadow = "none";
                  }}
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-muted-foreground transition-colors"
                  onClick={() => setShowPw((v) => !v)}
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

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
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-border text-center">
            <p className="text-xs text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link
                href="/auth/register"
                className="font-semibold transition-colors"
                style={{ color: "hsl(var(--primary))" }}
              >
                Create one free
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
