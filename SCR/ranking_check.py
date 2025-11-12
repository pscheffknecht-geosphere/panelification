import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import matplotlib as mpl
import matplotlib.colors as colors
from joblib import Parallel, delayed
import fss_cumsum as fss

from paths import PAN_DIR_PLOTS

import logging
logger = logging.getLogger(__name__)

def add_rank_robustness_info(data_list, args):
    logger.info("Calculating FSS samples for ranking robustness check, this can take a few minutes...")
    cwfss_tmp = Parallel(n_jobs=2, backend='threading')(
        delayed(fss.CWFSS)(
        sim["precip_data_resampled"], data_list[0]['precip_data_resampled'], 
        nsamples=1250, threshold_limiting="relative", 
        window_limits=[10., 200.]) for sim in data_list[1::])
    logger.info("Done.")
    for cwfss, sim in zip(cwfss_tmp, data_list[1::]):
        print(f"Bootstraping {sim['name']}, N = {10000}")
        cwfss.bootstrap(N=10000)
        sim[f"cwfss"] = cwfss
        sim[f"cwfss_robust"] = cwfss.cwfss
        


def extract_cwfss_array(data_list):
    logger.debug("Extracting FSS sample info.")
    fss_scores = np.zeros((len(data_list)-1, 10000))
    for ii, sim in enumerate(data_list[1::]):
        for key in [f"cwfss"]:
            c = sim[key]
            sim[f"cwfss_std"] = np.std(c.bootstrap_info)
            fss_scores[ii, :] = c.bootstrap_info
    return fss_scores


def draw_ranking_confidence_plot(data_list, start_date, end_date, verification_subdomain, args):
    logger.info("Drawing ranking robustness chart...")
    fss_scores = extract_cwfss_array(data_list)
    n_models, n_samples = fss_scores.shape
    fig, ax = plt.subplots(2, 2, figsize=(9, 2+2*(len(data_list)-1)*0.12), sharex=True, sharey=True, dpi=150)

    c1 = ax[0][0].pcolormesh(fss_scores, cmap="bone")
    ranks = np.argsort(np.argsort(fss_scores, axis=0), axis=0)
    ranks = ranks.max() + 1 - ranks
    c2 = ax[0][1].pcolormesh(ranks, cmap="RdYlGn_r") #, vmin=0., vmax=10.)

    sorted_ranks = np.sort(ranks, axis=1)
    c3 = ax[1][0].pcolormesh(sorted_ranks, cmap="RdYlGn_r") #, vmin=0., vmax=10.)

    colors = [
        (1., 1., 0., 1.),
        (0.7, 0.7, 0.7, 1.),
        (1., 0.5, 0.2, 1.)]

    cmap = mpl.colors.ListedColormap(colors)
    cmap.set_over("None")

    norm = mpl.colors.BoundaryNorm([1, 2, 3, 4], ncolors=3)
    c4 = plt.pcolormesh(sorted_ranks, cmap=cmap, norm=norm, zorder=0.2)

    frac_top1 = np.mean(sorted_ranks == 1, axis=1)
    frac_top2 = np.mean(sorted_ranks == 2, axis=1)
    frac_top3 = np.mean(sorted_ranks == 3, axis=1)

    most_common_rank = []
    most_common_rank_indicator = np.zeros(ranks.shape)

    for row in sorted_ranks:
        vals, counts = np.unique(row, return_counts=True)
        most_common_rank.append(vals[np.argmax(counts)])

    most_common_rank = np.array(most_common_rank)

    def get_rank_pos(ranks, most_common_rank):
        ranks_of_interest = np.arange(most_common_rank - 2, most_common_rank + 3)
        avg_idx = {
            r: np.mean(np.where(ranks == r)[0]) if np.any(ranks == r) else np.nan
            for r in ranks_of_interest
        }
        return avg_idx

    sizes = [5, 6, 8, 6, 5]

    old_cwfss = np.array([sim["fss_condensed_weighted"] for sim in data_list[1::]])
    old_ranks = np.argsort(np.argsort(-old_cwfss))
    # print(old_cwfss)
    # print(old_ranks)

    for ii in range(n_models):
        top1 = frac_top1[ii]*100.
        top2 = frac_top2[ii]*100.
        top3 = frac_top3[ii]*100.
        if top1 > 15:
            ax[1][1].text(n_samples/100.*(0.5*top1), ii+0.5, f"{top1:.1f}%", size=8, ha="center", va="center", zorder=100)
        if top2 > 15:
            ax[1][1].text(n_samples/100.*(top1 + 0.5*top2), ii+0.5, f"{top2:.1f}%", size=8, ha="center", va="center", zorder=100)
        if top3 > 15:
            ax[1][1].text(n_samples/100.*(top1 + top2 + 0.5*top3), ii+0.5, f"{top3:.1f}%", size=8, ha="center", va="center", zorder=100)
        if most_common_rank[ii] > 3:
            alpha = 0.5*(1. - 0.33333 * np.abs(sorted_ranks[ii, :] - most_common_rank[ii])).clip(0., 1.)
            ax[1][1].fill_between(np.arange(n_samples), ii+0.5+alpha, ii+0.5-alpha, 
                                  facecolor='lightgray', edgecolor='None', zorder=0.1)

            ranks_of_interest = get_rank_pos(sorted_ranks[ii, :], most_common_rank[ii])
            ss = 0
            for roi, pos in ranks_of_interest.items():
                if (sorted_ranks[ii, :] == roi).sum() > 0.1 * n_samples:
                    ax[1][1].text(ranks_of_interest[roi], ii+0.5, roi, ha="center", va="center", size=sizes[ss])
                ss += 1
        rank_text_x = 1.01 * n_samples
        ax[1][1].text(rank_text_x, ii+0.5, old_ranks[ii]+1, ha="left", va="center")

    _ = ax[0][0].set_yticks(np.arange(n_models))
    _ = ax[0][0].set_yticklabels([sim["name"] for sim in data_list[1::]], va='bottom')
    _ = ax[1][0].set_yticks(np.arange(n_models))
    _ = ax[1][0].set_yticklabels([sim["name"] for sim in data_list[1::]], va='bottom')

    for ax_ in ax.flat:
        ax_.grid(axis='y', color='w', lw=2)

    ax[0][0].set_title("a) bootstrapped cwFSS values", loc="left")
    ax[0][1].set_title("b) bootstrapped ranks", loc="left")
    ax[1][0].set_title("c) bootstrapped ranks (sorted)", loc="left")
    ax[1][1].set_title("d) ranks 1-3, colored + most common", loc="left")

    plt.tight_layout()

    print(fig.get_figheight() + 0.08)
    bot = .75 / fig.get_figheight()
    fig.subplots_adjust(bottom=bot)
    cax1 = fig.add_axes([0.1, 0.04, 0.35, 0.015])
    plt.colorbar(c1, cax=cax1, orientation="horizontal", label="cwFSS sample values")
    cax2 = fig.add_axes([0.55, 0.04, 0.35, 0.015])
    plt.colorbar(c2, cax=cax2, orientation="horizontal", label="rank")
    start_date_str = start_date.strftime("%Y%m%d_%H")
    img_file_name = f"{PAN_DIR_PLOTS}/{args.name}_{args.parameter}_ranking_{start_date_str}UTC_{args.duration:02d}h_acc_{verification_subdomain}.png"
    plt.savefig(img_file_name)
    logger.info(f"Saved chart to {img_file_name}")