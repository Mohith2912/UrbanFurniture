import path from 'node:path';
import { fileURLToPath } from 'node:url';

/** @type {import('next').NextConfig} */
const backend = process.env.URBAN_BACKEND_URL || 'http://127.0.0.1:5050';
const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

export default {
  reactStrictMode: true,
  turbopack: { root: frontendRoot },
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }];
  },
};
