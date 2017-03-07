#!/usr/bin/env python

"""
Calculate the tilt angle of alkyl chains
"""

import argparse
import numpy as np
import mdtraj as md
import itertools
import copy
import math
import matplotlib.pyplot as plt
from matplotlib import animation
import MDAnalysis as mda


def initialize():

    parser = argparse.ArgumentParser(description='Calculate the tilt angle of alkyl tails')

    parser.add_argument('-g', '--gro', default='wiggle.gro', help='Name of coordinate file')
    parser.add_argument('-t', '--traj', default='wiggle.trr', help='Trajectory file (.xtc or .trr)')
    parser.add_argument('-i', '--index', default='index.ndx', help='Index file containing groups used to measure tilt'
                        'angle. Each group should have a header line of the format [ groupname ]. The following line '
                        'should list the atoms in the order of their connectivity Each grouped should be separated by a '
                        'blank line')
    parser.add_argument('-o', '--output', default='tilt.png', type=str, help='Name of plot to be saved')
    parser.add_argument('-s', '--save', help='Save angle array', action="store_true")
    parser.add_argument('-l', '--load', help='Load previously saved angle array', action="store_true")
    parser.add_argument('--single_frame', help='Specify this for a single frame', action="store_true")
    parser.add_argument('--noshow', help='Specify this flag if you do not want to see the output plot', action="store_true")

    args = parser.parse_args()

    return args


def read_index(index):
    """
    :param index: index file
    Format: (1) Each group has a title formatted as follows: [ groupname ]
            (2) The line following each title should have the name of the atoms in each group written in order of their
            connectivity. They should all be contained on a single line
            (3) Each group should be separated by a blank line
    :return: index groups
    """

    grps = []
    sections = 0
    with open(index, 'r') as f:
        for line in f:
            if line.count('[ '):
                sections += 1
            elif line != "\n":
                grps.append(line.split())

    return grps


def angles(pos, atoms, normal=[0, 0, -1]):
    """
    :param pos: xyz positions of atoms in tail
    :param atoms: number of atoms
    :param normal: the normal vector to the plane with respect to which we will take an angle measurement
    :return: the angle distribution at each frame
    """

    normal = np.array(normal)
    nT = pos.shape[0]
    natoms = pos.shape[1]
    chains = natoms / atoms
    w = np.zeros([nT, chains])

    for i in range(nT):
        for j in range(chains):
            avg_tilt = 0
            for k in range(atoms - 1):  # atoms - 1 since there are n - 1 relevant vector in a straight chain
                v = pos[i, j*atoms + k, :] - pos[i, j*atoms + k + 1, :]
                vn = abs(np.dot(v, normal))
                nn = np.linalg.norm(normal)
                vv = np.linalg.norm(v)
                avg_tilt += np.arcsin(vn / (nn * vv)) * (180 / np.pi)
            avg_tilt /= (atoms - 1)
            w[i, j] = avg_tilt

    return w


if __name__ == "__main__":

    args = initialize()

    grps = read_index(args.index)
    ngrps = len(grps)

    # atoms = list(itertools.chain.from_iterable(grps))

    if args.load:
        all_tilt_angles = np.load('angles')
        times = np.load('times')
        print 'arrays loaded'
    else:
        if args.single_frame:
            traj = md.load('%s' % args.gro)
        else:
            traj = md.load('%s' % args.traj, top='%s' % args.gro)
        times = traj.time
        nT = times.shape[0]
        for i in range(ngrps):
            atoms = grps[i]
            keep = [a.index for a in traj.topology.atoms if a.name in atoms]  # restrict trajectory to chosen atoms
            t = traj.atom_slice(keep)  # NOTE: it's probably just luck that the atoms are written in order of their
                                    # connectivity. A reordering function may be necessary in the future
            pos = t.xyz  # get just the coordinates
            if i == 0:
                all_tilt_angles = angles(pos, len(atoms))
            else:
                tilt_angles_grp = angles(pos, len(atoms))
                all_tilt_angles = np.concatenate((all_tilt_angles, tilt_angles_grp), axis=1)

        if args.save:
            with open('angles', 'w') as f:
                np.save(f, all_tilt_angles)
            with open('times', 'w') as f:
                np.save(f, times)
            print "Arrays saved"

    if args.single_frame:
        # a = all_tilt_angles[0, :20]
        # b = np.zeros([a.shape[0] - 1])
        # for i in range(a.shape[0] - 1):
        #     b[i] = a[i + 1] - a[i]
        # print b
        print "Average Angle: %s +/- %s degrees" % (np.mean(all_tilt_angles[0, :]), np.std(all_tilt_angles[0, :]))
    else:
        nT = all_tilt_angles.shape[0]
        avgs = np.zeros([nT])
        stds = np.zeros([nT])

        for i in range(nT):
            stds[i] = np.std(all_tilt_angles[i, :])
            avgs[i] = np.mean(all_tilt_angles[i, :])

        print np.mean(avgs[nT/2:])
        print np.mean(stds[nT/2:])
        # Format and save figure
        plt.figure()
        plt.errorbar(times, avgs, yerr=stds)
        plt.title('Tilt angle versus time')
        plt.xlabel('Time (ps)')
        plt.ylabel('Tilt angle w.r.t xy plane (degrees)')
        plt.savefig(args.output)
        if not args.noshow:
            plt.show()