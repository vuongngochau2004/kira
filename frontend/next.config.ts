import type { NextConfig } from "next";
import { getBackendUrl } from './src/lib/api/backend-url';

const nextConfig: NextConfig = {
  // Enable standalone output for optimized Docker deployment
  output: "standalone",

  experimental: {
    // Increase proxy body size limit for file uploads (default is 10MB)
    proxyClientMaxBodySize: '100mb',
  } as NextConfig['experimental'],

  // API Rewrites — proxy to KIRA FastAPI backend
  async rewrites() {
    const apiUrl = getBackendUrl();
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
        // Important: Forward credentials for httpOnly cookie auth
        basePath: false,
      },
    ]
  },
};

export default nextConfig;
