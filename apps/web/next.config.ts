import type { NextConfig } from 'next';

const api = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
const config: NextConfig = {
  output: 'standalone',
  allowedDevOrigins: ['127.0.0.1'],
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${api}/api/:path*` },
      { source: '/assets/:path*', destination: `${api}/assets/:path*` },
    ];
  },
  async headers() {
    return [{ source: '/:path*', headers: [
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      { key: 'X-Frame-Options', value: 'DENY' },
      { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
    ] }];
  },
};
export default config;
