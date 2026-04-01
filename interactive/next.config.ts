import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  output: "export",
  basePath: isProd ? "/oci-vision-ai/interactive" : "",
  assetPrefix: isProd ? "/oci-vision-ai/interactive/" : "",
  images: { unoptimized: true },
};

export default nextConfig;
