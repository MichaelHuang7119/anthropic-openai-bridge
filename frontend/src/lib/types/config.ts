export interface CircuitBreakerConfig {
  failure_threshold: number;
  recovery_timeout: number;
}

export interface GlobalConfig {
  fallback_strategy: "priority" | "random";
  circuit_breaker: CircuitBreakerConfig;
}
