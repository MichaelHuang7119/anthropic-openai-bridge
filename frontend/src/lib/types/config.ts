export interface CircuitBreakerConfig {
  failure_threshold: number;
  recovery_timeout: number;
}

export interface GlobalConfig {
  fallback_strategy: "priority" | "random";
  circuit_breaker: CircuitBreakerConfig;
  retry_on_zero_output_tokens: boolean;
  retry_on_zero_output_tokens_retries: number;
}
