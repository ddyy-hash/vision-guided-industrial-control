export enum ConveyorStatusEnum {
  STOPPED = 'stopped',
  RUNNING = 'running',
  ADJUSTING = 'adjusting',
  ERROR = 'error',
  EMERGENCY_STOP = 'emergency_stop'
}

export enum ConveyorDirection {
  FORWARD = 'forward',
  BACKWARD = 'backward'
}

export enum DeviceType {
  STANDARD = 'standard',
  LIGHTWEIGHT = 'lightweight',
  HEAVY_DUTY = 'heavy_duty',
  PRECISION = 'precision',
  UNKNOWN = 'unknown'
}

export interface SpeedRange {
  min: number;
  max: number;
}

export interface ConveyorStatus {
  isRunning: boolean;
  currentSpeed: number;
  targetSpeed: number;
  actualSpeed: number;
  direction: ConveyorDirection;
  status: ConveyorStatusEnum;
  deviceType: DeviceType;
  speedRange: SpeedRange;
  temperature?: number;
  load?: number;
  healthScore?: number;
  lastUpdate: string;
  errorMessage?: string;
  warningMessages?: string[];
}

export interface ConveyorControlParams {
  speed: number;
  direction: ConveyorDirection;
  action?: 'start' | 'stop' | 'set_speed' | 'toggle_direction' | 'emergency_stop';
  acceleration?: number;
  deceleration?: number;
}

export interface DeviceCapabilities {
  deviceType: DeviceType;
  speedRange: SpeedRange;
  supportedDirections: ConveyorDirection[];
  maxAcceleration: number;
  maxDeceleration: number;
  precision: number;
  features: string[];
  recommendedSpeeds?: SpeedRecommendation[];
}

export interface SpeedRecommendation {
  speed: number;
  description: string;
  type: 'precision' | 'inspection' | 'standard' | 'high-speed' | 'custom';
  application?: string;
  icon?: string;
}

export interface ConveyorEvent {
  type: 'start' | 'stop' | 'speed_change' | 'direction_change' | 'error' | 'warning';
  timestamp: string;
  data: {
    previousSpeed?: number;
    currentSpeed?: number;
    previousDirection?: ConveyorDirection;
    currentDirection?: ConveyorDirection;
    errorCode?: string;
    errorMessage?: string;
    warningLevel?: 'low' | 'medium' | 'high';
  };
}

export interface ConveyorHistory {
  timestamp: string;
  speed: number;
  direction: ConveyorDirection;
  status: ConveyorStatusEnum;
  temperature?: number;
  load?: number;
  energyConsumption?: number;
}

export interface ConveyorStatistics {
  totalRuntime: number;
  averageSpeed: number;
  maxSpeed: number;
  minSpeed: number;
  directionChanges: number;
  emergencyStops: number;
  energyConsumption: number;
  maintenanceCount: number;
  lastMaintenance: string;
}

export interface ConveyorConfig {
  deviceId: string;
  name: string;
  description?: string;
  speedRange: SpeedRange;
  defaultSpeed: number;
  defaultDirection: ConveyorDirection;
  safetyLimits: {
    maxTemperature: number;
    maxLoad: number;
    emergencyStopDelay: number;
  };
  autoRecovery: boolean;
  notifications: {
    email: boolean;
    sms: boolean;
    push: boolean;
  };
  dataRetention: {
    historyDays: number;
    eventLogDays: number;
  };
}

export interface ConveyorAlertSettings {
  enabled: boolean;
  speedThreshold: {
    min: number;
    max: number;
  };
  temperatureThreshold: number;
  loadThreshold: number;
  vibrationThreshold?: number;
  notificationMethods: {
    email: boolean;
    sms: boolean;
    push: boolean;
    sound: boolean;
  };
  recipients: string[];
}

export interface MaintenanceRecord {
  id: string;
  deviceId: string;
  type: 'routine' | 'repair' | 'inspection' | 'calibration';
  description: string;
  performedBy: string;
  performedAt: string;
  nextScheduled?: string;
  partsReplaced?: string[];
  cost?: number;
  notes?: string;
  status: 'completed' | 'scheduled' | 'cancelled';
}

export type {
  ConveyorStatus,
  ConveyorControlParams,
  DeviceCapabilities,
  SpeedRecommendation,
  ConveyorEvent,
  ConveyorHistory,
  ConveyorStatistics,
  ConveyorConfig,
  ConveyorAlertSettings,
  MaintenanceRecord
};