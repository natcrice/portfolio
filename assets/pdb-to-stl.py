"""
PDB to STL Converter - Uniform Double Strand Mode
Converts a DNA origami PDB file into a 3D-printable STL file.
Each atom (P and C1') is represented as a small sphere.
Supports both planar (flat) and 3D structures via automatic planarity detection.
"""
import numpy as np
from stl import mesh   # numpy-stl: used to write the final STL file
import trimesh         # used to repair mesh after writing (fix normals, fill holes)
import os

# ── Input/Output paths ────────────────────────────────────────────────────────
INPUT_PDB  = "../input_files/ShortenedBundle.pdb"
OUTPUT_STL = "../output_files/FlatDoubleStranded.stl"

# ── Default parameters (may be overridden by auto-scale below) ────────────────
TARGET_SIZE_MM       = 300    # longest dimension of the printed model in mm
P_SPHERE_RADIUS_MM   = 0.5   # radius of spheres placed at phosphate (P) atoms
C1_SPHERE_RADIUS_MM  = 0.5   # radius of spheres placed at sugar (C1') atoms
SPHERE_STACKS = 3             # vertical subdivisions per sphere (more = rounder, slower)
SPHERE_SLICES = 4             # horizontal subdivisions per sphere (more = rounder, slower)

# ── Double-strand parameters ──────────────────────────────────────────────────
STRAND_OFFSET    = 20.0   # Angstroms: offset applied to duplicate non-scaffold atoms
                           # to simulate the complementary strand of the double helix

# ── Flattening parameters (used only for planar structures) ───────────────────
Z_SCALE          = 0.5    # compress Z axis to reduce helix wave height
DEWARP_RADIUS_MM = 12.0   # XY radius (mm) used to compute local Z average for dewarping
Z_FLOOR_MM       = 0.75   # remove atoms below this Z height (trims bottom outliers)
Z_CEIL_MM        = 4.5    # remove atoms above this Z height (trims top outliers)

# ── Planarity detection threshold ─────────────────────────────────────────────
# Ratio of smallest to 2nd-smallest PCA eigenvalue.
# Low ratio = structure is flat (planar); high ratio = structure is 3D.
PLANARITY_THRESHOLD = 0.05


# ── STEP 1: Read atoms from PDB file ─────────────────────────────────────────
def read_pdb_atoms(path):
    """
    Parses the PDB file and extracts 3D coordinates of P and C1' atoms.
    For non-scaffold models (model != 1), each atom is duplicated with a
    Y-offset (STRAND_OFFSET) to represent the complementary DNA strand.
    Returns two numpy arrays: p_pos and c1_pos.
    """
    print(f"\n[1/5] Reading PDB: {path}")
    p_pos, c1_pos = [], []
    current_model = None
    in_model = False
    duplicated = 0
    with open(path) as f:
        for line in f:
            record = line[:6].strip()
            if record == "MODEL":
                current_model = int(line.split()[1])
                in_model = True
            elif record == "ENDMDL":
                in_model = False
            elif record == "ATOM" and in_model:
                atom_name = line[12:16].strip()
                if atom_name in ("P", "C1'"):
                    try:
                        x = float(line[30:38])
                        y = float(line[38:46])
                        z = float(line[46:54])
                        # Add original atom
                        if atom_name == "P":
                            p_pos.append([x, y, z])
                        else:
                            c1_pos.append([x, y, z])
                        # Duplicate non-scaffold atoms with Y offset (double strand)
                        if current_model != 1:
                            if atom_name == "P":
                                p_pos.append([x, y + STRAND_OFFSET, z])
                            else:
                                c1_pos.append([x, y + STRAND_OFFSET, z])
                            duplicated += 1
                    except ValueError:
                        pass
    p_pos  = np.array(p_pos,  dtype=np.float64)
    c1_pos = np.array(c1_pos, dtype=np.float64)
    print(f"      Total P atoms:    {len(p_pos)}")
    print(f"      Total C1' atoms:  {len(c1_pos)}")
    print(f"      Atoms duplicated: {duplicated}")
    return p_pos, c1_pos


# ── STEP 1b: Planarity detection ──────────────────────────────────────────────
def detect_planarity(all_pos, threshold):
    """
    Uses PCA (principal component analysis) on atom positions to determine
    whether the structure is flat or 3D.
    Computes the ratio of the smallest to 2nd-smallest eigenvalue of the
    covariance matrix. A very small ratio means one dimension is nearly
    zero — i.e., the structure lies in a plane.
    """
    center = all_pos.mean(axis=0)
    centered = all_pos - center
    cov = np.cov(centered.T)
    eigenvalues, _ = np.linalg.eigh(cov)
    ratio = eigenvalues[0] / eigenvalues[1]   # smallest / 2nd smallest
    print(f"      Planarity ratio: {ratio:.4f} (threshold: {threshold})")
    if ratio < threshold:
        print(f"      → Structure is PLANAR — flattening enabled")
        return True
    else:
        print(f"      → Structure is 3D — flattening disabled")
        return False


# ── STEP 2: PCA projection ────────────────────────────────────────────────────
def project_to_plane(all_pos):
    """
    Rotates the structure so its largest spread is along X, second along Y,
    and smallest along Z. This ensures the structure is optimally oriented
    for printing (flat structures lie flat, 3D structures align to longest axis).
    Uses PCA eigenvectors as the new coordinate axes.
    """
    print(f"\n[2/5] Plane projection...")
    center = all_pos.mean(axis=0)
    centered = all_pos - center
    cov = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    normal = eigenvectors[:, 0] / np.linalg.norm(eigenvectors[:, 0])  # smallest variance → Z
    axis1  = eigenvectors[:, 2]   # largest variance → X
    axis2  = eigenvectors[:, 1]   # 2nd largest → Y
    new_x  = centered @ axis1
    new_y  = centered @ axis2
    new_z  = centered @ normal
    result = np.column_stack([new_x, new_y, new_z])
    print(f"      Z range: {new_z.min():.1f} to {new_z.max():.1f} Angstroms")
    return result


# ── Flattening helpers (planar structures only) ───────────────────────────────
def local_dewarp(positions, radius_mm):
    """
    Removes large-scale Z warp by subtracting the local Z average from each atom.
    For each atom, finds all neighbors within radius_mm in XY, computes their
    average Z, and subtracts it. This flattens gradual bending without
    removing the fine helix spiral.
    """
    print(f"      Local Z dewarp (radius={radius_mm} mm)...")
    result = positions.copy()
    xy = positions[:, :2]
    r2 = radius_mm ** 2
    local_z_avg = np.zeros(len(positions))
    chunk = 128
    for start in range(0, len(positions), chunk):
        end = start + chunk
        q = xy[start:end]
        diff = xy[:, None, :] - q[None, :, :]
        d2 = (diff**2).sum(axis=2)
        for ci in range(len(q)):
            nbrs = np.where(d2[:, ci] <= r2)[0]
            local_z_avg[start + ci] = positions[nbrs, 2].mean()
    result[:, 2] -= local_z_avg
    print(f"      Z range after dewarp: {result[:,2].min():.1f} to {result[:,2].max():.1f} mm")
    return result


def global_flatten(positions):
    """
    Fits a least-squares plane to all atom positions and subtracts it.
    Removes any residual tilt left after local dewarping.
    """
    xy = positions[:, :2]
    z  = positions[:, 2]
    A  = np.column_stack([xy, np.ones(len(xy))])
    coeffs, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
    z_plane = A @ coeffs
    result  = positions.copy()
    result[:, 2] -= z_plane
    print(f"      Global flatten: removed tilt (max correction {np.abs(z_plane).max():.1f} mm)")
    return result


# ── STEP 3: Sphere mesh generation ───────────────────────────────────────────
def make_sphere(center, radius, stacks, slices):
    """
    Generates vertices and triangular faces for a single sphere.
    stacks = number of horizontal rings (latitude)
    slices = number of vertical segments (longitude)
    More stacks/slices = rounder sphere but more triangles.
    """
    verts = []
    for i in range(stacks + 1):
        phi = np.pi * i / stacks
        for j in range(slices):
            theta = 2 * np.pi * j / slices
            verts.append([
                center[0] + radius * np.sin(phi) * np.cos(theta),
                center[1] + radius * np.sin(phi) * np.sin(theta),
                center[2] + radius * np.cos(phi)
            ])
    verts = np.array(verts)
    faces = []
    for i in range(stacks):
        for j in range(slices):
            a = i * slices + j
            b = i * slices + (j + 1) % slices
            c = (i + 1) * slices + j
            d = (i + 1) * slices + (j + 1) % slices
            faces += [[a, b, d], [a, d, c]]
    return verts, np.array(faces)


def build_all_spheres(p_pos, c1_pos, p_r, c1_r, stacks, slices):
    """
    Builds the full mesh by placing a sphere at every atom position.
    P atoms and C1' atoms can have different radii.
    All sphere meshes are concatenated into one large vertex/face array.
    Note: overlapping spheres are NOT boolean-unioned — they remain as
    separate meshes, which can cause non-manifold edges where they intersect.
    """
    print(f"\n[3/5] Building spheres...")
    all_v, all_f, offset, done = [], [], 0, 0
    total = len(p_pos) + len(c1_pos)
    for pos in p_pos:
        v, f = make_sphere(pos, p_r, stacks, slices)
        all_v.append(v); all_f.append(f + offset)
        offset += len(v); done += 1
        if done % 4000 == 0:
            print(f"        {done}/{total}...")
    for pos in c1_pos:
        v, f = make_sphere(pos, c1_r, stacks, slices)
        all_v.append(v); all_f.append(f + offset)
        offset += len(v); done += 1
        if done % 4000 == 0:
            print(f"        {done}/{total}...")
    all_v = np.vstack(all_v)
    all_f = np.vstack(all_f)
    print(f"      Total: {len(all_v):,} vertices, {len(all_f):,} triangles")
    return all_v, all_f


# ── STEP 4: Write STL file ────────────────────────────────────────────────────
def export_stl(verts, faces, path):
    """
    Writes the mesh to a binary STL file using numpy-stl.
    Creates the output directory if it doesn't exist.
    """
    print(f"\n[4/5] Writing STL: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    m = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
    for i, face in enumerate(faces):
        for j in range(3):
            m.vectors[i][j] = verts[face[j]]
        if (i + 1) % 100_000 == 0:
            print(f"        triangle {i+1:,}/{len(faces):,}...")
    m.save(path)
    size_mb = os.path.getsize(path) / 1024 / 1024
    print(f"      Saved ({size_mb:.1f} MB)")
    return size_mb


# ── STEP 5: Mesh repair ───────────────────────────────────────────────────────
def repair_stl(path):
    """
    Loads the STL back with trimesh and attempts to repair common mesh errors:
    - fix_normals: ensures all triangle normals point outward consistently
    - fill_holes: patches any open boundary edges
    Reports whether the result is fully watertight (no non-manifold edges).
    A watertight mesh is required for auto-support generation in most slicers.
    """
    print(f"\n[5/5] Repairing mesh...")
    m = trimesh.load(path)
    trimesh.repair.fix_normals(m)
    trimesh.repair.fill_holes(m)
    m.export(path)
    print(f"      Repair done. Watertight: {m.is_watertight}")
    if not m.is_watertight:
        print(f"      Non-manifold edges remaining: {len(trimesh.graph.connected_components(m.edges))}")


# ── Main pipeline ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  PDB to STL - Uniform Double Strand Mode + Dewarp")
    print("=" * 60)

    # Read all atom positions from the PDB file
    p_pos, c1_pos = read_pdb_atoms(INPUT_PDB)

    # Auto-scale: choose model size and sphere radius based on atom count.
    # More atoms = denser structure = use smaller spheres / smaller model
    # to keep print time reasonable.
    total_atoms = len(p_pos) + len(c1_pos)
    if total_atoms > 35000:
        global TARGET_SIZE_MM, P_SPHERE_RADIUS_MM, C1_SPHERE_RADIUS_MM
        TARGET_SIZE_MM      = 250
        P_SPHERE_RADIUS_MM  = 0.4
        C1_SPHERE_RADIUS_MM = 0.4
    elif total_atoms > 15000:
        TARGET_SIZE_MM      = 150
        P_SPHERE_RADIUS_MM  = 1.25
        C1_SPHERE_RADIUS_MM = 1.25
    else:
        # Small structure: use smaller model so atoms are closer together
        # and spheres overlap enough to look cohesive
        TARGET_SIZE_MM      = 50
        P_SPHERE_RADIUS_MM  = 1.25
        C1_SPHERE_RADIUS_MM = 1.25
    print(f"      Auto-scale: {total_atoms} atoms → {TARGET_SIZE_MM}mm, sphere radius {P_SPHERE_RADIUS_MM}mm")

    # Detect whether the structure is flat (planar) or 3D
    all_pos = np.vstack([p_pos, c1_pos])
    is_planar = detect_planarity(all_pos, PLANARITY_THRESHOLD)

    # Rotate structure so largest spread = X axis, smallest = Z axis
    projected = project_to_plane(all_pos)

    # Shift so minimum coordinate is at origin, then scale to TARGET_SIZE_MM
    p_pos  = projected[:len(p_pos)]  - projected.min(axis=0)
    c1_pos = projected[len(p_pos):]  - projected.min(axis=0)
    scale  = TARGET_SIZE_MM / np.vstack([p_pos, c1_pos]).max(axis=0)[:2].max()
    p_pos  *= scale
    c1_pos *= scale

    if is_planar:
        # ── Flatten planar structures ──────────────────────────────────────
        print(f"\n      Applying Z scale ({Z_SCALE}) and dewarp...")

        # Shift Z to start at 0, then compress Z to reduce helix wave height
        p_pos[:,  2] -= p_pos[:, 2].min()
        c1_pos[:, 2] -= c1_pos[:, 2].min()
        p_pos[:,  2] *= Z_SCALE
        c1_pos[:, 2] *= Z_SCALE

        # Remove large-scale Z warp, then remove residual global tilt
        all_combined = np.vstack([p_pos, c1_pos])
        dewarped = local_dewarp(all_combined, DEWARP_RADIUS_MM)
        dewarped = global_flatten(dewarped)
        p_pos  = dewarped[:len(p_pos)]
        c1_pos = dewarped[len(p_pos):]

        # Shift Z back to 0 after dewarping
        z_min  = min(p_pos[:, 2].min(), c1_pos[:, 2].min())
        p_pos[:,  2] -= z_min
        c1_pos[:, 2] -= z_min

        # Remove atoms that are too low (bed adhesion outliers)
        if Z_FLOOR_MM > 0:
            p_keep  = p_pos[:,  2] >= Z_FLOOR_MM
            c1_keep = c1_pos[:, 2] >= Z_FLOOR_MM
            print(f"      Z floor: removed {(~p_keep).sum()} P and {(~c1_keep).sum()} C1' atoms below {Z_FLOOR_MM} mm")
            p_pos  = p_pos[p_keep]
            c1_pos = c1_pos[c1_keep]

        # Remove atoms that are too high (outlier spikes)
        if Z_CEIL_MM > 0:
            p_keep  = p_pos[:,  2] <= Z_CEIL_MM
            c1_keep = c1_pos[:, 2] <= Z_CEIL_MM
            print(f"      Z ceil:  removed {(~p_keep).sum()} P and {(~c1_keep).sum()} C1' atoms above {Z_CEIL_MM} mm")
            p_pos  = p_pos[p_keep]
            c1_pos = c1_pos[c1_keep]

    else:
        # ── 3D structure: no flattening, just shift Z to start at 0 ───────
        print(f"\n      Skipping Z scale and dewarp (3D structure)")
        z_min  = min(p_pos[:, 2].min(), c1_pos[:, 2].min())
        p_pos[:,  2] -= z_min
        c1_pos[:, 2] -= z_min

    # Print final bounding box dimensions
    final = np.vstack([p_pos, c1_pos]).max(axis=0)
    print(f"\n      Final: {final[0]:.0f} x {final[1]:.0f} x {final[2]:.0f} mm")

    # Build sphere mesh, write STL, repair mesh
    verts, faces = build_all_spheres(
        p_pos, c1_pos,
        P_SPHERE_RADIUS_MM, C1_SPHERE_RADIUS_MM,
        SPHERE_STACKS, SPHERE_SLICES
    )
    size_mb = export_stl(verts, faces, OUTPUT_STL)
    repair_stl(OUTPUT_STL)

    print(f"\n  File: {OUTPUT_STL}  ({size_mb:.1f} MB)")
    print(f"  Planar={is_planar}  DEWARP={DEWARP_RADIUS_MM}  Z_SCALE={Z_SCALE}  Z_FLOOR={Z_FLOOR_MM}  Z_CEIL={Z_CEIL_MM}")


if __name__ == "__main__":
    main()