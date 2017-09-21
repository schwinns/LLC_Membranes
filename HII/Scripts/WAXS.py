#!/usr/bin/env python

import matplotlib
matplotlib.rc('axes', color_cycle=['r', 'g', 'b', '#004060'])
import numpy as np
import matplotlib.pyplot as plt
import math


waxs = np.load('WAXS.npy')

center = np.array([530, 473])
hw = 400  # height and width (pixels)
r_high = hw - 155
r_low = hw - 215
bins = 180

waxs = waxs[center[0]-hw:center[0]+hw, center[1]-hw:center[1]+hw]

qpi = 1.7  # q value of pi-stacking reflection
axial = np.copy(waxs[:, int(waxs.shape[0]/2)])  # hold x constant at the center, and get all y values. The array is of the shape [y, x]
mid = axial.shape[0] / 2
axial[(mid - 150):(mid + 150)] = 0  # zero out middle values so we get the right maximum
Imax = np.amax(axial)  # max value of Intensity. It will correspond to location of pi-stacking reflection
Imax_pixel = np.where(axial == Imax)[0][0]
pixel_to_q = 1.7 / abs(mid - Imax_pixel)
qmax = mid*pixel_to_q

# The raw data contains super high intensity specs and some intensity near the center that is meant to be blocked out
# I zero out all of those so that the highest intensity is in the pi-stacking reflection.
for i in range(23):
    m = np.amax(waxs)
    x = np.where(waxs == m)[0][0]
    y = np.where(waxs == m)[1][0]
    waxs[x, y] = 0

fig, ax = plt.subplots()
waxs /= np.amax(waxs)  # normalize with respect to highest intensity in pi-stacking reflection
# plt.imshow(waxs, cmap='jet', extent=[-qmax, qmax, -qmax, qmax])
# plt.xlabel('$q_r$', fontsize=14)
# plt.ylabel('$q_z$', fontsize=14)
# plt.gcf().get_axes()[0].tick_params(labelsize=14)
# fig.savefig('raw_WAXS.png')
# fig.clf()
# #plt.show()
# exit()
x = np.linspace(-qmax, qmax, 2*hw)
y = np.linspace(qmax, -qmax, 2*hw)
xx, yy = np.meshgrid(x, y)

plt.pcolormesh(xx, yy, waxs, cmap='jet')
plt.gcf().get_axes()[0].set_ylim(-2.5, 2.5)
plt.gcf().get_axes()[0].set_xlim(-2.5, 2.5)
plt.gcf().get_axes()[0].set_xlabel('$q_r$', fontsize=14)
plt.gcf().get_axes()[0].set_ylabel('$q_z$', fontsize=14)
plt.gcf().get_axes()[0].set_aspect('equal')
plt.gcf().get_axes()[0].tick_params(labelsize=14)
fig.savefig('raw_WAXS.png')
fig.clf()
# plt.show()
exit()
angles = np.zeros([bins])
norm = np.zeros([bins])
ring = np.zeros_like(waxs)

for i in range(waxs.shape[0]):
    for j in range(waxs.shape[1]):
        if r_high > np.linalg.norm([i - hw, j - hw]) > r_low:
            ring[i, j] = waxs[i, j]
            v = np.array([hw, hw]) - np.array([i, j])
            if v[1] != 0:
                angle = np.arctan(float(v[0])/float(v[1])) * (180/np.pi)
                # This appears to be arctan(x/y) but the way I'm using the numpy matrix here, the x coordinate actually
                # represents the y component and vice versa. Here is an example: Consider the 3x3 matrix:
                # [ 1 2 3 ]     If we write the indices in    [(0, 0), (0, 1), (0, 2)]
                # [ 4 5 6 ]     place of the entries it       [(1, 0), (1, 1), (1, 2)]
                # [ 7 8 9 ]     looks like:                   [(2, 0), (2, 1), (2, 2)]
                # If I use the coordinates as unit distances, as I do above, I can measure the angle between points as
                # arctan(y/x). If I am interested in specifically the angle between (0,0) and (2,1) w.r.t. the
                # horizontal, then the y displacement is 2 and the x displacement is 1. The angle is arctan(2/1) = 63.
                # notice that 2 corresponds to the first entry of (2,1) which is typically thought of as x and 1
                # corresponds to the second entry which is typically though of as y.
            else:
                angle = 90

            bin = int((bins/2) + ((angle/90)*(bins/2)))
            if bin == bins:
                bin -= 1

            angles[bin] += waxs[i, j]
            norm[bin] += 1


avg = angles / norm  # normalize intensities so it is on a per count basis
angles = np.linspace(-90, 90, bins + 1)  # We will only see angles in the range of -90 to 90 since we use np.arctan
bin_angles = [(angles[i] + angles[i + 1])/2 for i in range(bins)]  # bars will be placed in the middle of the bins
width = angles[1] - angles[0]  # width of bins

print(np.max(avg) / np.mean(avg))

plt.bar(bin_angles, avg, width=width)
plt.show()

# plt.imshow(ring, vmax=0.05)
# plt.show()
