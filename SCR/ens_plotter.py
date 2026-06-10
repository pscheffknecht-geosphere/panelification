import datetime as dt
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm as bnorm
import numpy as np
import scipy.ndimage as ndimage
from cmcrameri import cm as ccm

import parameter_settings
from paths import PAN_DIR_PLOTS
from panel_plotter import add_borders

import logging
logger = logging.getLogger(__name__)
logging.getLogger('matplotlib').setLevel(logging.WARNING)


# ----------------------------- shared helpers ------------------------------

def _build_cmaps(args):
    levels, cmap, norm = parameter_settings.get_cmap_and_levels(args)
    spread_cmap = ccm.lipari_r
    spread_levels = np.array([0., 0.1, 0.25, 0.5, 1., 2., 3., 5., 7.5, 10., 15., 20., 30., 50.])
    ratio_cmap = plt.colormaps['RdBu']
    ratio_levels = np.array([0., 0.25, 0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2., 3., 5.])
    frac_cmap = plt.colormaps['RdBu_r']
    frac_levels = np.arange(0., 1.0001, 0.1)
    diff_cmap = ccm.broc_r #plt.colormaps['BrBG']
    diff_levels = np.array([-20., -10., -5., -2., -1., -0.5, -0.1, 0.1, 0.5, 1., 2., 5., 10., 20.])
    crps_cmap = plt.colormaps['magma_r']
    crps_levels = np.array([0., 0.1, 0.25, 0.5, 1., 2., 3., 5., 7.5, 10., 15., 20., 30.])
    _nbh_base = plt.colormaps["YlGnBu"] #ccm.nuuk_r #plt.colormaps['YlOrRd']
    nbh_cmap = mpl.colors.ListedColormap(_nbh_base(np.linspace(0., 0.66, _nbh_base.N)))
    nbh_levels = np.arange(0., 1.0001, 0.1)
    norm_cmap = plt.colormaps['cividis']
    norm_levels = np.array([0., 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
    norm_spread_levels = np.array([0., 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0])
    return {
        'precip': (cmap,        norm),
        'spread': (spread_cmap, bnorm(spread_levels, ncolors=spread_cmap.N)),
        'ratio':  (ratio_cmap,  bnorm(ratio_levels,  ncolors=ratio_cmap.N)),
        'frac':   (frac_cmap,   bnorm(frac_levels,   ncolors=frac_cmap.N)),
        'diff':   (diff_cmap,   bnorm(diff_levels,   ncolors=diff_cmap.N)),
        'crps':   (crps_cmap,   bnorm(crps_levels,   ncolors=crps_cmap.N)),
        'nbh':    (nbh_cmap,    bnorm(nbh_levels,    ncolors=nbh_cmap.N)),
        'norm':   (norm_cmap,   bnorm(norm_levels,   ncolors=norm_cmap.N)),
        'norm_spread': (spread_cmap, bnorm(norm_spread_levels, ncolors=spread_cmap.N)),
    }


def _build_specs(smooth_size):
    return [
        ('mean',              "Ensemble Mean",                                              'precip'),
        ('median',            "Ensemble Median",                                            'precip'),
        ('spread',            "Ensemble Spread (stdev)",                                    'spread'),
        ('ratio_mae',         "Spread / Mean |member - obs|",                               'ratio'),
        ('ratio_mae',         "Spread / Mean |member - obs|",                               'ratio'),
        ('ratio_mae_msm',     f"Spread/MAE, members smoothed ({smooth_size} gp)",           'ratio'),
        ('ratio_mae_osm',     f"Spread/MAE, obs smoothed ({smooth_size} gp)",               'ratio'),
        ('ratio_mae_both',    f"Spread/MAE, members & obs smoothed ({smooth_size} gp)",     'ratio'),
        ('ratio_mae_post',    f"Spread/MAE, result smoothed ({smooth_size} gp)",            'ratio'),
        ('ratio_median',      "Spread / |Median - obs|",                                    'ratio'),
        ('ratio_median_msm',  f"Spread/|Med-obs|, members smoothed ({smooth_size} gp)",     'ratio'),
        ('ratio_median_osm',  f"Spread/|Med-obs|, obs smoothed ({smooth_size} gp)",         'ratio'),
        ('ratio_median_both', f"Spread/|Med-obs|, members & obs smoothed ({smooth_size} gp)", 'ratio'),
        ('ratio_median_post', f"Spread/|Med-obs|, result smoothed ({smooth_size} gp)",      'ratio'),
        ('ratio_rmse',        "Spread / RMSE",                                              'ratio'),
        ('norm_mean',         "Spread / (Mean + 1)",                                        'norm_spread'),
        ('norm_median',       "Spread / (Median + 1)",                                      'norm_spread'),
        ('frac',              "Fraction of members above obs",                              'frac'),
        ('frac_msm',          f"Frac above obs, members smoothed ({smooth_size} gp)",       'frac'),
        ('frac_osm',          f"Frac above obs, obs smoothed ({smooth_size} gp)",           'frac'),
        ('frac_both',         f"Frac above obs, members & obs smoothed ({smooth_size} gp)", 'frac'),
        ('frac_post',         f"Frac above obs, result smoothed ({smooth_size} gp)",        'frac'),
        ('mean_minus_median', "Mean - Median",                                              'diff'),
        ('mean_div_median',   "Mean / Median",                                              'ratio'),
        ('crps',              "CRPS",                                                       'crps'),
        ('nbh',               "{nbh_title}",                                                'nbh'),
        ('nbh_20',            "{nbh_title_20}",                                             'nbh'),
    ]


def _get_default_show():
    return {
        'mean': True, 'median': True, 'spread': True,
        'ratio_mae': False, 'ratio_mae_msm': False, 'ratio_mae_osm': False,
        'ratio_mae_both': False, 'ratio_mae_post': False,
        'ratio_median': False, 'ratio_median_msm': False, 'ratio_median_osm': False,
        'ratio_median_both': False, 'ratio_median_post': False, 'ratio_rmse': False,
        'norm_mean': True, 'norm_median': False,
        'frac': False, 'frac_msm': False, 'frac_osm': False,
        'frac_both': False, 'frac_post': False,
        'mean_minus_median': True, 'mean_div_median': False,
        'crps': True, 'nbh': True, 'nbh_20': True,
    }


def _compute_plot_extent(ens_data, args):
    if args.zoom_to_subdomain:
        lon0 = ens_data[0].lon
        lat0 = ens_data[0].lat
        return [lon0.min() - 0.02, lon0.max() + 0.02,
                lat0.min() - 0.02, lat0.max() + 0.02]
    return args.region.extent


def _probe_map_ratio(proj, extent):
    probe_fig = plt.figure()
    probe_ax = probe_fig.add_subplot(projection=proj)
    probe_ax.set_extent(extent)
    ratio = probe_ax.get_data_ratio()
    plt.close(probe_fig)
    return ratio


# -------------------------- per-ensemble field calc ------------------------

def _disk_footprint(diameter):
    """Boolean disk of the given diameter (grid points), shaped (1, D, D) so
    it acts per-member in the (member, y, x) stack. Used for circular
    neighbourhoods in the exceedance-fraction panels."""
    r = (diameter - 1) / 2.0
    y, x = np.ogrid[:diameter, :diameter]
    return ((x - r) ** 2 + (y - r) ** 2 <= r ** 2)[None, :, :]


def _nbh_max_filter(exceed, size, shape):
    """Per-member neighbourhood max of a binary exceedance stack.

    shape='square' uses a separable size x size box (fast); shape='circle'
    uses a disk of diameter `size` (footprint-based, slower but isotropic)."""
    if shape == 'circle':
        return ndimage.maximum_filter(
            exceed, footprint=_disk_footprint(size), mode='nearest')
    return ndimage.maximum_filter(
        exceed, size=(1, size, size), mode='nearest')


def _compute_fields(ens, show, smooth_size, nbh_size, nbh_size_small, eps,
                    nbh_shape='square'):
    """Return (field_map, threshold). field_map: key -> (array, kind)."""
    data = ens.precip_data_resampled
    obs  = ens.obs_data_resampled
    ens_mean = np.mean(data, axis=0)
    ens_median = np.median(data, axis=0)

    need_spread = any(show[k] for k in (
        'spread', 'ratio_mae', 'ratio_median', 'ratio_mae_osm',
        'ratio_median_osm', 'norm_mean', 'norm_median'))
    spread = np.std(data, axis=0) if need_spread else None

    need_dsmooth = any(show[k] for k in (
        'ratio_mae_msm', 'ratio_mae_both', 'ratio_median_msm',
        'ratio_median_both', 'frac_msm', 'frac_both'))
    need_osmooth = any(show[k] for k in (
        'ratio_mae_osm', 'ratio_mae_both', 'ratio_median_osm',
        'ratio_median_both', 'frac_osm', 'frac_both'))
    data_smooth = ndimage.uniform_filter(data, size=(1, smooth_size, smooth_size),
        mode='nearest') if need_dsmooth else None
    obs_smooth = ndimage.uniform_filter(obs, size=smooth_size,
        mode='nearest') if need_osmooth else None
    spread_smooth = np.std(data_smooth, axis=0) if data_smooth is not None else None

    def _safe_ratio(num, den):
        return num / np.where(den < eps, np.nan, den)
    def _gt1_ratio(num, den):
        return num / np.where(den < 1., np.nan, den)

    fm = {}
    if show['mean']:   fm['mean']   = (ens_mean,   'precip')
    if show['median']: fm['median'] = (ens_median, 'precip')
    if show['spread']: fm['spread'] = (spread,     'spread')

    if show['ratio_mae']:
        mae = np.mean(np.abs(data - obs[None]), axis=0)
        fm['ratio_mae'] = (_safe_ratio(spread, mae), 'ratio')
    if show['ratio_rmse']:
        rmse = np.sqrt(np.mean(np.square(np.abs(data - obs[None])), axis=0))
        fm['ratio_rmse'] = (_safe_ratio(spread, rmse), 'ratio')
    if show['ratio_mae_msm']:
        mae = np.mean(np.abs(data_smooth - obs[None]), axis=0)
        fm['ratio_mae_msm'] = (_safe_ratio(spread_smooth, mae), 'ratio')
    if show['ratio_mae_osm']:
        mae = np.mean(np.abs(data - obs_smooth[None]), axis=0)
        fm['ratio_mae_osm'] = (_safe_ratio(spread, mae), 'ratio')
    if show['ratio_mae_both']:
        mae = np.mean(np.abs(data_smooth - obs_smooth[None]), axis=0)
        fm['ratio_mae_both'] = (_safe_ratio(spread_smooth, mae), 'ratio')
    if show['ratio_mae_post']:
        mae = np.mean(np.abs(data - obs[None]), axis=0)
        r = _safe_ratio(spread, mae)
        fm['ratio_mae_post'] = (ndimage.uniform_filter(r, size=smooth_size, mode='nearest'), 'ratio')

    if show['ratio_median']:
        fm['ratio_median'] = (_safe_ratio(spread, np.abs(ens_median - obs)), 'ratio')
    if show['ratio_median_msm']:
        med_s = np.median(data_smooth, axis=0)
        fm['ratio_median_msm'] = (_safe_ratio(spread_smooth, np.abs(med_s - obs)), 'ratio')
    if show['ratio_median_osm']:
        fm['ratio_median_osm'] = (_safe_ratio(spread, np.abs(ens_median - obs_smooth)), 'ratio')
    if show['ratio_median_both']:
        med_s = np.median(data_smooth, axis=0)
        fm['ratio_median_both'] = (_safe_ratio(spread_smooth, np.abs(med_s - obs_smooth)), 'ratio')
    if show['ratio_median_post']:
        r = _safe_ratio(spread, np.abs(ens_median - obs))
        fm['ratio_median_post'] = (ndimage.uniform_filter(r, size=smooth_size, mode='nearest'), 'ratio')

    if show['norm_mean']:   fm['norm_mean']   = (spread / (ens_mean + 1.),   'norm_spread')
    if show['norm_median']: fm['norm_median'] = (spread / (ens_median + 1.), 'norm_spread')

    if show['frac']:
        fm['frac'] = (np.mean(data > obs[None], axis=0), 'frac')
    if show['frac_msm']:
        fm['frac_msm'] = (np.mean(data_smooth > obs[None], axis=0), 'frac')
    if show['frac_osm']:
        fm['frac_osm'] = (np.mean(data > obs_smooth[None], axis=0), 'frac')
    if show['frac_both']:
        fm['frac_both'] = (np.mean(data_smooth > obs_smooth[None], axis=0), 'frac')
    if show['frac_post']:
        fa = np.mean(data > obs[None], axis=0)
        fm['frac_post'] = (ndimage.uniform_filter(fa, size=smooth_size, mode='nearest'), 'frac')

    if show['mean_minus_median']:
        fm['mean_minus_median'] = (ens_mean - ens_median, 'diff')
    if show['mean_div_median']:
        fm['mean_div_median'] = (_safe_ratio(ens_mean, ens_median), 'ratio')
    if show['crps']:
        fm['crps'] = (ens.CRPS, 'crps')

    threshold = None
    if show['nbh'] or show['nbh_20']:
        obs_p90 = np.nanpercentile(obs, 90)
        step = 5. if obs_p90 < 20. else 10.
        threshold = max(step, float(np.ceil(obs_p90 / step) * step))
        exceed = (data > threshold).astype(float)
        if show['nbh']:
            mhe = _nbh_max_filter(exceed, nbh_size, nbh_shape)
            fm['nbh'] = (np.mean(mhe, axis=0), 'nbh')
        if show['nbh_20']:
            mhe = _nbh_max_filter(exceed, nbh_size_small, nbh_shape)
            fm['nbh_20'] = (np.mean(mhe, axis=0), 'nbh')
    return fm, threshold


# ----------------------- drawing helpers ------------------------------------

def _draw_map(ax, lon, lat, field, kind, cmaps, data_proj):
    cmap, norm = cmaps[kind]
    return ax.pcolormesh(lon, lat, field, cmap=cmap, norm=norm,
                         transform=data_proj, shading='auto')


def _overlay_obs_threshold(ax, lon, lat, obs, threshold, data_proj):
    mpl.rcParams['hatch.linewidth'] = 0.4
    plt.rcParams.update({'hatch.color': (0., 0., 0., 0.6)})
    ax.contourf(lon, lat, obs, levels=[threshold, np.inf],
        colors='none', hatches=['////'], transform=data_proj)
    ax.contour(lon, lat, obs, levels=[threshold],
        colors='black', linewidths=0.7, transform=data_proj)


def _draw_obs_row(axes, ens_data, cmaps, extent, data_proj):
    obs_field = ens_data[0].obs_data_resampled
    obs_lon = ens_data[0].lon
    obs_lat = ens_data[0].lat
    n_cols = axes.shape[1]
    for col in range(n_cols):
        ax = axes[0, col]
        if col == 0:
            _draw_map(ax, obs_lon, obs_lat, obs_field, 'precip', cmaps, data_proj)
            ax.set_facecolor("silver")
            ax.set_extent(extent)
            add_borders(ax)
            ax.set_title(ens_data[0].obs_name)
            ax.text(-0.05, 0.5, ens_data[0].obs_name, va='center', ha='right',
                    rotation='vertical', transform=ax.transAxes, size=12)
        else:
            ax.axis('off')


def _place_colorbars(fig, axes, active_specs, mappables, cbar_info):
    cb_h = 0.0084
    cb_y = 0.045
    skip_next = False
    for i, (_key, _title, kind) in enumerate(active_specs):
        if skip_next:
            skip_next = False
            continue
        mappable = mappables.get(kind)
        if mappable is None:
            continue
        label, extend = cbar_info[kind]
        pos_left = axes[-1, i].get_position()
        if i == 0 and len(active_specs) > 1 and active_specs[1][2] == kind:
            pos_right = axes[-1, 1].get_position()
            x0 = pos_left.x0
            width = pos_right.x1 - pos_left.x0
            skip_next = True
        else:
            x0 = pos_left.x0
            width = pos_left.width
        cbar_ax = fig.add_axes([x0, cb_y, width, cb_h])
        plt.colorbar(mappable, cax=cbar_ax, orientation='horizontal',
                     label=label, extend=extend)


def _cbar_labels(args):
    return {
        'precip': (parameter_settings.colorbar_label(args), 'max'),
        'spread': ("Spread (stdev)",                        'max'),
        'ratio':  ("Ratio",                                 'both'),
        'norm':   ("Spread / (mean or median + 1)",         'max'),
        'norm_spread': ("Spread / (mean or median + 1)",    'max'),
        'frac':   ("Fraction of members above obs",         'neither'),
        'diff':   ("Mean - Median [mm]",                    'both'),
        'crps':   ("CRPS",                                  'max'),
        'nbh':    ("Nbh exceedance fraction",               'neither'),
    }


# ------------------------------- public API --------------------------------

def ens_map_panel(ens_data, verification_subdomain, args):
    """Panel plot with one row per ensemble (plus an obs row on top) and
    one column per active metric. Active metrics are controlled by the
    `show` dict in this function."""
    n_ens = len(ens_data)
    if n_ens == 0:
        logger.warning("No ensembles available for ens_map_panel.")
        return None

    smooth_size = 50
    nbh_size = 50
    nbh_size_small = 20
    nbh_shape = 'circle'  # 'square' = N x N box, 'circle' = disk of diameter N
    eps = 1e-6

    show = _get_default_show()
    specs = _build_specs(smooth_size)
    active_specs = [s for s in specs if show[s[0]]]
    n_cols = len(active_specs)
    n_rows = n_ens + 1

    cmaps = _build_cmaps(args)
    proj = args.region.plot_projection
    data_proj = args.region.data_projection
    extent = _compute_plot_extent(ens_data, args)
    map_ratio = _probe_map_ratio(proj, extent)
    col_w = 4.0
    row_h = max(1.5, col_w * map_ratio)

    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(col_w * n_cols, row_h * n_rows + 0.8),
        dpi=args.dpi,
        subplot_kw={'projection': proj},
        squeeze=False,
    )

    col_titles = [s[1] for s in active_specs]
    _draw_obs_row(axes, ens_data, cmaps, extent, data_proj)

    mappables = {}
    for ens_idx, ens in enumerate(ens_data):
        row = ens_idx + 1
        field_map, threshold = _compute_fields(ens, show, smooth_size, nbh_size,
            nbh_size_small, eps, nbh_shape=nbh_shape)
        if threshold is not None:
            reach = "diameter" if nbh_shape == 'circle' else "box"
            for i, s in enumerate(active_specs):
                if s[0] == 'nbh':
                    col_titles[i] = f"RR > {threshold:.0f} mm within {nbh_size} km ({reach})"
                elif s[0] == 'nbh_20':
                    col_titles[i] = f"RR > {threshold:.0f} mm within {nbh_size_small} km ({reach})"

        fields = [field_map[s[0]] for s in active_specs]
        for col, (field, kind) in enumerate(fields):
            ax = axes[row, col]
            mappables[kind] = _draw_map(ax, ens.lon, ens.lat, field, kind, cmaps, data_proj)
            if kind == 'nbh':
                _overlay_obs_threshold(ax, ens.lon, ens.lat, ens.obs_data_resampled,
                    threshold, data_proj)
            ax.set_facecolor("silver")
            ax.set_extent(extent)
            add_borders(ax)
            if row == 1:
                ax.set_title(col_titles[col])
            if col == 0:
                ax.text(-0.05, 0.5, ens.name, va='center', ha='right',
                        rotation='vertical', transform=ax.transAxes, size=12)

    fig.subplots_adjust(left=0.04, right=0.98, bottom=0.08, top=0.93,
                        wspace=0.05, hspace=0.05)
    obs_gap = 0.04
    for col in range(n_cols):
        pos = axes[0, col].get_position()
        axes[0, col].set_position([pos.x0, pos.y0 + obs_gap, pos.width, pos.height])

    _place_colorbars(fig, axes, active_specs, mappables, _cbar_labels(args))

    start_date_str = dt.datetime.strptime(args.start, "%Y%m%d%H").strftime("%Y%m%d_%H")
    outfilename = (f"{PAN_DIR_PLOTS}/{args.name}_{args.parameter}_ens_mean_median_spread_"
                   f"{start_date_str}UTC_acc_{args.duration}_{verification_subdomain}.png")
    plt.savefig(outfilename)
    plt.close(fig)
    logger.info(f"Saved ensemble mean/median/spread panel to {outfilename}")
    return outfilename


# ------------------------------ pFSS panel ---------------------------------

def get_value_range(ens_fss_data):
    """Max absolute pairwise pFSS difference across all ensemble pairs."""
    stack = np.stack([e.pFSS[2] for e in ens_fss_data], axis=0)
    diffs = stack[:, None] - stack[None, :]
    return float(np.nanmax(np.abs(diffs)))


def _diff_levels(vmax, max_levels=50):
    step = 0.001
    lv = np.arange(-vmax, vmax + 0.001, step)
    while lv.size > max_levels:
        step *= 2
        lv = np.arange(-vmax, vmax + 0.001, step)
    return lv, step


def ens_fss_plot(ens_data, windows, levels, verification_subdomain, args):
    """Pairwise pFSS comparison grid.

    Diagonal: each ensemble's pFSS surface (threshold x window).
    Upper triangle: pFSS[i] - pFSS[j] for i < j.
    Lower triangle: empty (the lower half is just the sign-flipped upper)."""
    n_members = len(ens_data)
    keep = np.array([l < 1000. for l in levels])
    plot_levels = [l for l, k in zip(levels, keep) if k]
    n_lev = len(plot_levels)
    n_rows = n_members + 2  # two extra rows: dFSSmean and dFSSstdev overviews
    row_dfm = n_members       # index of the dFSSmean row
    row_dfs = n_members + 1   # index of the dFSSstdev row
    fig, ax = plt.subplots(n_rows, n_members,
        figsize=(4 * n_members, 4 * n_rows), sharex=True, sharey=True, dpi=args.dpi,
        squeeze=False)
    vmax = 1. if n_members < 2 else get_value_range(ens_data)
    pfss = [np.asarray(e.pFSS[2])[keep, :] for e in ens_data]
    dfss_mean = [np.asarray(e.dFSSmean)[keep, :] for e in ens_data]
    dfss_std = [np.asarray(e.dFSSstdev)[keep, :] for e in ens_data]

    levels1 = np.arange(0., 1.01, 0.1)
    levels2, step = _diff_levels(vmax)
    logger.info(f"Using step = {step}, {levels2.size} levels")
    cmap1 = plt.colormaps['coolwarm_r']
    cmap2 = plt.colormaps['RdYlGn']
    norm1 = mpl.colors.BoundaryNorm(levels1, ncolors=cmap1.N)
    norm2 = mpl.colors.BoundaryNorm(levels2, ncolors=cmap2.N)

    logger.info("Making pFSS plots")
    c1, c2, c3, c4 = None, None, None, None
    cmap3 = plt.colormaps['Greens']
    norm3 = mpl.colors.BoundaryNorm(levels1, ncolors=cmap3.N)
    # dFSSstdev has its own, smaller range
    levels4 = np.arange(0., 0.51, 0.025)
    cmap4 = ccm.lajolla_r #plt.colormaps['magma']
    norm4 = mpl.colors.BoundaryNorm(levels4, ncolors=cmap4.N)

    for jj in range(n_members):
        for ii in range(n_members):
            cell = ax[jj][ii]
            if ii == jj:
                c1 = cell.pcolormesh(pfss[ii], cmap=cmap1, norm=norm1)
                cell.set_title(ens_data[ii].name, loc="left")
            elif ii > jj:
                diff = pfss[ii] - pfss[jj]
                c2 = cell.pcolormesh(diff, cmap=cmap2, norm=norm2)
                cell.set_title(f"{ens_data[ii].name} -\n{ens_data[jj].name}", loc="left")
            else:
                cell.axis('off')

    # Ensemble-coherence diagnostic rows: dFSSmean and dFSSstdev per ensemble.
    for ii in range(n_members):
        c3 = ax[row_dfm][ii].pcolormesh(dfss_mean[ii], cmap=cmap3, norm=norm3)
        ax[row_dfm][ii].set_title(f"dFSSmean: {ens_data[ii].name}", loc="left")
        c4 = ax[row_dfs][ii].pcolormesh(dfss_std[ii], cmap=cmap4, norm=norm4)
        ax[row_dfs][ii].set_title(f"dFSSstdev: {ens_data[ii].name}", loc="left")

    n_win = len(windows)
    for row in range(n_rows):
        for col in range(n_members):
            is_drawn = (row >= n_members) or (col >= row)
            if not is_drawn:
                continue
            a = ax[row][col]
            a.set_yticks([x + 0.5 for x in range(n_lev)])
            a.set_xticks([x + 0.5 for x in range(n_win)])
            a.set_yticklabels([str(x) for x in plot_levels])
            a.set_xticklabels([str(x) for x in windows], rotation=90)
            a.set_ylim([n_lev, 0.])
            a.set_xlim([0., n_win])
            a.tick_params(labelleft=True, labelbottom=True)
            if col == row or (row >= n_members and col == 0):
                a.set_ylabel("precip. threshold [mm]")
            if row == n_rows - 1 or (col == n_members - 1 and row == col):
                a.set_xlabel("window size [km]")

    plt.tight_layout()
    fig.subplots_adjust(bottom=0.09)
    cax1 = fig.add_axes([0.05, 0.04, 0.20, 0.008])
    cax2 = fig.add_axes([0.28, 0.04, 0.20, 0.008])
    cax3 = fig.add_axes([0.51, 0.04, 0.20, 0.008])
    cax4 = fig.add_axes([0.74, 0.04, 0.20, 0.008])

    plt.colorbar(c1, cax=cax1, orientation="horizontal", label="pFSS")
    if n_members > 1:
        cbar2 = plt.colorbar(c2, cax=cax2, orientation="horizontal",
                             label="pFSS difference")
        plt.draw()
        tick_labels = [label.get_text() for label in cbar2.ax.get_xticklabels()]
        tick_positions = cbar2.ax.get_xticks()
        cbar2.ax.set_xticks(tick_positions)
        cbar2.ax.set_xticklabels(tick_labels, rotation=30)
    plt.colorbar(c3, cax=cax3, orientation="horizontal",
                 label="dFSSmean (intra-ensemble pair FSS)")
    plt.colorbar(c4, cax=cax4, orientation="horizontal",
                 label="dFSSstdev (spread across member pairs)")

    start_date_str = dt.datetime.strptime(args.start, "%Y%m%d%H").strftime("%Y%m%d_%H")
    outfilename = (f"{PAN_DIR_PLOTS}/{args.name}_{args.parameter}_pFSS_"
                   f"{start_date_str}UTC_acc_{args.duration}_{verification_subdomain}.png")
    plt.savefig(outfilename)


# --------------------------- summary box plots ------------------------------

def _flat_finite(a):
    """Flatten an array to 1D and drop non-finite entries."""
    arr = np.asarray(a, dtype=float).ravel()
    return arr[np.isfinite(arr)]


def _score_list():
    """One panel per score, in this row-major order: (member_score_key,
    label). Each score lives on its own scale, so each gets its own panel.

    Scores are read by key from `Ensemble.member_scores` (per member,
    harvested in Ensemble.collect_member_scores). To add a score, append a
    (member_score_key, label) tuple here. A score whose key is absent on the
    ensembles is dropped automatically (e.g. cwfss_robust requires
    --check_ranking)."""
    return [
        ('bias_real',                   "BIAS [mm]"),
        ('mae',                         "MAE [mm]"),
        ('rms',                         "RMSE [mm]"),
        ('corr',                        "Correlation"),
        ('fss_condensed_weighted_rect', "cwFSS rect [0,1]"),
        ('cwfss_robust',                "cwFSS robust [0,1]"),
        ('fss_condensed_weighted',      "cwFSS (raw sum)"),
    ]


def _default_box_style():
    """Standard box-plot styling, kept as a single dict so the plot can be
    enhanced later (notches, means, custom whiskers, ...) by overriding
    individual keys without touching the layout code below."""
    return dict(
        notch=False,
        showmeans=False,
        showfliers=True,
        whis=1.5,
        patch_artist=True,
    )


def _member_sample(ens, key):
    """Per-member sample of one score for one ensemble (finite values only)."""
    return _flat_finite(getattr(ens, 'member_scores', {}).get(key, []))


def _available_scores(ens_data):
    """Drop scores absent on every ensemble."""
    return [(k, lbl) for (k, lbl) in _score_list()
            if any(_member_sample(e, k).size for e in ens_data)]


def _ens_colors(ens_data):
    """One colour per ensemble, taken from its configuration (all members of
    an ensemble share it). Falls back to the tab10 cycle if a config has no
    colour defined."""
    fallback = plt.colormaps['tab10']
    colors = []
    for i, e in enumerate(ens_data):
        c = getattr(e, 'color', None)
        colors.append(c if c else fallback(i % fallback.N))
    return colors


def _xtick_labels(ens_data):
    """Per-box x-tick label. Proper (non-lagged) single-init ensembles are
    labelled by their init time as DD-HH so several runs of the same
    configuration (same colour) can be told apart; a proper ensemble whose
    init times were merged (--merge_ens_init_times) has no single init and is
    labelled by its configuration name. Lagged ensembles are identified by the
    legend instead and get no x-tick label."""
    labels = []
    for e in ens_data:
        init = getattr(e, 'init', None)
        if getattr(e, 'lagged', False):
            labels.append("")
        elif getattr(e, 'merged_inits', False) or init is None:
            labels.append(getattr(e, 'conf', None) or e.name)
        else:
            labels.append(init.strftime("%d-%H"))
    return labels


def _legend_handles(ens_data, ens_colors):
    """One legend entry per configuration. Lagged ensembles are labelled
    '{conf}_lagged'; proper ensembles get a single entry per configuration
    (deduplicated), since their individual runs are distinguished by the
    init-time x-tick labels."""
    handles, seen = [], set()
    for e, c in zip(ens_data, ens_colors):
        conf = getattr(e, 'conf', None) or e.name
        label = f"{conf}_lagged" if getattr(e, 'lagged', False) else conf
        if label in seen:
            continue
        seen.add(label)
        handles.append(mpl.patches.Patch(facecolor=c, alpha=0.7, label=label))
    return handles


def _draw_single_score(ax, key, label, ens_data, ens_colors, style,
                       xticklabels, show_xticklabels):
    """One panel for one score: a box per ensemble, each spanning the
    ensemble's members. Panel is kept square (aspect ratio ~1). Only the
    bottom row of the grid shows x-tick labels (all panels share the x-axis)."""
    n_ens = len(ens_data)
    data, positions, colors = [], [], []
    for e_idx, ens in enumerate(ens_data):
        vals = _member_sample(ens, key)
        if vals.size == 0:
            continue
        data.append(vals)
        positions.append(e_idx + 1)
        colors.append(ens_colors[e_idx])

    if data:
        bp = ax.boxplot(data, positions=positions, widths=0.6, **style)
        if style.get('patch_artist'):
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        for median in bp['medians']:
            median.set_color('black')

    ax.set_title(label)
    ax.set_xticks(np.arange(1, n_ens + 1))
    if show_xticklabels:
        ax.set_xticklabels(xticklabels, rotation=90, fontsize=8)
    else:
        ax.set_xticklabels([])
    ax.set_xlim(0.5, n_ens + 0.5)
    ax.grid(axis='y', linestyle=':', alpha=0.5)
    if key == 'bias_real':
        ax.axhline(0., color='k', lw=0.5)
    ax.set_box_aspect(1)


def ens_score_boxplot(ens_data, verification_subdomain, args, box_style=None):
    """Summary box plots of per-member score distributions per ensemble.

    One panel per score (each on its own scale), arranged in a grid of up to
    `n_cols` columns with square panels. Each panel has one box per ensemble,
    spanning that ensemble's members. Pass `box_style` to override the default
    matplotlib boxplot kwargs (see `_default_box_style`); extend `_score_list`
    to add further scores."""
    n_ens = len(ens_data)
    if n_ens == 0:
        logger.warning("No ensembles available for ens_score_boxplot.")
        return None

    scores = _available_scores(ens_data)
    if not scores:
        logger.warning("No member scores available for ens_score_boxplot.")
        return None

    style = _default_box_style()
    if box_style:
        style.update(box_style)

    ens_colors = _ens_colors(ens_data)
    xticklabels = _xtick_labels(ens_data)

    n_cols = min(3, len(scores))
    n_rows = int(np.ceil(len(scores) / n_cols))
    panel_size = 3.2
    fig, axes = plt.subplots(n_rows, n_cols,
        figsize=(panel_size * n_cols, panel_size * n_rows + 1.0),
        dpi=args.dpi, squeeze=False)
    flat_axes = axes.ravel()

    # Label x-ticks only on the bottom-most panel of each column (all panels
    # share the same x-axis). With row-major fill these are the last <=n_cols
    # panels, which is correct even when the final row is partly empty.
    label_from = len(scores) - n_cols
    for i, (key, label) in enumerate(scores):
        _draw_single_score(flat_axes[i], key, label, ens_data, ens_colors,
                           style, xticklabels, show_xticklabels=(i >= label_from))
    for ax in flat_axes[len(scores):]:
        ax.axis('off')

    handles = _legend_handles(ens_data, ens_colors)
    # Cap legend columns to the grid width so it never overruns the figure
    # sides; it wraps onto extra rows and we reserve bottom space for them.
    leg_ncol = min(len(handles), n_cols)
    leg_rows = int(np.ceil(len(handles) / leg_ncol))
    bottom_margin = 0.03 + 0.025 * leg_rows
    fig.legend(handles=handles, loc='lower center', ncol=leg_ncol,
               fontsize=9, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"Ensemble member score distributions - {verification_subdomain}")
    fig.tight_layout(rect=[0, bottom_margin, 1, 0.95])
    # extra vertical room between rows so panel titles aren't cramped
    fig.subplots_adjust(hspace=0.35)

    start_date_str = dt.datetime.strptime(args.start, "%Y%m%d%H").strftime("%Y%m%d_%H")
    outfilename = (f"{PAN_DIR_PLOTS}/{args.name}_{args.parameter}_ens_score_boxplot_"
                   f"{start_date_str}UTC_acc_{args.duration}_{verification_subdomain}.png")
    plt.savefig(outfilename)
    plt.close(fig)
    logger.info(f"Saved ensemble score box plots to {outfilename}")
    return outfilename
