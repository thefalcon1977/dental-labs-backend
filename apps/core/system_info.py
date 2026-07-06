"""System information utilities for displaying startup information.

This module provides utilities for gathering and displaying system information
including CPU, memory, GPU, and platform details. Used primarily for startup
banners and logging system capabilities.

The module gracefully handles missing optional dependencies (psutil, GPUtil)
and provides fallback values when system information cannot be determined.
"""

import multiprocessing
import platform
import sys

try:
    import psutil  # type: ignore[import-untyped]
except ImportError:
    psutil = None  # type: ignore[assignment, misc]

try:
    import GPUtil  # type: ignore[import-untyped]
except ImportError:
    GPUtil = None  # type: ignore[assignment, misc]

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from apps.core.types import CpuInfoDict, GpuInfoDict, MemoryInfoDict, SystemInfoDict

console = Console()


def get_cpu_info() -> CpuInfoDict:
    """Get CPU information.

    Gathers CPU information including logical/physical core counts, architecture,
    processor name, and frequency (if available via psutil).

    Returns:
        Dictionary with CPU information:
        - logical_cores: Number of logical CPU cores
        - physical_cores: Number of physical CPU cores (or "N/A")
        - architecture: CPU architecture (e.g., "x86_64")
        - processor: Processor name
        - frequency_mhz: Current CPU frequency in MHz (if available)
        - frequency_min_mhz: Minimum CPU frequency (if available)
        - frequency_max_mhz: Maximum CPU frequency (if available)
    """
    cpu_count = multiprocessing.cpu_count()
    cpu_count_physical = psutil.cpu_count(logical=False) if psutil else None

    info: CpuInfoDict = {
        "logical_cores": cpu_count,
        "physical_cores": cpu_count_physical or "N/A",
        "architecture": platform.machine(),
        "processor": platform.processor(),
    }

    if psutil:
        try:
            freq = psutil.cpu_freq()
            if freq:
                info["frequency_mhz"] = round(freq.current, 2)
                info["frequency_min_mhz"] = round(freq.min, 2)
                info["frequency_max_mhz"] = round(freq.max, 2)
        except (AttributeError, OSError, RuntimeError):
            # CPU frequency not available on this system (e.g., some VMs, containers)
            # This is expected and acceptable - continue without frequency info
            pass

    return info


def get_memory_info() -> MemoryInfoDict:
    """Get memory information.

    Gathers system memory information including total, available, used memory,
    and usage percentage. Requires psutil library.

    Returns:
        Dictionary with memory information:
        - total_gb: Total memory in GB (or "N/A" if psutil unavailable)
        - available_gb: Available memory in GB
        - used_gb: Used memory in GB
        - percent: Memory usage percentage
    """
    if not psutil:
        return {
            "total_gb": "N/A (install psutil for details)",
            "available_gb": "N/A",
            "used_gb": "N/A",
            "percent": "N/A",
        }

    try:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        }
    except Exception:
        return {
            "total_gb": "N/A",
            "available_gb": "N/A",
            "used_gb": "N/A",
            "percent": "N/A",
        }


def get_gpu_info() -> GpuInfoDict:
    """Get GPU information.

    Attempts to detect and gather information about available GPUs. Supports
    NVIDIA GPUs via GPUtil library. Falls back gracefully if no GPUs are
    detected or libraries are unavailable.

    Returns:
        Dictionary with GPU information:
        - count: Number of GPUs detected
        - gpus: List of GPU information dictionaries (if available)
        - message: Status message if no GPUs detected
    """
    gpus = []

    # Try GPUtil first (NVIDIA GPUs)
    if GPUtil:
        try:
            gpu_list = GPUtil.getGPUs()
            for gpu in gpu_list:
                gpus.append(
                    {
                        "id": gpu.id,
                        "name": gpu.name,
                        "memory_total_mb": gpu.memoryTotal,
                        "memory_used_mb": gpu.memoryUsed,
                        "memory_free_mb": gpu.memoryFree,
                        "load_percent": gpu.load * 100,
                        "temperature_c": gpu.temperature,
                    }
                )
        except (RuntimeError, OSError, AttributeError):
            # GPUtil failed (no NVIDIA GPUs, nvidia-smi not available, etc.)
            # This is expected on systems without NVIDIA GPUs - continue to fallback
            pass

    # Note: psutil doesn't have great GPU support, so we skip it
    # If GPUtil didn't find GPUs, we return empty list

    if not gpus:
        return {
            "count": 0,
            "gpus": [],
            "message": "No GPU detected or GPU libraries not available",
        }

    return {
        "count": len(gpus),
        "gpus": gpus,
    }


def get_system_info() -> SystemInfoDict:
    """Get comprehensive system information.

    Gathers all available system information including platform details,
    Python version, CPU, memory, and GPU information.

    Returns:
        Dictionary with comprehensive system information:
        - platform: Operating system and platform details
        - python: Python version and executable path
        - cpu: CPU information (from get_cpu_info())
        - memory: Memory information (from get_memory_info())
        - gpu: GPU information (from get_gpu_info())
    """
    return {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "gpu": get_gpu_info(),
    }


def format_system_info(
    service_name: str,
    version: str,
    host: str,
    port: int,
    workers: int,
    workers_max: int,
    pool_size: int,
    max_overflow: int,
) -> None:
    """Format and display system information in Typer-style format.

    Uses Rich tables and panels to display system information in a clean,
    Typer-style format similar to CLI help output.

    Args:
        service_name: Name of the service
        version: Version of the service
        host: Host the service binds to
        port: Port the service binds to
        workers: Number of workers running
        workers_max: Maximum number of workers
        pool_size: Database pool size
        max_overflow: Database max overflow
    """
    info = get_system_info()

    # Create main table
    main_table = Table(
        show_header=True,
        header_style="bold magenta",
        border_style="blue",
        box=None,  # Use simple borders like Typer
        padding=(0, 1),
    )
    main_table.add_column("Setting", style="cyan", no_wrap=False, width=35)
    main_table.add_column("Value", style="yellow", overflow="fold", width=50)

    # Service Information Section
    main_table.add_row(
        "[bold cyan]Service Information[/bold cyan]",
        "",
        style="dim",
    )
    main_table.add_row("  Service Name", service_name)
    main_table.add_row("  Version", version)
    main_table.add_row("  Environment", f"{platform.system()} {platform.release()}")
    main_table.add_row("  Python", info["python"]["version"])
    main_table.add_row("  Host", host)
    main_table.add_row("  Port", str(port))

    # CPU Information Section
    main_table.add_row(
        "[bold cyan]CPU Information[/bold cyan]",
        "",
        style="dim",
    )
    main_table.add_row("  Logical Cores", str(info["cpu"]["logical_cores"]))
    main_table.add_row("  Physical Cores", str(info["cpu"]["physical_cores"]))
    main_table.add_row("  Architecture", info["cpu"]["architecture"])
    if "frequency_mhz" in info["cpu"]:
        main_table.add_row("  Frequency", f"{info['cpu']['frequency_mhz']} MHz")

    # Memory Information Section
    main_table.add_row(
        "[bold cyan]Memory Information[/bold cyan]",
        "",
        style="dim",
    )
    main_table.add_row("  Total", f"{info['memory']['total_gb']} GB")
    main_table.add_row("  Available", f"{info['memory']['available_gb']} GB")
    main_table.add_row(
        "  Used",
        f"{info['memory']['used_gb']} GB ({info['memory']['percent']}%)",
    )

    # GPU Information Section
    main_table.add_row(
        "[bold cyan]GPU Information[/bold cyan]",
        "",
        style="dim",
    )
    if info["gpu"]["count"] > 0:
        main_table.add_row("  GPUs Detected", str(info["gpu"]["count"]))
        for gpu in info["gpu"]["gpus"]:
            main_table.add_row(
                f"  GPU {gpu['id']}",
                f"{gpu['name']} ({gpu['memory_total_mb']} MB)",
            )
    else:
        main_table.add_row("  Status", info["gpu"]["message"])

    # Worker Configuration Section
    main_table.add_row(
        "[bold cyan]Worker Configuration[/bold cyan]",
        "",
        style="dim",
    )
    main_table.add_row("  Workers Running", str(workers))
    main_table.add_row("  Max Workers", str(workers_max))
    main_table.add_row("  Worker Class", "uvicorn.workers.UvicornWorker")

    # Database Pool Configuration Section
    main_table.add_row(
        "[bold cyan]Database Pool Configuration[/bold cyan]",
        "",
        style="dim",
    )
    main_table.add_row("  Pool Size", str(pool_size))
    main_table.add_row("  Max Overflow", str(max_overflow))
    main_table.add_row("  Max Connections", str(pool_size + max_overflow))
    main_table.add_row("  Pool Pre-ping", "Enabled")
    main_table.add_row("  Pool Recycle", "3600s")
    main_table.add_row("  Pool Timeout", "30s")

    # Display the table in a panel
    console.print()
    console.print(
        Panel(
            main_table,
            title="[bold green]Service Startup Information[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()


__all__ = [
    "get_system_info",
    "format_system_info",
    "get_cpu_info",
    "get_memory_info",
    "get_gpu_info",
]
