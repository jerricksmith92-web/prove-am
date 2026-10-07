import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.proveam.app',
  appName: 'Prove-am',
  webDir: 'www',
  server: {
    url: 'https://prove-am.onrender.com',
    cleartext: false
  }
};

export default config;
