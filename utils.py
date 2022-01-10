from datetime import datetime
import pandas as pd

NAN_VAL = -9999


def get_rowcol_intile(pos, block_width, block_height, block_x, block_y):
    """
    calculate row and col in original images based on pos index and block location
    Parameters
    ----------
    pos: integer
        position id of the pixel (i.e., i_row * n_cols + i_col + 1)
    block_width: integer
        the width of each block
    block_height: integer
        the height of each block
    block_x:integer
        block location at x direction
    block_y:integer
        block location at y direction
    Returns
    -------
    (original_row, original_col)
    row and col number (starting from 1) in original image (e.g., Landsat ARD 5000*5000)
    """
    original_row = int(pos / block_width + (block_y - 1) * block_height + 1)
    original_col = int(pos % block_width + (block_x - 1) * block_width + 1)
    return original_row, original_col


def get_time_now(tz):
    """
    Parameters
    ----------
    tz: string

    Returns
    -------
    datatime format of current time
    """
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')


def get_doy(ordinal_date):
    """
    Parameters
    ----------
    ordinal_date: int
    a ordinal date (MATLAB-format ordinal date)

    Returns: string
    -------
    doy
    """
    return str(pd.Timestamp.fromordinal(ordinal_date-366).timetuple().tm_yday).zfill(3)

