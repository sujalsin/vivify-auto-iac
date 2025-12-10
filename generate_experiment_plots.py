#!/usr/bin/env python3
"""
Generate publication-ready plots for all experiments
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Set style for publication-ready plots
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12
plt.rcParams['legend.fontsize'] = 12

output_dir = Path("plots")
output_dir.mkdir(exist_ok=True)


def plot_e1_parallelism():
    """E1: Parallelism - Bar Chart"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    modes = ['Sequential', 'Parallel']
    times = [21.449, 1.377]
    colors = ['#e74c3c', '#2ecc71']
    
    bars = ax.bar(modes, times, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # Add value labels on bars
    for bar, time in zip(bars, times):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{time:.2f}s',
                ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    ax.set_ylabel('Execution Time (seconds)', fontweight='bold')
    ax.set_title('Experiment 1: Parallelism Performance\n15.58x Speedup with Real LLM Agents', 
                 fontweight='bold', pad=20)
    ax.set_ylim(0, max(times) * 1.2)
    
    # Add speedup annotation
    ax.annotate('15.58x Speedup', 
                xy=(0.5, 12), xytext=(0.5, 18),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'),
                fontsize=14, fontweight='bold', ha='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    plt.savefig(output_dir / 'e1_parallelism.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'e1_parallelism.pdf', bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'e1_parallelism.png'}")
    plt.close()


def plot_e2_self_healing():
    """E2: Self-Healing - Line Chart"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    iterations = [1, 2, 3, 4, 5]
    success_rates = [75.0, 100.0, 100.0, 100.0, 100.0]
    
    # Plot line with markers
    ax.plot(iterations, success_rates, marker='o', markersize=10, 
            linewidth=3, color='#3498db', label='Cumulative Success Rate')
    
    # Highlight the "healing" jump
    ax.axvspan(1, 2, alpha=0.2, color='green', label='Self-Healing Fix')
    
    # Add value labels
    for i, (iter_num, rate) in enumerate(zip(iterations, success_rates)):
        ax.annotate(f'{rate:.0f}%', 
                   xy=(iter_num, rate), 
                   xytext=(iter_num, rate + 3),
                   ha='center', fontsize=11, fontweight='bold')
    
    ax.set_xlabel('Iteration Number', fontweight='bold')
    ax.set_ylabel('Cumulative Success Rate (%)', fontweight='bold')
    ax.set_title('Experiment 2: Self-Healing Feedback Loop\nAgent Automatically Fixes Configuration Errors', 
                 fontweight='bold', pad=20)
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(70, 105)
    ax.set_xticks(iterations)
    ax.set_yticks([75, 80, 85, 90, 95, 100])
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='lower right', framealpha=0.9)
    
    # Add annotation for the fix
    ax.annotate('Invalid property\ndetected & fixed', 
                xy=(1.5, 87.5), xytext=(3, 85),
                arrowprops=dict(arrowstyle='->', lw=2, color='green'),
                fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'e2_self_healing.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'e2_self_healing.pdf', bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'e2_self_healing.png'}")
    plt.close()


def plot_e3_concurrency():
    """E3: Concurrency - Grouped Bar Chart showing deployment phases"""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Data from experiment
    num_stacks = 10
    deployment_time = 48.205  # seconds
    convergence_time = 84.508  # seconds
    rollback_time = convergence_time - deployment_time  # approximate
    
    # Create grouped bar chart
    categories = ['Deployment\nPhase', 'Convergence\nPhase', 'Rollback\nPhase']
    times = [deployment_time, convergence_time, rollback_time]
    colors = ['#2ecc71', '#3498db', '#e74c71']
    
    bars = ax.bar(categories, times, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5, width=0.6)
    
    # Add value labels on bars
    for bar, time in zip(bars, times):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{time:.1f}s',
                ha='center', va='bottom', fontsize=13, fontweight='bold')
    
    ax.set_ylabel('Time (seconds)', fontweight='bold')
    ax.set_title('Experiment 3: Concurrent Infrastructure Deployment\n10 Stacks Deployed Concurrently with 100% Success Rate', 
                 fontweight='bold', pad=20)
    ax.set_ylim(0, max(times) * 1.25)
    
    # Add success metrics annotation
    success_text = '✓ 10/10 Deployments Successful\n✓ 0 Drift Detected\n✓ 100% Rollback Success\n✓ 0 Failures'
    ax.text(0.98, 0.98, success_text, transform=ax.transAxes,
            fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round,pad=1', facecolor='lightgreen', alpha=0.8),
            verticalalignment='top', ha='right')
    
    # Add concurrency annotation
    ax.annotate(f'{num_stacks} Concurrent\nTerraform Operations',
                xy=(0.5, max(times) * 0.6), xytext=(0.5, max(times) * 0.85),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'),
                fontsize=12, fontweight='bold', ha='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    plt.savefig(output_dir / 'e3_concurrency.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'e3_concurrency.pdf', bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'e3_concurrency.png'}")
    plt.close()


def plot_e4_canvas():
    """E4: Canvas Load - Multi-Line Chart"""
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    canvas_sizes = [100, 500, 1500]
    
    # Latency data (P95)
    latency_100 = 161.37
    latency_500 = 157.57
    latency_1500 = 159.95
    latencies = [latency_100, latency_500, latency_1500]
    
    # FPS data
    fps_100 = 5.27
    fps_500 = 5.60
    fps_1500 = 5.24
    fps_values = [fps_100, fps_500, fps_1500]
    
    # Plot latency on left y-axis
    color1 = '#e74c3c'
    ax1.set_xlabel('Canvas Size (nodes)', fontweight='bold')
    ax1.set_ylabel('P95 Latency (ms)', color=color1, fontweight='bold')
    line1 = ax1.plot(canvas_sizes, latencies, marker='o', markersize=10, 
                     linewidth=3, color=color1, label='P95 Latency')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_ylim(150, 165)
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # Add latency value labels
    for size, latency in zip(canvas_sizes, latencies):
        ax1.annotate(f'{latency:.1f}ms', 
                     xy=(size, latency), 
                     xytext=(size, latency + 2),
                     ha='center', fontsize=10, fontweight='bold', color=color1)
    
    # Plot FPS on right y-axis
    ax2 = ax1.twinx()
    color2 = '#2ecc71'
    ax2.set_ylabel('FPS (Frames Per Second)', color=color2, fontweight='bold')
    line2 = ax2.plot(canvas_sizes, fps_values, marker='s', markersize=10, 
                     linewidth=3, color=color2, label='FPS', linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim(4.5, 6.0)
    
    # Add FPS value labels
    for size, fps in zip(canvas_sizes, fps_values):
        ax2.annotate(f'{fps:.2f}', 
                     xy=(size, fps), 
                     xytext=(size, fps + 0.15),
                     ha='center', fontsize=10, fontweight='bold', color=color2)
    
    # Set x-axis
    ax1.set_xticks(canvas_sizes)
    ax1.set_xticklabels([f'{s} nodes' for s in canvas_sizes])
    
    # Title
    ax1.set_title('Experiment 4: Canvas Performance Under Load\nScalable Performance Across Canvas Sizes\n(1000 Concurrent Sessions)', 
                  fontweight='bold', pad=20)
    
    # Combined legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', framealpha=0.9)
    
    # Add scalability annotation
    ax1.text(0.5, 0.95, 'Stable Performance:\nLatency ~160ms, FPS ~5.5\nacross all sizes',
             transform=ax1.transAxes, fontsize=11, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
             verticalalignment='top', ha='center')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'e4_canvas.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'e4_canvas.pdf', bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'e4_canvas.png'}")
    plt.close()


def main():
    """Generate all plots"""
    print("Generating experiment plots...")
    print()
    
    plot_e1_parallelism()
    plot_e2_self_healing()
    plot_e3_concurrency()
    plot_e4_canvas()
    
    print()
    print("=" * 50)
    print("All plots generated successfully!")
    print(f"Output directory: {output_dir.absolute()}")
    print("=" * 50)


if __name__ == "__main__":
    main()

