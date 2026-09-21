import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const nextConfig: NextConfig = {
  // Disables streaming metadata. Dynamic routes (the calculator reads
  // searchParams, housing renders force-dynamic) would otherwise land
  // canonical, hreflang and the description in <body>. Metadata here is a
  // local dictionary lookup, so blocking it costs milliseconds and keeps the
  // SEO tags in <head> for every client.
  htmlLimitedBots: /.*/,
};

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

export default withNextIntl(nextConfig);
