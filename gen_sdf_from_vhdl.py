import re
import csv
import os
import sys

DEBUG = True
warnings_set = set() # Store warnings that have already been logged

default_config_file = r".\config_vhdl.txt"

# Log warnings without logging the same message more than once
def log_warning(message):
    global warnings_set
    if message not in warnings_set:
        print(f"WARNING : {message}")
        warnings_set.add(message)  

# Update the configuration (config = input_directory, output_file, excluded_directories, excluded_files) using the contents of config_file.txt
def extract_config(config_file,config) :
    if not os.path.exists(config_file):
        return config  # Return the original config if the file is not found
    input_directory, output_file, excluded_directories, excluded_files = config
    with open(config_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            line=line.strip()
            if line.startswith("input_directory ="):
                value = line.split("=")[1].strip().strip('"')
                if not input_directory:  
                    input_directory = value
            elif line.startswith("output_file ="):
                value = line.split("=")[1].strip().strip('"')
                if not output_file:  
                    output_file = value
            elif line.startswith("excluded_directories ="):
                value = line.split("=")[1].strip().strip('"')
                if not excluded_directories:  
                    excluded_directories = value.split(',')
            elif line.startswith("excluded_files ="):
                value = line.split("=")[1].strip().strip('"')
                if not excluded_files: 
                    excluded_files = value.split(',')
        return input_directory, output_file, excluded_directories, excluded_files
    
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
   The user provides the path to the directory containing VHDL files as an argument.
   Optionally, the user can specify the output path for the generated sdf.csv file.

   Example:
   python program.py <vhdl_directory_path> [sdf_csv_output_path]

   - <vhdl_directory_path>: Path to the directory containing VHDL files.
   - [sdf_csv_output_path]: Optional. Path to the output sdf.csv file. If not provided, 
                           the default is '<vhdl_directory_path>/sdf.csv'.

2. Advanced Usage (with a configuration file):
   The user provides a configuration file that specifies additional parameters, including
   directories and files to exclude from processing. 

   By default, the configuration file is `./config_vhdl.txt`, but this can be overridden
   by specifying the path to the configuration file.

   Example:
   python program.py <config_file_path>

   - <config_file_path>: Path to the configuration file (e.g., "/path/to/config.txt").

Configuration File:
-------------------
The configuration file must be written in the following format to ensure proper functionality:

  INPUT_DIRECTORY = "/path/to/vhdl_files"
  OUTPUT_FILE = "/path/to/output/sdf.csv"
  EXCLUDE_DIRECTORIES = exclude_dir_1, exclude_dir_2
  EXCLUDE_FILES = exclude_file_1.vhdl, exclude_file_2.vhdl


This format allows the user to define:
  - Input directory for VHDL files.
  - Output path for the generated sdf.csv file.
  - Directories and files to exclude from processing.

Notes:
------
- To modify the default configuration file, update the `default_config_file` variable in the script.
- Ensure that the configuration file is formatted correctly to avoid processing errors.
""")
    

# Remove comments from VHDL code to avoid disrupting regex functionality
def remove_comments(vhdl_code):                                                            
    code = re.sub(r'--.*', '', vhdl_code)
    return code

# Extract the entity name from VHDL code
def find_entity_name(vhdl_code):
    entity_pattern = r'\bentity\s+(\w+)\s+is\b'
    match = re.search(entity_pattern, vhdl_code, re.IGNORECASE)
    return match.group(1) if match else None


# Return the size of the signal in bits based on its type (Note: Generic names in the signal type are not replaced by assigned values) 
def signal_type_to_size(signal_type):
    size_pattern = r'(?:std_logic_vector|std_ulogic_vector|unsigned)\s*\(\s*(\d+)\s*(?:-\s*(\d+))?\s*downto\s*(\d+)\s*\)'
    size_pattern_generic = r'(?:std_logic_vector|std_ulogic_vector|unsigned)\s*\(\s*((?:\w+)|(?:\(.*?\)))\s*(?:-\s*(\d+))?\s*(?:-\s*(\d+))?\s*downto\s*(\d+)\s*\)'
    size_pattern_range = r'(?:std_logic_vector|std_ulogic_vector|unsigned)\s*\(\s*(\w+)\'range\s*\)'
    integer_pattern = r'integer(.*?)'
    if ((signal_type.strip().lower()=='std_logic')|(signal_type.strip().lower()=='std_ulogic')) :
        signal_size = '1'
    elif(signal_type.strip().lower() == 'byte') : 
        signal_size = '8'
    elif (match:=re.search(integer_pattern,signal_type,re.DOTALL | re.IGNORECASE)):
        signal_size = '32'
    elif (match:=re.search(size_pattern,signal_type,re.DOTALL | re.IGNORECASE)):
        signal_size = str(int(match.group(1))-(int(match.group(2)) if match.group(2) is not None else 0)-int(match.group(3))+1)
    elif (match:=re.search(size_pattern_generic,signal_type,re.DOTALL | re.IGNORECASE)) :
        if((-(int(match.group(2)) if match.group(2) is not None else 0)-(int(match.group(3)) if match.group(3) is not None else 0)+1-int(match.group(4)))==0) :
            signal_size = match.group(1)
        else : 
            signal_size = match.group(1)+str(1-(int(match.group(2)) if match.group(2) is not None else 0)-(int(match.group(3)) if match.group(3) is not None else 0)-int(match.group(4)))
    elif(match:=re.search(size_pattern_range,signal_type,re.DOTALL | re.IGNORECASE)) :
        signal_size = f"{match.group(1)} size"
    else :
        signal_size = 'unknown' 
        if(DEBUG) :
            # When debug mode is enabled
            log_warning(f'size of {signal_type} is unknown')
    return signal_size

# Return a list of functions, each element containing the function name and its code 
def extract_process(vhdl_code) : 
    
    process_pattern = r'((?:(\w+)\s*:)?\s*process.*?(?:end\s*(?:process|\2)))'

    matches = re.findall(process_pattern, vhdl_code, re.IGNORECASE | re.DOTALL)
    process_list =[]
    for i in range(len(matches)) : 
        process_list.append(["process "+matches[i][1],matches[i][0]])
    return process_list

# Return a list of functions, each element containing the function name and its code 
def extract_functions(vhdl_code) : 
    function_pattern = r'(function\s*(\w+).*?(?:end\s*(?:function|\2))\s*;)'
    matches = re.findall(function_pattern, vhdl_code, re.IGNORECASE | re.DOTALL)
    function_list =[]
    for i in range(len(matches)) : 
        function_list.append(["function "+matches[i][1],matches[i][0]])
    return function_list

# Return a list with [variable_name, variable_type, variable_size, process/function/instance name]
def extract_variables(list) :
    variable_pattern = r'variable\s*(\w+)\s*:\s*([\w\s\(\)\'\+\-]+);?'
    variables = []
    for i in range(len(list)) :
        matches = re.findall(variable_pattern,list[i][1],re.DOTALL|re.IGNORECASE)
        for j in range(len(matches)) :
            variables.append([matches[j][0],matches[j][1],signal_type_to_size(matches[j][1]),list[i][0]])
    return variables
                         

def extract_component_ports(vhdl_code):

    component_pattern = r'COMPONENT\s+(\w+)\s*(?:IS\s*)?(?:GENERIC\s*\((.*?)\)\s*;)?\s*port\s*\((.*?)end\s+component\s*'

    components_declarations = re.findall(component_pattern, vhdl_code, re.IGNORECASE | re.DOTALL)

    components = [] # list all components : [[comp_1_name,comp_1_port],[comp_2_name,comp_2_port],...]
    for component_name, generic, port_lines in components_declarations : 
        component = [component_name.strip().lower()]
        ports=[]
        port_declarations = []
        port_lines = port_lines.split(';')
        for line in port_lines :
            multiple_port_pattern    = r'((?:\w+\s*,\s*)*\w+)\s*:\s*(\bin\b|\bout\b|inout)\s*([\w\s\(\)\'+-]+)\s*'
            result = re.search(multiple_port_pattern,line,re.IGNORECASE|re.DOTALL)
            if result :
                name_list = result.group(1).split(',')
                for j in range (len(name_list)):
                    port_declarations.append([name_list[j],result.group(2),result.group(3)])
        
        for port_name, direction, port_type in port_declarations:
            port_type = re.sub(r'[\t\n\r]+', '', port_type).strip().lower()  # Earase \t, \n, \r
            port_type = re.sub(r'\)\s*\)', ')', port_type) # Replace )) by )
            if ((re.search(r'\(',port_type)== None)&(re.search(r'\)',port_type)!=None)) : 
                port_type = re.sub(r'\)', '', port_type)

            ports.append([
                port_name.strip().lower(), 
                direction.strip().lower(),  
                port_type.strip().lower()          
            ])
        component.append(ports) 
        components.append(component)
    return components

# Return a list of ports: [[port_name, direction (in/out/inout), type],...]
def extract_module_ports(vhdl_code):

    port_pattern = r'entity\s+\w+\s+is(?:.*?)port\s*\((.*?)end\s+'
    match = re.search(port_pattern, vhdl_code, re.IGNORECASE | re.DOTALL)

    ports = []
    if match:
        port_declarations = []
        port_lines = match.group(1)
        port_lines = port_lines.split(';')
        for line in port_lines :
            multiple_port_pattern    = r'((?:\w+\s*,\s*)*\w+)\s*:\s*(\bin\b|\bout\b|inout)\s*([\w\s\(\)\'+-]+)\s*'
            result = re.search(multiple_port_pattern,line,re.IGNORECASE|re.DOTALL)
            if result :
                name_list = result.group(1).split(',')
                for j in range (len(name_list)):
                    port_declarations.append([name_list[j],result.group(2),result.group(3)])
    
        for port_name, direction, port_type in port_declarations:
            port_type = re.sub(r'[\t\n\r]+', '', port_type).strip().lower()  # Earase \t, \n, \r
            port_type = re.sub(r'\)\s*\)', ')', port_type)  # Replace )) by )
            if ((re.search(r'\(',port_type)== None)&(re.search(r'\)',port_type)!=None)) : 
                port_type = re.sub(r'\)', '', port_type)
            ports.append([
                port_name.strip().lower(),   
                direction.strip().lower(),  
                port_type.strip().lower()        
            ])
    return ports


# Extract internal signals for each module code section
def extract_internal_signals(vhdl_code,port_map_list, entity_name):
    signals = []
    matches = []    
    multiple_signal_pattern = r'signal\s+((?:\w+\s*,\s*)*\w+)\s*:\s*([\w\s\(\)\'+-]+)\s*;?'
    matches_2 = re.findall(multiple_signal_pattern,vhdl_code,re.IGNORECASE|re.DOTALL)
    for matche_2 in matches_2 : 
        matche_2_list = matche_2[0].split(',')
        for j in range (len(matche_2_list)) :
            matches.append([matche_2_list[j],matche_2[1]])

    
    for signal_name, signal_type in matches: 
        instance_scr_name = []
        instance_dst_name = []
        module_dst_name = []
        module_src_name = []
        signal_size = signal_type_to_size(signal_type)
        for instance, component, ports  in port_map_list :
            for port in ports : 
                if (port[1]==signal_name.strip().lower()) :
                    if ((port [2] == 'in') | (port [2] == 'inout')) : 
                        instance_dst_name.append(instance)
                        module_dst_name.append(component)
                    
                    if ((port [2] == 'out' )| (port [2] == 'inout')) :
                        instance_scr_name.append(instance)
                        module_src_name.append(component)
        if (instance_dst_name == []) : 
            instance_dst_name.append(entity_name) 
            module_dst_name.append(entity_name)
        if (instance_scr_name == []) :
            module_src_name.append(entity_name)
            instance_scr_name.append(entity_name)    
        signals.append([signal_name.strip().lower(), signal_type.strip().lower(),signal_size.strip().lower(),instance_scr_name,module_src_name,instance_dst_name,module_dst_name])
    
    return signals

# Extract signals from module ports for each module code section
def extract_external_signals (module, port_map_list,entity_name) :
    signals = []
    for port in module :
        instance_scr_name = []
        instance_dst_name = []
        module_dst_name = []
        module_src_name = []
        signal_size = signal_type_to_size(port[2])
        if((port[1] == 'in') | (port[1] == 'inout')) :
            module_src_name.append('input')
            instance_scr_name.append('input')
        if ((port[1] == 'out') | (port[1] == 'inout')) : 
            module_dst_name.append('output')
            instance_dst_name.append('output')
        for instance, component, ports  in port_map_list :
            for port_a in ports : 
                if (port_a[1]==port[0]) :
                    if ((port_a [2] == 'in') | (port_a [2] == 'inout')) : 
                        instance_dst_name.append(instance)
                        module_dst_name.append(component)
                    
                    if ((port_a [2] == 'out' )| (port_a [2] == 'inout')) :
                        instance_scr_name.append(instance)
                        module_src_name.append(component)
        if (instance_dst_name == []) : 
            instance_dst_name.append(entity_name) 
            module_dst_name.append(entity_name)
        if (instance_scr_name == []) :
            module_src_name.append(entity_name)
            instance_scr_name.append(entity_name)    
        signals.append([port[0], port[2],signal_size,instance_scr_name,module_src_name,instance_dst_name,module_dst_name])
    return signals 
        
# Return the direction of a port (in/out/inout)
def dir_finding(component_name,port_name,component_list) : 
    for component_name_i, ports in component_list : 
        if (component_name_i==component_name) : 
            for port in ports : 
                if (port_name == port[0]) :
                    return port[1]
                

# Return a list of component instance : [[instance,component,[port,signal,dir(in/out/inout)],...],...]
def extract_port_map(vhdl_code, component_list) :
    port_map_pattern = r'(\w+)\s*:\s*(\w+)\s+(?:generic\s+map\s*\(.*?\)\s*)?port\s+map\s*\((.*?)\)\s*;'

    matches = re.findall(port_map_pattern, vhdl_code, re.IGNORECASE | re.DOTALL)
    port_maps = []
    for instance_name, component_name, ports in matches:
        port_mapping = []
        port_lines = ports.split(',')
        for i in range(len(port_lines)):
            if re.search('=>',port_lines[i],re.IGNORECASE|re.DOTALL) != None :
                port, signal_full = [item.strip().lower() for item in port_lines[i].split('=>',maxsplit=1)]
                
            else : # Case where the port map is assigned in this manner: port map (clk, in_a, out_b, ...)"
                signal_full = port_lines[i]
                for component_name_i, component_ports in component_list : 
                    if (component_name_i==component_name) : 
                        port = component_ports[i][0] # Use only the order of the component's ports to associate them with signals"
                        break
            signal_match = re.match(r'(\w+)', signal_full)
            signal = signal_match.group(1) if signal_match else signal_full
            port_mapping.append([port,signal.strip().lower(),dir_finding(component_name.lower(),port,component_list)])
        port_maps.append([
            instance_name.lower(),
            component_name.lower(),
            port_mapping 
        ])
    return port_maps

def find_package (vhdl_code,directory_path):
    library_pattern = r'library\s*\w+\s*;\s*use\s*\w+\.(\w+)\.all;'
    matches = re.findall(library_pattern,vhdl_code,re.DOTALL|re.IGNORECASE)
    components=[]
    for match in matches :
        for root, dirs, files in os.walk(directory_path):
                dirs[:] = [d for d in dirs if d not in ['bench', 'sim', 'testbench']]   
                for file_name in files:
                    if (file_name.lower()==(match.lower()+'.vhd')):
                        file_path = os.path.join(root, file_name)
                        try : 
                            with open(file_path, "r") as file:
                                vhdl_code_full = file.read()
                                vhdl_code = remove_comments(vhdl_code_full) 
                                components = components + extract_component_ports(vhdl_code)  
                        except FileNotFoundError:
                            print(f"Error: File '{file_path}' not found.")
    return components


def convert_to_csv_string(value): # (eg : [a,b,c] => "a,b,c")
    if isinstance(value, (list, tuple)):
        return ",".join(map(str, value))  
    return str(value)

def write_signals_to_csv(input_file_name,output_file_path, vhdl_code,components_list_extended):
    if (find_entity_name(vhdl_code)==None) :
        if(DEBUG) :
            print(f"Warning : No entity found in {input_file_name}")
    else :
        entity_name = find_entity_name(vhdl_code)
        component_list = extract_component_ports(vhdl_code)+components_list_extended
        module = extract_module_ports(vhdl_code)
        port_map_list = extract_port_map(vhdl_code,component_list)
        external_signals = extract_external_signals(module,port_map_list, entity_name)
        internal_signals = extract_internal_signals(vhdl_code,port_map_list, entity_name)
        variables = extract_variables(extract_functions(vhdl_code)+extract_process(vhdl_code))
        with open(output_file_path, mode='a', newline='') as file_csv:
            writer = csv.writer(file_csv)
            writer = csv.writer(file_csv,delimiter= ';')
            writer.writerow([f"file_name({input_file_name})"])
            writer.writerow(["component", "signal_name", "type", "size","instance src", "component_src", "instance_dst", "component_dst"])
            
            for signal in external_signals:
                writer.writerow([
                entity_name,
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
            for variable in variables : 
                writer.writerow([
                    "Variable",
                    variable[0],
                    variable[1],
                    variable[2],
                    variable[3],
                    variable[3],
                    variable[3],
                    variable[3]
                ])

# Process all signals extractions in vhdl file       
def extract (input_file_name,input_file_path,output_file_path) : 
    try:
        with open(input_file_path, "r") as file:
            vhdl_code_full = file.read()
            vhdl_code = remove_comments(vhdl_code_full)
            write_signals_to_csv(input_file_name,output_file_path, vhdl_code) 
    except FileNotFoundError:
        print(f"Error: File '{input_file_path}' not found.")

def process_files_in_directory(directory_path, output_txt_path, excluded_directories,excluded_files):
    if not os.path.exists(directory_path):
        print(f"The specified directory {directory_path} does not exist.\n")
    else:
        open(output_txt_path, 'w').close()                                                                             
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in excluded_directories]
            files[:] = [f for f in files if f not in excluded_files]     
            for file_name in files:
                if file_name.lower().endswith('.vhd'):                                                           
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, "r") as file:
                            vhdl_code_full = file.read()
                            vhdl_code = remove_comments(vhdl_code_full)
                            components_list_extended = find_package(vhdl_code,directory_path)
                            write_signals_to_csv(file_name,output_txt_path, vhdl_code,components_list_extended) 
                    except FileNotFoundError:
                        print(f"Error: File '{file_path}' not found.")
                                            
        if os.path.getsize(output_txt_path) == 0 :
            print(f".vhd files was not found. Or there is simply no .vhd file in project.\n")
        else :
            print(f".vhd parsing done successfully\n")    


# Main program entry point
def main():
    
    config = (0,0,[],[])
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
        input_directory,output_file,excluded_directories,excluded_files=config
        for arg in sys.argv :
            if arg.endswith(".csv") :
                output_file=arg
        for arg in sys.argv : 
            if not (arg.endswith(".txt")|arg.endswith(".csv")|arg.endswith(".py")) :
                input_directory = arg
        config = (input_directory,output_file,excluded_directories,excluded_files)
    input_directory,output_file,excluded_directories,excluded_files=extract_config(default_config_file,config)
    if input_directory == 0 : 
        print ("Put input_directory_file on argument")
        sys.exit(1)
    elif (output_file == 0) :
        output_file = input_directory+r"\sdf.csv"
    print(f"Input Directory: {input_directory}")
    print(f"Output File Path: {output_file}")
    print (f"Excluded_directories {excluded_directories}")
    print (f"Excluded_files {excluded_files}")   
    process_files_in_directory(input_directory,output_file,excluded_directories,excluded_files)
        


if __name__ == "__main__":
    main()
