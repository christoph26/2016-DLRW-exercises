#!/usr/bin/env python

'''
A simple Python wrapper for the bh_tsne binary that makes it easier to use it
for TSV files in a pipeline without any shell script trickery.

Note: The script does some minimal sanity checking of the input, but don't
    expect it to cover all cases. After all, it is a just a wrapper.

Example:

    > echo -e '1.0\t0.0\n0.0\t1.0' | ./bhtsne.py -d 2 -p 0.1
    -2458.83181442  -6525.87718385
    2458.83181442   6525.87718385

The output will not be normalised, maybe the below one-liner is of interest?:

    python -c 'import numpy; d = numpy.loadtxt("/dev/stdin");
        d -= d.min(axis=0); d /= d.max(axis=0);
        numpy.savetxt("/dev/stdout", d, fmt='%.8f', delimiter="\t")'

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2013-01-22
'''

# Copyright (c) 2013, Pontus Stenetorp <pontus stenetorp se>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from argparse import ArgumentParser, FileType
from os.path import abspath, dirname, isfile, join as path_join
from shutil import rmtree
from struct import calcsize, pack, unpack
from subprocess import Popen
from sys import stderr, stdin, stdout
from tempfile import mkdtemp
from load_data import load_data
import numpy as np
import pylab as plot
import timeit
from PIL import Image
from utils import scale_to_unit_interval


### Constants
BH_TSNE_BIN_PATH = path_join(dirname(__file__), 'bh_tsne')
assert isfile(BH_TSNE_BIN_PATH), ('Unable to find the bh_tsne binary in the '
    'same directory as this script, have you forgotten to compile it?: {}'
    ).format(BH_TSNE_BIN_PATH)
# Default hyper-parameter values from van der Maaten (2013)
DEFAULT_NO_DIMS = 2
DEFAULT_PERPLEXITY = 30.0
DEFAULT_THETA = 0.5
EMPTY_SEED = -1

###

def _argparse():
    argparse = ArgumentParser('bh_tsne Python wrapper')
    argparse.add_argument('-d', '--no_dims', type=int,
                          default=DEFAULT_NO_DIMS)
    argparse.add_argument('-p', '--perplexity', type=float,
            default=DEFAULT_PERPLEXITY)
    # 0.0 for theta is equivalent to vanilla t-SNE
    argparse.add_argument('-t', '--theta', type=float, default=DEFAULT_THETA)
    argparse.add_argument('-r', '--randseed', type=int, default=EMPTY_SEED)
    
    argparse.add_argument('-v', '--verbose', action='store_true')
    argparse.add_argument('-i', '--input', type=FileType('r'), default=stdin)
    argparse.add_argument('-o', '--output', type=FileType('w'),
            default=stdout)
    return argparse


class TmpDir:
    def __enter__(self):
        self._tmp_dir_path = mkdtemp()
        return self._tmp_dir_path

    def __exit__(self, type, value, traceback):
        rmtree(self._tmp_dir_path)


def _read_unpack(fmt, fh):
    return unpack(fmt, fh.read(calcsize(fmt)))

def bh_tsne(samples, no_dims=DEFAULT_NO_DIMS, perplexity=DEFAULT_PERPLEXITY, theta=DEFAULT_THETA, randseed=EMPTY_SEED,
        verbose=False, sample_dim=None):
    # Assume that the dimensionality of the first sample is representative for
    #   the whole batch
    if sample_dim is None:
        sample_dim = len(samples[0])
    sample_count = len(samples)

    # bh_tsne works with fixed input and output paths, give it a temporary
    #   directory to work in so we don't clutter the filesystem
    with TmpDir() as tmp_dir_path:
        # Note: The binary format used by bh_tsne is roughly the same as for
        #   vanilla tsne
        with open(path_join(tmp_dir_path, 'data.dat'), 'wb') as data_file:
            # Write the bh_tsne header
            data_file.write(pack('iiddi', sample_count, sample_dim, theta, perplexity, no_dims))
            # Then write the data
            for sample in samples:
                data_file.write(pack('{}d'.format(len(sample)), *sample))
            # Write random seed if specified
            if randseed != EMPTY_SEED:
                data_file.write(pack('i', randseed))

        # Call bh_tsne and let it do its thing
        with open('/dev/null', 'w') as dev_null:
            bh_tsne_p = Popen((abspath(BH_TSNE_BIN_PATH), ), cwd=tmp_dir_path,
                    # bh_tsne is very noisy on stdout, tell it to use stderr
                    #   if it is to print any output
                    stdout=stderr if verbose else dev_null)
            bh_tsne_p.wait()
            assert not bh_tsne_p.returncode, ('ERROR: Call to bh_tsne exited '
                    'with a non-zero return code exit status, please ' +
                    ('enable verbose mode and ' if not verbose else '') +
                    'refer to the bh_tsne output for further details')

        # Read and pass on the results
        with open(path_join(tmp_dir_path, 'result.dat'), 'rb') as output_file:
            # The first two integers are just the number of samples and the
            #   dimensionality
            result_samples, result_dims = _read_unpack('ii', output_file)
            # Collect the results, but they may be out of order
            results = [_read_unpack('{}d'.format(result_dims), output_file)
                for _ in xrange(result_samples)]
            # Now collect the landmark data so that we can return the data in
            #   the order it arrived
            results = [(_read_unpack('i', output_file), e) for e in results]
            # Put the results in order and yield it
            results.sort()
            for _, result in results:
                yield result
            # The last piece of data is the cost for each sample, we ignore it
            #read_unpack('{}d'.format(sample_count), output_file)

def produce_MNIST_plot(n_samples=None, fancy_markers=False, output_name='plot.png'):

    data, labels = load_data('mnist.pkl.gz')[0]

    if n_samples is not None:
        data = data[:n_samples]
        labels = labels[:n_samples]

    print('...bh tsne started')

    results = []
    start_time = timeit.default_timer()

    for result in bh_tsne(data):
        results = np.concatenate((results, np.asarray(result)))

    end_time = timeit.default_timer()
    print('The code run for %.1fs' % ((end_time - start_time)))

    results = np.reshape(results, (-1, 2))

    # normalize results
    res_min = np.min(results, axis=0)
    results = results - res_min
    res_max = np.max(results, axis=0)
    results = results / res_max

    if fancy_markers:
        picture_size=8000
        outarray = np.zeros((picture_size, picture_size), dtype='uint8')
        outarray[...] = 255

        for i in xrange(results.shape[0]):
            xpos = int(results[i][0] * (picture_size - 1000) + 500)
            ypos = int(results[i][1] * (picture_size - 1000) + 500)
            pic = scale_to_unit_interval(data[i].reshape((28,28)))
            pic = 1 - pic
            outarray[xpos:xpos + 28, ypos:ypos + 28] = pic * 255

        image = Image.fromarray(outarray)

        image.save(output_name)
    else:
        plot.scatter(results[:, 0], results[:, 1], 20, labels, marker='.', edgecolor='none')
        plot.savefig(output_name)

if __name__ == '__main__':
    produce_MNIST_plot(n_samples=10000, fancy_markers=True, output_name='mnist_plot_fancy.png')