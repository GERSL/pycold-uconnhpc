#! /bin/bash

# variable inputs
h="027"
v="019"
method="OBCOLD"

RES=$(sbatch submit_tileprocessing.sh $h $v $method)
jid1=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_tileprocessing.sh was submitted: $jid1"
    
RES=$(sbatch --dependency=afterok:$jid1 submit_exportChangeMap.sh $h $v $method)
jid2=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_exportChangeMap.sh was submitted: $jid2"


h="011"
v="009"
RES=$(sbatch --dependency=afterok:$jid2 submit_tileprocessing.sh $h $v $method)
jid3=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_tileprocessing.sh was submitted: $jid3"

RES=$(sbatch --dependency=afterok:$jid3 submit_exportChangeMap.sh $h $v $method)
jid4=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_exportChangeMap.sh was submitted: $jid4"


exit 0
