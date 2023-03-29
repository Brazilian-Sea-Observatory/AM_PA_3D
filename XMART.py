import re, datetime, time
import glob, os, shutil
import subprocess, sys
from ftplib import FTP
import requests
from Input_XMART import *


#####################################################
def next_date (run):
    global next_start_date
    global next_end_date
        
    next_start_date = initial_date + datetime.timedelta(days = run)
    next_end_date = next_start_date + datetime.timedelta(days = 1)

#####################################################
def write_date(file_name):
        
    with open(file_name) as file:
        file_lines = file.readlines()
        
    number_of_lines = len(file_lines)
    
    for n in range(0,number_of_lines):
        line = file_lines[n]        
        if re.search("^START.+:", line):
            file_lines[n] = "START " + ": " + str(next_start_date.strftime("%Y %m %d ")) + "0 0 0\n"

        elif re.search("^END.+:", line):    
            file_lines[n] = "END " + ": " + str(next_end_date.strftime("%Y %m %d ")) + "0 0 0\n"
            
    with open(file_name,"w") as file:
        for n in range(0,number_of_lines) :
            file.write(file_lines[n])

#####################################################
def copy_initial_files(level):

    initial_files_dir = (backup_dir[level]+"//"+str(old_start_date.strftime("%Y%m%d")) + "_" + str(old_end_date.strftime("%Y%m%d")))
    
    if os.path.exists(initial_files_dir):
        
        os.chdir(results_dir[level])
        
        files = glob.glob("*.fin*")
        for filename in files:
            os.remove(filename)
        
        files_fin = glob.iglob(os.path.join(initial_files_dir,"*_2.fin*"))
        for file in files_fin:
            if os.path.isfile(file):
                shutil.copy(file, results_dir[level])
                    
        files_fin = glob.iglob(os.path.join(results_dir[level],"*_2.fin*"))
        for file in files_fin:
            if os.path.isfile(file):
                os.rename(file, file.replace("_2.fin","_1.fin"))
#####################################################
def backup(level):
    
    backup_dir_date = (backup_dir[level]+"//"+str(next_start_date.strftime("%Y%m%d")) + "_" + str(next_end_date.strftime("%Y%m%d")))
        
    if not os.path.exists(backup_dir_date):
        os.makedirs(backup_dir_date)
        
    os.chdir(results_dir[level])
    
    files = glob.glob("MPI*.*")
    for file in files:
        os.remove(file)
        
    files = glob.iglob(os.path.join(results_dir[level],"*.hdf*"))
    for file in files:
        shutil.copy(file, backup_dir_date)
        os.remove(file)
        
    files = glob.iglob(os.path.join(results_dir[level],"*_2.fin*"))
    for file in files:
        shutil.copy(file, backup_dir_date)

    files = glob.iglob(os.path.join(results_dir[level],"*.fin*"))
    for file in files:
        os.remove(file)
    
    if timeseries_backup == 1:
        timeseries_dir = results_dir[level]+ "//run2"
        os.chdir(timeseries_dir)
        files = glob.iglob(os.path.join(timeseries_dir,"*.*"))
        for file in files:
            shutil.copy(file, backup_dir_date)

#####################################################
def convert(date, hdf_file):
        
    convert2netcdf_file = convert2netcdf_dir + "//Convert2netcdf.dat"
    
    with open(convert2netcdf_file) as file:
        file_lines = file.readlines()
        
    number_of_lines = len(file_lines)
    
    for n in range(0,number_of_lines):
        line = file_lines[n]        
        if re.search("^HDF_FILE.+:", line):
            backup_dir_date = (backup_dir[level]+"\\" + date)
            file_lines[n] = "HDF_FILE " + ": " + backup_dir_date + "\\" + hdf_file + "\n"

        elif re.search("^NETCDF_FILE.+:", line):    
            file_lines[n] = "NETCDF_FILE " + ": " + backup_dir_date + "\\" + hdf_file + ".nc\n"
            
        elif re.search("^REFERENCE_TIME.+:", line):
            file_lines[n] = "REFERENCE_TIME " + ": " + str(next_start_date.strftime("%Y %m %d ")) + "0 0 0\n"
            
    with open(convert2netcdf_file,"w") as file:
        for n in range(0,number_of_lines) :
            file.write(file_lines[n])
    
    os.chdir(convert2netcdf_dir)
    output = subprocess.call(["Convert2netcdf.exe"])


#####################################################
#Funcao para envio de mensagem pelo Bot do Telegram
def telegram_msg(message):
        if telegram_messages == 1:
                #message = "hello from your telegram bot"
                urlbot = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
                print(requests.get(urlbot).json()) # this sends the message
#####################################################

if forecast_mode == 1:

        initial_date = datetime.datetime.combine(datetime.datetime.today(), datetime.time.min) + datetime.timedelta(days = refday_to_start)
        
else:
        interval = end - start
        number_of_runs = interval.days
        initial_date = datetime.datetime.combine(start, datetime.time.min)
        
for run in range (0,number_of_runs):    

    #Update dates
    next_date (run)
    
    #Pre-processing
    os.chdir(boundary_conditions_dir)
    files = glob.glob("*.hdf*")
    for filename in files:
        os.remove(filename)
                
    #Copy Meteo boundary conditions
    if number_of_meteo > 0:
        f_missing = True
        for n in range(0, number_of_meteo):
            
            f_meteo = (dir_meteo[n]+"//"+str(next_start_date.strftime("%Y%m%d")) + "_" + str(next_end_date.strftime("%Y%m%d"))+"//"+file_name_meteo[n])
            
            f_exists = os.path.exists(f_meteo)
            
            if f_exists:
                f_size = os.path.getsize(f_meteo)
            
                if f_size > f_min_meteo:

                    shutil.copy(f_meteo, boundary_conditions_dir)
                    os.rename(file_name_meteo[n], "meteo.hdf5")
                    print("Get meteo from: " + f_meteo)
                    f_missing = False
                    break
            
        if f_missing == True:
            msg = "Message from XMART: model " + model_name + "\nMeteo file is missing or is too small for " + str(next_start_date.strftime("%Y%m%d"))
            telegram_msg(msg)
            sys.exit (msg)
        
    #Copy ocean boundary conditions
    #Hydrodynamics
    if number_of_hydro > 0:
        for n in range(0, number_of_hydro):
            f_hydro = (dir_hydro[n]+"//"+str(next_start_date.strftime("%Y%m%d")) + "_" + str(next_end_date.strftime("%Y%m%d"))+"//"+file_hydro[n])
            f_exists = os.path.exists(f_hydro)
        
            if f_exists:
                f_size = os.path.getsize(f_hydro)
                if f_size > f_min_hydro:
                    shutil.copy(f_hydro, boundary_conditions_dir)
                else:
                    msg = "Message from XMART: model " + model_name + "\nHydrodynamic BC file is too small for " + str(next_start_date.strftime("%Y%m%d"))
                    telegram_msg(msg)
                    sys.exit (msg)
            else:
                msg = "Message from XMART: model " + model_name + "\nHydrodynamic BC file is missing for " + str(next_start_date.strftime("%Y%m%d"))
                telegram_msg(msg)
                sys.exit (msg)
    
    #Water properties
    if number_of_wp > 0:
        for n in range(0, number_of_wp):
            f_wp = (dir_wp[n]+"//"+str(next_start_date.strftime("%Y%m%d")) + "_" + str(next_end_date.strftime("%Y%m%d"))+"//"+file_wp[n])
            f_exists = os.path.exists(f_wp)
            
            if f_exists:
                f_size = os.path.getsize(f_wp)
                if f_size > f_min_wp:
                    shutil.copy(f_wp, boundary_conditions_dir)
                else:
                    msg = "Message from XMART: model " + model_name + "\nWater Properties BC file is too small for " + str(next_start_date.strftime("%Y%m%d"))
                    telegram_msg(msg)
                    sys.exit (msg)
            else:
                msg = "Message from XMART: model " + model_name + "\nWater Properties BC file is missing for " + str(next_start_date.strftime("%Y%m%d"))
                telegram_msg(msg)
                sys.exit (msg)
            
    #Copy rivers boundary conditions
    if rivers == 1:    
    
        river_files = glob.iglob(os.path.join(dir_rivers_average,"*.dat"))
        for file in river_files:
            shutil.copy(file, boundary_conditions_dir)
            
        if forecast_mode == 1:
            dir_rivers_date = (dir_rivers_forecast+"//"+str(initial_date.strftime("%Y%m%d")))
        
        else:
            dir_rivers_date = (dir_rivers_forecast+"//"+str(next_start_date.strftime("%Y%m%d")))
        
        f_exists = os.path.exists(dir_rivers_date)
        if f_exists:
            river_files = glob.iglob(os.path.join(dir_rivers_date,"*.dat"))
            for file in river_files:
                shutil.copy(file, boundary_conditions_dir)
        
    ##############################################
    #MOHID
    
    #Update dates
    for level in range (0,number_of_domains):
        os.chdir(data_dir [level])
        write_date("Model_2.dat")
    
    #Copy initial files (.fin)
    old_start_date = next_start_date - datetime.timedelta(days = 1)
    old_end_date = next_end_date - datetime.timedelta(days = 1)
    
    for level in range (0,number_of_domains):
        copy_initial_files(level)
    
    #Run
    os.chdir(exe_dir)
    output = subprocess.call([exe_file])
    #output = subprocess.call([exe_file])
    
    if not ("Program Mohid Water successfully terminated") in open(mohid_log, encoding='latin-1').read():
        msg = "Message from XMART: model " + model_name + "\nProgram Mohid Water was not successfully terminated for " + str(next_start_date.strftime("%Y%m%d"))
        telegram_msg(msg)
        sys.exit (msg)
        
    #Backup
    for level in range (0,number_of_domains):
    
        backup(level)
        
        date = str(next_start_date.strftime("%Y%m%d")) + "_" + str(next_end_date.strftime("%Y%m%d"))
        
        if convert2netcdf == 1:
        
            for file in range (0, len(convert_list)):
                convert(date, convert_list[file])
    
        #Send ftp
        if send_ftp == 1:
            
            ftp=FTP(server)
            ftp.login(user,password)
            ftp.cwd(cwd)
            
            if not date in ftp.nlst():
                ftp.mkd(date)
                
            ftp.cwd(date)
            
            backup_dir_date = (backup_dir[level]+"\\" + date)
            os.chdir(backup_dir_date)
            
            for file in range (0, len(ftp_list)):
                #ftp.set_pasv(False)
                ftp.storbinary('STOR '+ftp_list[file],open(ftp_list[file],'rb'))

            ftp.quit()

