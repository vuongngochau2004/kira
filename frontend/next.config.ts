import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for optimized Docker deployment
  output: "standalone",

  experimental: {
    // Increase proxy body size limit for file uploads (default is 10MB)
    proxyClientMaxBodySize: '100mb',
  } as NextConfig['experimental'],

  // API Rewrites — proxy to KIRA FastAPI backend
  async rewrites() {
    const apiUrl = process.env.KIRA_API_URL || 'http://127.0.0.1:8888';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
};

export default nextConfig;
