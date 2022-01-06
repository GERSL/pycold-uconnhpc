from os.path import join
from datetime import datetime
import datetime as dt
import gdal

def get_rowcol_intile(pos, block_width, block_height, block_x, block_y):
    """
    calculate row and col in original images based on pos index and block location
    :param pos: position id of the pixel (i.e., i_row * n_cols + i_col)
    :param block_width: the width of each block
    :param block_height: the height of each block
    :param block_x: block location at x direction
    :param block_y: block location at y direction
    :return: row and col number (starting from 1) in original image (e.g., Landsat ARD 5000*5000)
    """
    original_row = int(pos / block_width + (block_y - 1) * block_height + 1)
    original_col = int(pos % block_width + (block_x - 1) * block_width + 1)
    return original_row, original_col


def tileprocessing_report(result_log_path, stack_path, version, algorithm, params, startpoint, tz):
    """
    output tile-based processing report
    :param result_log_path: outputted log path
    :param stack_path: stack data folder
    :param version: version of current pyscold software
    :param algorithm: COLD, OBCOLD, or S-CCD
    :param params: a structure of inputted parameters
    :param startpoint: timepoint that the program starts
    :param tz: time zone
    :return:
    """
    endpoint = datetime.now(tz)
    file = open(result_log_path, "w")
    file.write("PYCOLD V{} \n".format(version))
    file.write("Author: Su Ye(remoteseningsuy@gmail.com)\n")
    file.write("Algorithm: {} \n".format(algorithm))
    file.write("Starting_time: {}\n".format(startpoint.strftime('%Y-%m-%d %H:%M:%S')))
    file.write("Change probability threshold: {}\n".format(params['probability_threshold']))
    file.write("Conse: {}\n".format(params['conse']))
    file.write("First date: {}\n".format(params['starting_date']))
    file.write("n_cm_maps: {}\n".format(params['n_cm_maps']))
    file.write("stack_path: {}\n".format(stack_path))
    file.write("The program starts at {}\n".format(startpoint.strftime('%Y-%m-%d %H:%M:%S')))
    file.write("The program ends at {}\n".format(endpoint.strftime('%Y-%m-%d %H:%M:%S')))
    file.write("The program lasts for {:.2f}mins\n".format((endpoint - startpoint) / dt.timedelta(minutes=1)))
    if algorithm == 'OBCOLD':
        file.write("Land-cover-specific parameters:\n")
        file.write("  C1_threshold: {}\n".format(params['C1_threshold']))
        file.write("  C1_sizeslope: {}\n".format(params['C1_sizeslope']))
        file.write("  C2_threshold: {}\n".format(params['C2_threshold']))
        file.write("  C2_sizeslope: {}\n".format(params['C2_sizeslope']))
        file.write("  C3_threshold: {}\n".format(params['C3_threshold']))
        file.write("  C3_sizeslope: {}\n".format(params['C3_sizeslope']))
        file.write("  C4_threshold: {}\n".format(params['C4_threshold']))
        file.write("  C4_sizeslope: {}\n".format(params['C4_sizeslope']))
        file.write("  C5_threshold: {}\n".format(params['C5_threshold']))
        file.write("  C5_sizeslope: {}\n".format(params['C5_sizeslope']))
        file.write("  C6_threshold: {}\n".format(params['C6_threshold']))
        file.write("  C6_sizeslope: {}\n".format(params['C6_sizeslope']))
        file.write("  C7_threshold: {}\n".format(params['C7_threshold']))
        file.write("  C7_sizeslope: {}\n".format(params['C7_sizeslope']))
        file.write("  C8_threshold: {}\n".format(params['C8_threshold']))
        file.write("  C8_sizeslope: {}\n".format(params['C8_sizeslope']))
    file.close()


def get_time_now(tz):
    """
    :param tz: time zone
    :return: return readable format of current time
    """
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')


def reading_start_end_dates(stack_path):
    """
    :param stack_path: stack_path for saving starting_last_dates.txt
    :return:
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
        f.close()
        return starting_date, ending_date


def gdal_save_file_1band(out_path, array, gdal_type, trans, proj, cols, rows, image_format='GTiff'):
    """
    save array as tiff format
    Parameters
    ----------
    out_path : full outputted path
    array : numpy array to be saved
    gdal_type: gdal type
    trans: transform coefficients
    proj: projection
    rows: the row number
    cols: the col number
    image_format: default is GTiff
    Returns
    -------
    TRUE OR FALSE
    """
    outdriver = gdal.GetDriverByName(image_format)
    outdata = outdriver.Create(out_path, cols, rows, 1, gdal_type)
    if outdata == None:
        return False
    outdata.GetRasterBand(1).WriteArray(array)
    outdata.FlushCache()
    outdata.SetGeoTransform(trans)
    outdata.FlushCache()
    outdata.SetProjection(proj)
    outdata.FlushCache()
    outdata = None
    return True
