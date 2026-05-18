export const HongZOS = {
  enableHardwareAcceleration: () => {
    console.log("[HongZOS] GPU加速已启用");
    return true;
  },

  connectDevice: (deviceId: string) => {
    return {
      sendCommand: (cmd: string) => console.log(`发送指令到${deviceId}: ${cmd}`),
      onData: (callback: (data: any) => void) => {
        setInterval(() => callback({
          temp: 25 + Math.random() * 10,
          load: Math.random() * 100
        }), 1000);
      }
    }
  },

  createSecureChannel: () => {
    return {
      send: (data: any) => console.log("安全发送:", data),
      receive: (callback: (data: any) => void) => {}
    }
  }
}