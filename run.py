#!/usr/bin/env python3
"""
ThetaGrid Project Runner
Starts both backend and frontend services
"""

import os
import sys
import subprocess
import time
import signal
import webbrowser
from pathlib import Path

# Colors for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_color(text, color):
    print(f"{color}{text}{Colors.RESET}")

def check_port(port):
    """Check if a port is already in use"""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    except:
        return False

def run_command(command, cwd=None, shell=False, background=False):
    """Run a shell command"""
    try:
        if background:
            return subprocess.Popen(
                command,
                cwd=cwd,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        else:
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=shell,
                capture_output=True,
                text=True
            )
            return result
    except Exception as e:
        print_color(f"Error running command: {e}", Colors.RED)
        return None

def main():
    print_color("\n" + "="*50, Colors.CYAN)
    print_color("🚀 THETAGRID PROJECT STARTUP", Colors.BOLD + Colors.CYAN)
    print_color("="*50, Colors.CYAN)
    
    # Get project root
    project_root = Path(__file__).parent.absolute()
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"
    
    # Check directories
    if not backend_dir.exists():
        print_color(f"Backend directory not found: {backend_dir}", Colors.RED)
        return
    if not frontend_dir.exists():
        print_color(f"Frontend directory not found: {frontend_dir}", Colors.RED)
        return
    
    # Check ports
    print_color("\n🔍 Checking ports...", Colors.YELLOW)
    if check_port(8000):
        print_color("   Port 8000 (Backend) is already in use!", Colors.RED)
        print_color("   Please stop any existing services on port 8000", Colors.YELLOW)
        return
    
    if check_port(5173):
        print_color("   Port 5173 (Frontend) is already in use!", Colors.RED)
        print_color("   Please stop any existing services on port 5173", Colors.YELLOW)
        return
    
    print_color("   Ports are available ✓", Colors.GREEN)
    
    # Start backend
    print_color("\n🔧 Starting Backend (FastAPI)...", Colors.YELLOW)
    print_color(f"   Directory: {backend_dir}", Colors.BLUE)
    
    # Check virtual environment
    venv_path = backend_dir / ".venv"
    if not venv_path.exists():
        print_color("   ❌ Virtual environment not found!", Colors.RED)
        print_color("   Create with: python -m venv .venv", Colors.YELLOW)
        print_color("   Then install: pip install -r requirements.txt", Colors.YELLOW)
        return
    
    # Start backend in background
    backend_cmd = ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    
    # Use the virtual environment's Python
    venv_python = venv_path / "bin" / "python"
    if not venv_python.exists():
        venv_python = venv_path / "Scripts" / "python.exe"
    
    if venv_python.exists():
        backend_cmd = [str(venv_python), "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    
    backend_process = run_command(backend_cmd, cwd=str(backend_dir), background=True)
    if not backend_process:
        print_color("   ❌ Failed to start backend!", Colors.RED)
        return
    
    print_color("   ✅ Backend started (PID: {})".format(backend_process.pid), Colors.GREEN)
    
    # Wait for backend to initialize
    print_color("   Waiting for backend to start...", Colors.BLUE)
    time.sleep(5)
    
    # Start frontend
    print_color("\n🎨 Starting Frontend (React/Vite)...", Colors.YELLOW)
    print_color(f"   Directory: {frontend_dir}", Colors.BLUE)
    
    # Check node_modules
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print_color("   Installing npm dependencies...", Colors.YELLOW)
        npm_install = run_command(["npm", "install"], cwd=str(frontend_dir))
        if npm_install and npm_install.returncode != 0:
            print_color("   ❌ Failed to install dependencies!", Colors.RED)
            backend_process.terminate()
            return
    
    # Start frontend in background
    frontend_process = run_command(["npm", "run", "dev"], cwd=str(frontend_dir), background=True)
    if not frontend_process:
        print_color("   ❌ Failed to start frontend!", Colors.RED)
        backend_process.terminate()
        return
    
    print_color("   ✅ Frontend started (PID: {})".format(frontend_process.pid), Colors.GREEN)
    
    # Wait for frontend to initialize
    print_color("   Waiting for frontend to start...", Colors.BLUE)
    time.sleep(3)
    
    # Display success message
    print_color("\n" + "="*50, Colors.GREEN)
    print_color("🎉 THETAGRID IS NOW RUNNING!", Colors.BOLD + Colors.GREEN)
    print_color("="*50, Colors.GREEN)
    print_color("\n🌐 Access the application:", Colors.CYAN)
    print_color("   Frontend (Dashboard):  " + Colors.BOLD + "http://localhost:5173/" + Colors.RESET)
    print_color("   Backend API:           " + Colors.BOLD + "http://localhost:8000/" + Colors.RESET)
    print_color("   API Documentation:     " + Colors.BOLD + "http://localhost:8000/docs" + Colors.RESET)
    print_color("   WebSocket (Live Data): " + Colors.BOLD + "ws://localhost:8000/ws" + Colors.RESET)
    
    print_color("\n📊 Available API endpoints:", Colors.MAGENTA)
    print_color("   GET /api/market         - Live market data")
    print_color("   GET /api/option-chain/{index} - Option chains")
    print_color("   GET /api/buildup/{index} - OI buildup analysis")
    print_color("   GET /api/straddle-history/{index} - Straddle premium history")
    print_color("   GET /api/positions      - Angel One positions")
    print_color("   GET /api/status         - System status")
    
    print_color("\n📈 Current features:", Colors.YELLOW)
    print_color("   ✓ Live NIFTY & SENSEX data")
    print_color("   ✓ Live INDIA VIX")
    print_color("   ✓ Live Gift Nifty (scraped)")
    print_color("   ✓ Option chain analytics")
    print_color("   ✓ OI buildup analysis")
    print_color("   ✓ ATM straddle premium tracking")
    print_color("   ✓ PCR, Max Pain, Expected Move")
    print_color("   ✓ Angel One integration")
    
    print_color("\n🛑 To stop the application:", Colors.RED)
    print_color("   Press Ctrl+C in this terminal", Colors.BOLD)
    
    # Ask to open browser
    try:
        response = input("\nOpen frontend in browser? (Y/n): ").strip().lower()
        if response in ['', 'y', 'yes']:
            webbrowser.open("http://localhost:5173")
            print_color("   Opening browser...", Colors.GREEN)
    except:
        pass
    
    print_color("\n" + "="*50, Colors.CYAN)
    print_color("Monitoring logs... (Press Ctrl+C to stop)", Colors.CYAN)
    print_color("="*50, Colors.CYAN)
    
    # Signal handler for cleanup
    def signal_handler(sig, frame):
        print_color("\n\n🛑 Stopping services...", Colors.RED)
        backend_process.terminate()
        frontend_process.terminate()
        print_color("✅ Services stopped", Colors.GREEN)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Monitor processes
    try:
        # Print backend output
        print_color("\n📡 Backend logs:", Colors.YELLOW)
        for line in iter(backend_process.stdout.readline, ''):
            if line:
                print(f"   {line}", end='')
        
        # Print frontend output
        print_color("\n🎨 Frontend logs:", Colors.MAGENTA)
        for line in iter(frontend_process.stdout.readline, ''):
            if line:
                print(f"   {line}", end='')
                
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()