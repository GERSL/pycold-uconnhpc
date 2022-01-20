# pycold-uconnhpc

# A script repo for applying pycold package in UCONN HPC environment

### Author: Su Ye (remotesensingsuy@gmail.com)

## Before you use....

I am a big fan of conda because it is always easier to install pre-compiled than compiling everything from sources, while I did see many people prefer pip than conda for its high-level flexibility and to pursue the most up-to-date package version. I did encounter package conflict issues when I mixed using conda and pip. So to guarantee everything working in UCONN HPC, I sugggest using pip install consistently, except for using conda to set up virtual environment and install gdal (see the below details).

If you are Window system user and choose python as your primary programming language, you may consider choosing Cygwin terminal (https://www.cygwin.com/), as other GUI-based terminals such as MobaXterm may have issues with Jupyter notebook connection.  CLI-based terminal often incorporates many modern computing tools such as git and conda so that you don't need to switch terminals, while GUI-based may be more native to window users. It is up to you.

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

Again you need to request an interative node if you are in login node. UCONN HPC set http restriction for login node, so you can't get access to github (which is annoying!).

```
fisbatch -n 6 --partition=EpycPriority --nodelist=cn449 --account=zhz18039
```

If you haven't set up your GitHub account in HPC, please set up the configuration first. 

```
config --global user.name "SuYe99"   # put your username
```

You also need to generate your personal token, and github doesn't accept password since 2021. You can check the steps in [personal token steps](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token). After your generating the token, copy your token to the place that you store keys.

Before you started cloning, first put the below line so that you just need to put your username and token for one time, and no need for future.

```
git config --global credential.helper store
```

clone repo from our lab github page, and it should prompt username and password (i.e., token) request as your first time set-up 

```
git clone https://github.com/GERSL/pycold.git
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
pip install --r requirements.txt
pip install -e .
```

install pycold in development mode (The benefit you get from developers mode is that when you make a change to Python code, you see that change immediately when you rerun the program )

```
bash run_developer_setup.sh
```

A quick test using python console

```python
import pycold
```

** Note that the pycold can be only successfully installed in OCX and Linux platform. I encounterred a compiler issue in the Window system, and will work on Window platform later this year.

#### (optional) update your local repo only when pycold is updated in the remote

```
git pull -f  
```



## Step 3: uconn_hpc_pycold package for production

Clone and install requirements:

```
git clone https://github.com/GERSL/pycold-uconnhpc.git
cd uconn_hpc_pycold
conda activate pycold_py37
pip install --r requirements.txt
# have to install gdal separately using conda, no better solution so far
conda install gdal
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

To use it, you need to change the below four lines:

```
h="027"   # the h id of your ard tile
v="009"    # the v id of your ard tile
working_dir="/scratch/your_scratch_folder"   # the place to save the result folder
yaml_path="/home/your_home_folder/uconn_hpc_pycold/config.yaml"   # the path of your config yaml
```

This job typically took 15 mins  to finish (200 cores, skylake or EpycPriority nodes); you will see a folder named 'h * v * _stack' created in working_dir.

#### submit_pycold_workflow_template.sh: 

A script for submitting the COLD algorithm job. Again, please rename it to **submit_AutoPrepareDataARD.sh** first. To use it, you need to change the same four lines in **submit_pycold_workflow.sh**. 

```
h="027"   # the h id of your ard tile
v="009"    # the v id of your ard tile
working_dir="/scratch/your_scratch_folder"   # the place to save the result folder
yaml_path="/home/your_home_folder/uconn_hpc_pycold/config.yaml"   # the path of your config yaml
```

To use Object-based COLD, just add --method='OB-COLD' into the end of 'python3 pycold_workflow.py ...' line. The program will generate an additional folder ('cm_maps') for change magnitude, direction and date snapshots 

This process typically took 1-1.5 hours to finish (200 cores, skylake or EpycPriority nodes); you will see a folder named 'h * v * _results' created in working_dir.

#### submit_exportChangeMap_template.sh 

a script for submitting a job for exporting change map. Rename it to **submit_exportChangeMap.sh**, and then change the below our lines:

```
h="027"  # the h id of your ard tile
v="009"   # the v id of your ard tile
reccg_path="/scratch/your_scratch_folder/h${h}v${v}_results"  # change it pointed to your scratch folder
reference_path="/home/your_home_folder/lcmap_lc2001/LCMAP_CU_2001_V01_LCPRI_${h}${v}.tif"   # a reference image that the program can grab georeference for the outputted image.
out_path="/scratch/your_scratch_folder/h${h}v${v}_results"  # the place to save the result folder
yaml_path="/home/your_home_folder/Document/uconn_hpc_pycold/config.yaml"  # yaml folder
```

The outputted map will be saved in "/scratch/suy20004/h${h}v${v}_results/cold_maps"

### pipeline_pycold.sh (Coming soon)

A script that does stacking and COLD in a sequence:



Other notes:

* After you change the above files for the first time, you only need to change 'h' and 'v' for the next time to point to your interested tiles, so it would be much easier to use after the first configuration was finished.

* Feel free to add '\#SBATCH --mail-user=' into the slurm files if you want to receive email notification.

## Other examples for pycold

#### A jupyter notebook for displaying time series and break from a csv-based time series

In pycold repo: tool/notebook/pycold_example.ipynb



#### A jupyter notebook for displaying time series and break for any pixel from Landsat ARD (coming soon)



