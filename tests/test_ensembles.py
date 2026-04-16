"""Tests for ensembles.py — detect_ensembles and add_ensemble_pseudo_members."""

import datetime as dt
import numpy as np
import pytest

import ensembles


def _sim(name, ensemble, init, precip, lon=None, lat=None):
    if lon is None:
        lon = np.zeros((4, 4))
    if lat is None:
        lat = np.zeros((4, 4))
    return {
        'name': name, 'ensemble': ensemble, 'init': init,
        'precip_data': np.asarray(precip, dtype=float),
        'lon': lon, 'lat': lat,
        'case': 'X', 'lead': 1,
    }


class TestDetectEnsembles:

    def test_detects_grouping(self):
        data = [
            _sim('obs', None, dt.datetime(2026, 1, 1), np.zeros((4, 4))),
            _sim('m1', 'ens_a', dt.datetime(2026, 1, 1), np.ones((4, 4))),
            _sim('m2', 'ens_a', dt.datetime(2026, 1, 1, 6), np.full((4, 4), 2.)),
            _sim('x',  'ens_b', dt.datetime(2026, 1, 1), np.full((4, 4), 5.)),
        ]
        out = ensembles.detect_ensembles(data)
        assert set(out.keys()) == {'ens_a', 'ens_b'}
        assert out['ens_a']['member_count'] == 2
        assert out['ens_a']['data_indices'] == [1, 2]
        assert out['ens_b']['member_count'] == 1

    def test_no_ensemble_key_ignored(self):
        data = [_sim('a', None, dt.datetime(2026, 1, 1), np.zeros((4, 4)))]
        # missing 'ensemble' key entirely
        del data[0]['ensemble']
        assert ensembles.detect_ensembles(data) == {}

    def test_falsy_ensemble_ignored(self):
        data = [_sim('a', '', dt.datetime(2026, 1, 1), np.zeros((4, 4)))]
        assert ensembles.detect_ensembles(data) == {}


class TestAddEnsemblePseudoMembers:

    def test_appends_mean_and_median(self):
        fields = [np.full((3, 3), v) for v in (1., 2., 6.)]
        data = [
            _sim('obs', None, dt.datetime(2026, 1, 1), np.zeros((3, 3))),
            _sim('m1', 'e', dt.datetime(2026, 1, 1), fields[0]),
            _sim('m2', 'e', dt.datetime(2026, 1, 1, 6), fields[1]),
            _sim('m3', 'e', dt.datetime(2026, 1, 1, 12), fields[2]),
        ]
        ens = ensembles.detect_ensembles(data)
        n_before = len(data)
        out = ensembles.add_ensemble_pseudo_members(data, ens)
        assert out is data
        assert len(data) == n_before + 2
        mean_sim, median_sim = data[-2], data[-1]
        assert mean_sim['name'] == 'e_mean'
        assert median_sim['name'] == 'e_median'
        assert mean_sim['pseudo'] is True
        assert median_sim['pseudo'] is True
        # mean = (1+2+6)/3 = 3, median = 2
        np.testing.assert_allclose(mean_sim['precip_data'], 3.)
        np.testing.assert_allclose(median_sim['precip_data'], 2.)

    def test_uses_latest_init(self):
        fields = [np.zeros((2, 2)), np.ones((2, 2))]
        latest = dt.datetime(2026, 1, 1, 12)
        data = [
            _sim('obs', None, dt.datetime(2026, 1, 1), np.zeros((2, 2))),
            _sim('m1', 'e', dt.datetime(2026, 1, 1), fields[0]),
            _sim('m2', 'e', latest, fields[1]),
        ]
        ens = ensembles.detect_ensembles(data)
        ensembles.add_ensemble_pseudo_members(data, ens)
        assert data[-2]['init'] == latest
        assert data[-1]['init'] == latest

    def test_pseudo_inherits_grid(self):
        lon = np.arange(4).reshape(2, 2).astype(float)
        lat = lon + 10.
        data = [
            _sim('obs', None, dt.datetime(2026, 1, 1), np.zeros((2, 2)),
                 lon=lon, lat=lat),
            _sim('m1', 'e', dt.datetime(2026, 1, 1), np.ones((2, 2)),
                 lon=lon, lat=lat),
            _sim('m2', 'e', dt.datetime(2026, 1, 1), np.full((2, 2), 3.),
                 lon=lon, lat=lat),
        ]
        ens = ensembles.detect_ensembles(data)
        ensembles.add_ensemble_pseudo_members(data, ens)
        np.testing.assert_array_equal(data[-1]['lon'], lon)
        np.testing.assert_array_equal(data[-1]['lat'], lat)

    def test_no_ensembles_no_change(self):
        data = [_sim('obs', None, dt.datetime(2026, 1, 1), np.zeros((2, 2)))]
        ensembles.add_ensemble_pseudo_members(data, {})
        assert len(data) == 1
