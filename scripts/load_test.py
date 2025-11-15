#!/usr/bin/env python3
"""
Load testing script for Anthropic OpenAI Bridge.
Target: 10k QPS

Usage:
    python scripts/load_test.py --url http://localhost:5175 --qps 10000 --duration 60
"""
import asyncio
import aiohttp
import argparse
import time
import statistics
from typing import List, Dict
import json


class LoadTester:
    """Load testing tool for API endpoints."""
    
    def __init__(self, base_url: str, api_key: str = "test-key"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.results: List[Dict] = []
    
    async def make_request(self, session: aiohttp.ClientSession, request_id: int) -> Dict:
        """Make a single API request."""
        url = f"{self.base_url}/v1/messages"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": f"Test request {request_id}. Say hello."
                }
            ]
        }
        
        start_time = time.time()
        try:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_time = time.time() - start_time
                status = response.status
                body = await response.text()
                
                return {
                    "request_id": request_id,
                    "status": status,
                    "response_time": response_time,
                    "success": 200 <= status < 300,
                    "error": None
                }
        except asyncio.TimeoutError:
            return {
                "request_id": request_id,
                "status": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": "timeout"
            }
        except Exception as e:
            return {
                "request_id": request_id,
                "status": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    async def run_test(self, target_qps: int, duration: int, concurrency: int = None):
        """
        Run load test.
        
        Args:
            target_qps: Target queries per second
            duration: Test duration in seconds
            concurrency: Max concurrent requests (default: target_qps * 2)
        """
        if concurrency is None:
            concurrency = min(target_qps * 2, 1000)  # Cap at 1000 concurrent
        
        print(f"Starting load test:")
        print(f"  Target QPS: {target_qps}")
        print(f"  Duration: {duration}s")
        print(f"  Max Concurrency: {concurrency}")
        print(f"  URL: {self.base_url}")
        
        connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=concurrency)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            start_time = time.time()
            end_time = start_time + duration
            request_id = 0
            semaphore = asyncio.Semaphore(concurrency)
            
            async def worker():
                nonlocal request_id
                while time.time() < end_time:
                    async with semaphore:
                        current_id = request_id
                        request_id += 1
                        result = await self.make_request(session, current_id)
                        self.results.append(result)
                    
                    # Rate limiting: wait to maintain target QPS
                    if target_qps > 0:
                        await asyncio.sleep(1.0 / target_qps)
            
            # Start workers
            workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
            await asyncio.gather(*workers)
        
        self.print_results()
    
    def print_results(self):
        """Print test results."""
        if not self.results:
            print("No results collected")
            return
        
        total_requests = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total_requests - successful
        
        response_times = [r["response_time"] for r in self.results if r["success"]]
        
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {successful} ({successful/total_requests*100:.2f}%)")
        print(f"Failed: {failed} ({failed/total_requests*100:.2f}%)")
        
        if response_times:
            print(f"\nResponse Time Statistics:")
            print(f"  Min: {min(response_times):.3f}s")
            print(f"  Max: {max(response_times):.3f}s")
            print(f"  Mean: {statistics.mean(response_times):.3f}s")
            print(f"  Median: {statistics.median(response_times):.3f}s")
            if len(response_times) > 1:
                print(f"  Std Dev: {statistics.stdev(response_times):.3f}s")
            
            # Percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.50)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            print(f"\nPercentiles:")
            print(f"  P50: {p50:.3f}s")
            print(f"  P95: {p95:.3f}s")
            print(f"  P99: {p99:.3f}s")
        
        # Error breakdown
        errors = {}
        for r in self.results:
            if not r["success"]:
                error_type = r.get("error", f"HTTP {r['status']}")
                errors[error_type] = errors.get(error_type, 0) + 1
        
        if errors:
            print(f"\nError Breakdown:")
            for error_type, count in errors.items():
                print(f"  {error_type}: {count}")
        
        # Calculate actual QPS based on response times
        if response_times and len(response_times) > 1:
            test_duration = max(response_times) - min(response_times)
            if test_duration > 0:
                actual_qps = len(response_times) / test_duration
                print(f"\nActual QPS: {actual_qps:.2f}")
        
        print("="*60)


async def main():
    parser = argparse.ArgumentParser(description="Load test for Anthropic OpenAI Bridge")
    parser.add_argument("--url", default="http://localhost:5175", help="Base URL of the API")
    parser.add_argument("--api-key", default="test-key", help="API key for authentication")
    parser.add_argument("--qps", type=int, default=1000, help="Target queries per second")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--concurrency", type=int, default=None, help="Max concurrent requests")
    
    args = parser.parse_args()
    
    tester = LoadTester(args.url, args.api_key)
    await tester.run_test(args.qps, args.duration, args.concurrency)


if __name__ == "__main__":
    asyncio.run(main())

