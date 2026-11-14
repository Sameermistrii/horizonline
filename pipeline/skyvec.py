"""
Sun/Earth directions for ANY lunar site from one reference site's Horizons data.
Horizons az/el at a reference site -> Moon-fixed (MEAN_ME) vectors -> az/el at another site.
Earth parallax is handled with the Earth-site range (topocentric), the Sun's is negligible.
"""
import numpy as np

R = 1737.4  # km, LOLA/Horizons reference sphere


def enu(lat, lon):
    p, l = np.radians(lat), np.radians(lon)
    E = np.array([-np.sin(l), np.cos(l), 0.0])
    N = np.array([-np.sin(p) * np.cos(l), -np.sin(p) * np.sin(l), np.cos(p)])
    U = np.array([np.cos(p) * np.cos(l), np.cos(p) * np.sin(l), np.sin(p)])
    return E, N, U


def azel_to_vec(lat, lon, az, el):
    """Local az/el (deg) -> Moon-fixed unit vectors, shape (n, 3)."""
    E, N, U = enu(lat, lon)
    a, e = np.radians(az)[:, None], np.radians(el)[:, None]
    return np.cos(e) * np.sin(a) * E + np.cos(e) * np.cos(a) * N + np.sin(e) * U


def vec_to_azel(lat, lon, v):
    E, N, U = enu(lat, lon)
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    az = np.degrees(np.arctan2(v @ E, v @ N)) % 360
    el = np.degrees(np.arcsin(np.clip(v @ U, -1, 1)))
    return az, el


def body_position(ref_lat, ref_lon, ref_h_km, az, el, range_km):
    """Body position in the Moon-fixed frame (km from Moon centre)."""
    _, _, U = enu(ref_lat, ref_lon)
    return (R + ref_h_km) * U + azel_to_vec(ref_lat, ref_lon, az, el) * np.asarray(range_km)[:, None]


def azel_at(lat, lon, h_km, pos):
    _, _, U = enu(lat, lon)
    return vec_to_azel(lat, lon, pos - (R + h_km) * U)
