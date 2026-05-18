import { createPinia } from 'pinia';
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { deviceManager, Device } from '../services/DeviceManager';
import { detectPlatform, getPlatformConfig } from '../utils/platform';

export const useSystemStore = defineStore('system', () => {
  const platform = ref(detectPlatform());
  const config = ref(getPlatformConfig());
  const isConnected = ref(false);
  const systemStatus = ref<'normal' | 'warning' | 'error'>('normal');
  const alerts = ref<Array<{ id: string; type: string; message: string; timestamp: Date }>>([]);

  const user = ref({
    name: '操作员',
    role: 'operator',
    permissions: ['device-control', 'system-monitor', 'data-view']
  });

  const devices = computed(() => deviceManager.getAllDevices());
  const onlineDevices = computed(() =>
    devices.value.filter(d => d.status === 'online')
  );
  const offlineDevices = computed(() =>
    devices.value.filter(d => d.status === 'offline')
  );

  const productionData = ref({
    totalCount: 1248,
    passRate: 92.7,
    efficiency: 85.3,
    energyConsumption: 3.2
  });

  const systemMonitor = ref({
    cpu: 42,
    memory: 30,
    disk: 65,
    temperature: 38,
    uptime: 0
  });

  function updateSystemStatus() {
    const errorDevices = devices.value.filter(d => d.status === 'error');
    const offlineCount = offlineDevices.value.length;

    if (errorDevices.length > 0) {
      systemStatus.value = 'error';
    } else if (offlineCount > 0) {
      systemStatus.value = 'warning';
    } else {
      systemStatus.value = 'normal';
    }
  }

  function addAlert(type: string, message: string) {
    alerts.value.push({
      id: Date.now().toString(),
      type,
      message,
      timestamp: new Date()
    });

    if (alerts.value.length > 50) {
      alerts.value = alerts.value.slice(-50);
    }
  }

  function clearAlert(id: string) {
    const index = alerts.value.findIndex(alert => alert.id === id);
    if (index > -1) {
      alerts.value.splice(index, 1);
    }
  }

  function updateProductionData(data: Partial<typeof productionData.value>) {
    productionData.value = { ...productionData.value, ...data };
  }

  function updateSystemMonitor(data: Partial<typeof systemMonitor.value>) {
    systemMonitor.value = { ...systemMonitor.value, ...data };
  }

  function initialize() {
    setInterval(() => {
      updateSystemMonitor({
        cpu: Math.floor(Math.random() * 30) + 30,
        memory: Math.floor(Math.random() * 20) + 25,
        temperature: Math.floor(Math.random() * 10) + 35
      });
    }, 5000);

    setInterval(() => {
      updateSystemStatus();
    }, 1000);
  }

  return {
    platform,
    config,
    isConnected,
    systemStatus,
    alerts,
    user,
    devices,
    onlineDevices,
    offlineDevices,
    productionData,
    systemMonitor,

    updateSystemStatus,
    addAlert,
    clearAlert,
    updateProductionData,
    updateSystemMonitor,
    initialize
  };
});

export const pinia = createPinia();
