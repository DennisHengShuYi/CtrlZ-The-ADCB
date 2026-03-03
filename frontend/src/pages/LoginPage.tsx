import { SignIn } from "@clerk/clerk-react";

// Vercel-style triangle logo (SVG inline)
function VercelLogo() {
  return (
    <svg
      className="auth-logo"
      viewBox="0 0 74 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M37.0001 0L74.0001 64H0L37.0001 0Z" fill="black" />
    </svg>
  );
}

export default function LoginPage() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Logo + Branding */}
        <VercelLogo />
        <h1 className="auth-title">Welcome back</h1>
        <p className="auth-subtitle">Sign in to your account to continue</p>

        {/* Clerk embedded sign-in widget */}
        <div className="clerk-widget">
          <SignIn routing="hash" />
        </div>
      </div>
    </div>
  );
}
