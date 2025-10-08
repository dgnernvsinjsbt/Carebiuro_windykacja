import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://2c8c19a88f5aea69a06fca9cdd7a8f69@o4508690685370368.ingest.us.sentry.io/4508690761916416",

  // Set tracesSampleRate to 1.0 to capture 100% of transactions for tracing.
  // We recommend adjusting this value in production
  tracesSampleRate: 1.0,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Environment detection
  environment: process.env.NODE_ENV,

  // Replay Configuration
  replaysOnErrorSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,

  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
});
