import re
import csv
import os
import sys

DEBUG = True
warnings_set = set() # Store warnings that have already been logged

default_config_file = r".\config_verilog.txt"

# Log warnings without logging the same message more than once
def log_warning(message):
    global warnings_set
    if message not in warnings_set:
        print(f"WARNING : {message}")
        warnings_set.add(message)   


# Update the configuration (config = input_directory, output_file, excluded_directories, excluded_files) using the contents of config_file.txt
def extract_config(config_file,config) :
    if not os.path.exists(config_file):
        return config # Return the original config if the file is not found
    input_directory, output_file, excluded_directories, excluded_files, define_list = config
    with open(config_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            line=line.strip()
            if line.lower().startswith("input_directory ="):
                value = line.split("=")[1].strip().strip('"')
                if not input_directory:  
                    input_directory = value
            elif line.lower().startswith("output_file ="):
                value = line.split("=")[1].strip().strip('"')
                if not output_file: 
                    output_file = value
            elif line.lower().startswith("excluded_directories ="):
                value = line.split("=")[1].strip().strip('"')
                if not excluded_directories: 
                    excluded_directories = value.split(',')
            elif line.lower().startswith("excluded_files ="):
                value = line.split("=")[1].strip().strip('"')
                if not excluded_files: 
                    excluded_files = value.split(',')
            elif line.lower().startswith("define_list ="):
                value = line.split("=")[1].strip().strip('"')
                if not define_list:  
                    define_list = value.split(',')
        return input_directory, output_file, excluded_directories, excluded_files, define_list
    
    
def help ():
    print("""
DEGUG:
------
          
The variable `DEBUG` enables all warnings for debugging purposes. This can be disabled by
modifying its state directly in the script if detailed warnings are not needed.
          
Usage:
------   

There are two main usage scenarios:

1. Simple Usage (without configuration files):
   The user provides the path to the directory containing Verilog files as an argument.
   Optionally, the user can specify the output path for the generated sdf.csv file.

   Example:
   python program.py <verilog_directory_path> [sdf_csv_output_path]

   - <verilog_directory_path>: Path to the directory containing Verilog files.
   - [sdf_csv_output_path]: Optional. Path to the output sdf.csv file. If not provided, 
                           the default is '<Verilog_directory_path>/sdf.csv'.

2. Advanced Usage (with a configuration file):
   The user provides a configuration file that specifies additional parameters, including
   directories and files to exclude from processing. 

   By default, the configuration file is `./config_verilog.txt`, but this can be overridden
   by specifying the path to the configuration file.

   Example:
   python program.py <config_file_path>

   - <config_file_path>: Path to the configuration file (e.g., "/path/to/config.txt").

Configuration File:
-------------------
The configuration file must be written in the following format to ensure proper functionality:

  INPUT_DIRECTORY = "/path/to/verilog_files"
  OUTPUT_FILE = "/path/to/output/sdf.csv"
  EXCLUDE_DIRECTORIES = exclude_dir_1, exclude_dir_2
  EXCLUDE_FILES = exclude_file_1.verilog, exclude_file_2.verilog
  define_list = define_1,define_2


This format allows the user to define:
  - Input directory for Verilog files.
  - Output path for the generated sdf.csv file.
  - Directories and files to exclude from processing.

Notes:
------
- To modify the default configuration file, update the `default_config_file` variable in the script.
- Ensure that the configuration file is formatted correctly to avoid processing errors.
""")
    

# Remove comments from Verilog code to avoid disrupting regex functionality
def remove_comments(verilog_code):                                                            
    verilog_code = re.sub(r'//.*', '', verilog_code)                                                
    verilog_code = re.sub(r'/\*.*?\*/', '', verilog_code, flags=re.DOTALL)                           
    verilog_code = re.sub(r'function\s.*?endfunction', '', verilog_code, flags=re.DOTALL) 
    return verilog_code
    
# Extract the module name from Verilog code
def find_module_name(verilog_code):
    module_pattern = r'module\s*(\w+)'  # Search key-word "module" followed by the module_name
    match = re.search(module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip().lower() if match else None

# Return [(module_1_name,module_1_code),(module_2_name,module_2_code),...]
def find_modules(verilog_code):
    module_pattern =  r'(module\s+(\w+)\s*(?:#\s*\(.*?\))?\s*\((.*?\)\s*;.*?)endmodule)'
    matches = re.findall(module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    if matches :
        return [(match[1].lower(), match[0]) for match in matches]
    return 0

# Return the size of the signal in bits based on its type 
def size_of_signal(signal_type):
    size_pattern = r'\[\s*(\d+)\s*(?:-\s*(\d+))?\s*:\s*(\d+)\s*\]'
    size_pattern_generic = r'\[\s*((?:\w+)|(?:\(.*?\))|(?:[\d\w]+\s*[\*\/]\s*[\d\w]+)|(?:[\w]+\s*[\+\-]\s*[\w]+))\s*([\-\+]\s*\d+)?\s*([\-\+]\s*\d+)?\s*:\s*(\d+)\s*\]'
    integer_pattern = r'integer(.*?)'
    if (match:=re.search(integer_pattern,signal_type,re.DOTALL | re.IGNORECASE)):
        signal_size = '32'
    elif (match:=re.search(size_pattern,signal_type,re.DOTALL | re.IGNORECASE)):
        signal_size = str(int(match.group(1))-(int(match.group(2)) if match.group(2) is not None else 0)-int(match.group(3))+1)
    elif (match:=re.search(size_pattern_generic,signal_type,re.DOTALL | re.IGNORECASE)) :
        if((int(match.group(2).replace(" ","")) if match.group(2) is not None else 0)+(int(match.group(3).replace(" ","")) if match.group(3) is not None else 0)+1-int(match.group(4))) == 0 :
            signal_size = match.group(1)
        elif ((int(match.group(2).replace(" ","")) if match.group(2) is not None else 0)+(int(match.group(3).replace(" ","")) if match.group(3) is not None else 0)+1-int(match.group(4))) < 0 :
            signal_size = match.group(1)+str(1+(int(match.group(2).replace(" ","")) if match.group(2) is not None else 0)+(int(match.group(3).replace(" ","")) if match.group(3) is not None else 0)-int(match.group(4)))
        elif ((int(match.group(2).replace(" ","")) if match.group(2) is not None else 0)+(int(match.group(3).replace(" ","")) if match.group(3) is not None else 0)+1-int(match.group(4))) > 0 :
            signal_size = match.group(1)+"+"+str(1+(int(match.group(2).replace(" ","")) if match.group(2) is not None else 0)+(int(match.group(3).replace(" ","")) if match.group(3) is not None else 0)-int(match.group(4)))
    elif ((signal_type.strip().lower()=='wire')|(signal_type.strip().lower()=='reg')) :
        signal_size = '1'
    else :
        signal_size = 'unknown'
        if(DEBUG == True) :
            # When debug mode is enabled
            log_warning(f'size of {signal_type} is unknown')  
    return signal_size

# Manage ifdef, ifndef with define_list : return the code without undefined code section
def manage_define(verilog_code,define_list) :
    pattern_clean = r"^`(?!ifdef|ifndef|else|include)\w.*"
    verilog_code = re.sub(pattern_clean, "", verilog_code, flags=re.MULTILINE|re.IGNORECASE) # Deleate lines with '`' wich is not followed by ifdef,ifned,else and endif
    ifdef_pattern = r'`ifdef\s*(\w+)\s*([^`]*)(?:`else([^`]*))?`endif'
    ifndef_pattern = r'`ifndef\s*(\w+)\s*([^`]*)(?:`else([^`]*))?`endif'
    while((re.search(ifdef_pattern,verilog_code,re.IGNORECASE|re.DOTALL)!=None)|(re.search
                                                                                 (ifndef_pattern,verilog_code,re.IGNORECASE|re.DOTALL)!=None)):
        match_1 = re.search(ifdef_pattern,verilog_code,re.IGNORECASE|re.DOTALL)         
        if match_1 :
            if any(match_1.group(1) in define_element for define_element in define_list):
                verilog_code = re.sub(ifdef_pattern,match_1.group(2),verilog_code,count=1,flags=re.DOTALL|re.IGNORECASE)
            else : 
                if (match_1.group(3)==None) :
                    verilog_code = re.sub(ifdef_pattern,'',verilog_code,count=1,flags=re.DOTALL|re.IGNORECASE)
                else :
                    verilog_code = re.sub(ifdef_pattern,match_1.group(3),verilog_code,count=1,flags=re.DOTALL|re.IGNORECASE)
        match_2 = re.search(ifndef_pattern,verilog_code,re.IGNORECASE|re.DOTALL)
        if match_2:
            if any(match_2.group(1) in define_element for define_element in define_list):
                if (match_2.group(3)==None) :
                    verilog_code = re.sub(ifndef_pattern,'',verilog_code,count=1,flags=re.DOTALL|re.IGNORECASE)
                else :
                    verilog_code = re.sub(ifndef_pattern,match_2.group(3),verilog_code,count=1,flags=re.DOTALL|re.IGNORECASE)
            else : 
                verilog_code = re.sub(ifndef_pattern,match_2.group(2),verilog_code,count=1,flags=re.DOTALL|re.IGNORECASE)
    return verilog_code
    
# Return the following type of list : [[module_1_name,[[port_1_name,direction(in/out/inout),type],...]],...]
def extract_module(module_name, module_code):
    ports = []
    port_declarations = []
    multiple_port_pattern    = r'\b(input|output|inout)\s*(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)?\s*(\[\s*[\w\d\s\(\)\:\-\+/\*]+\])?\s*(\w+(?:\s*,\s*((?!input\b|output\b|inout\b)\w+))*)'
    port_lines = module_code.split('\n')
    for line in port_lines :
        result = re.search(multiple_port_pattern,line,re.IGNORECASE|re.DOTALL)
        if result : 
            name_list = result.group(4).split(',')
            for i in range (len(name_list)):
                port_declarations.append([result.group(1),(result.group(2) if result.group(2) is not None else "").strip()+" "+(result.group(3) if result.group(3) is not None else "").strip(),name_list[i]])
    for direction, port_type, port_name in port_declarations:
        port_type = re.sub(r'[\t\n\r]+', '', port_type).strip().lower()  # Deleate \t, \n, \r
        port_type = re.sub(r'\)\s*\)', ')', port_type)  # Replace )) by )
        if 'wire' not in port_type and 'reg' not in port_type:
            port_type = 'wire ' + port_type

        ports.append([
            port_name.strip().lower(),   
            direction.strip().lower(),  
            port_type.strip().lower()        
        ])
    module = [module_name,ports]

    return module

# Return the following type of list  : [port_name,direction,type] if the port is found else warning 
def find_port(port_name, module_name,module_list) : 
    for i in range (len(module_list)) :
        if (module_list[i][1][0] == module_name) :
            for j in range(len(module_list[i][1][1])) :
                if module_list[i][1][1][j][0] == port_name : 
                    return module_list[i][1][1][j]
            log_warning(f"port {port_name} of module {module_name} is not found \n \n")
            return ['','unknow']
    log_warning(f"module {module_name} is not found")
    return ['','unknow']
    
# Extract all submodules from code, return : [[inst_1,sub_module_name,submodule_ports],...]
def extract_submodule_list(verilog_code, module_list) :
    sub_module_pattern = r'(?:(?:\w+)\s*#\s*\(\s*parameter )|(\w+)\s*(?:#\s*\((?:.*?(?:\(.*?\)\s*)*)*\))?\s*(\w+)\s*\(\s*\.(.*?)(?:\)\s*\);)'
    signal_inst_pattern = r'\s*\.(\w+)\s*\(\s*(\w+)\s*(?:\[.*?\])?\s*\)'

    matches = re.findall(sub_module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    try:
        matches.remove(('','',''))
    except ValueError:
        pass 

    submodules_inst = []
    for i in range (len(matches)) :

        module_name,module_inst,ports = matches[i][0].strip().lower(),matches[i][1].strip().lower(), matches[i][2].strip().lower()
        ports = '.'+ports+')'  # the first . is captured by the regex
        submodule_ports = []
        port_lines = ports.split(',')
        for line in port_lines:
            matches_2 = re.search(signal_inst_pattern,line,re.IGNORECASE | re.DOTALL )
            if matches_2 :
                signal_full = matches_2[2]
                port = matches_2[1]
                signal_match = re.match(r'(\w+)', signal_full)
                signal = signal_match.group(1) if signal_match else signal_full
                submodule_ports.append([port.strip().lower(),signal.strip().lower(),find_port(port,module_name,module_list)[1]])
        submodules_inst.append([
            module_inst.lower(),
            module_name.lower(),
            submodule_ports ])
    return submodules_inst

# Extract internal signals for each module code section
def extract_internal_signals (module_code,module_name,submodule_list):
    signals = []
    signal_declarations_full = []
    multiple_signal_pattern    = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),;]|(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)\s*(\[\s*[\w\d\s\:\-\+\(\)/\*]+\])?\s*((?:(?!input\b|output\b|inout\b)\w+)(?:\s*,\s*((?!input\b|output\b|inout\b)\w+))*)'
    code_lines = module_code.split(';')
    for line in code_lines :
        result = re.search(multiple_signal_pattern,line,re.IGNORECASE|re.DOTALL)
        if result : 
            name_list = (result.group(3) if result.group(1) is not None else "").split(',')
            for i in range (len(name_list)):
                signal_declarations_full.append([(result.group(1) if result.group(1) is not None else "").strip() +" "+(result.group(2) if result.group(2) is not None else "").strip(),name_list[i]])
    # Deleate empty signals
    signal_declarations = [sublist for sublist in signal_declarations_full if sublist != [' ', '']]

    for signal_type, signal_name in signal_declarations: 
        instance_scr_name = []
        instance_dst_name = []
        module_dst_name = []
        module_src_name = []
        signal_size = size_of_signal(signal_type)

        for instance, submodule, ports  in submodule_list :
            for port in ports : 
                if (port[1]==signal_name.strip().lower()) :
                    if ((port [2] == 'input') | (port [2] == 'inout')) : 
                        instance_dst_name.append(instance)
                        module_dst_name.append(submodule)
                    
                    if ((port [2] == 'output' )| (port [2] == 'inout')) :
                        instance_scr_name.append(instance)
                        module_src_name.append(submodule)
        if (instance_dst_name == []) : 
            instance_dst_name.append(module_name) 
            module_dst_name.append(module_name)
        if (instance_scr_name == []) :
            module_src_name.append(module_name)
            instance_scr_name.append(module_name)    
        signals.append([signal_name.strip().lower(), signal_type.strip().lower(),signal_size.strip().lower(),instance_scr_name,module_src_name,instance_dst_name,module_dst_name])
    return signals

# Extract signals from module ports for each module code section : [[port_name_1,dir,size,instance_src_name,module_src_name,instance_dst_name,module_dst_name],[port_name_2,dir,...],...]
def extract_external_signals (module_list,module_name,submodule_list) :
    signals = []
    module = []
    for i in range (len(module_list)) :
        if (module_list[i][1][0]==module_name.strip().lower()) :
            module = module_list[i][1][1]
    if (module==[]) :
        log_warning(f'module {module_name} is not found')
    for port in module :
        instance_scr_name = []
        instance_dst_name = []
        module_dst_name = []
        module_src_name = []
        signal_size=size_of_signal(port[2])
        if((port[1] == 'input') | (port[1] == 'inout')) :
            module_src_name.append('input')
            instance_scr_name.append('input')
        if ((port[1] == 'output') | (port[1] == 'inout')) : 
            module_dst_name.append('output')
            instance_dst_name.append('output')
        for instance, component, ports  in submodule_list :
            for port_a in ports : 
                if (port_a[1]==port[0]) :
                    if ((port_a [2] == 'input') | (port_a [2] == 'inout')) : 
                        instance_dst_name.append(instance)
                        module_dst_name.append(component)

                    if ((port_a [2] == 'output' )| (port_a [2] == 'inout')) :
                        instance_scr_name.append(instance)
                        module_src_name.append(component)
        if (instance_dst_name == []) : 
            instance_dst_name.append(module_name) 
            module_dst_name.append(module_name)
        if (instance_scr_name == []) :
            module_src_name.append(module_name)
            instance_scr_name.append(module_name)    
        signals.append([port[0], port[2],signal_size.strip().lower(),instance_scr_name,module_src_name,instance_dst_name,module_dst_name])
    return signals 

def remove_redundant_signals (internal_signals,external_signals) :
    for i in range (len(external_signals)): 
        for j in range(len(internal_signals)) :
            if (external_signals[i][0]==internal_signals[j][0]) : 
                external_signals[i][1]=internal_signals[j][1]
                external_signals[i][2]=internal_signals[j][2]
                del internal_signals[j]
                break
    return internal_signals, external_signals



        
def convert_to_csv_string(value): # (eg : [a,b,c] => "a,b,c")
    if isinstance(value, (list, tuple)):
        return ",".join(map(str, value))  
    return str(value)


def write_signals_to_csv(input_file_name,output_file, verilog_code, module_list):
        if find_modules(verilog_code):
            with open(output_file, mode='a', newline='') as file_csv:
                writer = csv.writer(file_csv)
                writer = csv.writer(file_csv,delimiter= ';')
                writer.writerow([f"file_name({input_file_name})"])
                writer.writerow(["component", "signal_name", "type", "size","instance src", "component_src", "instance_dst", "component_dst"])
                for module_name,module_code in find_modules(verilog_code) :
                    submodule_list = extract_submodule_list(module_code,module_list)
                    internal_signals = extract_internal_signals(module_code,module_name,submodule_list)
                    external_signals = extract_external_signals(module_list,module_name,submodule_list)
                    internal_signals,external_signals = remove_redundant_signals(internal_signals,external_signals)
                    for signal in external_signals:
                        writer.writerow([
                        module_name,
                        signal[0],
                        signal[1],
                        signal[2],
                        convert_to_csv_string(signal[3]),
                        convert_to_csv_string(signal[4]),
                        convert_to_csv_string(signal[5]),
                        convert_to_csv_string(signal[6])
                    ])
                    for signal in internal_signals:
                        writer.writerow([
                            "Internal",
                            signal[0],
                            signal[1],
                            signal[2],
                            convert_to_csv_string(signal[3]),
                            convert_to_csv_string(signal[4]),
                            convert_to_csv_string(signal[5]),
                            convert_to_csv_string(signal[6])
                        ])

def process_files_in_directory(directory_path, output_txt_path, define_list,excluded_directories,excluded_files):
    module_list = []
    if not os.path.exists(directory_path):
        print(f"The specified directory {directory_path} does not exist.\n")
    else:
        try : 
            open(output_txt_path, 'w').close()                                                                             
            for root, dirs, files in os.walk(directory_path):
                dirs[:] = [d for d in dirs if d not in excluded_directories]
                files[:] = [f for f in files if f not in excluded_files]      
                for file_name in files:
                    if file_name.lower().endswith(".v"):                                                           
                        file_path = os.path.join(root, file_name)
                        try:
                            with open(file_path, "r") as file:
                                verilog_code_full = file.read()
                                verilog_code = remove_comments(verilog_code_full)
                                verilog_code = manage_define(verilog_code,define_list)
                                if find_modules(verilog_code):
                                    for module_name,module_code in find_modules(verilog_code) :
                                        module_list.append([file_name,extract_module(module_name,module_code)]) 
                        except FileNotFoundError:
                            print(f"Error: File '{file_path}' not found.")
        except KeyboardInterrupt :
            print (f"Module of file : {file_name} is extacted")
        try :
            for root, dirs, files in os.walk(directory_path):
                dirs[:] = [d for d in dirs if d not in excluded_directories]
                files[:] = [f for f in files if f not in excluded_files]      
                # Extract all modules in directory in modules
                for file_name in files:

                    if file_name.lower().endswith(".v"):                                                           
                        file_path = os.path.join(root, file_name)
                        try:
                            with open(file_path, "r") as file:
                                verilog_code_full = file.read()
                                verilog_code = remove_comments(verilog_code_full)
                                verilog_code = manage_define(verilog_code,define_list)
                                write_signals_to_csv(file_name,output_txt_path,verilog_code,module_list)
                        except FileNotFoundError:
                            print(f"Error: File '{file_path}' not found.")
        except KeyboardInterrupt :
            print (f"Signals of file : {file_name} are extacted")          

        if os.path.getsize(output_txt_path) == 0 :
            print(f".v files was not found. Or there is simply no .v file in project.\n")
        else :
            print(f".v parsing done successfully\n")    



# Main program
def main():
    
    config = (0,0,[],[],[])
    if DEBUG : 
        print('DEBUG Mode enable')
    else : 
        print('DEBUG Mode disable')
    if len(sys.argv) > 1 :
        if (sys.argv[1] == "-help") :
            help()
            return 0
        for arg in sys.argv :
            if arg.endswith(".txt") :
                print (f"Config file : {arg}")
                config=extract_config(arg,config)
        input_directory,output_file,excluded_directories,excluded_files,define_list=config
        for arg in sys.argv :
            if arg.endswith(".csv") :
                output_file=arg
        for arg in sys.argv : 
            if not (arg.endswith(".txt")|arg.endswith(".csv")|arg.endswith(".py")) :
                input_directory = arg
        config = (input_directory,output_file,excluded_directories,excluded_files,define_list)
    input_directory,output_file,excluded_directories,excluded_files,define_list=extract_config(default_config_file,config)
    if input_directory == 0 : 
        print ("Put input_directory_file on argument")
        sys.exit(1)
    elif (output_file == 0) :
        output_file = input_directory+r"\sdf.csv"
    
        
    print(f"Input Directory: {input_directory}")
    print(f"Output File Path: {output_file}")
    print (f"Excluded_directories {excluded_directories}")
    print (f"Excluded_files {excluded_files}")   
    print (f"Define list : {define_list}")
    process_files_in_directory(input_directory,output_file,define_list,excluded_directories,excluded_files)



if __name__ == "__main__":
    main()
