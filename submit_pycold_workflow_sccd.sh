#!/bin/bash
##SBATCH --partition=generalsky                         # Name of Partition
#SBATCH --partition=EpycPriority
#SBATCH --account=zhz18039
##SBATCH --account=osgusers
##SBATCH --partition=OSGPriority
##SBATCH --partition=generalepyc                         # Name of Partition
##SBATCH --share
#SBATCH --ntasks=1
#SBATCH --time=12:00:00                              # Job should run for up to 1.5 hours (for example)
#SBATCH --array 1-200
#SBATCH --mail-type=END                              # Event(s) that triggers email notification (BEGIN,END,FAIL,ALL)
##SBATCH --exclude=cn[66-69,71-136,325-328,376]
#SBATCH --exclude=cn355,cn406,cn217,cn373,cn67,cn87,cn376,cn68,cn116,cn338,cn330,cn398,cn346,cn364,cn368 


h="030"
v="006"
data_dir="/shared/cn449/DataLandsatARDCONUS"
working_dir="/scratch/suy20004/suy20004"
yaml_path="/home/suy20004/Document/pycold-uconnhpc/config.yaml"

source_path="$data_dir/h${h}v${v}"
stack_path="$working_dir/h${h}v${v}_stack"
result_path="$working_dir/h${h}v${v}_sccdresults"
seedmap_path="/home/suy20004/lcmap_lc2001/LCMAP_CU_2001_V01_LCPRI_${h}${v}.tif"

module purge
# load commonly-used module
module load gcc/5.4.0-alt sqlite/3.18.0 tcl/8.6.6.8606 zlib/1.2.11 libjpeg-turbo/1.5.90 openssl/1.0.2o libcurl/7.60.0 jasper/1.900.1 proj/4.9.3 szip/2.1.1 hdf4/4.2.13 java/1.8.0_162 mpi/openmpi/3.1.0-gcc hdf5/1.10.2-gcc-openmpi netcdf/4.6.1-gcc-openmpi geos/3.5.0 gdal/2.2.0
module load zlib/1.2.11
module load java/1.8.0_162
module load gsl/2.4

source /home/suy20004/miniconda3/etc/profile.d/conda.sh
conda activate pycold_py37
python3 pycold_workflow.py --rank=$SLURM_ARRAY_TASK_ID --n_cores=$SLURM_ARRAY_TASK_MAX --result_path=$result_path --seedmap_path=$seedmap_path --stack_path=$stack_path --yaml_path=$yaml_path --method='SCCDOFFLINE' --upper_datebound=737790
