#!/bin/bash
##SBATCH --partition=generalsky                         # Name of Partition
#SBATCH --partition=EpycPriority
#SBATCH --account=zhz18039
## SBATCH --ntasks=1                                # Request 256 CPU cores
#SBATCH --time=12:00:00                              # Job should run for up to 1.5 hours (for example)
#SBATCH --array 1-200
#SBATCH --mail-type=END                              # Event(s) that triggers email notification (BEGIN,END,FAIL,ALL)
#SBATCH --exclude=cn355,cn406,cn217,cn373,cn67,cn87,cn376,cn68


h="027"   # the h id of your ard tile
v="009"    # the v id of your ard tile
working_dir="/scratch/your_scratch_folder"   # the place to save the result folder
yaml_path="/your_pycold-uconnhpc_path/pycold-uconnhpc/config.yaml"
pycold_path="/your_pycold_path/pycold"
data_dir="/shared/cn449/DataLandsatARDCONUS"


source_path="$data_dir/h${h}v${v}"
stack_path="$working_dir/h${h}v${v}_stack"

module purge
# load commonly-used module
module load gcc/5.4.0-alt sqlite/3.18.0 tcl/8.6.6.8606 zlib/1.2.11 libjpeg-turbo/1.5.90 openssl/1.0.2o libcurl/7.60.0 jasper/1.900.1 proj/4.9.3 szip/2.1.1 hdf4/4.2.13 java/1.8.0_162 mpi/openmpi/3.1.0-gcc hdf5/1.10.2-gcc-openmpi netcdf/4.6.1-gcc-openmpi geos/3.5.0 gdal/2.2.0
module load zlib/1.2.11
module load java/1.8.0_162
module load gsl/2.4
source /home/suy20004/Document/pipenv/ts-py38/bin/activate

python3 $pycold_path/src/python/pycold/imagetool/prepare_ard.py --source_dir=$source_path --out_dir=$stack_path --rank=$SLURM_ARRAY_TASK_ID --n_cores=$SLURM_ARRAY_TASK_MAX --yaml_path=$yaml_path --h
