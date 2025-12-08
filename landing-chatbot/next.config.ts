import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Explicitly set turbopack root to this directory
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
