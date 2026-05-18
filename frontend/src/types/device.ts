export enum DeviceType {
  ROBOT_ARM = 'robot_arm',
  CONVEYOR_BELT = 'conveyor_belt',
  VISION_SYSTEM = 'vision_system',
  TEMPERATURE_SENSOR = 'temperature_sensor',
  PLC = 'plc',
  UNKNOWN = 'unknown'
}

export enum PairingStatus {
  UNPAIRED = 'unpaired',
  PAIRED = 'paired',
  PAIRING = 'pairing'
}

export enum ConnectionStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  ERROR = 'error'
}

export enum DeviceStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  ERROR = 'error',
  OFFLINE = 'offline'
}

export enum ConnectionType {
  SERIAL = 'serial',
  ETHERNET = 'ethernet',
  USB = 'usb',
  BLUETOOTH = 'bluetooth',
  WIFI = 'wifi'
}

export interface DeviceInfo {
  device_id: string;
  name: string;
  device_type: DeviceType;
  model?: string;
  manufacturer?: string;
  serial_number?: string;
  firmware_version?: string;
  connection_type: ConnectionType;
  connection_info: string;
  connection_params: Record<string, any>;
  last_seen: string;
  created_at: string;
  updated_at: string;
  is_online: boolean;
  status: ConnectionStatus;
  pairing_status: PairingStatus;
  description?: string;
  tags?: string[];
  capabilities?: string[];
  health_score?: number;
  port?: string;
  auto_connect?: boolean;
  last_connection_time?: string;
  connection_count?: number;
}

export interface PairingRecord {
  pairing_id: string;
  device_id: string;
  device_name: string;
  device_type: DeviceType;
  connection_info: string;
  paired_at: string;
  auto_connect: boolean;
  last_connected?: string;
  connection_count: number;
  custom_name?: string;
  status: 'active' | 'inactive' | 'deleted';
}

export interface DeviceStatusDetail {
  device_id: string;
  status: DeviceStatus;
  last_connection_time?: string;
  last_disconnection_time?: string;
  connection_duration?: number;
  error_count: number;
  last_error?: string;
  battery_level?: number;
  signal_strength?: number;
  temperature?: number;
  cpu_usage?: number;
  memory_usage?: number;
  network_speed?: number;
  uptime?: number;
  last_heartbeat?: string;
}

export interface ConnectionHistory {
  id: string;
  device_id: string;
  event_type: 'connect' | 'disconnect' | 'error' | 'scan';
  timestamp: string;
  details?: Record<string, any>;
  error_message?: string;
  ip_address?: string;
  port?: string;
  connection_duration?: number;
}

export interface DeviceConfig {
  device_id: string;
  name?: string;
  description?: string;
  auto_connect?: boolean;
  reconnect_attempts?: number;
  reconnect_interval?: number;
  heartbeat_interval?: number;
  timeout?: number;
  baud_rate?: number;
  data_bits?: number;
  stop_bits?: number;
  parity?: 'none' | 'even' | 'odd';
  flow_control?: boolean;
  network_timeout?: number;
  buffer_size?: number;
  max_retries?: number;
  custom_settings?: Record<string, any>;
  updated_at?: string;
}

export interface DeviceStatistics {
  total_devices: number;
  connected_devices: number;
  disconnected_devices: number;
  error_devices: number;
  total_connections: number;
  successful_connections: number;
  failed_connections: number;
  average_connection_time: number;
  total_errors: number;
  by_type: Record<DeviceType, number>;
  by_status: Record<DeviceStatus, number>;
  health_score: number;
  last_updated: string;
}

export interface ScanResult {
  devices_found: number;
  new_devices: number;
  existing_devices: number;
  scan_duration: number;
  timestamp: string;
  devices: DeviceInfo[];
}

export interface DeviceEvent {
  type: 'connected' | 'disconnected' | 'error' | 'status_changed' | 'config_updated';
  device_id: string;
  timestamp: string;
  data: any;
  severity?: 'info' | 'warning' | 'error';
}

export interface DeviceCapability {
  name: string;
  description: string;
  supported: boolean;
  parameters?: Record<string, any>;
}

export interface DeviceHealth {
  device_id: string;
  overall_score: number; // 0-100
  components: {
    connectivity: number;
    performance: number;
    battery: number;
    temperature: number;
    memory: number;
  };
  issues: string[];
  recommendations: string[];
  last_check: string;
}

export interface DeviceGroup {
  id: string;
  name: string;
  description?: string;
  device_ids: string[];
  created_at: string;
  updated_at: string;
  color?: string;
  icon?: string;
}

export interface DeviceOperationLog {
  id: string;
  device_id: string;
  operation: string;
  user?: string;
  timestamp: string;
  details?: Record<string, any>;
  success: boolean;
  error_message?: string;
}

export interface DeviceAlertSettings {
  device_id: string;
  enabled: boolean;
  alerts: {
    connectivity: boolean;
    performance: boolean;
    battery: boolean;
    temperature: boolean;
    custom: boolean;
  };
  thresholds: {
    battery_low: number;
    temperature_high: number;
    cpu_high: number;
    memory_high: number;
  };
  notification_methods: {
    email: boolean;
    sms: boolean;
    push: boolean;
    webhook: boolean;
  };
  recipients: string[];
}

export interface DeviceFirmware {
  device_id: string;
  current_version: string;
  latest_version?: string;
  update_available: boolean;
  release_notes?: string;
  update_url?: string;
  checksum?: string;
  size?: number;
  released_at?: string;
}

export interface DeviceLocation {
  device_id: string;
  latitude?: number;
  longitude?: number;
  altitude?: number;
  accuracy?: number;
  address?: string;
  floor?: string;
  room?: string;
  building?: string;
  campus?: string;
  last_updated: string;
}

export interface DeviceNetworkInfo {
  device_id: string;
  ip_address?: string;
  mac_address?: string;
  subnet_mask?: string;
  gateway?: string;
  dns_servers?: string[];
  signal_strength?: number;
  network_type?: string;
  ssid?: string;
  bssid?: string;
  channel?: number;
  frequency?: number;
  tx_rate?: number;
  rx_rate?: number;
  last_updated: string;
}

export interface DevicePerformanceMetrics {
  device_id: string;
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_in: number;
  network_out: number;
  temperature: number;
  uptime: number;
  response_time: number;
  error_rate: number;
}

export interface DeviceDataPoint {
  device_id: string;
  timestamp: string;
  metric: string;
  value: number | string | boolean;
  unit?: string;
  tags?: Record<string, string>;
}

export interface DeviceCommand {
  id: string;
  device_id: string;
  command: string;
  parameters?: Record<string, any>;
  timeout?: number;
  priority?: 'low' | 'normal' | 'high';
  created_at: string;
  executed_at?: string;
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'cancelled';
  result?: any;
  error_message?: string;
}

export interface DeviceTemplate {
  id: string;
  name: string;
  description?: string;
  device_type: DeviceType;
  connection_type: ConnectionType;
  default_config: DeviceConfig;
  capabilities: DeviceCapability[];
  icon?: string;
  color?: string;
  created_at: string;
  updated_at: string;
}

export interface DeviceDiscoveryConfig {
  enabled: boolean;
  scan_interval: number;
  auto_connect: boolean;
  connection_timeout: number;
  discovery_methods: {
    serial: boolean;
    network: boolean;
    bluetooth: boolean;
    usb: boolean;
  };
  network_ranges?: string[];
  serial_ports?: string[];
  bluetooth_services?: string[];
  filters?: {
    manufacturers?: string[];
    models?: string[];
    types?: DeviceType[];
  };
}

export type {
  DeviceInfo,
  DeviceStatusDetail,
  ConnectionHistory,
  DeviceConfig,
  DeviceStatistics,
  ScanResult,
  DeviceEvent,
  DeviceCapability,
  DeviceHealth,
  DeviceGroup,
  DeviceOperationLog,
  DeviceAlertSettings,
  DeviceFirmware,
  DeviceLocation,
  DeviceNetworkInfo,
  DevicePerformanceMetrics,
  DeviceDataPoint,
  DeviceCommand,
  DeviceTemplate,
  DeviceDiscoveryConfig
};