export default {
  puppeteerOptions: {
    executablePath: "/usr/bin/chromium",
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
    ],
    timeout: 60000,
  },

  puppeteerClusterOptions: {
    maxConcurrency: 1,
  },

  lighthouseOptions: {
    maxWaitForLoad: 60000,
  },

  debug: true,
}
