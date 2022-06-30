#!/bin/sh
#SBATCH --partition=parallel
##SBATCH --account=osgusers
##SBATCH --partition=OSGPriority
#SBATCH --ntasks=50
#SBATCH --time=6:00:00                              # Job should run for up to 1.5 hours (for example)
#SBATCH --mail-type=END                              # Event(s) that triggers email notification (BEGIN,END,FAIL,ALL)

h="027"
v="009"
method="COLD"
reccg_path="/scratch/your_scratch_folder/h${h}v${v}_results"
reference_path="/home/your_home_folder/lcmap_lc2001/LCMAP_CU_2001_V01_LCPRI_${h}${v}.tif"
out_path="/scratch/your_scratch_folder/h${h}v${v}_results"
yaml_path="/home/your_home_folder/Document/pycold-uconnhpc/config.yaml"
pycold_path='/home/your_home_folder/pycold'



module purge
module load gsl/2.4
module load proj/4.9.2 geos/3.5.0 mpi/openmpi/2.1.0 libjpeg-turbo/1.1.90 hdf5/1.8.19 netcdf/4.4.1.1-ompi-2.1.0 expat/2.2.0 gdal/2.2.1
module load sqlite/3.18.0 tcl/8.6.6.8606 gcc/5.4.0-alt zlib/1.2.11 java/1.8.0_162 mpi/openmpi/3.1.3 python/3.6.8 
# source /home/suy20004/miniconda3/etc/profile.d/conda.sh
# conda activate pycold

mpirun python3 $pycold_path/src/python/pycold/imagetool/exportChangeMap.py --reccg_path=$reccg_path --reference_path=$reference_path --out_path=$out_path --method=$method --yaml_path=$yaml_path
