/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {
    rules: {
      '*.svg': {
        loaders: ['@svgr/webpack'],
        as: '*.js',
      },
    },
  },
  transpilePackages: ['@xm-port/shared', '@xm-port/ui'],
  eslint: {
    // During builds, allow the build to complete even if there are ESLint errors
    ignoreDuringBuilds: true,
  },
}

module.exports = nextConfig