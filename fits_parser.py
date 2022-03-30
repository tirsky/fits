import time
import os
import shutil
import typer

from astropy.io import fits as pyfits

    


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
    else:
        typer.secho(f"Welcome to FITS {name}", fg=typer.colors.MAGENTA)
        root_folder = typer.prompt("Enter the source folder path (for example, C:\\Users)")
        type = typer.prompt("Enter type (for example, LIGHT)")
        flag = typer.prompt("Enter flag (for example, _CALIBRATED)")
        dest_folder = typer.prompt("Enter destination folder path (for example, C:\\Users\Light)")
        with open('config.txt', 'w') as f:
            f.write(f'{root_folder}\n{type}\n{flag}\n{dest_folder}')

    typer.secho(f"Processing started", fg=typer.colors.GREEN)
    typer.echo(f'Processing files in {root_folder}')
    typer.echo(f'Type: {type}')
    typer.echo(f'flag: {flag}')
    typer.echo(f'Destination folder: {dest_folder}')
    typer.echo(f'Processing files...')

    if not os.path.exists(dest_folder):
        os.mkdir(dest_folder)
    skipped_files = 0
    processed_files = 0
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
                    copy_file(file_path, destination_folder)
                    rename_file(file_path, destination_folder, flag)
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



def copy_file(file_path, destination_folder):
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
            typer.echo(f'Do you want to delete original file? (y/n)')
            answer = input()
            if answer == 'y':
                os.remove(file_path)
                typer.echo(f'File {file_name} deleted')
        else:
            typer.echo(f'File {file_name} not copied')
    else:
        shutil.copy(file_path, destination_folder)
        typer.echo(f'File {file_name} copied to {destination_folder}')
        typer.echo(f'Do you want to delete original file? (y/n)')
        answer = input()
        if answer == 'y':
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


#fix FITS HEADER for CALIBRATED files add HISTORY = CALIBRATED to header
def fix_fits_header(file_path):
    hdulist = pyfits.open(file_path, mode='update')
    hdr = hdulist[0].header
    hdr.add_history('= CALIBRATED')
    hdulist.flush()
    hdulist.close()
    typer.echo(f'File {file_path} header fixed')

    

if __name__ == "__main__":
    app()

