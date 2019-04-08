#!/usr/bin/env python

import numpy as np
from LLC_Membranes.analysis.rdf import System
from LLC_Membranes.llclib import file_rw
import matplotlib.pyplot as plt
import names

def calculate_rdf(res, path, gro='berendsen.gro', traj='PR_nojump.xtc', atoms=None):

	print('Calculating RDF of residue %s' % r)
	if atoms is not None:
		rdf = System('%s/%s' %(path, gro), '%s/%s' %(path, traj), r, 'HII', atoms=atoms)
	else:
		rdf = System('%s/%s' %(path, gro), '%s/%s' %(path, traj), r, 'HII')

	rdf.radial_distribution_function(bins=50, spline=True, npts_spline=10, cut=1.5)

	rdf.bootstrap(200)
	
	file_rw.save_object(rdf, '%s/rdf_%s.pl' % (path, res))

	return rdf

recalculate = False 
residues = ["DMS", "ATO"]
residues = ["SOH", "GCL"]
residues = ["THF", "PCB", "EAC", "DMF"]
residues = ["MET", "BUT"]
wt=10
n = np.zeros(len(residues))

for i, r in enumerate(residues):
	print(i, r)
	path = "/home/bcoscia/Documents/Gromacs/Transport/NaGA3C11/%s/%dwt" %(r,wt)

	if recalculate:
		rdf = calculate_rdf(r, path)
	else:
		try:
			rdf = file_rw.load_object('%s/rdf_%s.pl' %(path, r))
		except FileNotFoundError:
			rdf = calculate_rdf(r, path)

	zbox = rdf.t.unitcell_vectors[:, 2, 2].mean()
	mean = rdf.density.mean(axis=0)
	V = np.array([zbox * mean[i] * np.pi*(rdf.r[i + 1] ** 2 - rdf.r[i] ** 2) for i in range(len(rdf.r) - 1)])
	plt.plot(V)

plt.ylabel('Density', fontsize=14)
plt.xlabel('Distance from pore center (nm)', fontsize=14)
plt.gcf().get_axes()[0].tick_params(labelsize=14)
plt.legend(fontsize=14)
plt.tight_layout()
plt.show()