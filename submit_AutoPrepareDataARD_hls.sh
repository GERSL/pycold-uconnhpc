#!/bin/bash
##SBATCH --partition=generalsky                         # Name of Partition
#SBATCH --partition=EpycPriority
#SBATCH --account=zhz18039
#SBATCH --ntasks=1                                # Request 256 CPU cores
#SBATCH --time=12:00:00                              # Job should run for up to 1.5 hours (for example)
#SBATCH --array 1-100
#SBATCH --mail-type=END                              # Event(s) that triggers email notification (BEGIN,END,FAIL,ALL)
#SBATCH --exclude=cn355,cn406,cn217,cn373,cn67,cn87,cn376,cn68,cn448

tile_id="18TYM"
data_dir="/scratch/suy20004/suy20004/meta"
yaml_path="/home/suy20004/Document/pycold-uconnhpc/config_hls.yaml"

source_path="$data_dir/${tile_id}"
stack_path="/scratch/suy20004/suy20004/${tile_id}_stack"
pycold_path='/home/suy20004/Document/pycold'

module purge
module load gsl/2.4
# load commonly-used module
module load gcc/5.4.0-alt sqlite/3.18.0 tcl/8.6.6.8606 zlib/1.2.11 libjpeg-turbo/1.5.90 openssl/1.0.2o libcurl/7.60.0 jasper/1.900.1 proj/4.9.3 szip/2.1.1 hdf4/4.2.13 java/1.8.0_162 mpi/openmpi/3.1.0-gcc hdf5/1.10.2-gcc-openmpi netcdf/4.6.1-gcc-openmpi geos/3.5.0 gdal/2.2.0
module load zlib/1.2.11
module load java/1.8.0_162
module load gsl/2.4

source /home/suy20004/miniconda3/etc/profile.d/conda.sh
conda activate pycold_py38

python3 $pycold_path/src/python/pycold/imagetool/AutoPrepareDataARD.py --source_dir=$source_path --out_dir=$stack_path --rank=$SLURM_ARRAY_TASK_ID --n_cores=$SLURM_ARRAY_TASK_MAX --yaml_path=$yaml_path --collection=HLS
