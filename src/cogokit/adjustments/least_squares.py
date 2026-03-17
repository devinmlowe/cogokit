"""Least-squares network adjustment for control survey networks.

Implements a parametric (Gauss-Markov) least-squares adjustment supporting
distance, angle, direction, and azimuth observations. Direction observations
include per-station orientation unknowns.

Requires NumPy (optional dependency): pip install cogokit[lsa]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

try:
    import numpy as np
except ImportError:
    raise ImportError(
        "NumPy is required for least-squares adjustment. "
        "Install with: pip install cogokit[lsa]"
    )

from cogokit.core import Point
from cogokit.geodetic.conversions import ecef_to_geodetic, geodetic_to_ecef


# ---------------------------------------------------------------------------
# Observation types
# ---------------------------------------------------------------------------

@dataclass
class DistanceObservation:
    """Observed horizontal distance between two points."""

    from_point: int
    to_point: int
    distance: float
    std_dev: float = 0.005


@dataclass
class AngleObservation:
    """Observed horizontal angle at a point (backsight → foresight, clockwise)."""

    at_point: int
    from_point: int
    to_point: int
    angle: float  # radians
    std_dev: float = 0.00005


@dataclass
class DirectionObservation:
    """Observed direction from instrument station to a target.

    Directions require an orientation unknown per instrument station.
    """

    at_point: int
    to_point: int
    direction: float  # radians
    std_dev: float = 0.00005


@dataclass
class AzimuthObservation:
    """Observed azimuth from one point to another."""

    from_point: int
    to_point: int
    azimuth: float  # radians
    std_dev: float = 0.00005


@dataclass
class GpsBaselineObservation:
    """Observed GPS baseline vector in ECEF (delta X, Y, Z).

    Each baseline contributes 3 rows to the design matrix (one per component).
    Weight is the inverse of the 3x3 covariance matrix.  When covariance is
    None, a diagonal matrix using std_dev^2 is assumed.
    """

    from_point: int
    to_point: int
    dx: float  # ECEF delta-X in metres
    dy: float  # ECEF delta-Y in metres
    dz: float  # ECEF delta-Z in metres
    covariance: np.ndarray | None = None  # 3x3 covariance matrix
    std_dev: float = 0.010  # used when covariance is None


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class AdjustmentResult:
    """Result of a least-squares network adjustment."""

    adjusted_points: dict[int, Point]
    residuals: list[float]
    std_errors: dict[int, tuple[float, float]]  # point number -> (std_N, std_E)
    reference_variance: float
    iterations: int
    converged: bool
    adjusted_points_3d: dict[int, tuple[float, float, float]] | None = None  # pn -> (X, Y, Z)


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

Observation = (
    DistanceObservation | AngleObservation | DirectionObservation
    | AzimuthObservation | GpsBaselineObservation
)


class Network:
    """Least-squares network adjustment for 2D and 3D survey networks.

    Supports fixed (control) points and approximate (unknown) points with
    distance, angle, direction, azimuth, and GPS baseline observations.

    When GPS baseline observations are present, the network operates in 3D
    mode using ECEF coordinates.  Use ``add_fixed_point_3d`` and
    ``add_approximate_point_3d`` to supply geodetic positions that are
    converted to ECEF internally.

    .. note::
       Mixed 2D + 3D observations are not yet supported.  GPS-only networks
       are the target for this first implementation.  Adding the ECEF-to-local
       rotation matrix for mixed mode is a future enhancement (TODO).
    """

    def __init__(self) -> None:
        self.fixed_points: dict[int, Point] = {}
        self.approximate_points: dict[int, Point] = {}
        self.observations: list[Observation] = []
        # 3D ECEF coordinate stores  {point_number: (X, Y, Z)}
        self.fixed_points_3d: dict[int, tuple[float, float, float]] = {}
        self.approximate_points_3d: dict[int, tuple[float, float, float]] = {}

    # -------------------------------------------------------------------
    # 2D point management
    # -------------------------------------------------------------------

    def add_fixed_point(self, point: Point) -> None:
        """Add a fixed (control) point that will not be adjusted."""
        if point.number is None:
            raise ValueError("Point must have a number")
        self.fixed_points[point.number] = point

    def add_approximate_point(self, point: Point) -> None:
        """Add an approximate (unknown) point to be adjusted."""
        if point.number is None:
            raise ValueError("Point must have a number")
        self.approximate_points[point.number] = point

    # -------------------------------------------------------------------
    # 3D point management
    # -------------------------------------------------------------------

    def add_fixed_point_3d(self, num: int, lat: float, lon: float, h: float) -> None:
        """Add a fixed 3D point from geodetic coordinates (lat/lon in radians)."""
        self.fixed_points_3d[num] = geodetic_to_ecef(lat, lon, h)

    def add_approximate_point_3d(self, num: int, lat: float, lon: float, h: float) -> None:
        """Add an approximate 3D point from geodetic coordinates (lat/lon in radians)."""
        self.approximate_points_3d[num] = geodetic_to_ecef(lat, lon, h)

    def add_observation(self, obs: Observation) -> None:
        """Add an observation of any supported type."""
        self.observations.append(obs)

    @property
    def _is_3d(self) -> bool:
        """True if the network contains GPS baseline observations."""
        return any(isinstance(obs, GpsBaselineObservation) for obs in self.observations)

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _get_point(self, pn: int) -> Point:
        """Look up a point by number from fixed or approximate points."""
        if pn in self.fixed_points:
            return self.fixed_points[pn]
        if pn in self.approximate_points:
            return self.approximate_points[pn]
        raise ValueError(f"Point {pn} not found in network")

    @staticmethod
    def _azimuth(pi: Point, pj: Point) -> float:
        """Compute azimuth from pi to pj (radians, 0..2π)."""
        dn = pj.northing - pi.northing
        de = pj.easting - pi.easting
        az = math.atan2(de, dn)
        if az < 0:
            az += 2 * math.pi
        return az

    @staticmethod
    def _normalize_angle(a: float) -> float:
        """Normalize an angle difference to [-π, π)."""
        while a > math.pi:
            a -= 2 * math.pi
        while a <= -math.pi:
            a += 2 * math.pi
        return a

    def _build_unknown_index(self) -> tuple[list[int], int, dict[int, int]]:
        """Build the mapping of unknowns to parameter indices.

        Returns:
            point_nums: sorted list of approximate point numbers
            n_coord_unknowns: number of coordinate unknowns (2 per point)
            orientation_index: mapping of instrument station number to
                parameter index for its orientation unknown
        """
        point_nums = sorted(self.approximate_points.keys())
        n_coord = len(point_nums) * 2  # N, E per point

        # Find unique instrument stations for direction observations
        direction_stations: set[int] = set()
        for obs in self.observations:
            if isinstance(obs, DirectionObservation):
                direction_stations.add(obs.at_point)

        orientation_index: dict[int, int] = {}
        for i, stn in enumerate(sorted(direction_stations)):
            orientation_index[stn] = n_coord + i

        return point_nums, n_coord, orientation_index

    def _param_index(self, pn: int, point_nums: list[int]) -> int | None:
        """Get the parameter index for a point's northing (easting = index + 1).

        Returns None if the point is fixed (not in the unknown list).
        """
        try:
            idx = point_nums.index(pn)
            return idx * 2
        except ValueError:
            return None

    # -------------------------------------------------------------------
    # Adjustment
    # -------------------------------------------------------------------

    def adjust(
        self,
        max_iterations: int = 10,
        convergence: float = 1e-8,
    ) -> AdjustmentResult:
        """Perform iterative least-squares adjustment.

        Args:
            max_iterations: Maximum number of iterations.
            convergence: Convergence threshold (max absolute coordinate correction).

        Returns:
            AdjustmentResult with adjusted coordinates and statistics.
        """
        if not self.observations:
            raise ValueError("Network has no observations")

        if self._is_3d:
            return self._adjust_3d(max_iterations, convergence)

        if not self.approximate_points:
            raise ValueError("Network has no unknown (approximate) points to adjust")

        point_nums, n_coord, orientation_index = self._build_unknown_index()
        n_unknowns = n_coord + len(orientation_index)
        n_obs = len(self.observations)

        # Initialize orientation unknowns to zero
        orientation_values: dict[int, float] = {stn: 0.0 for stn in orientation_index}

        converged = False
        iteration = 0

        for iteration in range(1, max_iterations + 1):
            # Build A, W, l
            A = np.zeros((n_obs, n_unknowns))
            W = np.zeros((n_obs, n_obs))
            l_vec = np.zeros(n_obs)

            for row, obs in enumerate(self.observations):
                w = 1.0 / (obs.std_dev ** 2)
                W[row, row] = w

                if isinstance(obs, DistanceObservation):
                    self._fill_distance_row(A, l_vec, row, obs, point_nums)
                elif isinstance(obs, AzimuthObservation):
                    self._fill_azimuth_row(A, l_vec, row, obs, point_nums)
                elif isinstance(obs, AngleObservation):
                    self._fill_angle_row(A, l_vec, row, obs, point_nums)
                elif isinstance(obs, DirectionObservation):
                    self._fill_direction_row(
                        A, l_vec, row, obs, point_nums,
                        orientation_index, orientation_values,
                    )

            # Normal equations: N = A^T W A, n = A^T W l
            AtW = A.T @ W
            N_mat = AtW @ A
            n_vec = AtW @ l_vec

            # Solve
            try:
                delta = np.linalg.solve(N_mat, n_vec)
            except np.linalg.LinAlgError:
                break

            # Update approximate coordinates
            for i, pn in enumerate(point_nums):
                pt = self.approximate_points[pn]
                self.approximate_points[pn] = Point(
                    northing=pt.northing + delta[2 * i],
                    easting=pt.easting + delta[2 * i + 1],
                    elevation=pt.elevation,
                    number=pt.number,
                    description=pt.description,
                )

            # Update orientation unknowns
            for stn, idx in orientation_index.items():
                orientation_values[stn] += delta[idx]

            # Check convergence on coordinate corrections only
            max_delta = max(abs(delta[i]) for i in range(n_coord))
            if max_delta < convergence:
                converged = True
                break

        # Compute final residuals: v = A @ delta - l  (post-adjustment)
        # Recompute l_vec with final coordinates to get residuals
        residuals_vec = A @ delta - l_vec
        residuals = residuals_vec.tolist()

        # Degrees of freedom
        dof = n_obs - n_unknowns

        # A posteriori reference variance
        if dof > 0:
            vtwv = float(residuals_vec.T @ W @ residuals_vec)
            reference_variance = vtwv / dof
        else:
            reference_variance = 0.0

        # Standard errors of adjusted unknowns
        std_errors: dict[int, tuple[float, float]] = {}
        try:
            Qxx = np.linalg.inv(N_mat)
            variance_factor = max(reference_variance, 1e-30)
            for i, pn in enumerate(point_nums):
                var_n = abs(Qxx[2 * i, 2 * i]) * variance_factor
                var_e = abs(Qxx[2 * i + 1, 2 * i + 1]) * variance_factor
                std_errors[pn] = (math.sqrt(var_n), math.sqrt(var_e))
        except np.linalg.LinAlgError:
            for pn in point_nums:
                std_errors[pn] = (0.0, 0.0)

        # Build adjusted points dict (fixed + adjusted)
        adjusted_points: dict[int, Point] = {}
        for pn, pt in self.fixed_points.items():
            adjusted_points[pn] = pt
        for pn, pt in self.approximate_points.items():
            adjusted_points[pn] = pt

        return AdjustmentResult(
            adjusted_points=adjusted_points,
            residuals=residuals,
            std_errors=std_errors,
            reference_variance=reference_variance,
            iterations=iteration,
            converged=converged,
        )

    # -------------------------------------------------------------------
    # Row-fill methods for the design matrix
    # -------------------------------------------------------------------

    def _fill_distance_row(
        self,
        A: np.ndarray,
        l_vec: np.ndarray,
        row: int,
        obs: DistanceObservation,
        point_nums: list[int],
    ) -> None:
        pi = self._get_point(obs.from_point)
        pj = self._get_point(obs.to_point)
        dn = pj.northing - pi.northing
        de = pj.easting - pi.easting
        dist = math.hypot(dn, de)
        if dist < 1e-12:
            return

        # Partials: dD/dNi = -(Nj-Ni)/D, dD/dEi = -(Ej-Ei)/D
        dD_dNi = -dn / dist
        dD_dEi = -de / dist
        dD_dNj = dn / dist
        dD_dEj = de / dist

        idx_i = self._param_index(obs.from_point, point_nums)
        idx_j = self._param_index(obs.to_point, point_nums)

        if idx_i is not None:
            A[row, idx_i] = dD_dNi
            A[row, idx_i + 1] = dD_dEi
        if idx_j is not None:
            A[row, idx_j] = dD_dNj
            A[row, idx_j + 1] = dD_dEj

        l_vec[row] = obs.distance - dist

    def _fill_azimuth_row(
        self,
        A: np.ndarray,
        l_vec: np.ndarray,
        row: int,
        obs: AzimuthObservation,
        point_nums: list[int],
    ) -> None:
        pi = self._get_point(obs.from_point)
        pj = self._get_point(obs.to_point)
        dn = pj.northing - pi.northing
        de = pj.easting - pi.easting
        dist_sq = dn * dn + de * de
        if dist_sq < 1e-24:
            return

        # Partials: dAz/dNi = (Ej-Ei)/D^2, dAz/dEi = -(Nj-Ni)/D^2
        dAz_dNi = de / dist_sq
        dAz_dEi = -dn / dist_sq
        dAz_dNj = -de / dist_sq
        dAz_dEj = dn / dist_sq

        idx_i = self._param_index(obs.from_point, point_nums)
        idx_j = self._param_index(obs.to_point, point_nums)

        if idx_i is not None:
            A[row, idx_i] = dAz_dNi
            A[row, idx_i + 1] = dAz_dEi
        if idx_j is not None:
            A[row, idx_j] = dAz_dNj
            A[row, idx_j + 1] = dAz_dEj

        computed_az = self._azimuth(pi, pj)
        l_vec[row] = self._normalize_angle(obs.azimuth - computed_az)

    def _fill_angle_row(
        self,
        A: np.ndarray,
        l_vec: np.ndarray,
        row: int,
        obs: AngleObservation,
        point_nums: list[int],
    ) -> None:
        """Angle at B from A to C = azimuth(B→C) - azimuth(B→A)."""
        pb = self._get_point(obs.at_point)
        pa = self._get_point(obs.from_point)
        pc = self._get_point(obs.to_point)

        # Azimuth B→A
        dn_ba = pa.northing - pb.northing
        de_ba = pa.easting - pb.easting
        d_ba_sq = dn_ba * dn_ba + de_ba * de_ba
        if d_ba_sq < 1e-24:
            return

        # Azimuth B→C
        dn_bc = pc.northing - pb.northing
        de_bc = pc.easting - pb.easting
        d_bc_sq = dn_bc * dn_bc + de_bc * de_bc
        if d_bc_sq < 1e-24:
            return

        # Partials for azimuth B→A w.r.t. unknowns
        # dAz_BA/dNB = de_ba / d_ba_sq,  dAz_BA/dEB = -dn_ba / d_ba_sq
        # dAz_BA/dNA = -de_ba / d_ba_sq, dAz_BA/dEA = dn_ba / d_ba_sq

        # Partials for azimuth B→C w.r.t. unknowns
        # dAz_BC/dNB = de_bc / d_bc_sq,  dAz_BC/dEB = -dn_bc / d_bc_sq
        # dAz_BC/dNC = -de_bc / d_bc_sq, dAz_BC/dEC = dn_bc / d_bc_sq

        # Angle = Az_BC - Az_BA, so partials = partials_BC - partials_BA
        idx_b = self._param_index(obs.at_point, point_nums)
        idx_a = self._param_index(obs.from_point, point_nums)
        idx_c = self._param_index(obs.to_point, point_nums)

        if idx_b is not None:
            # d(angle)/dNB = dAz_BC/dNB - dAz_BA/dNB
            A[row, idx_b] += de_bc / d_bc_sq - de_ba / d_ba_sq
            # d(angle)/dEB = dAz_BC/dEB - dAz_BA/dEB
            A[row, idx_b + 1] += -dn_bc / d_bc_sq + dn_ba / d_ba_sq

        if idx_a is not None:
            # d(angle)/dNA = -dAz_BA/dNA = -(-de_ba / d_ba_sq) = de_ba / d_ba_sq
            # Wait: angle = Az_BC - Az_BA
            # d(angle)/dNA = 0 - dAz_BA/dNA = -(-de_ba / d_ba_sq) = de_ba / d_ba_sq
            A[row, idx_a] += de_ba / d_ba_sq
            # d(angle)/dEA = 0 - dAz_BA/dEA = -(dn_ba / d_ba_sq) = -dn_ba / d_ba_sq
            A[row, idx_a + 1] += -dn_ba / d_ba_sq

        if idx_c is not None:
            # d(angle)/dNC = dAz_BC/dNC - 0 = -de_bc / d_bc_sq
            A[row, idx_c] += -de_bc / d_bc_sq
            # d(angle)/dEC = dAz_BC/dEC - 0 = dn_bc / d_bc_sq
            A[row, idx_c + 1] += dn_bc / d_bc_sq

        # Computed angle
        az_ba = self._azimuth(pb, pa)
        az_bc = self._azimuth(pb, pc)
        computed_angle = az_bc - az_ba
        if computed_angle < 0:
            computed_angle += 2 * math.pi

        l_vec[row] = self._normalize_angle(obs.angle - computed_angle)

    def _fill_direction_row(
        self,
        A: np.ndarray,
        l_vec: np.ndarray,
        row: int,
        obs: DirectionObservation,
        point_nums: list[int],
        orientation_index: dict[int, int],
        orientation_values: dict[int, float],
    ) -> None:
        """Direction = azimuth + orientation unknown."""
        pi = self._get_point(obs.at_point)
        pj = self._get_point(obs.to_point)
        dn = pj.northing - pi.northing
        de = pj.easting - pi.easting
        dist_sq = dn * dn + de * de
        if dist_sq < 1e-24:
            return

        # Same partials as azimuth
        idx_i = self._param_index(obs.at_point, point_nums)
        idx_j = self._param_index(obs.to_point, point_nums)

        if idx_i is not None:
            A[row, idx_i] = de / dist_sq
            A[row, idx_i + 1] = -dn / dist_sq
        if idx_j is not None:
            A[row, idx_j] = -de / dist_sq
            A[row, idx_j + 1] = dn / dist_sq

        # Orientation unknown column
        orient_idx = orientation_index[obs.at_point]
        A[row, orient_idx] = 1.0

        computed_az = self._azimuth(pi, pj)
        orient_val = orientation_values.get(obs.at_point, 0.0)
        # Direction = azimuth + orientation  =>  obs = computed_az + orient
        # l = observed - computed = obs.direction - (computed_az + orient_val)
        l_vec[row] = self._normalize_angle(obs.direction - computed_az - orient_val)

    # -------------------------------------------------------------------
    # 3D (GPS baseline) adjustment
    # -------------------------------------------------------------------

    def _get_point_3d(self, pn: int) -> tuple[float, float, float]:
        """Look up ECEF coordinates for a point by number."""
        if pn in self.fixed_points_3d:
            return self.fixed_points_3d[pn]
        if pn in self.approximate_points_3d:
            return self.approximate_points_3d[pn]
        raise ValueError(f"3D point {pn} not found in network")

    def _param_index_3d(self, pn: int, point_nums: list[int]) -> int | None:
        """Get the parameter index for a 3D point's X (Y = +1, Z = +2).

        Returns None if the point is fixed.
        """
        try:
            idx = point_nums.index(pn)
            return idx * 3
        except ValueError:
            return None

    def _adjust_3d(
        self,
        max_iterations: int = 10,
        convergence: float = 1e-8,
    ) -> AdjustmentResult:
        """Perform 3D least-squares adjustment for GPS baseline networks.

        GPS baselines have identity Jacobians (dF/dXi = -I, dF/dXj = +I)
        so the adjustment converges in one iteration for linear observations.
        """
        if not self.approximate_points_3d:
            raise ValueError("Network has no unknown (approximate) 3D points to adjust")

        point_nums = sorted(self.approximate_points_3d.keys())
        n_unknowns = len(point_nums) * 3  # X, Y, Z per point

        # Count observation rows: GPS baselines contribute 3 rows each
        n_obs = 0
        for obs in self.observations:
            if isinstance(obs, GpsBaselineObservation):
                n_obs += 3
            else:
                raise ValueError(
                    "Mixed 2D and GPS baseline observations are not yet supported. "
                    "Use a GPS-only network for 3D adjustment."
                )

        converged = False
        iteration = 0

        for iteration in range(1, max_iterations + 1):
            A = np.zeros((n_obs, n_unknowns))
            W = np.zeros((n_obs, n_obs))
            l_vec = np.zeros(n_obs)

            row = 0
            for obs in self.observations:
                if isinstance(obs, GpsBaselineObservation):
                    pi = self._get_point_3d(obs.from_point)
                    pj = self._get_point_3d(obs.to_point)

                    # Computed baseline
                    computed_dx = pj[0] - pi[0]
                    computed_dy = pj[1] - pi[1]
                    computed_dz = pj[2] - pi[2]

                    # Misclosures
                    l_vec[row] = obs.dx - computed_dx
                    l_vec[row + 1] = obs.dy - computed_dy
                    l_vec[row + 2] = obs.dz - computed_dz

                    # Jacobian: identity partials
                    idx_i = self._param_index_3d(obs.from_point, point_nums)
                    idx_j = self._param_index_3d(obs.to_point, point_nums)

                    if idx_i is not None:
                        A[row, idx_i] = -1.0
                        A[row + 1, idx_i + 1] = -1.0
                        A[row + 2, idx_i + 2] = -1.0
                    if idx_j is not None:
                        A[row, idx_j] = 1.0
                        A[row + 1, idx_j + 1] = 1.0
                        A[row + 2, idx_j + 2] = 1.0

                    # Weight matrix (3x3 block)
                    if obs.covariance is not None:
                        W_block = np.linalg.inv(obs.covariance)
                    else:
                        w = 1.0 / (obs.std_dev ** 2)
                        W_block = np.diag([w, w, w])

                    W[row:row + 3, row:row + 3] = W_block
                    row += 3

            # Normal equations
            AtW = A.T @ W
            N_mat = AtW @ A
            n_vec = AtW @ l_vec

            try:
                delta = np.linalg.solve(N_mat, n_vec)
            except np.linalg.LinAlgError:
                break

            # Update approximate coordinates
            for i, pn in enumerate(point_nums):
                x, y, z = self.approximate_points_3d[pn]
                self.approximate_points_3d[pn] = (
                    x + delta[3 * i],
                    y + delta[3 * i + 1],
                    z + delta[3 * i + 2],
                )

            # Check convergence
            max_delta = max(abs(delta[i]) for i in range(n_unknowns))
            if max_delta < convergence:
                converged = True
                break

        # Final residuals
        residuals_vec = A @ delta - l_vec
        residuals = residuals_vec.tolist()

        # Degrees of freedom
        dof = n_obs - n_unknowns

        if dof > 0:
            vtwv = float(residuals_vec.T @ W @ residuals_vec)
            reference_variance = vtwv / dof
        else:
            reference_variance = 0.0

        # Standard errors
        std_errors: dict[int, tuple[float, float]] = {}
        try:
            Qxx = np.linalg.inv(N_mat)
            variance_factor = max(reference_variance, 1e-30)
            for i, pn in enumerate(point_nums):
                var_x = abs(Qxx[3 * i, 3 * i]) * variance_factor
                var_y = abs(Qxx[3 * i + 1, 3 * i + 1]) * variance_factor
                # Report horizontal-ish std errors as (X, Y) for now
                std_errors[pn] = (math.sqrt(var_x), math.sqrt(var_y))
        except np.linalg.LinAlgError:
            for pn in point_nums:
                std_errors[pn] = (0.0, 0.0)

        # Build 3D adjusted points (ECEF)
        adjusted_3d: dict[int, tuple[float, float, float]] = {}
        for pn, xyz in self.fixed_points_3d.items():
            adjusted_3d[pn] = xyz
        for pn, xyz in self.approximate_points_3d.items():
            adjusted_3d[pn] = xyz

        # Also build 2D adjusted_points dict by converting ECEF -> geodetic -> Point
        adjusted_points: dict[int, Point] = {}
        for pn, (x, y, z) in adjusted_3d.items():
            lat, lon, h = ecef_to_geodetic(x, y, z)
            adjusted_points[pn] = Point(
                northing=math.degrees(lat),
                easting=math.degrees(lon),
                elevation=h,
                number=pn,
            )

        return AdjustmentResult(
            adjusted_points=adjusted_points,
            residuals=residuals,
            std_errors=std_errors,
            reference_variance=reference_variance,
            iterations=iteration,
            converged=converged,
            adjusted_points_3d=adjusted_3d,
        )
