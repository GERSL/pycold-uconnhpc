#!/bin/sh
##SBATCH --partition=generalsky
#SBATCH --partition=parallel
##SBATCH --account=osgusers
##SBATCH --partition=OSGPriority
#SBATCH --ntasks=40
#SBATCH --time=6:00:00                              # Job should run for up to 1.5 hours (for example)
#SBATCH --mail-type=END                              # Event(s) that triggers email notification (BEGIN,END,FAIL,ALL)
#SBATCH --exclude=cn355,cn406,cn217,cn373,cn67,cn87,cn376,cn68,cn116,cn338,cn330,cn398,cn346,cn364,cn368,cn400,cn329,cn333


tile_id="18TYM"
working_dir="/scratch/suy20004/suy20004"
yaml_path="/home/suy20004/Document/pycold-uconnhpc/config_hls.yaml"
reference_path="/home/suy20004/HLS.L30.T18TYM.2022074T153249.v2.0.B10.tif"

stack_path="$working_dir/${tile_id}_stack"
reccg_path="$working_dir/${tile_id}_sccd"
out_path="$working_dir/${tile_id}_sccd"

# module purge
# module load gcc/5.4.0-alt sqlite/3.18.0 tcl/8.6.6.8606 zlib/1.2.11 libjpeg-turbo/1.5.90 openssl/1.0.2o libcurl/7.60.0 jasper/1.900.1 proj/4.9.3 szip/2.1.1 hdf4/4.2.13 java/1.8.0_162 mpi/openmpi/3.1.0-gcc hdf5/1.10.2-gcc-openmpi netcdf/4.6.1-gcc-openmpi geos/3.5.0 gdal/2.2.0
# module load zlib/1.2.11
# module load java/1.8.0_162
# module load gsl/2.4
# module load sqlite/3.18.0 tcl/8.6.6.8606 gcc/5.4.0-alt zlib/1.2.11 java/1.8.0_162 mpi/openmpi/3.1.3
# module load glib/2.14
# module load mpi/openmpi/4.0.3
# source /home/suy20004/miniconda3/etc/profile.d/conda.sh
# conda activate pycold_py38

module purge
module load gsl/2.4
module load proj/4.9.2 geos/3.5.0 mpi/openmpi/2.1.0 libjpeg-turbo/1.1.90 hdf5/1.8.19 netcdf/4.4.1.1-ompi-2.1.0 expat/2.2.0 gdal/2.2.1
module load sqlite/3.18.0 tcl/8.6.6.8606 gcc/5.4.0-alt zlib/1.2.11 java/1.8.0_162 mpi/openmpi/3.1.3 python/3.6.8


mpirun python3 /home/suy20004/Document/pycold/src/python/pycold/imagetool/ExportChangeMap.py --reccg_path=$reccg_path --reference_path=$reference_path --out_path=$out_path --yaml_path=$yaml_path --year_lowbound=2015 --year_uppbound=2021 --method="SCCDOFFLINE"
