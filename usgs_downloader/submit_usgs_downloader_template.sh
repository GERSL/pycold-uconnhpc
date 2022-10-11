#!/bin/bash
##SBATCH --partition=generalsky                         # Name of Partition
#SBATCH --partition=EpycPriority
#SBATCH --account=zhz18039
#SBATCH --ntasks=12                                # Request 256 CPU cores
#SBATCH --time=48:00:00                              # Job should run for up to 1.5 hours (for example)
#SBATCH --mail-type=END                              # Event(s) that triggers email notification (BEGIN,END,FAIL,ALL)
#SBATCH --exclude=cn355,cn406,cn217,cn373,cn67,cn87,cn376,cn68


module purge
# load commonly-used module
module load gcc/5.4.0-alt sqlite/3.18.0 tcl/8.6.6.8606 zlib/1.2.11 libjpeg-turbo/1.5.90 openssl/1.0.2o libcurl/7.60.0 jasper/1.900.1 proj/4.9.3 szip/2.1.1 hdf4/4.2.13 java/1.8.0_162 mpi/openmpi/3.1.0-gcc hdf5/1.10.2-gcc-openmpi netcdf/4.6.1-gcc-openmpi geos/3.5.0 gdal/2.2.0
module load zlib/1.2.11
module load java/1.8.0_162
module load gsl/2.4
source /home/suy20004/Document/pipenv/ts-py38/bin/activate

python usgs_downloader.py -u *** -p *** -d /shared/cn450/suuuuuu/p123r031 -f ./example_filter.json --filter-is-path -t 4 -m 10000 -c landsat_ot_c2_l2
