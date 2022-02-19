import os, sys

# script to find the gaps in the downloaded data

suffices = [ '_QA.tar', '_TA.tar', '_SR.tar', '_BT.tar', '_ST.tar', '.jpg', '.xml' ]
missing = []

files = os.listdir("/home/ubuntu/landsat_tars")
for f in files:
    i = -1
    for suffex in suffices:
        try:
            i = f.rindex(suffex)
        except:
            pass
    if i == -1:
        print("unknown file: %s !" % f, file=sys.stderr)
        continue
    file = f[0:i]
    if file in missing:
        # already found it as missing, skip
        continue
    for suffex in suffices:
        check = os.path.join("/home/ubuntu/landsat_tars", file + suffex)
        if not os.path.exists(check):
            entity_id = file[0:24] + file[33:]
            missing.append(file)
            print(entity_id)
            break
