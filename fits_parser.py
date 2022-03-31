from itertools import count
import time
import os
import shutil
import typer

from astropy.io import fits as pyfits
import glob
import numpy as np

app = typer.Typer()


@app.command()
def process(name: str = 'process', formal: bool = False):
    '''
    #process all files in folder
    #param name: name of processing 'process'
    #param formal: if True, process files with formal naming convention
    '''

    current_dir = os.getcwd()
    typer.echo(f'Current working directory: {current_dir}')
    if os.path.exists(os.path.join(current_dir, 'config.txt')):
        with open(os.path.join(current_dir, 'config.txt'), 'r') as f:
            lines = f.readlines()
            root_folder = lines[0].strip()
            type = lines[1].strip()
            flag = lines[2].strip()
            dest_folder = lines[3].strip()
            dark_folder = lines[4].strip()
            bias_folder = lines[5].strip()
            flat_folder = lines[6].strip()
            delete_files = lines[7].strip()
    else:
        typer.secho(f"Welcome to FITS {name}", fg=typer.colors.MAGENTA)
        root_folder = typer.prompt("Enter the source folder path (for example, C:\\Users)")
        type = typer.prompt("Enter type (for example, LIGHT)")
        flag = typer.prompt("Enter flag (for example, _CALIBRATED)")
        dest_folder = typer.prompt("Enter destination folder path (for example, C:\\Users\Light)")
        dark_folder = typer.prompt("Enter dark folder path (for example, C:\\Users\Dark)")
        bias_folder = typer.prompt("Enter bias folder path (for example, C:\\Users\Bias)")
        flat_folder = typer.prompt("Enter flat folder path (for example, C:\\Users\Flat)")
        delete_files = typer.confirm("Do you want to delete files after processing?", default=False)
        with open('config.txt', 'w') as f:
            f.write(f'{root_folder}\n{type}\n{flag}\n{dest_folder}\n{dark_folder}\n{bias_folder}\n{flat_folder}\n{delete_files}')

    typer.echo(f'Start combining(median) DARK files')
    dark = summarize_dark(dark_folder)
    typer.echo(f'DARK files combined')
    typer.echo(f'Start combining(median) BIAS files')
    bias = summarize_bias(bias_folder)
    typer.echo(f'BIAS files combined')
    typer.echo(f'Start processing files')

    typer.secho(f"Processing started", fg=typer.colors.GREEN)
    typer.echo(f'Processing files in {root_folder}')
    typer.echo(f'Type: {type}')
    typer.echo(f'flag: {flag}')
    typer.echo(f'Destination folder: {dest_folder}')
    typer.secho(f'Delete files after processing: {delete_files}', fg=typer.colors.RED)
    typer.secho(f'Sleeping for 10 seconds... before processing', fg=typer.colors.YELLOW)
    time.sleep(10)
    typer.echo(f'Processing files...')

    if not os.path.exists(dest_folder):
        os.mkdir(dest_folder)
    skipped_files = 0
    processed_files = 0
    flat_combined = False
    with typer.progressbar(os.listdir(root_folder), label="Processing files") as files:
        for file in files:
            #if file has already contains _CALIBRATED in name, skip it
            if flag in file:
                skipped_files += 1
                continue
            file_path = os.path.join(root_folder, file)
            if skip_file(file_path):
                skipped_files += 1
                continue
            hdulist = pyfits.open(file_path)
            hdr = hdulist[0].header
            if process_fits_type(hdr, type):
                object = process_fits_object(hdr)
                if object:
                    date = process_file_date(hdr)
                    filter = process_fiter(hdr)
                    destination_folder = create_folder_filter(file_path, object, type, date, filter, dest_folder)
                    copy_file(file_path, destination_folder, delete_files)
                    new_file_path = rename_file(file_path, destination_folder, flag)
                    typer.echo(f'Start combining(median) FLAT files')
                    if filter == 'C' and not flat_combined:
                        flat = summarize_flat(flat_folder, filter)
                        if flat.any():
                            flat_combined = True
                    else:
                        if not flat_combined:
                            flat = summarize_flat(flat_folder, filter)
                    typer.echo(f'FLAT files combined')
                    get_final_image(new_file_path, bias, dark, flat)
                    typer.echo(f'File {file} processed')
                    processed_files += 1
                else:
                    typer.echo(f'File {file} not processed')
            else:
                typer.echo(f'File {file} not processed')
            hdulist.close()
        typer.echo()
        color = typer.colors.GREEN
        typer.secho(f"Processing finished", fg=color)
        typer.echo(f'{processed_files} files processed')        
        typer.echo(f'Files skipped: {skipped_files}')

    # if formal:
    #     shutil.rmtree(root_folder)
    #     typer.secho(f"Source folder {root_folder} deleted", fg=typer.colors.GREEN)



def process_fits_type(hdr, type):
    '''
    check if file is of type
    '''
    if hdr['IMAGETYP'] == type:
        return True
    else:
        return False

def process_file_date(hdr):
    '''
    get date from file content if exists and return only yyyy-mm-dd
    '''
    if hdr['DATE-OBS']:
        date = hdr['DATE-OBS']
        date_split = date.split('T')[0].split('-')
        date = '-'.join(date_split)
        return date
    else:
        return False

def process_fiter(hdr):
    '''
    get filter from file content
    '''
    filter = hdr.get('FILTER', 'C') 
    if filter:
        return filter
    else:
        return False
        
        

def process_fits_object(hdr):
    '''
    get object name from file content 
    '''
    if hdr['OBJECT']:
        return hdr['OBJECT']
    else:
        return False

 

def create_folder_filter(file_path, object, type, date, filter, dest_folder):
    '''
    create folder with type and FILTER like this /OBJECT/DATE-OBS/type/FILTER (get param FILTER from file content)
    '''
    root_folder = os.path.dirname(file_path)
    objects_folder = os.path.join(root_folder, dest_folder)
    if not os.path.exists(objects_folder):
        os.mkdir(objects_folder)
    object_folder = os.path.join(objects_folder, object)
    if not os.path.exists(object_folder):
        os.mkdir(object_folder)
    type_folder = os.path.join(object_folder, type)
    if not os.path.exists(type_folder):
        os.mkdir(type_folder)
    date_folder = os.path.join(type_folder, date)
    if not os.path.exists(date_folder):
        os.mkdir(date_folder)
    filter_folder = os.path.join(date_folder, filter)
    if not os.path.exists(filter_folder):
        os.mkdir(filter_folder)
    return filter_folder


def skip_file(file_path):
    if not file_path.endswith('.fits'):
        return True
    else:
        return False



def copy_file(file_path, destination_folder, delete_files=False):
    '''
    copy file to destination folder
    '''
    file_name = os.path.basename(file_path)
    if os.path.exists(os.path.join(destination_folder, file_name)):
        typer.echo(f'File {file_name} already exists in destination folder')
        typer.echo(f'Do you want to replace it? (y/n)')
        answer = input()
        if answer == 'y':
            shutil.copy(file_path, destination_folder)
            typer.echo(f'File {file_name} copied to {destination_folder}')
            if str(delete_files.lower()) == 'y':
                os.remove(file_path)
                typer.echo(f'File {file_name} deleted')
        else:
            typer.echo(f'File {file_name} not copied')
    else:
        shutil.copy(file_path, destination_folder)
        typer.echo(f'File {file_name} copied to {destination_folder}')
        if str(delete_files.lower()) == 'y':
            os.remove(file_path)
            typer.echo(f'File {file_name} deleted')


def rename_file(file_path, destination_folder, flag):
    '''
    rename fits file after move to destination folder add _CALIBRATED to end of file before extention .FITS
    '''
    file_name = os.path.basename(file_path)
    file_name_split = file_name.split('.fits')
    file_name_split[0] += flag
    new_file_name = '.'.join(file_name_split) + 'fits'
    new_file_path = os.path.join(destination_folder, new_file_name)
    old_file_path = os.path.join(destination_folder, file_name)
    os.rename(old_file_path, new_file_path)
    typer.echo(f'File {file_name} renamed')
    fix_fits_header(new_file_path)
    return new_file_path


def fix_fits_header(file_path):
    hdulist = pyfits.open(file_path, mode='update')
    hdr = hdulist[0].header
    hdr.add_history('= CALIBRATED')
    hdulist.flush()
    hdulist.close()
    typer.echo(f'File {file_path} header fixed')

    
def calibrate_file(file_path, bias_path, dark_path, flat_path):
    hdulist = pyfits.open(file_path, mode='update')
    hdr = hdulist[0].header
    if hdr['IMAGETYP'] == 'OBJECT':
        data = hdulist[0].data
        bias = pyfits.getdata(bias_path)
        dark = pyfits.getdata(dark_path)
        flat = pyfits.getdata(flat_path)
        data = data - bias
        data = data - dark
        data = data / flat
        hdulist[0].data = data
        hdulist.flush()
        hdulist.close()
        typer.echo(f'File {file_path} calibrated')
    else:
        typer.echo(f'File {file_path} not calibrated')


#get temperature from header
def get_temperature(hdr):
    if hdr['TEMP']:
        return hdr['TEMP']
    else:
        return False


def mediancombine(filelist, filter=None):
    '''
    median combine files
    '''
    n = len(filelist)
    first_frame_data = pyfits.getdata(filelist[0])
    imsize_y, imsize_x = first_frame_data.shape
    fits_stack = np.zeros((imsize_y, imsize_x , n), dtype = np.float32) 
    count = 0
    for ii in range(0, n):
        if filter:
            hdr = pyfits.getheader(filelist[ii])
            if hdr.get('FILTER', 'C') == filter:
                im = pyfits.getdata(filelist[ii])
                fits_stack[:,:,ii] = im
                print(f'{filelist[ii]} added to stack with filter {filter}')
                count += 1
            else:
                continue
        else:
            im = pyfits.getdata(filelist[ii])
            fits_stack[:,:,ii] = im
    if filter and count == 0:
        #color typer red
        typer.secho(f'No files with filter {filter} found', color='red')
        exit()
    med_frame = np.median(fits_stack, axis=2)
    return med_frame



#summirize FITS dark files in folder by median
def summarize_dark(folder_path):
    files = glob.glob(os.path.join(folder_path, '*.fits'))
    return mediancombine(files)
    # data = []
    # for file in files:
    #     hdulist = pyfits.open(file, mode='update')
    #     data.append(hdulist[0].data)
    #     hdulist.close()
    # median = np.median(data, axis=0)
    # return median

#summirize FITS flat files in folder by median
def summarize_flat(folder_path, filter):
    print(f'Filter: {filter}')
    files = glob.glob(os.path.join(folder_path, '*.fits'))
    return mediancombine(files, filter)
    # data = []
    # for file in files:
    #     hdulist = pyfits.open(file, mode='update')
    #     data.append(hdulist[0].data)
    #     hdulist.close()
    # median = np.median(data, axis=0)
    # return median

#summirize FITS bias files in folder by median
def summarize_bias(folder_path):
    files = glob.glob(os.path.join(folder_path, '*.fits'))
    return mediancombine(files)
    # data = []
    # for file in files:
    #     hdulist = pyfits.open(file, mode='update')
    #     data.append(hdulist[0].data)
    #     hdulist.close()
    # median = np.median(data, axis=0)
    # return median


def get_final_image(light_path, bias, dark, flat):
    hdulist = pyfits.open(light_path, mode='update')
    light = hdulist[0].data
    final = light - bias - (dark - bias)
    final = final / (flat - bias)
    hdulist[0].data = final
    hdulist.flush()
    hdulist.close()
    typer.echo(f'File {light_path} stored')



if __name__ == "__main__":
    app()

