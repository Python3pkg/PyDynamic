# -*- coding: utf-8 -*-
"""
    Fit of a FIR filter to a simulated reciprocal frequency response of a
    second-order dynamic system. The deconvolution filter is applied to the
    simulated response of the system to a shock-like Gaussian signal.
    In this example uncertainties associated with the simulated system are
    propagated to the estimate of the input signal.

"""
import numpy as np
import scipy.signal as dsp
import matplotlib.pyplot as plt

import PyDynamic.deconvolution.fit_filter as deconv
from PyDynamic.misc.SecondOrderSystem import sos_phys2filter
from PyDynamic.misc.testsignals import shocklikeGaussian
from PyDynamic.misc.filterstuff import kaiser_lowpass, db
from PyDynamic.uncertainty.propagate_filter import FIRuncFilter
from PyDynamic.misc.tools import make_semiposdef

rst = np.random.RandomState(10)

##### FIR filter parameters
N = 12  # filter order
tau = 6 # time delay

# parameters of simulated measurement
Fs = 500e3
Ts = 1 / Fs

# sensor/measurement system
f0 = 36e3; uf0 = 0.01*f0
S0 = 0.124; uS0= 0.001*S0
delta = 0.0055; udelta = 0.1*delta

# transform continuous system to digital filter
bc, ac = sos_phys2filter(S0,delta,f0)
b, a = dsp.bilinear(bc, ac, Fs)

# simulate input and output signals
time = np.arange(0, 4e-3 - Ts, Ts)
x = shocklikeGaussian(time, t0 = 2e-3, sigma = 1e-5, m0=0.8)
y = dsp.lfilter(b, a, x)
noise = 1e-3
yn = y + np.random.randn(np.size(y)) * noise

# Monte Carlo for calculation of unc. assoc. with [real(H),imag(H)]
runs = 10000
MCS0 = S0 + rst.randn(runs)*uS0
MCd  = delta+ rst.randn(runs)*udelta
MCf0 = f0 + rst.randn(runs)*uf0
f = np.linspace(0, 120e3, 200)
HMC = np.zeros((runs, len(f)),dtype=complex)
for k in range(runs):
    bc_,ac_ = sos_phys2filter(MCS0[k], MCd[k], MCf0[k])
    b_,a_ = dsp.bilinear(bc_,ac_,Fs)
    HMC[k,:] = dsp.freqz(b_,a_,2*np.pi*f/Fs)[1]

Hc = np.mean(HMC,dtype=complex,axis=0)
H = np.r_[np.real(Hc), np.imag(Hc)]
UH= np.cov(np.c_[np.real(HMC),np.imag(HMC)],rowvar=0)
UH= make_semiposdef(UH)
# Calculation of FIR deconvolution filter and its assoc. unc.
bF, UbF = deconv.LSFIR_unc(H,UH,N,tau,f,Fs)

# correlation of filter coefficients
CbF = UbF/(np.tile(np.sqrt(np.diag(UbF))[:,np.newaxis],(1,N+1))*
		   np.tile(np.sqrt(np.diag(UbF))[:,np.newaxis].T,(N+1,1)))

# Deconvolution Step1: lowpass filter for noise attenuation
fcut = f0+20e3; low_order = 100
blow, lshift = kaiser_lowpass(low_order, fcut, Fs)
shift = -tau - lshift
# Deconvolution Step2: Application of deconvolution filter
xhat,Uxhat = FIRuncFilter(yn,noise,bF,UbF,shift,blow)


# Plot of results
fplot = np.linspace(0, 80e3, 1000)
Hc = dsp.freqz(b,a, 2*np.pi*fplot/Fs)[1]
Hif = dsp.freqz(bF, 1.0, 2 * np.pi * fplot / Fs)[1]
Hl = dsp.freqz(blow, 1.0, 2 * np.pi * fplot / Fs)[1]

plt.figure(1); plt.clf()
plt.plot(fplot*1e-3, db(Hc), fplot*1e-3, db(Hif*Hl), fplot*1e-3, db(Hc*Hif*Hl))
plt.legend(('System freq. resp.', 'compensation filter','compensation result'))
# plt.title('Amplitude of frequency responses')
plt.xlabel('frequency / kHz',fontsize=22)
plt.ylabel('amplitude / dB',fontsize=22)
plt.tick_params(which="both",labelsize=16)

fig = plt.figure(2);plt.clf()
ax = fig.add_subplot(1,1,1)
plt.imshow(UbF,interpolation="nearest")
plt.colorbar(ax=ax)
# plt.title('Uncertainty of deconvolution filter coefficients')

plt.figure(3); plt.clf()
plt.plot(time*1e3,np.c_[x,yn,xhat])
plt.legend(('input signal','output signal','estimate of input'))
# plt.title('time domain signals')
plt.xlabel('time / ms',fontsize=22)
plt.ylabel('signal amplitude / au',fontsize=22)
plt.tick_params(which="both",labelsize=16)
plt.xlim(1.5,4)
plt.ylim(-0.41,0.81)

plt.figure(4);plt.clf()
plt.plot(time*1e3,Uxhat)
# plt.title('Uncertainty of estimated input signal')
plt.xlabel('time / ms',fontsize=22)
plt.ylabel('signal uncertainty / au',fontsize=22)
plt.subplots_adjust(left=0.15,right=0.95)
plt.tick_params(which='both', labelsize=16)
plt.xlim(1.5,4)

plt.figure(5);plt.clf()
plt.errorbar(list(range(N+1)), bF, np.sqrt(np.diag(UbF)))

plt.show()
