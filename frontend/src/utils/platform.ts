/// <reference types="vite/client" />
export enum PlatformType {
  WINDOWS = 'windows',
  LINUX = 'linux',
  HONGZOS = 'hongzos',
  KYLIN = 'kylin',
  UOS = 'uos',
  HARMONY = 'harmony',
  UNKNOWN = 'unknown'
}

export interface PlatformInfo {
  type: PlatformType;
  name: string;
  version: string;
  hasHardwareAcceleration: boolean;
}

export function detectPlatform(): PlatformInfo {
  const userAgent = navigator.userAgent.toLowerCase();
  const platform = navigator.platform.toLowerCase();
  let type = PlatformType.UNKNOWN;
  let name = 'Unknown';
  let version = '';
  let hasHardwareAcceleration = false;

  if (userAgent.includes('hongzos') || platform.includes('hongzos')) {
    type = PlatformType.HONGZOS;
    name = 'HongZOS';
    version = '1.0';
    hasHardwareAcceleration = true;
  } else if (userAgent.includes('kylin') || platform.includes('kylin')) {
    type = PlatformType.KYLIN;
    name = 'Kylin';
    version = '';
    hasHardwareAcceleration = true;
  } else if (userAgent.includes('uos') || platform.includes('uos')) {
    type = PlatformType.UOS;
    name = 'UOS';
    version = '';
    hasHardwareAcceleration = true;
  } else if (userAgent.includes('harmony') || platform.includes('harmony')) {
    type = PlatformType.HARMONY;
    name = 'HarmonyOS';
    version = '';
    hasHardwareAcceleration = true;
  } else if (userAgent.includes('windows') || platform.includes('win')) {
    type = PlatformType.WINDOWS;
    name = 'Windows';
    version = /windows nt ([\d.]+)/.exec(userAgent)?.[1] || '';
    hasHardwareAcceleration = true;
  } else if (userAgent.includes('linux') || platform.includes('linux')) {
    type = PlatformType.LINUX;
    name = 'Linux';
    version = '';
    hasHardwareAcceleration = true;
  }

  return { type, name, version, hasHardwareAcceleration };
}

export function getPlatformConfig() {
  const platform = detectPlatform();

  switch (platform.type) {
    case PlatformType.HONGZOS:
      return {
        theme: 'hongzos-dark',
        apiTimeout: 8000,
        maxConnections: 50,
        features: {
          robotArm: true,
          conveyor: true,
          vision: true,
          temperature: true,
          advancedAnalytics: true
        }
      };

    case PlatformType.WINDOWS:
      return {
        theme: 'windows-light',
        apiTimeout: 5000,
        maxConnections: 30,
        features: {
          robotArm: true,
          conveyor: true,
          vision: true,
          temperature: true,
          advancedAnalytics: false
        }
      };

    case PlatformType.LINUX:
      return {
        theme: 'linux-minimal',
        apiTimeout: 6000,
        maxConnections: 40,
        features: {
          robotArm: true,
          conveyor: true,
          vision: true,
          temperature: true,
          advancedAnalytics: true
        }
      };

    default:
      return {
        theme: 'default',
        apiTimeout: 5000,
        maxConnections: 20,
        features: {
          robotArm: true,
          conveyor: true,
          vision: false,
          temperature: false,
          advancedAnalytics: false
        }
      };
  }
}

export function getPlatformAPIEndpoints() {
  const platform = detectPlatform();
  const baseURL = import.meta.env.VITE_API_BASE_URL;

  return {
    auth: `\${baseURL}/api/auth`,
    devices: `\${baseURL}/api/devices`,
    robotArm: `\${baseURL}/api/robot-arm`,
    conveyor: `\${baseURL}/api/conveyor`,
    vision: `\${baseURL}/api/vision`,
    temperature: `\${baseURL}/api/temperature`,
    monitoring: `\${baseURL}/api/monitoring`,
    alerts: `\${baseURL}/api/alerts`,
    platform: platform.type === PlatformType.HONGZOS ?
      `\${baseURL}/api/hongzos` :
      `\${baseURL}/api/generic`
  };
}
