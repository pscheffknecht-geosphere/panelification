from __future__ import print_function
import os
import time


rows, cols = os.popen('stty size', 'r').read().split()

def progress_print(ii, imax, label="Hello! "):
    nmax = int(cols)-len(label)-3
    n = int((ii)/float(imax)*nmax)
    print("\r"+label+"["+n*"="+(nmax-n)*" "+"]",end=' ')


def double_progress_print(ii, imax, jj, jmax):
    mmax = int((int(cols)-17)/2)
    m = int((ii)/float(imax)*mmax)
    nmax = int(cols)-17 - mmax
    n = int((jj)/float(jmax)*nmax)
    return_str = "\rHello ["+n*"="+(nmax-n)*" "+"]["+m*"="+(mmax-m)*" "+"] there"
    return return_str


def main():
    for ii in range(300):
        progress_print(ii, 299)
        time.sleep(0.005)
    for ii in range(30):
        for jj in range(50):
            strr = double_progress_print(ii, 29, jj, 49)
            print(strr, end='')
            time.sleep(0.002)
    print(" ")


if __name__ == "__main__":
    main()
