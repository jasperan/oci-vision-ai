import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  output: "export",
  basePath: isProd ? "/oci-vision-ai" : "",
  assetPrefix: isProd ? "/oci-vision-ai/" : "",
  images: { unoptimized: true },
};

export default nextConfig;
