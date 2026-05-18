import { detectPlatform, PlatformInfo, PlatformType } from '../utils/platform';

export interface SystemAdapter {
  enableHardwareAcceleration(): Promise<boolean>;
  connectDevice(deviceId: string): DeviceConnection;
  getSystemInfo(): PlatformInfo;
  startDataCollection(): void;
  stopDataCollection(): void;
}

export interface DeviceConnection {
  sendCommand(cmd: string): Promise<void>;
  onData(callback: (data: any) => void): void;
  disconnect(): void;
}

class WindowsAdapter implements SystemAdapter {
  private platform: PlatformInfo;

  constructor() {
    this.platform = detectPlatform();
  }

  async enableHardwareAcceleration(): Promise<boolean> {
    console.log('[Windows] 启用硬件加速');
    return this.platform.hasHardwareAcceleration;
  }

  connectDevice(deviceId: string): DeviceConnection {
    return new WindowsDeviceConnection(deviceId);
  }

  getSystemInfo(): PlatformInfo {
    return this.platform;
  }

  startDataCollection(): void {
    console.log('[Windows] 开始数据采集');
  }

  stopDataCollection(): void {
    console.log('[Windows] 停止数据采集');
  }
}

class LinuxAdapter implements SystemAdapter {
  private platform: PlatformInfo;

  constructor() {
    this.platform = detectPlatform();
  }

  async enableHardwareAcceleration(): Promise<boolean> {
    console.log('[Linux] 启用硬件加速');
    return this.platform.hasHardwareAcceleration;
  }

  connectDevice(deviceId: string): DeviceConnection {
    return new LinuxDeviceConnection(deviceId);
  }

  getSystemInfo(): PlatformInfo {
    return this.platform;
  }

  startDataCollection(): void {
    console.log('[Linux] 开始数据采集');
  }

  stopDataCollection(): void {
    console.log('[Linux] 停止数据采集');
  }
}

class HongZOSAdapter implements SystemAdapter {
  private platform: PlatformInfo;

  constructor() {
    this.platform = detectPlatform();
  }

  async enableHardwareAcceleration(): Promise<boolean> {
    console.log('[HongZOS] 启用分布式硬件加速');
    return true;
  }

  connectDevice(deviceId: string): DeviceConnection {
    return new HongZOSDeviceConnection(deviceId);
  }

  getSystemInfo(): PlatformInfo {
    return this.platform;
  }

  startDataCollection(): void {
    console.log('[HongZOS] 开始分布式数据采集');
  }

  stopDataCollection(): void {
    console.log('[HongZOS] 停止分布式数据采集');
  }
}

class WindowsDeviceConnection implements DeviceConnection {
  constructor(private deviceId: string) {}

  async sendCommand(cmd: string): Promise<void> {
    console.log(`[Windows] 发送命令到设备${this.deviceId}: ${cmd}`);
  }

  onData(callback: (data: any) => void): void {
    setInterval(() => {
      callback({
        temp: 25 + Math.random() * 10,
        load: Math.random() * 100,
        timestamp: Date.now()
      });
    }, 1000);
  }

  disconnect(): void {
    console.log(`[Windows] 断开设备\${this.deviceId}连接`);
  }
}

class LinuxDeviceConnection implements DeviceConnection {
  constructor(private deviceId: string) {}

  async sendCommand(cmd: string): Promise<void> {
    console.log(`[Linux] 发送命令到设备${this.deviceId}: ${cmd}`);
  }

  onData(callback: (data: any) => void): void {
    setInterval(() => {
      callback({
        temp: 25 + Math.random() * 10,
        load: Math.random() * 100,
        timestamp: Date.now()
      });
    }, 1000);
  }

  disconnect(): void {
    console.log(`[Linux] 断开设备\${this.deviceId}连接`);
  }
}

class HongZOSDeviceConnection implements DeviceConnection {
  constructor(private deviceId: string) {}

  async sendCommand(cmd: string): Promise<void> {
    console.log(`[HongZOS] 分布式命令发送到设备${this.deviceId}: ${cmd}`);
  }

  onData(callback: (data: any) => void): void {
    setInterval(() => {
      callback({
        temp: 25 + Math.random() * 10,
        load: Math.random() * 100,
        timestamp: Date.now(),
        nodeId: this.deviceId
      });
    }, 1000);
  }

  disconnect(): void {
    console.log(`[HongZOS] 断开分布式设备\${this.deviceId}连接`);
  }
}

export const createSystemAdapter = (): SystemAdapter => {
  const platform = detectPlatform();

  switch (platform.type) {
    case PlatformType.WINDOWS:
      return new WindowsAdapter();
    case PlatformType.LINUX:
      return new LinuxAdapter();
    case PlatformType.HONGZOS:
      return new HongZOSAdapter();
    default:
      console.warn('未知操作系统，使用默认适配器');
      return new WindowsAdapter();
  }
};

export const SystemAPI = createSystemAdapter();
