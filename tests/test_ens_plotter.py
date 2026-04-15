"""Tests for ens_plotter.py — configuration helpers and field computation.

The drawing pipeline needs cartopy / real region objects; here we only
exercise the pure helpers."""

import argparse
import types
import numpy as np
import pytest

import ens_plotter


class TestConfigHelpers:

    def test_default_show_keys_match_specs(self):
        show = ens_plotter._get_default_show()
        spec_keys = {s[0] for s in ens_plotter._build_specs(50)}
        assert spec_keys == set(show.keys())

    def test_default_show_defaults(self):
        show = ens_plotter._get_default_show()
        for k in ('mean', 'median', 'spread', 'crps', 'nbh', 'nbh_20',
                  'mean_minus_median', 'norm_mean'):
            assert show[k] is True
        for k in ('ratio_mae', 'frac', 'frac_msm', 'frac_post',
                  'mean_div_median', 'norm_median'):
            assert show[k] is False

    def test_specs_tuples_shape(self):
        specs = ens_plotter._build_specs(50)
        for key, title, kind in specs:
            assert isinstance(key, str)
            assert isinstance(title, str)
            assert isinstance(kind, str)

    def test_cbar_labels_cover_all_kinds(self):
        specs = ens_plotter._build_specs(50)
        kinds = {s[2] for s in specs}
        args = argparse.Namespace(parameter='precip', d_windows=[], duration=1,
                                  mode='normal', cmap='mycolors', colormap='new')
        labels = ens_plotter._cbar_labels(args)
        for kind in kinds:
            assert kind in labels, f"missing cbar label for kind={kind}"


class TestCmapDict:

    def _args(self):
        return argparse.Namespace(parameter='precip', d_windows=[], duration=1,
                                  mode='normal', cmap='mycolors', colormap='new')

    def test_all_kinds_present(self):
        cmaps = ens_plotter._build_cmaps(self._args())
        expected = {'precip', 'spread', 'ratio', 'frac', 'diff',
                    'crps', 'nbh', 'norm', 'norm_spread'}
        assert expected.issubset(cmaps.keys())

    def test_each_entry_is_cmap_norm_pair(self):
        cmaps = ens_plotter._build_cmaps(self._args())
        for kind, val in cmaps.items():
            assert len(val) == 2
            cmap, norm = val
            # cmap must be callable (matplotlib colormap)
            assert callable(cmap)


class TestComputeFields:
    """Use a minimal ensemble stand-in (duck-typed) to exercise _compute_fields."""

    def _make_ens(self, seed=0):
        rng = np.random.default_rng(seed)
        nx = ny = 16
        members = 5
        data = rng.uniform(0., 10., size=(members, ny, nx))
        obs = rng.uniform(0., 10., size=(ny, nx))
        ens = types.SimpleNamespace(
            precip_data_resampled=data,
            obs_data_resampled=obs,
            CRPS=np.zeros((ny, nx)),
            lon=np.zeros((ny, nx)),
            lat=np.zeros((ny, nx)),
            name='test_ens',
            obs_name='OBS',
        )
        return ens

    def test_default_show_produces_expected_keys(self):
        ens = self._make_ens()
        show = ens_plotter._get_default_show()
        fm, thr = ens_plotter._compute_fields(ens, show, smooth_size=5,
                                              nbh_size=5, nbh_size_small=3,
                                              eps=1e-6)
        active = {k for k, v in show.items() if v}
        assert set(fm.keys()) == active
        assert thr is not None  # nbh is on → threshold computed

    def test_threshold_rounded_to_step(self):
        ens = self._make_ens()
        show = ens_plotter._get_default_show()
        _, thr = ens_plotter._compute_fields(ens, show, 5, 5, 3, 1e-6)
        # step is 5 if P90<20 else 10 — and value must be a multiple of step
        assert thr % 5 == 0 or thr % 10 == 0

    def test_nbh_disabled_skips_threshold(self):
        ens = self._make_ens()
        show = {k: False for k in ens_plotter._get_default_show()}
        show['mean'] = True
        fm, thr = ens_plotter._compute_fields(ens, show, 5, 5, 3, 1e-6)
        assert thr is None
        assert set(fm.keys()) == {'mean'}

    def test_only_nbh_20(self):
        ens = self._make_ens()
        show = {k: False for k in ens_plotter._get_default_show()}
        show['nbh_20'] = True
        fm, thr = ens_plotter._compute_fields(ens, show, 5, 5, 3, 1e-6)
        assert thr is not None
        assert 'nbh_20' in fm and 'nbh' not in fm
        field, kind = fm['nbh_20']
        assert kind == 'nbh'
        # fraction of members — must be in [0, 1]
        assert field.min() >= 0. and field.max() <= 1.

    def test_spread_matches_numpy(self):
        ens = self._make_ens()
        show = {k: False for k in ens_plotter._get_default_show()}
        show['spread'] = True
        fm, _ = ens_plotter._compute_fields(ens, show, 5, 5, 3, 1e-6)
        field, _ = fm['spread']
        np.testing.assert_allclose(field, np.std(ens.precip_data_resampled, axis=0))

    def test_mean_minus_median_sign(self):
        ens = self._make_ens(seed=42)
        show = {k: False for k in ens_plotter._get_default_show()}
        show['mean_minus_median'] = True
        fm, _ = ens_plotter._compute_fields(ens, show, 5, 5, 3, 1e-6)
        field, kind = fm['mean_minus_median']
        assert kind == 'diff'
        expected = (np.mean(ens.precip_data_resampled, axis=0)
                    - np.median(ens.precip_data_resampled, axis=0))
        np.testing.assert_allclose(field, expected)
