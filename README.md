# pycold-uconnhpc

# A script repo for applying pycold package in UCONN HPC environment
### Author: Su Ye (remotesensingsuy@gmail.com)

## Before you use....

I am a big fan of conda because it is always easier to install pre-compiled than compiling everything from sources (especially for gdal library), while I did see many people prefer pip than conda for its high-level flexibility. The below are only based on my experience with conda. At least, it worked.

If you are Window system user and choose python as your primary programming language, Cygwin terminal (https://www.cygwin.com/) is recommended, as other window-based terminals such as Mobabus may have issues with Jupyter notebook connection.  Another advantage of using CLI-based terminal than GUI-based is CLI-based terminal often incorporates many useful softwares such as git and conda, where you can better keep up with modern computational technology. 

## Step 1: locally install conda

As UCONN set http restriction in login node as well as HPC team suggests using conda in a newer redhat version (i.e, Skylake, EPYCPriority, and OSGPriority), we need an interactive mode to locally install conda (e.g., calling 6 cores from EPYCPriority node):

```
fisbatch -n 6 --partition=EpycPriority --nodelist=cn449 --account=zhz18039
```

Then download conda installation files

```
curl -L -O https://repo.anaconda.com/miniconda/Miniconda3-py37_4.9.2-Linux-x86_64.sh

bash Miniconda3-py37_4.9.2-Linux-x86_64.sh -b -p ~/miniconda3
```

With Miniconda installed to your home directory, export PATH, so that it may be used:

```
export PATH=$HOME/miniconda3/bin:$PATH*
```

Create the gdal miniconda environment to support python 3.7

```
conda create -n pycold_py37 python=3.7
```

The terminal might prompt you on what Terminal Setting you are using.

Select the **BASH** option (should be the first option)

Once the above installs and sets up, **EXIT** out of the node, resubmit the Fisbatch job from the first step, and your terminal should change to look like the following:

(base) [yournetidhere@cnXX ~]$ (where XX is the compute node)

Once you are set up with the above syntax, miniconda has been set up successfully.

Then you can activate the gdal instance you created:

```
conda activate pycold_py37
```



## Step 2: install pycold

clone repo from our lab github page (assuming you are still in the interactive model, and git can't be supported in the login node)

```
git clone https://github.com/GERSL/pycold/pycold.git
```

cd to the repo, load all essential modules and activate pycold environment

```
cd pycold
module load gcc/5.4.0-alt sqlite/3.18.0 tcl/8.6.6.8606 zlib/1.2.11 libjpeg-turbo/1.5.90 openssl/1.0.2o libcurl/7.60.0 jasper/1.900.1 proj/4.9.3 szip/2.1.1 hdf4/4.2.13 java/1.8.0_162 mpi/openmpi/3.1.0-gcc hdf5/1.10.2-gcc-openmpi netcdf/4.6.1-gcc-openmpi geos/3.5.0 gdal/2.2.0 
module load zlib/1.2.11
module load java/1.8.0_162
module load gsl/2.4
conda activate pycold_py37
```

install requirements

```
pip install -r requirements.txt
pip install -e .
# have to install gdal separately using conda, no better solution so far
conda install gdal
```

install pycold in development mode (The benefit you get from developers mode is that when you make a change to Python code, you see that change immediately when you rerun the program )

```
bash run_developer_setup.sh
```

A quick test using python console

```python
import pycold
```

** Note that the pycold can be only successfully installed in OCX and Linux platform temporally. I encounterred a compiler issue in the Window system, and will work on Window platform later this year.



## Step 3: uconn_hpc_pycold package for production

Clone and install requirements:

```
git clone https://github.com/GERSL/uconn_hpc_pycold/uconn_hpc_pycold.git
cd uconn_hpc_pycold
conda activate pycold_py37
conda install --file requirements.txt
```

#### config.yaml

The package relies on config.yaml to control configuration. Just change it as you need. There are seven configs so far:

- n_rows: the row number of the dataset 

- n_cols: the col number of the dataset

- n_block_x: the block number along with x axis. 

- n_block_y: the block number along with y axis

- probability_threshold: change probability, default is 0.99 

- conse: consecutive number of observation for change decision

- CM_OUTPUT_INTERVAL:  interval days for outputing change magnitudes, only useful for OBCOLD

*Different with MATLAB version that uses scanline as processing unit, the whole software use a square-like block as parallelization unit; this way can greatly reduce disk by eliminating those blocks that has all invalid pixels or cloud/shadow blocks. As a result, it only only need ~300 GB space for stacking files, and also much faster for deleting the files.*

#### submit_AutoPrepareDataARD_template.sh

A script for submitting the stacking job. Please firstly rename it to **submit_AutoPrepareDataARD.sh**. The reason for doing this is I already add submit_AutoPrepareDataARD.sh to .gitignore, so the next time you pull from the recent git repo, your slurm files won't be overwritten.

```
mv submit_AutoPrepareDataARD_template.sh submit_AutoPrepareDataARD.sh
```

To use it, you need to change the below two lines:

```
working_dir="/scratch/your_scratch_folder"   # the place to save the result folder
yaml_path="/home/your_home_folder/uconn_hpc_pycold/config.yaml"   # the path of your config yaml
```

Then run the below slurm command (027 is ARD tile h; 015 is ARD tile v):
```
sbatch submit_AutoPrepareDataARD.sh 027 015
```
This job typically took 15 mins  to finish (200 cores, skylake or EpycPriority nodes); you will see a folder named 'h * v * _stack' created in working_dir.

#### submit_pycold_workflow_template.sh: 

A script for submitting the COLD algorithm job. Again, please rename it to **submit_AutoPrepareDataARD.sh** first. To use it, you need to change the same four lines in **submit_pycold_workflow.sh**. 

```
working_dir="/scratch/your_scratch_folder"   # the place to save the result folder
yaml_path="/home/your_home_folder/uconn_hpc_pycold/config.yaml"   # the path of your config yaml
```

```
sbatch submit_pycold_workflow.sh 027 015
```



This process typically took 1-1.5 hours to finish (200 cores, skylake or EpycPriority nodes); you will see a folder named 'h * v * _results' created in working_dir.

#### submit_exportChangeMap_template.sh 

a script for submitting a job for exporting change map. Rename it to **submit_exportChangeMap.sh**, and then change the below our lines:

```
reccg_path="/scratch/your_scratch_folder/h${h}v${v}_results"  # change it pointed to your scratch folder
reference_path="/home/your_home_folder/lcmap_lc2001/LCMAP_CU_2001_V01_LCPRI_${h}${v}.tif"   # a reference image that the program can grab georeference for the outputted image.
out_path="/scratch/your_scratch_folder/h${h}v${v}_results"  # the place to save the result folder
yaml_path="/home/your_home_folder/Document/uconn_hpc_pycold/config.yaml"  # yaml folder
```

```
sbatch submit_exportChangeMap.sh 027 015
```

The outputted map will be saved in "/scratch/suy20004/h${h}v${v}_results/cold_maps"

### pipeline_pycold.sh

A script that does stacking and COLD in a sequence:



Other notes:

* After you change the above files for the first time, you only need to change 'h' and 'v' for the next time to point to your interested tiles, so it is very easy to use.

* Feel free to add '\#SBATCH --mail-user=' into the slurm files if you want to receive email notification.

## Other examples for pycold

#### A jupyter notebook for displaying time series and break from a csv-based time series

In pycold repo: tool/notebook/pycold_example.ipynb



#### A jupyter notebook for displaying time series and break for any pixel from Landsat ARD (coming soon)



