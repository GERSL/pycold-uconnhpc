# This script is an example for running pyscold in UCONN job array environment
# Due to the independence features of job array, we use writing disk files for communication
# Three types of logging files are used: 1) print() to save block-based  processing info into individual slurm file;
# 2) system.log is mainly used to log runtime information; 3) tile_processing_report.log records config for each tile
# 2) and 3) are only called when rank == 1
import yaml
import os
from os.path import join
import pandas as pd
import datetime as dt
import numpy as np
import pycold
import logging
from datetime import datetime
from pytz import timezone
import click
import time
from pycold import cold_detect
from scipy.stats import chi2
from utils import get_rowcol_intile, get_time_now, get_doy

TOTAL_IMAGE_BANDS = 7
NAN_VAL = -9999


def assemble_cmmaps(config, result_path, cmmap_path, starting_date, n_cm_maps, keyword):
    """
    this function reorganized block-based fix-interval CM intermediate files into map-based output (one map per interval)
    Parameters
    ----------
    config: dictionary
        pycold config dictionary
    result_path: string
        the path where block-based CM intermediate files are
    cmmap_path: string
        the path to save the new map-based output
    starting_date: integer
        the starting date of the dataset
    n_cm_maps: integer
        the number of change magnitude outputted per pixel
    keyword: {'CM', 'CM_date', 'CM_direction'}
    Returns
    -------

    """
    if keyword == 'CM':
        output_type = np.int16
    elif keyword == 'CM_date':
        output_type = np.int32
    elif keyword == 'CM_direction':
        output_type = np.uint8

    cm_map_list = [np.full((config['n_rows'], config['n_cols']),
                           NAN_VAL, dtype=output_type) for x in range(n_cm_maps)]
    for iblock in range(config['n_blocks']):
        current_block_y = int(np.floor(iblock / config['n_block_x'])) + 1
        current_block_x = iblock % config['n_block_y'] + 1
        try:
            cm_block = np.load(join(result_path, '{}_x{}_y{}.npy'.format(keyword, current_block_x, current_block_y)))
        except OSError as e:
            print('Reading CM files fails: {}'.format(e))
        #    continue

        cm_block_reshape = np.reshape(cm_block, (config['block_width'] * config['block_height'],
                                                 n_cm_maps))
        hori_profile = np.hsplit(cm_block_reshape, n_cm_maps)
        for count, maps in enumerate(cm_map_list):
            maps[(current_block_y - 1) * config['block_height']:current_block_y * config['block_height'],
            (current_block_x - 1) * config['block_width']:current_block_x * config['block_width']] = \
                hori_profile[count].reshape(config['block_height'], config['block_width'])

    # output cm images
    for count, cm_map in enumerate(cm_map_list):
        ordinal_date = starting_date + count * config['CM_OUTPUT_INTERVAL']
        outfile = join(cmmap_path, '{}_maps_{}_{}{}.npy'.format(keyword, str(ordinal_date),
                                                                pd.Timestamp.fromordinal(ordinal_date - 366).year,
                                                                get_doy(ordinal_date)))
        np.save(outfile, cm_map)


def tileprocessing_report(result_log_path, stack_path, version, algorithm, config, startpoint, tz):
    """
    output tile-based processing report
    Parameters
    ----------
    result_log_path: string
        outputted log path
    stack_path: string
        stack path
    version: string
    algorithm: string
    config: dictionary structure
    startpoint: a time point, when the program starts
    tz: string, time zone

    Returns
    -------

    """
    endpoint = datetime.now(tz)
    file = open(result_log_path, "w")
    file.write("PYCOLD V{} \n".format(version))
    file.write("Author: Su Ye(remoteseningsuy@gmail.com)\n")
    file.write("Algorithm: {} \n".format(algorithm))
    file.write("Starting_time: {}\n".format(startpoint.strftime('%Y-%m-%d %H:%M:%S')))
    file.write("Change probability threshold: {}\n".format(config['probability_threshold']))
    file.write("Conse: {}\n".format(config['conse']))
    file.write("stack_path: {}\n".format(stack_path))
    file.write("The program starts at {}\n".format(startpoint.strftime('%Y-%m-%d %H:%M:%S')))
    file.write("The program ends at {}\n".format(endpoint.strftime('%Y-%m-%d %H:%M:%S')))
    file.write("The program lasts for {:.2f}mins\n".format((endpoint - startpoint) / dt.timedelta(minutes=1)))
    if algorithm == 'OBCOLD':
        file.write("Land-cover-specific config:\n")
        file.write("  C1_threshold: {}\n".format(config['C1_threshold']))
        file.write("  C1_sizeslope: {}\n".format(config['C1_sizeslope']))
        file.write("  C2_threshold: {}\n".format(config['C2_threshold']))
        file.write("  C2_sizeslope: {}\n".format(config['C2_sizeslope']))
        file.write("  C3_threshold: {}\n".format(config['C3_threshold']))
        file.write("  C3_sizeslope: {}\n".format(config['C3_sizeslope']))
        file.write("  C4_threshold: {}\n".format(config['C4_threshold']))
        file.write("  C4_sizeslope: {}\n".format(config['C4_sizeslope']))
        file.write("  C5_threshold: {}\n".format(config['C5_threshold']))
        file.write("  C5_sizeslope: {}\n".format(config['C5_sizeslope']))
        file.write("  C6_threshold: {}\n".format(config['C6_threshold']))
        file.write("  C6_sizeslope: {}\n".format(config['C6_sizeslope']))
        file.write("  C7_threshold: {}\n".format(config['C7_threshold']))
        file.write("  C7_sizeslope: {}\n".format(config['C7_sizeslope']))
        file.write("  C8_threshold: {}\n".format(config['C8_threshold']))
        file.write("  C8_sizeslope: {}\n".format(config['C8_sizeslope']))
    file.close()


def reading_start_end_dates(stack_path, cm_interval):
    """
    Parameters
    ----------
    stack_path: string
        stack_path for saving starting_last_dates.txt
    cm_interval: interval
        day interval for outputting change magnitudes
    Returns
    -------
        (starting_date, n_cm_maps)
        starting_date - starting date is the first date of the whole dataset,
        n_cm_maps - the number of change magnitudes to be outputted per pixel per band
    """
    # read starting and ending dates, note that all blocks only has one starting and last date (mainly for obcold)
    try:
        f = open(join(stack_path, "starting_last_dates.txt"),
                 "r")  # read starting and ending date info from stack files
    except IOError as e:
        raise
    else:
        starting_date = int(f.readline().rstrip('\n'))
        ending_date = int(f.readline().rstrip('\n'))
        n_cm_maps = int((ending_date - starting_date + 1) / cm_interval) + 1
        f.close()
        return starting_date, n_cm_maps


def is_finished_cold_blockfinished(result_path, nblocks):
    """
    check if the COLD algorithm finishes all blocks
    Parameters
    ----------
    result_path: the path that save COLD results
    nblocks: the block number

    Returns: boolean
    -------
        True -> all block finished
    """
    for n in range(nblocks):
        if not os.path.exists(os.path.join(result_path, 'COLD_block{}_finished.txt'.format(n+1))):
            return False
    return True


def is_finished_assemble_cmmaps(cmmap_path, n_cm, starting_date, cm_interval):
    """
    Parameters
    ----------
    cmmap_path: the path for saving change magnitude maps
    n_cm: the number of change magnitudes outputted per pixel
    starting_date: the starting date of the whole dataset
    cm_interval: the day interval for outputting change magnitudes

    Returns: boolean
    -------
    True -> assemble finished
    """
    for count in range(n_cm):
        ordinal_date = starting_date + count * cm_interval
        if not os.path.exists(join(cmmap_path,
                                   'CM_maps_{}_{}{}.npy'.format(str(ordinal_date),
                                                                pd.Timestamp.fromordinal(ordinal_date-366).year,
                                                                get_doy(ordinal_date)))):
            return False
        if not os.path.exists(join(cmmap_path,
                                   'CM_date_maps_{}_{}{}.npy'.format(str(ordinal_date),
                                                                     pd.Timestamp.fromordinal(ordinal_date-366).year,
                                                                     get_doy(ordinal_date)))):
            return False
        if not os.path.exists(join(cmmap_path,
                                   'CM_direction_maps_{}_{}{}.npy'.format(str(ordinal_date),
                                                                          pd.Timestamp.fromordinal(ordinal_date-366).year,
                                                                          get_doy(ordinal_date)))):
            return False
    return True


@click.command()
@click.option('--rank', type=int, default=0, help='the rank id')
@click.option('--n_cores', type=int, default=0, help='the total cores assigned')
@click.option('--stack_path', type=str, default=None, help='the path for stack data')
@click.option('--result_path', type=str, default=None, help='the path for storing results')
@click.option('--yaml_path', type=str, default=None, help='YAML path')
@click.option('--method', type=click.Choice(['COLD', 'OB-COLD', 'SCCD-OFFLINE']), help='COLD, OB-COLD, SCCD-OFFLINE')
def main(rank, n_cores, stack_path, result_path, yaml_path, method):
    b_outputCM = False if method == 'COLD' or method == 'SCCD-OFFLINE' else True  # only when ob-cold b_outputCM is True
    tz = timezone('US/Eastern')
    start_time = datetime.now(tz)
    if rank == 1:
        if not os.path.exists(result_path):
            os.makedirs(result_path)
        if b_outputCM:
            if not os.path.exists(join(result_path, 'cm_maps')):
                os.makedirs(join(result_path, 'cm_maps'))
        # system logging
        logging.basicConfig(filename='{}/system.log'.format(result_path),
                            filemode='w', level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info("The per-pixel COLD algorithm begins: {}".format(start_time.strftime('%Y-%m-%d %H:%M:%S')))

        if not os.path.exists(stack_path):
            logger.error("Failed to locate stack folders. The program ends: {}"
                         .format(datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')))
            return

    # Reading config
    with open(yaml_path, 'r') as yaml_obj:
        config = yaml.safe_load(yaml_obj)
    threshold = chi2.ppf(config['probability_threshold'], 5)

    # set up some additional config
    config['block_width'] = int(config['n_cols'] / config['n_block_x'])  # width of a block
    config['block_height'] = int(config['n_rows'] / config['n_block_y'])  # height of a block
    config['n_blocks'] = config['n_block_x'] * config['n_block_y']
    if (config['n_cols'] % config['block_width'] != 0) or (config['n_rows'] % config['block_height'] != 0):
        print('n_cols, n_rows must be divisible respectively by block_width, block_height! Please double '
              'check your config yaml')
        exit()

    # starting and ending date will be used for obcold
    try:
        starting_date, n_cm_maps = reading_start_end_dates(stack_path, config['CM_OUTPUT_INTERVAL'])
    except IOError as e:
        exit()

    nblock_eachcore = int(np.ceil(config['n_block_x'] * config['n_block_y'] * 1.0 / n_cores))
    for i in range(nblock_eachcore):
        block_id = n_cores * i + rank  # from 1 to 200, if 200 cores
        if block_id > config['n_block_x'] * config['n_block_y']:
            break

        block_y = int((block_id - 1) / config['n_block_x']) + 1  # note that block_x and block_y start from 1
        block_x = int((block_id - 1) % config['n_block_x']) + 1

        # skip the block if the change record block has been created
        if os.path.exists(join(result_path, 'COLD_block{}_finished.txt'.format(block_id))):
            continue

        block_folder = join(stack_path, 'block_x{}_y{}'.format(block_x, block_y))

        img_files = [f for f in os.listdir(block_folder) if f.startswith('L')]

        # sort image files by dates
        img_dates = [pd.Timestamp.toordinal(dt.datetime(int(folder_name[9:13]), 1, 1) +
                                            dt.timedelta(int(folder_name[13:16]) - 1)) + 366
                     for folder_name in img_files]
        files_date_zip = sorted(zip(img_dates, img_files))
        img_files_sorted = [x[1] for x in files_date_zip]
        img_dates_sorted = np.asarray([x[0] for x in files_date_zip])
        img_tstack = [np.load(join(block_folder, f)).reshape(config['block_width'] * config['block_height'],
                                                             TOTAL_IMAGE_BANDS + 1)
                      for f in img_files_sorted]
        img_tstack = np.dstack(img_tstack)

        # initialize a list (may better change it to generator for future)
        result_collect = []
        CM_collect = []
        direction_collect = []
        date_collect = []

        # start looping every pixel in the block
        for pos in range(config['block_width'] * config['block_height']):
            original_row, original_col = get_rowcol_intile(pos, config['block_width'],
                                                           config['block_height'], block_x, block_y)
            try:
                if b_outputCM:
                    [cold_result, CM, CM_direction, CM_date] = cold_detect(img_dates_sorted,
                                                                           img_tstack[pos, 0, :].astype(np.int64),
                                                                           img_tstack[pos, 1, :].astype(np.int64),
                                                                           img_tstack[pos, 2, :].astype(np.int64),
                                                                           img_tstack[pos, 3, :].astype(np.int64),
                                                                           img_tstack[pos, 4, :].astype(np.int64),
                                                                           img_tstack[pos, 5, :].astype(np.int64),
                                                                           img_tstack[pos, 6, :].astype(np.int64),
                                                                           img_tstack[pos, 7, :].astype(np.int64),
                                                                           pos=config['n_cols'] * (original_row - 1) +
                                                                           original_col,
                                                                           conse=config['conse'],
                                                                           starting_date=starting_date,
                                                                           n_cm=n_cm_maps,
                                                                           cm_output_interval=config['CM_OUTPUT_INTERVAL'],
                                                                           b_output_cm=b_outputCM)
                else:
                    cold_result = cold_detect(img_dates_sorted,
                                              img_tstack[pos, 0, :].astype(np.int64),
                                              img_tstack[pos, 1, :].astype(np.int64),
                                              img_tstack[pos, 2, :].astype(np.int64),
                                              img_tstack[pos, 3, :].astype(np.int64),
                                              img_tstack[pos, 4, :].astype(np.int64),
                                              img_tstack[pos, 5, :].astype(np.int64),
                                              img_tstack[pos, 6, :].astype(np.int64),
                                              img_tstack[pos, 7, :].astype(np.int64),
                                              t_cg=threshold,
                                              conse=config['conse'],
                                              pos=config['n_cols'] * (original_row - 1) + original_col)
            except RuntimeError:
                print("COLD fails at original_row {}, original_col {} ({})".format(original_row, original_col,
                                                                                   datetime.now(tz)
                                                                                   .strftime('%Y-%m-%d %H:%M:%S')))
            except Exception as e:
                print(e)
            else:
                result_collect.append(cold_result)
                if b_outputCM:
                    CM_collect.append(CM)
                    direction_collect.append(CM_direction)
                    date_collect.append(CM_date)

        # save the dataset
        np.save(join(result_path, 'record_change_x{}_y{}_cold.npy'.format(block_x, block_y)), np.hstack(result_collect))
        if b_outputCM:
            np.save(join(result_path, 'CM_date_x{}_y{}.npy'.format(block_x, block_y)), np.hstack(date_collect))
            np.save(join(result_path, 'CM_direction_x{}_y{}.npy'.format(block_x, block_y)), np.hstack(direction_collect))
            np.save(join(result_path, 'CM_x{}_y{}.npy'.format(block_x, block_y)), np.hstack(CM_collect))

        with open(os.path.join(result_path, 'COLD_block{}_finished.txt'.format(block_id)), 'w') as fp:
            pass

        print("Per-pixel COLD processing is finished for block_x{}_y{} ({})"
              .format(block_x, block_y, datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')))

    # wait for all cores to be finished
    while not is_finished_cold_blockfinished(result_path, config['n_block_x'] * config['n_block_y']):
        time.sleep(15)

    if b_outputCM:  # reorganize block-based intermediate CM outputs
        if rank == 1:
            logger.info("The per-pixel COLD algorithm ends and starts assembling CM files: {}"
                        .format(datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')))
            # assemble_cmmaps(config, result_path, join(result_path, 'cm_maps'), starting_date, n_cm_maps, 'CM')
            tmp_filenames = [file for file in os.listdir(result_path)
                                         if file.startswith('CM_x')]
            for file in tmp_filenames:
                os.remove(join(result_path, file))
        elif rank == 2:
            assemble_cmmaps(config, result_path, join(result_path, 'cm_maps'), starting_date, n_cm_maps, 'CM_direction')
            tmp_filenames = [file for file in os.listdir(result_path)
                             if file.startswith('CM_direction')]
            for file in tmp_filenames:
                os.remove(join(result_path, file))
        elif rank == 3:
            assemble_cmmaps(config, result_path, join(result_path, 'cm_maps'), starting_date, n_cm_maps, 'CM_date')
            tmp_filenames = [file for file in os.listdir(result_path)
                             if file.startswith('CM_date')]
            for file in tmp_filenames:
                os.remove(join(result_path, file))
        else:
            while not is_finished_assemble_cmmaps(join(result_path, 'cm_maps'), n_cm_maps,
                                                  starting_date, config['CM_OUTPUT_INTERVAL']):
                time.sleep(15)
    if rank == 1:
        # tile_based report
        tileprocessing_report(join(result_path, 'tile_processing_report.log'),
                              stack_path, pycold.__version__, method, config, start_time, tz)
        logger.info("The whole procedure finished: {}".format(datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')))


if __name__ == '__main__':
    main()

