#t-SNE

##Problem 27-29
To run t-SNE on a large number of data samples, an optimized version of the algorithms is necessary. Having a runtime of O(n²) the standard algorithms is to expensive for large datasets, as e.g. required for Problem 29.

"bhtsne.py" contains an implementation of the Barnes-Hut-SNE algorithm using the BH-SNE implementation and the python wrapper from "http://lvdmaaten.github.io/tsne". Before execution, the BH-SNE implementation must be compiled by the commando:

g++ sptree.cpp tsne.cpp -o bh_tsne -O2

Information about compiling in Windows can be found here: https://github.com/lvdmaaten/bhtsne/

The algorithms can be executed for the MNIST-dataset with the method "produce_MNIST_plot(n_samples=None, fancy_markers=False, output_name='plot.png')". It performs BH-SNE as described in the paper and saves the results in a plot.

n_samples: number of samplex, which are used in the algorithms. If the value is "None", all samples are used.
fancy_markers: Flag that specifies the design of the result plot. If the flag is false, a colourfull scatterplot is produced. If it is true, a plot with the imput data as markers analogous to figure 5 of the paper is produced.
output_name: File name of the result plot
 
The following table contains execution times for different numbers of samples:

| n_samples | execution time | time per sample |
|-----------|----------------|-----------------|
|  1000     |      7.1 s     |       0.0071    |
| 10000     |    240.3 s     |       0.02403   |
| 50000     |   2825.1 s     |       0.0565    |

The table shows clearly that the complexity of the algorithms scales definetly slower than quadratic. More detailled or quantitative meassures are difficult due to unstable ressource conditions on my laptop (background programmes, varying availability of main memmory, etc). A second execution with all samples for examples took 3172 seconds (variation of 12% compared to the first execution).


The plots "tsne_mnist_fancy.png" and "tsne_mnist_scatter.png" show the result plots of executions with all data points:

<p align="center">
  <img src="tsne_mnist_fancy.png" width="500"/>
  <img src="tsne_mnist_scatter.png" width="500"/>
</p>


