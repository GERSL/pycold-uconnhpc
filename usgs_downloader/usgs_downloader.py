"""
Machine-to-machine USGS data downloader

Based on and uses code from Dr. Su Ye's https://github.com/SuYe99/S-CCD/blob/53f23b5e22294d582dc8466ebdc03d22a032d6c2/tool/python/download_m2m.py
As well as the example code provided by USGS

Author: Ian Abrams

Dataset Name	Dataset ID
Landsat 5 TM Collection 1 Level 1	landsat_tm_c1
Landsat 5 TM Collection 2 Level 1	landsat_tm_c2_l1
Landsat 5 TM Collection 2 Level 2	landsat_tm_c2_l2
Landsat 7 ETM+ Collection 1 Level 1	landsat_etm_c1
Landsat 7 ETM+ Collection 2 Level 1	landsat_etm_c2_l1
Landsat 7 ETM+ Collection 2 Level 2	landsat_etm_c2_l2
Landsat 8 Collection 1 Level 1	landsat_8_c1
Landsat 8 Collection 2 Level 1	landsat_ot_c2_l1
Landsat 8 Collection 2 Level 2	landsat_ot_c2_l2
Sentinel 2A	sentinel_2a
"""

import requests, json, sys, threading, os, time, re, random
from argparse import ArgumentParser
import geopandas as gp

# script state vars
client=None
DEBUG_ENABLED=False
api_token=None
threads = []
MAX_THREADS = -1
active_threads = -1
file_count = 0
last_print_file_count = 0
FILE_COUNT_MAX = -1
new_file_count = 0
out_dir_path = None
download_queue = []
active_downloader = False
downloader_lock = threading.Lock()
available_thread_callsigns = []


# pad a string (or truncate it) so that it is a certain length
def make_size(msg, size):
    return (msg[0:min(size, len(msg))] if len(msg) > 0 else "") + " "*(max(size-len(msg), 0))


# all of the messaging utilties
def debug_print(msg, use_stderr=False, prefix=None):
    message(msg, make_size("[DEBUG]", 8) + (prefix if prefix else ""), True, use_stderr)


def info_print(msg, prefix=None):
    message(msg, make_size("[INFO]", 8) + (prefix if prefix else ""), False, False)


def warn_print(msg, prefix=None):
    message(msg, make_size("[WARN]", 8) + (prefix if prefix else ""), False, False)


def err_print(msg, prefix=None):
    message(msg, make_size("[ERR]", 8) + (prefix if prefix else ""), False, True,)


# the generic message utility
def message(msg, prefix="", is_debug_print=False, use_stderr=False):
    global DEBUG_ENABLED
    # only print debug if in debug mode
    if is_debug_print and not DEBUG_ENABLED:
        return
    
    # choose stream to print to
    use_stream = sys.stderr if use_stderr else sys.stdout
    
    if isinstance(msg, dict):
        msg = json.dumps(msg)
    
    if isinstance(msg, list):
        isStrList = True
        for item in msg:
            if not isinstance(item, str):
                isStrList = False
        msg = '\n'.join(msg) if isStrList else json.dumps(msg)
    
    if not isinstance(msg, str):
        msg = str(msg)
    
    # add prefix to every line
    msg = prefix + ("\n" + prefix).join(msg.split('\n'))
    
    # print message
    use_stream.write(msg + '\n')
    use_stream.flush()


def exit_with_err():
    if client != None:
        client.logout()
    sys.exit(1)


def standard_err_handler(exception):
    if api_token != None:
        api_req("logout")
    err_print(str(exception))
    exit_with_err()


# This does not do any fancy url concatenation,
# so base url and endpoitns should be compatable (eg not base_url="https://example.com" endpoint="api/login")
def api_req(endpoint, data={}, base_url="https://m2m.cr.usgs.gov/api/api/json/stable/",
            err_handler=standard_err_handler):
    global api_token
    headers = {}
    if api_token:
        headers['X-Auth-Token'] = api_token
    debug_print("Sending to %s (%s): %s" % (endpoint, "with token" if api_token else "without token", data), False)
    resp = requests.post(base_url + endpoint, json=data, headers=headers)
    
    # attempt to print response
    try:
        debug_print(("Received from %s:" % endpoint) + json.dumps(resp.json()), False)
    except:
        pass
    
    # do error checking
    try:
        resp.raise_for_status()
        if resp == None:
            raise Exception("Empty resp to API request at endpoint %s" % endpoint)
        resp_json = resp.json()
        if resp_json.get('errorCode'):
            raise Exception("API Error")
            
        # no errors, we can return
        return resp_json["data"]
    except Exception as e:
        try:
            # attempt to get the specific API error (instead of the HTTP error status code)
            resp_json = resp.json()
            e = ': '.join([resp_json.get('errorCode'), resp_json.get('errorMessage')])
        except:
            pass
        err_handler(e)
        return None


def download_file(url, attempt_num=1, thread_name=None):
    global downloader_lock, file_count, FILE_COUNT_MAX, last_print_file_count, new_file_count
    filename = None
    try:
        # Using HEAD command to save on bandwidth (as we won't need the body if we are skipping it!)

        resp = requests.Session().get(url, stream=True, allow_redirects=True)
        # resp = requests.head(url, stream=True, allow_redirects=True)
        try:
            disposition = resp.headers["Content-Disposition"]
            filename = re.findall("filename=(.+)", disposition)[0].strip('"')
        except:
            raise Exception("Unable to extract filename from HEAD response")
        debug_print("Downloading %s ..." % filename, prefix=thread_name)
        file_path = os.path.join(out_dir_path, filename)
        if os.path.isfile(file_path):
            # we have the file already, skip it
            # since there may be many (which would impact speed), we won't print most skips
            with downloader_lock:
                file_count = file_count + 1
                debug_print("Skipped %s" % filename, prefix=thread_name)
                if file_count - last_print_file_count >= 100:
                    info_print("Skipped to (%s / %s): previous were already downloaded" % (make_size(str(file_count), len(str(FILE_COUNT_MAX))), str(FILE_COUNT_MAX)), prefix=thread_name)
                    last_print_file_count = file_count
        else:
            open(file_path, "wb").write(resp.content)
            with downloader_lock:
                file_count = file_count + 1
                if file_count - last_print_file_count > 1:
                    info_print("Skipped to (%s / %s): previous were already downloaded" % (make_size(str(file_count),
                                                                                                     len(str(FILE_COUNT_MAX))),
                                                                                           str(FILE_COUNT_MAX)), prefix=thread_name)
                info_print("Downloaded (%s / %s): %s" % (make_size(str(file_count), len(str(FILE_COUNT_MAX))),
                                                         str(FILE_COUNT_MAX), filename), prefix=thread_name)
                last_print_file_count = file_count
                new_file_count = new_file_count + 1
    except Exception as e:
        err_print("An error ('%s') occurred while downloading from %s: %s" % (str(type(e)), url, str(e)), prefix=thread_name)
        if attempt_num < 3:
            warn_print("Failed attempt #%d to download %s. Will attempt to retry in 30 seconds..." % (attempt_num, filename if filename else "from " + url), prefix=thread_name)
            time.sleep(30)
            download_file(url, attempt_num+1, thread_name)
        else:
            err_print("Failed three times to download from %s. Giving up on it" % url, prefix=thread_name)


def start_downloader():
    global active_threads, downloader_lock, thread_names, download_queue
    if MAX_THREADS > 0:
        with downloader_lock:
            thread_name = available_thread_callsigns.pop()
    
    debug_print("Downloader started", prefix=thread_name)
    
    while True:
        with downloader_lock:
            # to avoid a race condition, I'm putting this logic here, even though it's ugly
            if len(download_queue) == 0:
                active_threads = active_threads - 1
                if MAX_THREADS > 0:
                    available_thread_callsigns.append(thread_name)
                debug_print("Downloader concluded", prefix=thread_name)
                break
            url = download_queue.pop()
        download_file(url, thread_name=thread_name)


# enqueue a url for download
# if there is no active downloading, this also starts the downloading process
# the downloading process is multithreaded and will run until the queue is emptied
def queue_download(new_url):
    global active_threads, download_queue
    debug_print("Enqueuing download: %s" % new_url)
    # enqueue the url and check if there is an active downloader
    with downloader_lock:
        download_queue.append(new_url)
        if active_threads >= MAX_THREADS:
            debug_print("At max threads (%d), not making a new downloader" % active_threads)
            return
        # we may make another downloader
        active_threads = active_threads + 1
        thread = threading.Thread(target=start_downloader)
        thread.start()
        threads.append(thread)
    

def build_command_line_arguments():
    description = ('Search and download data (skip those already downloaded)')
    parser = ArgumentParser(description=description, add_help=False)
    parser.add_argument('--help', action='help', help='Show this help message and exit')
    parser.add_argument('-d', '--directory', type=str, dest='directory', required=True, metavar='<path to dir>',
                        help='Directory to store the downloaded data')
    parser.add_argument('-u', '--username', type=str, dest='username', required=True, default=None, metavar='<username>',
                        help='ERS Username (with full M2M download access)')
    parser.add_argument('-p', '--password', type=str, dest='password', required=True, default=None, metavar='<password>',
                        help='ERS Password')
    parser.add_argument('-h', '--horizontal', type=int, help='horizontal id for ARD')
    parser.add_argument('-v', '--vertical', type=int, help='horizontal id for ARD')
    parser.add_argument('-s', '--scenes-file', type=str, dest='scenes_file', metavar='<path to scenes file>',
                        help='Path to a line-separated list of IDs for scenes to download')
    parser.add_argument('-f', '--filter', type=str, dest='filt', metavar='<filer JSON contents>',
                        help='A JSON SceneFilter search the database with')
    parser.add_argument('--filter-is-path', dest='filter_is_path',
                        help='Use the filter option as a path to a file containing the JSON data, '
                             'rather than the data itself', action='store_true')
    parser.add_argument('-c', '--dataset', type=str, dest='dataset', default='landsat_ard_tile_c2', metavar='<dataset name>',
                        help='Name of the data set or id of the entity from which to download data')
    parser.add_argument('-m', '--max', type=int, dest='max_results', default=10000, metavar='<max threads>',
                        help="Maximum number of results for the search (if applicable)")
    parser.add_argument('-t', '--threads', type=int, dest='max_threads', default=2, metavar='<max threads>',
                        help="Maximum number of threads this script may use for downloading")
    parser.add_argument('-D', '--debug', dest='debug', help='Enable debug printing', action='store_true')
    args = parser.parse_args()
    return args


def do_nothing():
    pass


def get_pretty_thread_print_prefix(thread_name):
    return make_size("<" + thread_name + ">", len(str(MAX_THREADS-1)) + 3) # 3 comes from 2 for the < and > and 1 for a space between the prefix and the text


# document for json keyword: https://m2m.cr.usgs.gov/api/docs/reference/#dataset-search
if __name__ == "__main__":
    try:
        args = build_command_line_arguments()
        DEBUG_ENABLED = args.debug
        out_dir_path = args.directory
        if args.max_threads <= 0:
            raise Exception("Must have at least one download thread!")
        
        if args.max_threads > 0:
            available_thread_callsigns = [get_pretty_thread_print_prefix(str(i)) for i in range(args.max_threads-1) ]
        
        # create the thread pool controller
        MAX_THREADS = args.max_threads
        active_threads = 1 # this main thread
        
        # log in
        api_token = api_req("login", {"username": args.username, "password": args.password})
        scenes = []

        if args.dataset == 'ARD_TILE' or args.dataset == 'landsat_ard_tile_c2':
            try:
                field = gp.read_file(os.path.join(os.getcwd(), 'CONUS_ARD_grid/conus_ard_grid.shp')).to_crs(4326)
            except:
                print('Error: cannot locate hls_s2_tiles.shp file')

            fieldShape = field[(field['h'] == args.horizontal) & (field['v'] == args.vertical)]['geometry']
            centerx = (float(fieldShape.bounds['minx']) + float(fieldShape.bounds['maxx'])) / 2
            centery = (float(fieldShape.bounds['miny']) + float(fieldShape.bounds['maxy'])) / 2

            SpatialFilter = {"filterType" : "mbr",
                             "lowerLeft" : { "latitude" : centery, "longitude" : centerx },
                             "upperRight" : { "latitude" : centery, "longitude" : centerx }}
        else:
            SpatialFilter = None  # put a temp here
        
        # check if scenes are supplied by list
        if args.scenes_file:
            f = open(args.scenes_file, "r")
            lines = f.readlines()
            f.close()
            for line in lines:
                scenes.append(line.strip())
            info_print("Scenes provided via scene list file added")

        # check if we need to search for scenes
        if args.filt:
            filt = args.filt
            if args.filter_is_path:
                filt = open(filt, "r").read()
            filt = json.loads(filt)
            filt["spatialFilter"] = SpatialFilter
            data = {"datasetName" : args.dataset, "sceneFilter": filt, "maxResults" : args.max_results}
            info_print("Searching for scenes with provided SceneFilter")
            resp = api_req("scene-search", data)
            for result in resp["results"]:
                scenes.append(result["entityId"])
        
        shopping_cart = [] # the products we want to download
        
        if len(scenes) == 0:
            # give some sanity output
            warn_print("No scenes found!")
        else:
            info_print("%d scenes found" % len(scenes))
            
            # get the available products for the scenes
            products_info = api_req("download-options", { "datasetName": args.dataset, "entityIds": scenes})
            for product_info in products_info:
                # for now, we will download anything that's in one of our scene's bundles
                if product_info["available"]:
                    if args.dataset == 'landsat_ard_tile_c2':
                        if product_info["productName"] == 'C2 ARD Tile Surface Reflectance Bundle Download' or \
                                product_info["productName"] == 'C2 ARD Tile Brightness Temperature Bundle Download':
                            # add the product to cart
                            shopping_cart.append({ "productId": product_info["id"], "entityId": product_info["entityId"] })
                    else:
                        shopping_cart.append({"productId": product_info["id"], "entityId": product_info["entityId"]})
            
            FILE_COUNT_MAX = len(shopping_cart)
            
            # for the label, we will use a random 16-length string from the alphabet
            label = ""
            for _ in range(16):
                char_val = random.randint(97, 97 + 26 - 1)
                should_capitalize = random.randint(0,1)
                char_val = char_val-32 if should_capitalize == 1 else char_val
                label += chr(char_val)
            info_print("Using label '%s' for the download request" % label)
            
            # create the output directory, if it doesn't exist
            if not os.path.isdir(out_dir_path):
                os.mkdir(out_dir_path)
            
            # send the download request for our shopping cart
            download_info = api_req("download-request", {"downloads": shopping_cart, "label": label})

            # ids of products whose download urls have been acquired
            acquired_id_urls = []
            
            # there are two sets of urls it gives: 'available' (can be downloaded now)
            # and 'preparing' (being processed, will be available to download 'soon')
            
            # we can simply queue the available
            for product_download in download_info["availableDownloads"]:
                queue_download(product_download["url"])
                acquired_id_urls.append(product_download)
            
            # and for the processing, we wait until it's available
            while len(acquired_id_urls) < len(shopping_cart):
                info_print("%d of %d download urls acquired -- waiting 30 seconds for more to become available..." % (len(acquired_id_urls), len(shopping_cart)))
                time.sleep(30)
                new_download_info = api_req("download-retrieve", { "label": label })
                for product_download in new_download_info["available"]:
                    if product_download["downloadId"] not in acquired_id_urls:
                        acquired_id_urls.append(product_download["downloadId"])
                        queue_download(product_download["url"])
            
            info_print("All (%d of %d) download urls have been acquired" % (len(acquired_id_urls), FILE_COUNT_MAX))
            
    except Exception as e:
        raise e
    finally:
        while True:
            thread = None
            with downloader_lock:
                if len(threads) == 0:
                    break
                thread = threads.pop()
            thread.join()
        # if the last few were skipped, let us know
        with downloader_lock:
            if file_count - last_print_file_count > 0:
                    info_print("Skipped to (%s / %s): previous were already downloaded" % (make_size(str(file_count),
                                                                                                     len(str(FILE_COUNT_MAX))),
                                                                                           str(FILE_COUNT_MAX)))
        # log out
        # if api_token:
        #    api_req("logout", err_handler=do_nothing)
        info_print("Done. %d new files downloaded" % new_file_count)
