#!/usr/bin/env python3
"""
Start Anthropic OpenAI Bridge server.

This script starts the FastAPI server with uvicorn, supporting:
- Custom HOST and PORT via environment variables
- Port availability checking
- Auto-reload in development mode
- Proper error handling
"""

import os
import sys
import socket
import argparse
import uvicorn


def check_port_available(host: str, port: int) -> bool:
    """Check if a port is available on the given host."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # Port is available if connection fails
    except socket.gaierror:
        # If hostname resolution fails, assume port check is not possible
        # but don't block startup (might be a DNS issue)
        return True
    except Exception:
        # On any other error, assume port is available
        return True


def find_process_using_port(port: int) -> str:
    """Try to find which process is using the port."""
    import subprocess
    
    # Try lsof first
    try:
        result = subprocess.run(
            ['lsof', '-i', f':{port}', '-sTCP:LISTEN', '-t'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            return f"PID(s): {', '.join(pids)}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Try netstat as fallback
    try:
        result = subprocess.run(
            ['netstat', '-tuln'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if f':{port} ' in line and 'LISTEN' in line:
                    return "Found via netstat"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    return "Unknown"


def main():
    """Main entry point for starting the proxy server."""
    parser = argparse.ArgumentParser(
        description='Start Anthropic OpenAI Bridge server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_proxy.py
  python start_proxy.py --host 127.0.0.1 --port 3000
  HOST=0.0.0.0 PORT=8000 python start_proxy.py --reload
  python start_proxy.py --no-reload
        """
    )
    
    parser.add_argument(
        '--host',
        default=None,
        help='Host to bind to (default: 0.0.0.0, or HOST env var if set to valid IP/hostname)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.environ.get('PORT', '8000')),
        help='Port to bind to (default: 8000, or PORT env var)'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        default=os.environ.get('RELOAD', 'false').lower() in ('true', '1', 'yes'),
        help='Enable auto-reload on code changes (default: False, set RELOAD=true to enable)'
    )
    parser.add_argument(
        '--no-reload',
        action='store_false',
        dest='reload',
        help='Disable auto-reload'
    )
    parser.add_argument(
        '--log-level',
        default=os.environ.get('LOG_LEVEL', 'info'),
        choices=['critical', 'error', 'warning', 'info', 'debug', 'trace'],
        help='Log level (default: info, or LOG_LEVEL env var)'
    )
    
    args = parser.parse_args()
    
    # Set PROVIDER_CONFIG_PATH if not already set
    if 'PROVIDER_CONFIG_PATH' not in os.environ:
        os.environ['PROVIDER_CONFIG_PATH'] = './provider.json'
    
    # Determine host: prefer command line arg, then env var (if valid), else default
    host_env = os.environ.get('HOST', '').strip()
    
    # Validate host: should look like an IP address or simple hostname
    # Filter out system identifiers that conda/bash might set
    invalid_hosts = ['x86_64-conda-linux-gnu', 'linux', 'aarch64-conda-linux-gnu']
    
    if args.host is not None:
        host = args.host
    elif host_env and host_env not in invalid_hosts and len(host_env) < 50:
        # Basic validation: not in blacklist and reasonable length
        host = host_env
    else:
        host = '0.0.0.0'
    
    # Check port availability
    port = args.port
    
    if not check_port_available(host, port):
        process_info = find_process_using_port(port)
        print(f"❌ Error: Port {port} is already in use", file=sys.stderr)
        print(f"   Process info: {process_info}", file=sys.stderr)
        print(f"\n💡 Solutions:", file=sys.stderr)
        print(f"   1. Stop the existing process: kill <PID>", file=sys.stderr)
        print(f"   2. Use a different port: python start_proxy.py --port {port + 1}", file=sys.stderr)
        print(f"   3. Or set PORT env var: PORT={port + 1} python start_proxy.py", file=sys.stderr)
        sys.exit(1)
    
    # Print startup information
    print("🚀 Starting Anthropic OpenAI Bridge Server")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Provider Config: {os.environ.get('PROVIDER_CONFIG_PATH', './provider.json')}")
    print(f"   Auto-reload: {'Enabled' if args.reload else 'Disabled'}")
    print(f"   Log level: {args.log_level}")
    print()
    
    # Start uvicorn server
    try:
        # Force polling mode for watchfiles to avoid DNS issues with native watching
        if args.reload:
            os.environ['WATCHFILES_FORCE_POLLING'] = '1'
        
        # Build uvicorn.run arguments
        run_kwargs = {
            "app": "app.main:app",
            "host": host,
            "port": port,
            "reload": args.reload,
            "log_level": args.log_level,
        }
        
        # reload_dirs is available in uvicorn (note: plural form)
        # Use it to explicitly specify watch directory when reload is enabled
        if args.reload:
            run_kwargs['reload_dirs'] = [os.getcwd()]
        
        uvicorn.run(**run_kwargs)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

