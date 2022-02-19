#!/bin/bash

if [[ $# -ge 2 ]]
then

USER=$1 # your m2m user
PASS=$2 # your m2m pass
MAX_RESULTS=50000 # maximum number of search results (excludes scenes provided directly with the --scenes option)
MAX_THREADS=4 # maximum number of threads used
OUTPUT_DIR=/tmp/landsat_tars # folder to put the landsat tars in

# Download scenes using a filter
python usgs_downloader.py -u "$USER" -p "$PASS" -d "$OUTPUT_DIR" \
	-f ./example_filter.json --filter-is-path -m $MAX_RESULTS -t $MAX_THREADS

# Locate and download the gaps in the data
#python find_missing_files.py > missing.txt
#python usgs_downloader.py -u $USER -p $PASS -d ./landsat_tars --scenes ./missing.txt
#rm missing.txt

else

echo "Please provide a username and password (eg '$0 \"username\" \"password\"')"

fi
