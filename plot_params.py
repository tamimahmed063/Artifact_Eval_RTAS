# plot_params.py

import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def plot_exps(
    df,
    x_col,
    y_cols,
    labels,
    output_file='output.pdf',
    base_font_size=18,
    plot_size=(4.5, 3.1),
    xlabel='Utilization',
    ylabel='Schedulability \nRatio',
    xticks=None,
    yticks=None,
    xlim=None,
    ylim=(-0.05, 1.05),
):
    """
    Parameters
    ----------
    df            : pd.DataFrame — input data
    x_col         : str — column name for x-axis
    y_cols        : list of str — column names for each line
    labels        : list of str — legend labels for each line
    output_file   : str — output file path (.pdf or .png)
    base_font_size: int — base font size for all text
    plot_size     : tuple — figure size (width, height) in inches
    xlabel        : str — x-axis label
    ylabel        : str — y-axis label
    xticks        : list — custom x-axis tick positions
    yticks        : list — custom y-axis tick positions
    xlim          : tuple or None — x-axis limits; auto if None
    ylim          : tuple — y-axis limits
    """

    # --- Style config ---
    sns.set_palette("deep")
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial'],
        'font.size': base_font_size,
        'axes.labelsize': base_font_size,
        'axes.titlesize': base_font_size - 3,
        'xtick.labelsize': base_font_size - 3,
        'ytick.labelsize': base_font_size - 3,
        'legend.fontsize': base_font_size - 6,
        'figure.titlesize': base_font_size,
        'lines.linewidth': 1,
        'lines.markersize': 4,
        'grid.linewidth': 1,
        'axes.linewidth': 1,
        'xtick.major.width': 1,
        'ytick.major.width': 1,
        'figure.dpi': 100,
    })

    # --- Colors, markers, linestyles per line ---
    colors     = ["#005a00", "#b34700", "#0055b3", "#7a007a"]
    linestyles = ['-', '--', '-.', ':']
    markers    = ['v', 'o', 's', '^']

    # --- Figure ---
    fig, ax = plt.subplots(figsize=plot_size)
    x = df[x_col]

    for i, (y_col, label) in enumerate(zip(y_cols, labels)):
        c = colors[i % len(colors)]
        ax.plot(
            x, df[y_col],
            color=c,
            linestyle=linestyles[i % len(linestyles)],
            marker=markers[i % len(markers)],
            markersize=5,
            markerfacecolor='white',
            markeredgecolor=c,
            markeredgewidth=1,
            linewidth=1,
            alpha=1,
            label=label,
        )

    # --- Axes labels and limits ---
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(ylim)
    ax.set_xlim(xlim if xlim else (x.min() - 0.02, x.max() + 0.05))

    if xticks is not None:
        ax.set_xticks(xticks)
    if yticks is not None:
        ax.set_yticks(yticks)

    # --- Grid ---
    ax.grid(True, linestyle=':', alpha=0.2, linewidth=1)

    # --- Legend ---
    legend = ax.legend(loc='lower left', frameon=True, fancybox=False,
                       shadow=False, fontsize=base_font_size - 4)
    legend.get_frame().set_edgecolor('black')
    legend.get_frame().set_linewidth(1)
    legend.get_frame().set_alpha(0.7)

    # --- Spines and ticks ---
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_color('black')
    ax.tick_params(direction='out', which='both')

    plt.tight_layout()

    # --- Save ---
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    plt.savefig(output_file, format=output_file.split('.')[-1],
                dpi=3000, bbox_inches='tight', pad_inches=0.1)
    print(f"Saved: {output_file}")
    #plt.show()
    return fig, ax


def plot_box(
    data,
    output_file,
    base_font_size=20,
    plot_size=(10, 5.5),
    xlabel='Number of Constraints',
    ylabel='Time (s)',
    cutoff=3600,
    ylim=(-5, 4000),
    yticks=None,
):
    """
    Parameters
    ----------
    data          : pd.DataFrame — must have columns: Number of Constrains, q1, median,
                    q3, lower_whisker, upper_whisker, outlier
    output_file   : str — output file path (.pdf or .png)
    base_font_size: int — base font size for all text
    plot_size     : tuple — figure size (width, height) in inches
    xlabel        : str — x-axis label
    ylabel        : str — y-axis label
    cutoff        : float — cut-off time line (default 3600s)
    ylim          : tuple — y-axis limits
    yticks        : list or None — custom y-axis ticks
    """

    sns.set_palette("deep")
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': base_font_size,
        'axes.labelsize': base_font_size,
        'axes.titlesize': base_font_size - 5,
        'legend.fontsize': base_font_size - 6,
        'figure.titlesize': base_font_size,
        'lines.linewidth': 1,
        'lines.markersize': 4,
        'grid.linewidth': 1,
        'axes.linewidth': 1,
        'xtick.major.width': 1,
        'ytick.major.width': 1,
        'figure.dpi': 100,
    })

    blue   = '#000075'
    orange = '#e66101'

    fig, ax = plt.subplots(figsize=plot_size)

    box_data  = []
    positions = []
    labels    = []

    for _, row in data.iterrows():
        c_min, c_max     = row['Number of Constrains'][0], row['Number of Constrains'][1]
        constrains_avg   = (c_min + c_max) / 2
        constrains_label = f"[{c_min//1000}K, {c_max//1000}K]"

        stats = {
            'med'   : row['median'],
            'q1'    : row['q1'],
            'q3'    : row['q3'],
            'whislo': row['lower_whisker'],
            'whishi': row['upper_whisker'],
            'fliers': np.array(row['outlier']) if len(row['outlier']) > 0 else np.array([]),
        }

        box_data.append(stats)
        positions.append(constrains_avg)
        labels.append(constrains_label)

    bp = ax.bxp(box_data, positions=positions, patch_artist=True,
                showfliers=True, widths=8000, showmeans=False)

    # --- Symlog scale ---
    ax.set_yscale('symlog', linthresh=50)
    if yticks is None:
        yticks = [0, 10, 25, 50, 100, 200, 500, 1000, 2000, 3600]
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(int(t)) for t in yticks])

    # --- Cut-off line ---
    ax.axhline(y=cutoff, color=orange, linestyle='--', linewidth=1, alpha=1, zorder=10)
    ax.annotate('Cut-off Time', xy=(positions[1], cutoff), xytext=(positions[2], cutoff / 2),
                fontsize=base_font_size - 4, color='black', ha='center', va='bottom',
                arrowprops=dict(arrowstyle='->', color='black', alpha=0.8, lw=1,
                                connectionstyle="arc3,rad=-0.1"))

    # --- Box styling ---
    for patch in bp['boxes']:
        patch.set_facecolor('white')
        patch.set_edgecolor(blue)
        patch.set_linewidth(1)
    for whisker in bp['whiskers']:
        whisker.set(color=blue, linewidth=1, linestyle='-')
    for cap in bp['caps']:
        cap.set(color=blue, linewidth=1)
    for median in bp['medians']:
        median.set(color=blue, linewidth=1)
    for flier in bp['fliers']:
        flier.set(marker='o', markerfacecolor='white', markeredgecolor=blue,
                  markersize=3, markeredgewidth=1, alpha=1.0)

    # --- Axes formatting ---
    ax.set_xlabel(xlabel, labelpad=15)
    ax.set_ylabel(ylabel)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=30, ha='center')
    ax.set_ylim(ylim)
    ax.grid(True, linestyle=':', alpha=0.2, linewidth=1)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_visible(True)

    ax.tick_params(axis='x', which='major', labelsize=base_font_size - 4,
                   width=1, length=4, direction='in')
    ax.tick_params(axis='y', which='major', labelsize=base_font_size - 4,
                   width=1, length=4, direction='in')

    plt.tight_layout()
    # --- Debug ---
    print(f"Number of boxes: {len(box_data)}")
    print(f"Positions: {positions}")
    print(f"Labels: {labels}")
    print(f"Figure has axes: {len(fig.axes)}")
    print(f"Saving to: {os.path.abspath(output_file)}")

    # --- Save ---
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    fmt = output_file.split('.')[-1]
    plt.savefig(output_file, format=fmt, dpi=3000, bbox_inches='tight', pad_inches=0.1)
    print(f"Saved: {output_file}")
    #plt.show()
    return fig, ax


def plot_ilp_hard(
    df,
    x_col,
    y_cols,
    labels,
    output_file='output.pdf',
    base_font_size=18,
    plot_size=(4.5, 3.1),
    xlabel='Utilization',
    ylabel='Schedulability \nRatio',
    xticks=None,
    yticks=None,
    xlim=None,
    ylim=(-0.05, 1.05),
):
    """
    Parameters
    ----------
    df            : pd.DataFrame — input data
    x_col         : str — column name for x-axis
    y_cols        : list of str — column names for each line
    labels        : list of str — legend labels for each line
    output_file   : str — output file path (.pdf or .png)
    base_font_size: int — base font size for all text
    plot_size     : tuple — figure size (width, height) in inches
    xlabel        : str — x-axis label
    ylabel        : str — y-axis label
    xticks        : list — custom x-axis tick positions
    yticks        : list — custom y-axis tick positions
    xlim          : tuple or None — x-axis limits; auto if None
    ylim          : tuple — y-axis limits
    """

    # --- Style config ---
    sns.set_palette("deep")
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial'],
        'font.size': base_font_size,
        'axes.labelsize': base_font_size,
        'axes.titlesize': base_font_size - 3,
        'xtick.labelsize': base_font_size - 3,
        'ytick.labelsize': base_font_size - 3,
        'legend.fontsize': base_font_size - 8,
        'figure.titlesize': base_font_size,
        'lines.linewidth': 1,
        'lines.markersize': 4,
        'grid.linewidth': 1,
        'axes.linewidth': 1,
        'xtick.major.width': 1,
        'ytick.major.width': 1,
        'figure.dpi': 100,
    })

    # --- Colors, markers, linestyles per line ---
    colors     = ["#005a00", "#b34700", "#0055b3", "#7a007a"]
    linestyles = ['-', '--', '-.', ':']
    markers    = ['v', 'o', 's', '^']

    # --- Figure ---
    fig, ax = plt.subplots(figsize=plot_size)
    x = df[x_col]

    for i, (y_col, label) in enumerate(zip(y_cols, labels)):
        c = colors[i % len(colors)]
        ax.plot(
            x, df[y_col],
            color=c,
            linestyle=linestyles[i % len(linestyles)],
            marker=markers[i % len(markers)],
            markersize=5,
            markerfacecolor='white',
            markeredgecolor=c,
            markeredgewidth=1,
            linewidth=1,
            alpha=1,
            label=label,
        )

    # --- Axes labels and limits ---
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(ylim)
    ax.set_xlim(xlim if xlim else (x.min() - 0.02, x.max() + 0.05))

    if xticks is not None:
        ax.set_xticks(xticks)
    if yticks is not None:
        ax.set_yticks(yticks)

    # --- Grid ---
    ax.grid(True, linestyle=':', alpha=0.2, linewidth=1)

    # --- Legend ---
    legend = ax.legend(loc='lower left', frameon=True, fancybox=False,
                       shadow=False, fontsize=base_font_size - 4)
    legend.get_frame().set_edgecolor('black')
    legend.get_frame().set_linewidth(1)
    legend.get_frame().set_alpha(0.7)

    # --- Spines and ticks ---
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_color('black')
    ax.tick_params(direction='out', which='both')

    plt.tight_layout()

    # --- Save ---
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    plt.savefig(output_file, format=output_file.split('.')[-1],
                dpi=3000, bbox_inches='tight', pad_inches=0.1)
    print(f"Saved: {output_file}")
    #plt.show()
    return fig, ax

def plot_ilp_hard(
    df,
    x_col,
    y_cols,
    labels,
    output_file='output.pdf',
    base_font_size=18,
    plot_size=(4.5, 3),
    xlabel='Utilization',
    ylabel='Admissibility (%)',
    xticks=None,
    yticks=None,
    xlim=None,
    ylim=(-5, 105),
    legend_loc='lower left',
):
    """
    Parameters
    ----------
    df            : pd.DataFrame — input data
    x_col         : str — column name for x-axis
    y_cols        : list of str — exactly 2 columns [reserved, no_reserved]
    labels        : list of str — exactly 2 labels
    output_file   : str — output file path (.pdf or .png)
    base_font_size: int — base font size
    plot_size     : tuple — figure size
    xlabel        : str — x-axis label
    ylabel        : str — y-axis label
    xticks        : list or None — custom x ticks
    yticks        : list or None — custom y ticks
    xlim          : tuple or None — x-axis limits; auto if None
    ylim          : tuple — y-axis limits
    legend_loc    : str — legend location
    """

    # --- Colors (fixed as in original) ---
    a = "#005a00"   # Deep forest green  → Reserved Queue
    b = "#b34700"   # Darker orange      → No Reserved Queue

    sns.set_palette("deep")
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial'],
        'font.size': base_font_size,
        'axes.labelsize': base_font_size,
        'axes.titlesize': base_font_size - 3,
        'xtick.labelsize': base_font_size - 3,
        'ytick.labelsize': base_font_size - 3,
        'legend.fontsize': base_font_size - 8,
        'figure.titlesize': base_font_size,
        'lines.linewidth': 1,
        'lines.markersize': 4,
        'grid.linewidth': 1,
        'axes.linewidth': 1,
        'xtick.major.width': 1,
        'ytick.major.width': 1,
        'figure.dpi': 100,
    })

    fig, ax = plt.subplots(figsize=plot_size)
    x = df[x_col]

    # --- Line 1: Reserved Queue ---
    ax.plot(x, df[y_cols[0]],
            color=a, linestyle='-', marker='v', markersize=5,
            markerfacecolor='white', markeredgecolor=a, markeredgewidth=1,
            linewidth=1, alpha=1, label=labels[0])

    # --- Line 2: No Reserved Queue ---
    ax.plot(x, df[y_cols[1]],
            color=b, linestyle='--', marker='o', markersize=4,
            markerfacecolor='white', markeredgecolor=b, markeredgewidth=1,
            linewidth=1, alpha=1, label=labels[1])

    # --- Axes ---
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(xlim if xlim else (x.min() - 0.02, x.max() + 0.05))
    ax.set_ylim(ylim)

    if xticks is not None:
        ax.set_xticks(xticks)
    if yticks is not None:
        ax.set_yticks(yticks)

    # --- Grid ---
    ax.grid(True, linestyle=':', alpha=0.2, linewidth=1)
    ax.set_axisbelow(True)

    # --- Legend ---
    legend = ax.legend(loc=legend_loc, frameon=True, fancybox=False,
                       shadow=False, fontsize=base_font_size - 5)
    legend.get_frame().set_edgecolor('black')
    legend.get_frame().set_linewidth(1)
    legend.get_frame().set_alpha(1)

    # --- Spines ---
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_color('black')

    plt.tight_layout()

    # --- Save ---
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    fmt = output_file.split('.')[-1]
    plt.savefig(output_file, format=fmt, dpi=3000, bbox_inches='tight', pad_inches=0.1)
    print(f"Saved: {output_file}")
    #plt.show()
    return fig, ax


def plot_weakly_hard(
    df,
    x_col,
    y_cols,
    labels,
    output_file='output.pdf',
    base_font_size=20,
    plot_size=(8.5, 5.5),
    xlabel='Total Utilization',
    ylabel='Schedulability Ratio',
    xticks=None,
    yticks=None,
    xlim=None,
    ylim=(-0.05, 1.05),
    legend_loc='lower left',
):
    """
    Parameters
    ----------
    df            : pd.DataFrame — input data
    x_col         : str — column name for x-axis
    y_cols        : list of str — column names in plot order [w2h1, w1h1, w1h2, w0h1]
    labels        : list of str — legend labels in same order
    output_file   : str — output file path (.pdf or .png)
    base_font_size: int — base font size
    plot_size     : tuple — figure size
    xlabel        : str — x-axis label
    ylabel        : str — y-axis label
    xticks        : list or None
    yticks        : list or None
    xlim          : tuple or None
    ylim          : tuple
    legend_loc    : str
    """

    sns.set_palette("deep")
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'DejaVu Sans'],
        'font.size': base_font_size,
        'axes.labelsize': base_font_size,
        'axes.titlesize': base_font_size - 2,
        'xtick.labelsize': base_font_size - 3,
        'ytick.labelsize': base_font_size - 3,
        'legend.fontsize': base_font_size - 4,
        'figure.titlesize': base_font_size,
        'lines.linewidth': 1.6,
        'lines.markersize': 6,
        'grid.linewidth': 0.8,
        'axes.linewidth': 1.0,
        'xtick.major.width': 1.0,
        'ytick.major.width': 1.0,
        'figure.dpi': 120,
    })

    # --- Fixed style per line (order: w2h1, w1h1, w1h2, w0h1) ---
    colors_list     = ["#005a00", "#005a00", "#005a00", "#b34700"]
    linestyles_list = ["-.",":", "--", "-"]
    markers_list    = ["s", "^", "o", "d"]

    fig, ax = plt.subplots(figsize=plot_size)
    x = df[x_col]

    for i, (y_col, label) in enumerate(zip(y_cols, labels)):
        ax.plot(
            x, df[y_col],
            color=colors_list[i % len(colors_list)],
            linestyle=linestyles_list[i % len(linestyles_list)],
            marker=markers_list[i % len(markers_list)],
            markersize=7,
            markerfacecolor='white',
            markeredgecolor=colors_list[i % len(colors_list)],
            markeredgewidth=1.3,
            linewidth=1.8,
            label=label,
        )

    # --- Axes ---
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(ylim)
    ax.set_xlim(xlim if xlim else (x.min() - 0.02, x.max() + 0.02))

    if xticks is not None:
        ax.set_xticks(xticks)
    if yticks is not None:
        ax.set_yticks(yticks)

    # --- Grid ---
    ax.grid(True, linestyle=':', alpha=0.18)

    # --- Legend ---
    legend = ax.legend(
        loc=legend_loc, frameon=True, fancybox=False, shadow=False,
        handlelength=2.5, handletextpad=0.1, borderpad=0.3,
    )
    legend.get_frame().set_edgecolor('black')
    legend.get_frame().set_linewidth(1.0)
    legend.get_frame().set_alpha(0.92)

    # --- Spines ---
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)
        spine.set_color('black')
    ax.tick_params(direction='out', which='both')

    plt.tight_layout()

    # --- Save ---
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    fmt = output_file.split('.')[-1]
    plt.savefig(output_file, format=fmt, dpi=3000, bbox_inches='tight', pad_inches=0.08)
    print(f"Saved: {output_file}")
    #plt.show()
    return fig, ax


def plot_bar_response(
    df,
    output_file,
    class_col='Class',
    x_col='No.',
    y_col='R/P',
    base_font_size=18,
    plot_size=(4.5, 3.1),
    xlabel='Packet Instance',
    ylabel='Normalized\nResponse Time',
    xlim=(0, 205),
    ylim=(0, 1.55),
    xticks=None,
    yticks=None,
    apply_class_override=False,
):
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial'],
        'font.size': base_font_size,
        'axes.labelsize': base_font_size - 3,
        'axes.titlesize': base_font_size - 2,
        'xtick.labelsize': base_font_size - 3,
        'ytick.labelsize': base_font_size - 3,
        'legend.fontsize': base_font_size - 4,
        'figure.titlesize': base_font_size - 4,
        'lines.linewidth': 1,
        'lines.markersize': 1,
        'grid.linewidth': 1,
        'axes.linewidth': 1,
        'xtick.major.width': 1,
        'ytick.major.width': 1,
        'figure.dpi': 100,
    })

    COLORS = {
        'mandatory'     : "#E6D0C9",
        'mandatory_edge': "#B8958A",
        'optional'      : "#D0D8E8",
        'optional_edge' : "#8695B5",
    }

    if apply_class_override:
        df = df.copy()
        df[class_col] = df.groupby("Flow").cumcount().add(1).apply(
            lambda x: 8 if x % 3 == 0 else None
        ).fillna(df[class_col]).astype(int)

    colors      = [COLORS['optional']      if c == 8 else COLORS['mandatory']      for c in df[class_col]]
    edge_colors = [COLORS['optional_edge'] if c == 8 else COLORS['mandatory_edge'] for c in df[class_col]]

    fig, ax = plt.subplots(figsize=plot_size)

    for x, y, color, edge_color in zip(df[x_col], df[y_col], colors, edge_colors):
        ax.bar(x, y, width=1.0, color=color, edgecolor=edge_color,
               linewidth=0.7, alpha=1, zorder=2, align='edge')

    ax.margins(x=0)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if xticks is not None:
        ax.set_xticks(xticks)
    if yticks is not None:
        ax.set_yticks(yticks)

    ax.grid(True, linestyle=':', alpha=0.2, linewidth=1)
    ax.set_axisbelow(True)
    ax.axhline(y=1, color='black', linestyle='--', linewidth=0.8, alpha=0.8, zorder=1)

    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_color('black')
        spine.set_visible(True)
        spine.set_zorder(3)

    ax.tick_params(axis='x', which='major', width=1, length=6, direction='out', color='black')
    ax.tick_params(axis='y', which='major', width=1, length=6, direction='out', color='black')

    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, facecolor=COLORS['mandatory'],
                       edgecolor=COLORS['mandatory_edge'], linewidth=1, label='Mandatory'),
        plt.Rectangle((0, 0), 1, 1, facecolor=COLORS['optional'],
                       edgecolor=COLORS['optional_edge'],  linewidth=1, label='Optional'),
    ]
    legend = ax.legend(
        handles=legend_elements,
        loc='upper center', ncol=2,
        frameon=True, fancybox=False, shadow=False,
        edgecolor='black', facecolor='white',
        columnspacing=0.6, handletextpad=0.4,
        labelspacing=0.4, handlelength=1.5,
        handleheight=0.3, borderpad=0.3,
    )
    legend.get_frame().set_linewidth(1)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    fmt = output_file.split('.')[-1]
    plt.savefig(output_file, format=fmt, dpi=3000, bbox_inches='tight', pad_inches=0.1)
    print(f"Saved: {output_file}")
    plt.close()
    return fig, ax