# PERFORMANCE BENCHMARK SCRIPT - PowerShell Version
# For Windows PowerShell execution

Write-Host "==========================================" -ForegroundColor Blue
Write-Host "DISTRIBUTED SYSTEMS BENCHMARK" -ForegroundColor Blue
Write-Host "==========================================" -ForegroundColor Blue

function Print-Section {
    param([string]$title)
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Blue
    Write-Host $title -ForegroundColor Blue
    Write-Host "==========================================" -ForegroundColor Blue
    Write-Host ""
}

function Check-Services {
    Write-Host "Checking if all services are running..." -ForegroundColor Cyan
    
    $services = @(
        @{Name="Lock Manager"; Port=8001},
        @{Name="Queue System"; Port=9001},
        @{Name="Cache System"; Port=7001}
    )
    
    $allRunning = $true
    
    foreach ($service in $services) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/" -Method GET -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "   OK $($service.Name) (Port $($service.Port)) - Running" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "   ERROR $($service.Name) (Port $($service.Port)) - Not responding" -ForegroundColor Red
            $allRunning = $false
        }
    }
    
    if (-not $allRunning) {
        Write-Host ""
        Write-Host "WARNING: Some services are not running. Please start all services first:" -ForegroundColor Yellow
        Write-Host "   docker-compose up -d" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Press Enter to continue anyway or Ctrl+C to exit..." -ForegroundColor Cyan
        Read-Host
    }
    
    return $allRunning
}

function Install-PythonDependencies {
    Write-Host "Installing Python dependencies for benchmarking..." -ForegroundColor Cyan
    
    try {
        # Check if pip is available
        python -m pip --version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Python pip not found. Please install Python 3.7+ with pip." -ForegroundColor Red
            return $false
        }
        
        # Install benchmark requirements
        Write-Host "   Installing matplotlib, pandas, numpy..." -ForegroundColor Gray
        python -m pip install matplotlib pandas numpy seaborn aiohttp --quiet
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   OK: Dependencies installed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "   ERROR: Failed to install dependencies" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "   ERROR: Installing dependencies failed" -ForegroundColor Red
        return $false
    }
}

function Run-Benchmark {
    param([int]$operations = 50)
    
    Write-Host "Starting performance benchmark..." -ForegroundColor Cyan
    Write-Host "   Operations per test: $operations" -ForegroundColor Gray
    Write-Host "   This may take several minutes..." -ForegroundColor Gray
    Write-Host ""
    
    try {
        # Run Python benchmark script
        python benchmark.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "Benchmark completed successfully!" -ForegroundColor Green
            Write-Host ""
            
            # Check if output files were generated
            if (Test-Path "performance_analysis.png") {
                Write-Host "Performance charts generated: performance_analysis.png" -ForegroundColor Green
            }
            
            if (Test-Path "performance_report.md") {
                Write-Host "Performance report generated: performance_report.md" -ForegroundColor Green
            }
            
            return $true
        } else {
            Write-Host "Benchmark failed with exit code: $LASTEXITCODE" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "Error running benchmark" -ForegroundColor Red
        return $false
    }
}

function Show-Results {
    Write-Host ""
    Print-Section "BENCHMARK RESULTS"
    
    if (Test-Path "performance_report.md") {
        Write-Host "Opening performance report..." -ForegroundColor Cyan
        
        # Try to open with default markdown viewer
        try {
            Start-Process "performance_report.md"
        }
        catch {
            Write-Host "   Report saved as: performance_report.md" -ForegroundColor Gray
        }
    }
    
    if (Test-Path "performance_analysis.png") {
        Write-Host "Opening performance charts..." -ForegroundColor Cyan
        
        # Try to open image
        try {
            Start-Process "performance_analysis.png"
        }
        catch {
            Write-Host "   Charts saved as: performance_analysis.png" -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    Write-Host "Generated Files:" -ForegroundColor Yellow
    
    if (Test-Path "performance_analysis.png") {
        $imageSize = (Get-Item "performance_analysis.png").Length
        $imageSizeKB = [Math]::Round($imageSize/1024, 1)
        Write-Host "   performance_analysis.png (Size: $imageSizeKB KB)" -ForegroundColor White
    }
    
    if (Test-Path "performance_report.md") {
        $reportSize = (Get-Item "performance_report.md").Length
        $reportSizeKB = [Math]::Round($reportSize/1024, 1)
        Write-Host "   performance_report.md (Size: $reportSizeKB KB)" -ForegroundColor White
    }
}

function Generate-CustomReport {
    Write-Host ""
    Print-Section "GENERATING CUSTOM REPORT"
    
    $currentDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $computerName = $env:COMPUTERNAME
    $psVersion = $PSVersionTable.PSVersion.ToString()
    
    $reportContent = @"
# Performance Analysis Report

**Nama:** Rionando Soeksin Putra
**NIM:** 11221063
**MK:** Sistem Paralel dan Terdistribusi A

## Ringkasan Eksekutif

Laporan ini menyajikan analisis performa komprehensif dari implementasi sistem terdistribusi, membandingkan arsitektur single-node versus distributed-node pada tiga komponen inti: Lock Manager, Message Queue System, dan Cache System.

## Metodologi Testing

- Test Duration: $currentDate
- Operations per Test: 50 operations
- Testing Environment: Windows PowerShell
- Services Tested: Lock Manager, Queue System, Cache System
- Configurations: Single Node vs Distributed (3 nodes each)

## Key Performance Indicators

### Metrics Measured:
- Average Latency: Response time in milliseconds
- Throughput: Operations per second
- Success Rate: Percentage of successful operations
- Resource Utilization: System resource consumption

### Test Scenarios:
- Lock Manager: Acquire/Release lock operations
- Queue System: Produce/Consume/Acknowledge message flow
- Cache System: Write/Read operations with MESI protocol

## Analysis Results

[Benchmark results will be inserted here after running the Python script]

## Technical Implementation Details

### Distributed Lock Manager (Raft Consensus)
- Algorithm: Raft consensus for leader election
- Consistency: Strong consistency guarantees
- Fault Tolerance: 2/3 majority requirement
- Network Overhead: Leader election + log replication

### Message Queue System (Consistent Hashing)
- Distribution: Consistent hashing with virtual nodes
- Delivery: At-least-once delivery guarantee
- Persistence: Redis backend storage
- Replication Factor: 2x redundancy

### Cache System (MESI Protocol)
- Coherence: MESI state machine implementation
- Communication: Bus snooping for invalidations
- States: Modified, Exclusive, Shared, Invalid
- Eviction: LRU (Least Recently Used) policy

## Conclusions and Recommendations

The performance analysis demonstrates the classic distributed systems trade-offs between consistency, availability, and partition tolerance (CAP theorem). While single-node configurations show better raw performance, distributed systems provide essential production capabilities including fault tolerance, horizontal scalability, and geographic distribution.

Generated on: $currentDate
System: $computerName
PowerShell Version: $psVersion
"@

    $reportContent | Out-File -FilePath "custom_performance_report.md" -Encoding UTF8
    Write-Host "   Custom report template created: custom_performance_report.md" -ForegroundColor Green
}

# Main execution flow
Print-Section "PERFORMANCE BENCHMARK SETUP"

# Check services
$servicesRunning = Check-Services

# Install dependencies
Write-Host ""
$depsInstalled = Install-PythonDependencies

if (-not $depsInstalled) {
    Write-Host ""
    Write-Host "Failed to install required dependencies. Exiting..." -ForegroundColor Red
    Write-Host "Please install Python 3.7+ and try again." -ForegroundColor Yellow
    exit 1
}

# Ask user for confirmation
Write-Host ""
Write-Host "Ready to start performance benchmark!" -ForegroundColor Green
Write-Host ""
Write-Host "This benchmark will:" -ForegroundColor Yellow
Write-Host "   - Test Lock Manager (single vs distributed)" -ForegroundColor White
Write-Host "   - Test Queue System (single vs distributed)" -ForegroundColor White  
Write-Host "   - Test Cache System (single vs distributed)" -ForegroundColor White
Write-Host "   - Generate performance charts and detailed report" -ForegroundColor White
Write-Host ""

$response = Read-Host "Continue with benchmark? (y/N)"

if ($response -match "^[Yy]") {
    # Run benchmark
    Print-Section "RUNNING PERFORMANCE TESTS"
    
    $benchmarkSuccess = Run-Benchmark -operations 50
    
    if ($benchmarkSuccess) {
        # Show results
        Show-Results
        
        # Generate custom report
        Generate-CustomReport
        
        Print-Section "BENCHMARK COMPLETE!"
        
        Write-Host "Performance analysis completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Key Outputs:" -ForegroundColor Blue
        Write-Host "   - Performance comparison charts with visualizations" -ForegroundColor White
        Write-Host "   - Detailed performance report with analysis" -ForegroundColor White
        Write-Host "   - Single vs Distributed performance metrics" -ForegroundColor White
        Write-Host "   - Technical recommendations and insights" -ForegroundColor White
        Write-Host ""
        Write-Host "Ready for academic submission and presentation!" -ForegroundColor Yellow
        
    } else {
        Write-Host ""
        Write-Host "Benchmark failed. Please check:" -ForegroundColor Red
        Write-Host "   - All services are running (docker-compose up -d)" -ForegroundColor Gray
        Write-Host "   - Python and dependencies are properly installed" -ForegroundColor Gray
        Write-Host "   - No network connectivity issues" -ForegroundColor Gray
    }
    
} else {
    Write-Host ""
    Write-Host "Benchmark cancelled by user." -ForegroundColor Gray
    Write-Host "   Run this script again when ready to benchmark." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Press Enter to exit..." -ForegroundColor Cyan
Read-Host