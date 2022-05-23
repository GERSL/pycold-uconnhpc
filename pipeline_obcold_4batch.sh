#! /bin/bash

# variable inputs
h="030"
v="006"
method="OBCOLD"

RES=$(sbatch submit_pycold_workflow.sh $h $v $method)
jid1=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_pycold_workflow.sh was submitted: $jid1"
    
RES=$(sbatch --dependency=afterok:$jid1 submit_exportChangeMap.sh $h $v $method)
jid2=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_exportChangeMap.sh was submitted: $jid2"


h="021"
v="008"
RES=$(sbatch --dependency=afterok:$jid2 submit_pycold_workflow.sh $h $v $method)
jid3=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_pycold_workflow.sh was submitted: $jid3"

RES=$(sbatch --dependency=afterok:$jid3 submit_exportChangeMap.sh $h $v $method)
jid4=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_exportChangeMap.sh was submitted: $jid4"


h="021"
v="015"
RES=$(sbatch --dependency=afterok:$jid4 submit_pycold_workflow.sh $h $v $method)
jid5=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_pycold_workflow.sh was submitted: $jid5"

RES=$(sbatch --dependency=afterok:$jid5 submit_exportChangeMap.sh $h $v $method)
jid6=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_exportChangeMap.sh was submitted: $jid6"


h="014"
v="006"
RES=$(sbatch --dependency=afterok:$jid6 submit_pycold_workflow.sh $h $v $method)
jid7=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_pycold_workflow.sh was submitted: $jid7"

RES=$(sbatch --dependency=afterok:$jid7 submit_exportChangeMap.sh $h $v $method)
jid8=${RES##* }  # ${RES##* } isolates out the last word
echo "submit_exportChangeMap.sh was submitted: $jid8"

exit 0
