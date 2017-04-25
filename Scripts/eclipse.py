#! /usr/bin/env python

"""
Calculate the degree to which benzene rings are stacked. 0 implies no stacking, while 1 implies perfect stacking,
i.e. one benzene ring completely eclipses the ring below
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import path
import mdtraj as md
from scipy.spatial import ConvexHull
import warnings
import lc_class
from llclib import physical

warnings.filterwarnings("ignore")  # Couldn't get this to work: http://docs.python.org/2/library/warnings.html#temporarily-suppressing-warnings


def initialize():

    parser = argparse.ArgumentParser(description = 'Crosslink LLC structure')  # allow input from user

    parser.add_argument('-t', '--traj', default='traj_whole.xtc', help='Name of trajectory file (.xtc or .trr).'
                'Preprocess trajectory with -pbc nojump using gmx trjconv to minimize annoying jumps across boundaries.'
                'You will not see much of a difference from just using -pbc whole.')
    parser.add_argument('-g', '--gro', default='wiggle.gro', help='Name of coordinate file (.gro)')
    parser.add_argument('-b', '--build_mon', default='NAcarb11V', help='Class of monomer used to build structure')
    parser.add_argument('--single_frame', action="store_true", help='Only looking at a single frame')

    args = parser.parse_args()

    return args


def ccw(A,B,C):
    """
    Taken from here: http://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    """
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])


def intersect(A,B,C,D):
    """
    Return true if line segments AB and CD intersect
    Taken from here: http://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    """
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)


def slope(pt1, pt2):

    m = (pt1[1] - pt2[1]) / (pt1[0] - pt2[0])
    b = pt1[1] - m * pt1[0]

    return m, b


def intersection(A,B,C,D):
    """
    :param A: point 1 in vector 1
    :param B: point 2 in vector 1
    :param C: point 1 in vector 2
    :param D: point 2 in vector 2
    :return: The point of intersection (if there is one) or else return False
    """

    if ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D):  # if this is true, the lines intersect

        m1, b1 = slope(A, B)
        m2, b2 = slope(C, D)

        if abs(m2) == float('inf'):  # slope is infinite meaning pt1[x] = pt2[x]
            x_intersect = C[0]
            y_intersect = m1 * x_intersect + b1
        elif abs(m1) == float('inf'):  # same but for other line
            x_intersect = A[0]
            y_intersect = m2 * x_intersect + b2
        else:  # a normal case
            x_intersect = (b1 - b2) / (m2 - m1)
            y_intersect = m1 * x_intersect + b1

        return [x_intersect, y_intersect]

    else:
        return False  # case where they do not intersect


def overlap_pts(shape1, shape2, sides=6):

    pts = np.zeros([sides*2, 2])  # the max number of pts making up the intersecting polygon is somewhere around this. I'll fix it when it fails
    count = 0
    for i in range(sides):
        for j in range(sides):
            pt = intersection(shape1[i - 1, :], shape1[i, :], shape2[j - 1, :], shape2[j, :])
            if pt:
                pts[count, :] = pt
                count += 1

    # xyverts1 = np.array(box1)
    # xyverts2 = np.array(box2)
    # create matplotlib path objects that defines the two benzene rings as polygon l in 2D
    p1 = path.Path(shape1)
    p2 = path.Path(shape2)

    for i in range(shape2.shape[0]):
        if p1.contains_point(shape2[i, :]):
            pts[count, :] = shape2[i, :]
            count += 1
        if p2.contains_point(shape1[i, :]):
            pts[count, :] = shape1[i, :]
            count += 1

    return pts[~np.all(pts == 0, axis=1)]  # get rid of excess zeros


def order_pts(pts):
    """
    Create a convex polygon given unordered vertices
    See: http://scipy.github.io/devdocs/generated/scipy.spatial.ConvexHull.html
    :param pts: unordered points making up convex polygon vertices
    :return: vertices in counterclockwise order
    """

    hull = ConvexHull(pts)

    pts_ordered = np.zeros(pts.shape)
    count = 0
    for vertex in hull.vertices:
        pts_ordered[count, :] = [pts[vertex, 0], pts[vertex, 1]]
        count += 1

    return pts_ordered


def PolyArea(x,y):
    """
    Find area of polygon given an ordered set of vertices using the shoelace formula
    Code from : http://stackoverflow.com/questions/24467972/calculate-area-of-polygon-given-x-y-coordinates
    Basd on shoelace formula: https://en.wikipedia.org/wiki/Shoelace_formula
    :param x: numpy array of x coordinates
    :param y: numpy array of y coordinates
    :return: Area made by polygon formed from points fed to the function
    """
    return 0.5*np.abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))


def overlap(poly1, poly2):

    pts = overlap_pts(poly1, poly2)

    if pts.size > 4:
        pts_ordered = order_pts(pts)
        overlap_area = PolyArea(pts_ordered[:, 0], pts_ordered[:, 1])
    else:
        overlap_area = 0

    return overlap_area


def ring_centers(all_pos, natoms=6):
    """
    :param all_pos: positions of all atoms in rings
    :param natoms: number of atoms in each ring (default = 6 for benzene)
    :return:
    """

    nT = all_pos.shape[0]  # number of trajectory points
    nrings = all_pos.shape[1] / natoms  # number of rings in the system

    ring_center = np.zeros([nT, nrings, 3])  # new array with only the average positions of each benzene ring

    for t in range(nT):
        for i in range(nrings):
            for j in range(natoms):
                ring_center[t, i, :] += all_pos[t, i*natoms + j, :]
            ring_center[t, i, :] /= natoms  # average the locations

    return ring_center


def pbz(pos, box, pores=4):
    """
    Make a periodic image of the position in the +z and -z directions. Instead of just duplicating, the list will be
    restructured so there is continuity in each pore region. i.e. the order of the positions will go from lowest z to
    highest z before moving to the next pore. We are essentially tripling the system size
    :param pos: positions to be copied in the +/- z direction
    :param box: unit cell vectors
    :return: new list of positions
    """

    nT = pos.shape[0]
    npos = pos.shape[1]
    posppore = npos / 4

    newpos = np.zeros([nT, 3*npos, 3])
    z = [-1, 0, 1]
    for t in range(nT):
        zbox = np.linalg.norm(box[t, 2, :])  # z box dimension
        for p in range(pores):
            for j in range(len(z)):
                for i in range(posppore):
                    newpos[t, p*posppore*len(z) + j*posppore + i] = pos[t, p*posppore + i, :] + [0, 0, z[j]*zbox]

    return newpos


def overlap_pairs(centers, pores=4, layers=20, layersearch=1):
    """
    :param centers: positions of the centers of all rings extended periodically using pbz() function
    :param pores: number of pores in unit cell
    :param layers: number of layers in initial system build
    :param layersearch: number of layers deep to look for stacking
    :return: A trajectory of ring pairs. Index i corresponds to one ring. The entry at i corresponds to its pair
    """

    nT = centers.shape[0]  # number of trajectory points
    rings = centers.shape[1]  # number of rings in 'centers'
    real_rings = rings/3  # the total number of rings, not including periodic duplications
    real_rings_ppore = real_rings / pores  # number of rings per pore
    ring_per_layer = real_rings_ppore / layers  # monomers per layer

    pairs = np.zeros([nT, real_rings], dtype=int)  # dictionary of closest stacked pairs

    for t in range(nT):
        for p in range(pores):
            for i in range(real_rings + p*real_rings_ppore, real_rings + (p + 1)*real_rings_ppore):  # looking only at the rings in the original structure
                distances = np.zeros([ring_per_layer*layersearch])  # neglects rings position above ring i in the initial configuration
                shift = i % ring_per_layer  # how many rings into the layer are we?
                for j in range(distances.shape[0]):
                    distances[j] = np.linalg.norm(centers[t, i, :] - centers[t, i - shift - j - 1, :])

                ring_pair = i - shift - real_rings - np.argmin(distances) - 1

                if ring_pair < 0:
                    ring_pair += real_rings

                pairs[t, i - real_rings] = ring_pair

    return pairs


def all_overlaps(pos, pairs, atoms_p_ring=6):
    """
    :param pos: trajectory of positions of points making up rings
    :param pairs: pairs of rings whose overlaps will be compared
    :param natoms: number of atoms in a ring
    :return: the total area of overlap
    """

    nT = pos.shape[0]
    natoms = pos.shape[1]
    rings = natoms / atoms_p_ring

    area = np.zeros([nT])
    for t in range(nT):
        for i in range(rings):
            ring1_no = i
            ring2_no = pairs[t, i]
            ring1 = np.zeros([atoms_p_ring, 2])
            ring2 = np.zeros([atoms_p_ring, 2])
            for j in range(atoms_p_ring):
                ring1[j, :] = pos[t, ring1_no*atoms_p_ring + j, :2]
                ring2[j, :] = pos[t, ring2_no*atoms_p_ring + j, :2]
            area[t] += overlap(ring1, ring2)  # add overlap area to total overlap

    return area


if __name__ == "__main__":

    args = initialize()

    lc = lc_class.LC('%s.gro' % args.build_mon)

    benzene_c = lc.benzene_carbons

    if not args.single_frame:
        t = md.load(args.traj, top=args.gro)
    else:
        t = md.load(args.gro)

    box = t.unitcell_vectors

    keep = [a.index for a in t.topology.atoms if a.name in benzene_c]
    pos = t.atom_slice(keep).xyz

    centers = ring_centers(pos)

    periodic = pbz(centers, box)

    pairs = overlap_pairs(periodic)

    overlap_area = all_overlaps(pos, pairs)

    # Area of a single benzene ring - calculated separately based on a perfect hexagon with C-C bond length = .14 nm
    # benzene_area = 0.0497955083847  # nm^2 -- calculated using PolyArea and vertices of benzene from an initial config created with build.py
    benzene_area = 0.0509222937  # nm^2 -- based on a perfect hexagon with C-C bond length = .14 nm
    total_benzene_area = pos.shape[1] / len(benzene_c) * benzene_area

    plt.plot(t.time, 100 * overlap_area / total_benzene_area)
    plt.title('Degree of sandwiched stacking vs time')
    plt.xlabel('Time (ps)')
    plt.ylabel('Degree of layering (%)')
    plt.show()