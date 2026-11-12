#!/bin/bash

# VIX LEAPS Trade Analysis Launcher
# Run this script to see all analyses

echo "=========================================="
echo "  VIX LEAPS TRADE ANALYSIS SUITE"
echo "=========================================="
echo ""
echo "Select an option:"
echo ""
echo "  1) Full Trade Analysis (recommended)"
echo "  2) Interactive Scenario Calculator"
echo "  3) Real-time Position Monitor"
echo "  4) Run All Reports"
echo "  5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "Running Full Trade Analysis..."
        echo ""
        python3 vix_trade_analyzer.py
        ;;
    2)
        echo ""
        echo "Running Interactive Calculator..."
        echo ""
        python3 vix_calculator_interactive.py
        ;;
    3)
        echo ""
        echo "Running Position Monitor..."
        echo ""
        python3 backend/vix_leaps_monitor.py
        ;;
    4)
        echo ""
        echo "Running ALL reports..."
        echo ""
        echo "=========================================="
        echo "  1/3: FULL TRADE ANALYSIS"
        echo "=========================================="
        python3 vix_trade_analyzer.py
        echo ""
        echo ""
        echo "=========================================="
        echo "  2/3: INTERACTIVE SCENARIOS"
        echo "=========================================="
        python3 vix_calculator_interactive.py
        echo ""
        echo ""
        echo "=========================================="
        echo "  3/3: POSITION MONITOR"
        echo "=========================================="
        python3 backend/vix_leaps_monitor.py
        ;;
    5)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Please run again."
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Analysis complete!"
echo "=========================================="
