#!/usr/bin/env python3
"""
Home Health Analytics System Launcher

This script launches both the FastAPI backend and Next.js frontend
for the complete home health analytics system.
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")

    # Check Python packages
    try:
        import fastapi
        import uvicorn
        import pandas
        print("✅ Python dependencies: OK")
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        print("Run: pip install fastapi uvicorn pandas openpyxl pyyaml")
        return False

    # Check if Node.js is available
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js: {result.stdout.strip()}")
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False

    # Check if Next.js app exists
    dashboard_path = Path("home-health-dashboard")
    if dashboard_path.exists() and (dashboard_path / "package.json").exists():
        print("✅ Next.js application: Found")
    else:
        print("❌ Next.js application not found")
        return False

    return True

def check_data():
    """Check if analytics data is available."""
    print("\n📊 Checking analytics data...")

    # Check for analytics output
    analytics_files = list(Path("analytics_output").glob("*.xlsx"))
    if analytics_files:
        latest_file = max(analytics_files, key=lambda x: x.stat().st_mtime)
        print(f"✅ Analytics data: {latest_file.name}")
        return True
    else:
        print("⚠️  No analytics data found")
        print("   Running PDF extraction and analytics generation...")

        try:
            # Run PDF extraction
            subprocess.run([sys.executable, "home_health_extractor.py"], check=True)

            # Run analytics generation
            subprocess.run([sys.executable, "pivot_analytics.py"], check=True)

            print("✅ Analytics data generated successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate analytics data: {e}")
            return False

def start_api_server():
    """Start the FastAPI backend server."""
    print("\n🚀 Starting API server...")

    try:
        # Use virtual environment python if available
        venv_python = Path("venv/bin/python")
        python_cmd = str(venv_python) if venv_python.exists() else sys.executable

        # Start API server in background
        api_process = subprocess.Popen(
            [python_cmd, "api_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Give it time to start
        time.sleep(3)

        # Check if it's still running
        if api_process.poll() is None:
            print("✅ API server started on http://localhost:8000")
            return api_process
        else:
            stdout, stderr = api_process.communicate()
            print(f"❌ API server failed to start")
            print(f"Error: {stderr.decode()}")
            return None

    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None

def start_frontend():
    """Start the Next.js frontend."""
    print("\n🎨 Starting Next.js frontend...")

    try:
        # Change to dashboard directory
        os.chdir("home-health-dashboard")

        # Install dependencies if needed
        if not Path("node_modules").exists():
            print("📦 Installing Node.js dependencies...")
            subprocess.run(["npm", "install"], check=True)

        # Start Next.js dev server
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Give it time to start
        time.sleep(5)

        # Check if it's still running
        if frontend_process.poll() is None:
            print("✅ Frontend started on http://localhost:3000")
            return frontend_process
        else:
            stdout, stderr = frontend_process.communicate()
            print(f"❌ Frontend failed to start")
            print(f"Error: {stderr.decode()}")
            return None

    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return None
    finally:
        # Change back to original directory
        os.chdir("..")

def main():
    """Main launcher function."""
    print("🏥 HOME HEALTH ANALYTICS SYSTEM LAUNCHER")
    print("=" * 60)

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing dependencies.")
        return 1

    # Check/generate data
    if not check_data():
        print("\n❌ Data check failed. Cannot proceed without analytics data.")
        return 1

    # Start services
    print("\n🚀 Starting services...")

    # Start API server
    api_process = start_api_server()
    if not api_process:
        return 1

    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        # Clean up API process
        api_process.terminate()
        return 1

    # Success message
    print("\n" + "=" * 60)
    print("🎉 HOME HEALTH ANALYTICS SYSTEM IS RUNNING!")
    print("=" * 60)
    print("📊 Backend API: http://localhost:8000")
    print("   📋 API Docs: http://localhost:8000/docs")
    print("🎨 Frontend Dashboard: http://localhost:3000")
    print("\n💡 Features Available:")
    print("   • Executive Dashboard with KPIs and charts")
    print("   • Revenue by Claim analysis with search/sort")
    print("   • Service Costs breakdown")
    print("   • Patient Profitability analysis")
    print("   • Provider Performance metrics")
    print("   • Claims Analysis")
    print("   • Insurance Performance tracking")
    print("\n🔄 Data Summary:")

    # Show data summary
    try:
        import requests
        response = requests.get("http://localhost:8000/analytics/summary", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   • {data['total_patients']} patients")
            print(f"   • {data['total_claims']} claims")
            print(f"   • {data['total_visits']} visits")
            print(f"   • ${data['total_billed']:,.2f} total billed")
            print(f"   • {data['collection_rate']:.1f}% collection rate")
        else:
            print("   • Data loaded and ready")
    except:
        print("   • Data loaded and ready")

    print("\n⏹️  Press Ctrl+C to stop all services")
    print("=" * 60)

    try:
        # Wait for user interrupt
        while True:
            time.sleep(1)

            # Check if processes are still running
            if api_process.poll() is not None:
                print("⚠️  API server stopped unexpectedly")
                break

            if frontend_process.poll() is not None:
                print("⚠️  Frontend stopped unexpectedly")
                break

    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down services...")

        # Terminate processes
        if api_process and api_process.poll() is None:
            api_process.terminate()
            print("✅ API server stopped")

        if frontend_process and frontend_process.poll() is None:
            frontend_process.terminate()
            print("✅ Frontend stopped")

        print("👋 Thanks for using Home Health Analytics!")
        return 0

    return 1

if __name__ == "__main__":
    exit(main())