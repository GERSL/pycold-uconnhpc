#! /bin/bash

# variable inputs
h="003"
v="004"
method="COLD"

if [ "$1" == "c" ] # stacking + pycold + exportmaps
then
    RES=$(sbatch submit_prepareard.sh $h $v)
    jid1=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_prepareard.sh was submitted: $jid1"
    
    RES=$(sbatch --dependency=afterok:$jid1 submit_tileprocessing.sh $h $v $method)
    jid2=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_tileprocessing.sh was submitted: $jid2"
    
    RES=$(sbatch --dependency=afterok:$jid2 submit_exportChangeMap.sh $h $v $method)
    jid3=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_exportChangeMap.sh was submitted: $jid3"
else  # pycold + exportmaps
    RES=$(sbatch submit_tileprocessing.sh $h $v $method)
    jid2=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_tileprocessing.sh was submitted: $jid2"
    
    RES=$(sbatch --dependency=afterok:$jid2 submit_exportChangeMap.sh $h $v $method)
    jid3=${RES##* }  # ${RES##* } isolates out the last word
    echo "submit_exportChangeMap.sh was submitted: $jid3"
fi

exit 0
