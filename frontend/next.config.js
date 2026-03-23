/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_WS_URL: process.env.NEXT_PUBLIC_API_WS_URL,
  },
};

module.exports = nextConfig;
