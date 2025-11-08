export interface CategoryHealth {
  healthy: boolean;
  responseTime: number | null;
  error: string | null;
}

export interface ProviderHealth {
  name: string;
  healthy: boolean | null;
  enabled: boolean;
  priority: number;
  lastCheck: string | null;
  responseTime: number | null;
  error?: string | null;
  categories?: {
    big?: CategoryHealth;
    middle?: CategoryHealth;
    small?: CategoryHealth;
  };
}

export interface HealthStatus {
  status: 'healthy' | 'partial' | 'unhealthy' | 'error';
  timestamp: string;
  providers: ProviderHealth[];
  error?: string;
}
