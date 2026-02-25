import type { NextConfig } from "next";

function isTruthyEnv(val: string | undefined): boolean {
  if (!val) return false;
  const normalized = val.trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes";
}

const isLocal: boolean = isTruthyEnv(process.env.LOCAL);

if (process.env.NODE_ENV === "production" && isLocal) {
  throw new Error(
    "Refusing to build with LOCAL=true in production mode. LOCAL is for local development only.",
  );
}

const nextConfig: NextConfig = isLocal
  ? {
      env: {
        // Auto-enable auth bypass in the frontend for local mode.
        NEXT_PUBLIC_DISABLE_AUTH: "true",
      },
    }
  : {};

export default nextConfig;
