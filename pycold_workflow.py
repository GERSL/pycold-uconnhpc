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
from pycold.utils import get_rowcol_intile, get_doy, assemble_cmmaps
from pycold.utils import get_block_y, get_block_x, read_blockdata

STACK_BAND_NUM = 8
NAN_VAL = -9999


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

    #######################################################################################
    #                     Step 1: temporal analysis - COLD algorithm                      #
    #######################################################################################
    for i in range(nblock_eachcore):
        block_id = n_cores * i + rank  # from 1 to 200, if 200 cores
        if block_id > config['n_block_x'] * config['n_block_y']:
            break
        # skip the block if the change record block has been created
        if os.path.exists(join(result_path, 'COLD_block{}_finished.txt'.format(block_id))):
            continue

        block_y = get_block_x(block_id, config['n_block_x'])
        block_x = get_block_y(block_id, config['n_block_x'])
        block_folder = join(stack_path, 'block_x{}_y{}'.format(block_x, block_y))
        img_stack, img_dates_sorted = read_blockdata(block_folder, config['block_width'] * config['block_height'],
                                                     STACK_BAND_NUM)
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
                                                                           img_stack[pos, 0, :].astype(np.int64),
                                                                           img_stack[pos, 1, :].astype(np.int64),
                                                                           img_stack[pos, 2, :].astype(np.int64),
                                                                           img_stack[pos, 3, :].astype(np.int64),
                                                                           img_stack[pos, 4, :].astype(np.int64),
                                                                           img_stack[pos, 5, :].astype(np.int64),
                                                                           img_stack[pos, 6, :].astype(np.int64),
                                                                           img_stack[pos, 7, :].astype(np.int64),
                                                                           pos=config['n_cols'] * (original_row - 1) +
                                                                           original_col,
                                                                           conse=config['conse'],
                                                                           starting_date=starting_date,
                                                                           n_cm=n_cm_maps,
                                                                           cm_output_interval=config['CM_OUTPUT_INTERVAL'],
                                                                           b_output_cm=b_outputCM)
                else:
                    cold_result = cold_detect(img_dates_sorted,
                                              img_stack[pos, 0, :].astype(np.int64),
                                              img_stack[pos, 1, :].astype(np.int64),
                                              img_stack[pos, 2, :].astype(np.int64),
                                              img_stack[pos, 3, :].astype(np.int64),
                                              img_stack[pos, 4, :].astype(np.int64),
                                              img_stack[pos, 5, :].astype(np.int64),
                                              img_stack[pos, 6, :].astype(np.int64),
                                              img_stack[pos, 7, :].astype(np.int64),
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
            assemble_cmmaps(config, result_path, join(result_path, 'cm_maps'), starting_date, n_cm_maps, 'CM',
                            clean=True)
        elif rank == 2:
            assemble_cmmaps(config, result_path, join(result_path, 'cm_maps'), starting_date, n_cm_maps, 'CM_direction',
                            clean=True)

        elif rank == 3:
            assemble_cmmaps(config, result_path, join(result_path, 'cm_maps'), starting_date, n_cm_maps, 'CM_date',
                            clean=True)

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

