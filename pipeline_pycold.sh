#! /bin/bash

# variable inputs
h="029"   # change accordingly, horizontal id of the ARD tile
v="006"   # change accordingly, vertical id of the ARD tile
method="OBCOLD"   # change accordingly options can be OBCOLD, COLD and SCCD
yaml_path="/home/suy20004/Document/pycold-uconnhpc/config.yaml"  # change accordingly, parameter configuration
pycold_path='/home/suy20004/Document/pycold'  # change accordingly, pycold package path
working_dir="/scratch/suy20004/suy20004"   # change accordingly, the path to save stack and result files,
                                          # the program output will be 1) 'working_dir/h029v006_stack' and 2) 'working_dir/h029v006_results'
pip_env="/home/suy20004/Document/pipenv/ts-py38" # change accordingly, pip environment path

#data_dir="/shared/cn449/DataLandsatARDCONUS"  # no need to change, the old path
data_dir="/shared/cn449/CT_ARD"  # no need to change

if [ "$1" == "c" ] # stacking + pycold + exportmaps
then
    RES=$(sbatch submit_prepareard_pipe.sh $h $v $working_dir $data_dir $yaml_path $pycold_path $pip_env)
    jid1=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_prepareard_pipe.sh was submitted: $jid1"
    
    RES=$(sbatch --dependency=afterok:$jid1 submit_tileprocessing_pipe.sh $h $v $method $working_dir $yaml_path $pycold_path $pip_env)
    jid2=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_tileprocessing_pipe.sh was submitted: $jid2"
    
    RES=$(sbatch --dependency=afterok:$jid2 submit_exportChangeMap_pipe.sh $h $v $method $working_dir $yaml_path $pycold_path)
    jid3=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_exportChangeMap_pipe.sh was submitted: $jid3"
else  # pycold + exportmaps
    RES=$(sbatch submit_tileprocessing_pipe.sh $h $v $method $working_dir $yaml_path $pycold_path $pip_env)
    jid2=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_tileprocessing_pipe.sh was submitted: $jid2"
    
    RES=$(sbatch --dependency=afterok:$jid2 submit_exportChangeMap_pipe.sh $h $v $method $working_dir $yaml_path $pycold_path)
    jid3=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_exportChangeMap_pipe.sh was submitted: $jid3"
fi

exit 0
