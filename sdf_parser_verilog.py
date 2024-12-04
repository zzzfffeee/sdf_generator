import re
import csv
import os
import sys
import time

def remove_comments(verilog_code):                                                            
    verilog_code = re.sub(r'//.*', '', verilog_code)                                                
    verilog_code = re.sub(r'/\*.*?\*/', '', verilog_code, flags=re.DOTALL)                           
    verilog_code = re.sub(r'function\s.*?endfunction', '', verilog_code, flags=re.DOTALL) 
    return verilog_code


def find_module_name(verilog_code):
    """Find the name of the module."""
    module_pattern = r'module\s+(\w+)\s*\('  # Recherche le mot-clé "module" suivi du nom
    match = re.search(module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else None


def extract_module(verilog_code):

    module_pattern = r'module\s+(\w+)\s*(?:#\(.*?\))?\s*\((.*?\)\s*;.*?)endmodule'
    matches = re.findall(module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    modules = []

    if matches:
        for j in range(len(matches)) :     
            ports = []
            port_declarations = []
            single_port_pattern    = r'\b(input|output|inout)\s*(wire\b|reg\b)?\s*(\[\s*[\w\d\s\(\)\:\-]+\])?\s*(\w+)'
            double_port_pattern    = r'\b(input|output|inout)\s*(wire\b|reg\b)?\s*(\[\s*[\w\d\s\(\)\:\-]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            triple_port_pattern    = r'\b(input|output|inout)\s*(wire\b|reg\b)?\s*(\[\s*[\w\d\s\(\)\:\-]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            quad_port_pattern      = r'\b(input|output|inout)\s*(wire\b|reg\b)?\s*(\[\s*[\w\d\s\(\)\:\-]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            quintuple_port_pattern = r'\b(input|output|inout)\s*(wire\b|reg\b)?\s*(\[\s*[\w\d\s\(\)\:\-]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            sextuple_port_pattern  = r'\b(input|output|inout)\s*(wire\b|reg\b)?\s*(\[\s*[\w\d\s\(\)\:\-]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            single_port_declarations = re.findall( single_port_pattern, matches[j][1],re.IGNORECASE | re.DOTALL )
            double_port_declarations = re.findall( double_port_pattern, matches[j][1],re.IGNORECASE | re.DOTALL )
            triple_port_declarations = re.findall(triple_port_pattern, matches[j][1], re.IGNORECASE  | re.DOTALL)
            quad_port_declarations   = re.findall(quad_port_pattern, matches[j][1], re.IGNORECASE  | re.DOTALL)
            quintuple_port_declarations = re.findall(quintuple_port_pattern, matches[j][1], re.IGNORECASE | re.DOTALL)
            sextuple_port_declarations = re.findall(sextuple_port_pattern, matches[j][1], re.IGNORECASE | re.DOTALL)
        
            for i in range(len(single_port_declarations)) :
                port_declarations.append([single_port_declarations[i][0],single_port_declarations[i][1].strip()+" "+single_port_declarations[i][2],single_port_declarations[i][3]])
            for i in range(len(double_port_declarations)) : 
                port_declarations.append([double_port_declarations[i][0],double_port_declarations[i][1].strip()+" "+double_port_declarations[i][2],double_port_declarations[i][4]])
            for i in range(len(triple_port_declarations)) : 
                port_declarations.append([triple_port_declarations[i][0],triple_port_declarations[i][1].strip()+" "+triple_port_declarations[i][2],triple_port_declarations[i][5]])
            for i in range(len(quad_port_declarations)) : 
                port_declarations.append([quad_port_declarations[i][0],quad_port_declarations[i][1].strip()+" "+quad_port_declarations[i][2],quad_port_declarations[i][6]])
            for i in range(len(quintuple_port_declarations)):
                port_declarations.append([quintuple_port_declarations[i][0], quintuple_port_declarations[i][1].strip()+" "+quintuple_port_declarations[i][2], quintuple_port_declarations[i][7]])
            for i in range(len(sextuple_port_declarations)):
                port_declarations.append([sextuple_port_declarations[i][0], sextuple_port_declarations[i][1].strip()+" "+sextuple_port_declarations[i][2], sextuple_port_declarations[i][8]])
            for direction, port_type, port_name in port_declarations:
                port_type = re.sub(r'[\t\n\r]+', '', port_type).strip().lower()  # Earase \t, \n, \r
                port_type = re.sub(r'\)\s*\)', ')', port_type)  # Replace )) by )
                if 'wire' not in port_type and 'reg' not in port_type:
                    port_type = 'wire ' + port_type

                ports.append([
                    port_name.strip().lower(),   
                    direction.strip().lower(),  
                    port_type.strip().lower()        
                ])
            modules.append([matches[j][0].strip().lower(),ports])

    return modules

def find_port(port_name, module_name,module_list) : 
    for i in range (len(module_list)) :
        for j in range (len(module_list[i][1])) : 
            if (module_list[i][1][j][0]==module_name) :
                for k in range(len(module_list[i][1][j][1])) :
                    if module_list[i][1][j][1][k][0] == port_name : 
                        return module_list[i][1][j][1][k]
    print(f"WARNING : port {port_name} of module {module_name} is not found")
    return ['','unknow']


def extract_submodule_list(verilog_code, module_list) :
    sub_module_pattern = r'(?:(?:\w+)\s*#\(\s*parameter )|(\w+)\s*(?:#\((?:.*?(?:\(.*?\)\s*)*)*\))?\s*(\w+)\s*\(\s*\.(.*?)(?:\)\s*\);)'
    signal_inst_pattern = r'\s*\.(\w+)\s*\(\s*(\w+)\s*\)'

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
            matches_2 = re.match(signal_inst_pattern,line,re.IGNORECASE | re.DOTALL )
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


def extract_internal_signals (module_code,module_name,submodule_list):
    signals = []
    signal_declarations_full = []
    single_signal_pattern    = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(wire|reg)\s*(\[\s*[\w\d\s\:\-\(\)]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*'
    double_signal_pattern    = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(wire|reg)\s*(\[\s*[\w\d\s\:\-\(\)]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*'
    triple_signal_pattern    = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(wire|reg)\s*(\[\s*[\w\d\s\:\-\(\)]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
    quad_signal_pattern      = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(wire|reg)\s*(\[\s*[\w\d\s\:\-\(\)]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
    quintuple_signal_pattern = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(wire|reg)\s*(\[\s*[\w\d\s\:\-\(\)]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
    sextuple_signal_pattern  = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(wire|reg)\s*(\[\s*[\w\d\s\:\-\(\)]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
    single_signal_declarations = re.findall( single_signal_pattern, module_code,re.IGNORECASE | re.DOTALL )
    double_signal_declarations = re.findall( double_signal_pattern, module_code,re.IGNORECASE | re.DOTALL )
    triple_signal_declarations = re.findall(triple_signal_pattern, module_code, re.IGNORECASE  | re.DOTALL)
    quad_signal_declarations   = re.findall(quad_signal_pattern, module_code, re.IGNORECASE  | re.DOTALL)
    quintuple_signal_declarations = re.findall(quintuple_signal_pattern, module_code, re.IGNORECASE | re.DOTALL)
    sextuple_signal_declarations = re.findall(sextuple_signal_pattern, module_code, re.IGNORECASE | re.DOTALL)

    for i in range(len(single_signal_declarations)) :
        signal_declarations_full.append([single_signal_declarations[i][0]+" "+single_signal_declarations[i][1],single_signal_declarations[i][2]])
    for i in range(len(double_signal_declarations)) : 
        signal_declarations_full.append([double_signal_declarations[i][0]+" "+double_signal_declarations[i][1],double_signal_declarations[i][2]])
        signal_declarations_full.append([double_signal_declarations[i][0]+" "+double_signal_declarations[i][1],double_signal_declarations[i][3]])
    for i in range(len(triple_signal_declarations)) : 
        signal_declarations_full.append([triple_signal_declarations[i][0]+" "+triple_signal_declarations[i][1],triple_signal_declarations[i][2]])
        signal_declarations_full.append([triple_signal_declarations[i][0]+" "+triple_signal_declarations[i][1],triple_signal_declarations[i][3]])
        signal_declarations_full.append([triple_signal_declarations[i][0]+" "+triple_signal_declarations[i][1],triple_signal_declarations[i][4]])
    for i in range(len(quad_signal_declarations)) : 
        signal_declarations_full.append([quad_signal_declarations[i][0]+" "+quad_signal_declarations[i][1],quad_signal_declarations[i][2]])
        signal_declarations_full.append([quad_signal_declarations[i][0]+" "+quad_signal_declarations[i][1],quad_signal_declarations[i][3]])
        signal_declarations_full.append([quad_signal_declarations[i][0]+" "+quad_signal_declarations[i][1],quad_signal_declarations[i][4]])
        signal_declarations_full.append([quad_signal_declarations[i][0]+" "+quad_signal_declarations[i][1],quad_signal_declarations[i][5]])
    for i in range(len(quintuple_signal_declarations)):
        signal_declarations_full.append([quintuple_signal_declarations[i][0]+" "+quintuple_signal_declarations[i][1],quintuple_signal_declarations[i][2]])
        signal_declarations_full.append([quintuple_signal_declarations[i][0]+" "+quintuple_signal_declarations[i][1],quintuple_signal_declarations[i][3]])
        signal_declarations_full.append([quintuple_signal_declarations[i][0]+" "+quintuple_signal_declarations[i][1],quintuple_signal_declarations[i][4]])
        signal_declarations_full.append([quintuple_signal_declarations[i][0]+" "+quintuple_signal_declarations[i][1],quintuple_signal_declarations[i][5]])
        signal_declarations_full.append([quintuple_signal_declarations[i][0]+" "+quintuple_signal_declarations[i][1],quintuple_signal_declarations[i][6]])
    for i in range(len(sextuple_signal_declarations)):
        signal_declarations_full.append([sextuple_signal_declarations[i][0]+" "+sextuple_signal_declarations[i][1],sextuple_signal_declarations[i][2]])
        signal_declarations_full.append([sextuple_signal_declarations[i][0]+" "+sextuple_signal_declarations[i][1],sextuple_signal_declarations[i][3]])
        signal_declarations_full.append([sextuple_signal_declarations[i][0]+" "+sextuple_signal_declarations[i][1],sextuple_signal_declarations[i][4]])
        signal_declarations_full.append([sextuple_signal_declarations[i][0]+" "+sextuple_signal_declarations[i][1],sextuple_signal_declarations[i][5]])
        signal_declarations_full.append([sextuple_signal_declarations[i][0]+" "+sextuple_signal_declarations[i][1],sextuple_signal_declarations[i][6]])
        signal_declarations_full.append([sextuple_signal_declarations[i][0]+" "+sextuple_signal_declarations[i][1],sextuple_signal_declarations[i][7]])
    # Deleate empty signals
    signal_declarations = [sublist for sublist in signal_declarations_full if sublist != [' ', '']]


    for signal_type, signal_name in signal_declarations: 
        instance_scr_name = []
        instance_dst_name = []
        module_dst_name = []
        module_src_name = []

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
        signals.append([signal_name.strip().lower(), signal_type.strip().lower(),instance_scr_name,module_src_name,instance_dst_name,module_dst_name])
    return signals

def extract_external_signals (module_code,module_list,module_name,submodule_list) :
    signals = []
    for i in range (len(module_list)) :
        for j in range (len(module_list[i][1])) : 
            if (module_list[i][1][j][0]==module_name) :
                module = module_list[i][1][j][1]
    for port in module :
        instance_scr_name = []
        instance_dst_name = []
        module_dst_name = []
        module_src_name = []
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
        signals.append([port[0], port[2],instance_scr_name,module_src_name,instance_dst_name,module_dst_name])
    return signals 

def convert_to_csv_string(value): # (eg : [a,b,c] => "a,b,c")
    if isinstance(value, (list, tuple)):
        return ",".join(map(str, value))  
    return str(value)

def write_signals_to_csv(input_file_name,output_file_path, verilog_code, module_list):
    module_pattern =  r'module\s+(\w+)\s*(?:#\(.*?\))?\s*\((.*?)\)\s*;.*?endmodule'
    matches = re.findall(module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    if matches :
        for i in range(len(matches)) :   
            module_name = matches[i][0]
            module_code = matches [i][1]
            submodule_list = extract_submodule_list(verilog_code,module_list)
            internal_signals = extract_internal_signals(verilog_code,module_name,submodule_list)
            external_signals = extract_external_signals(verilog_code,module_list,module_name,submodule_list)
        with open(output_file_path, mode='a', newline='') as file_csv:
            writer = csv.writer(file_csv)
            writer = csv.writer(file_csv,delimiter= ';')
            writer.writerow([f"file_name({input_file_name})"])
            writer.writerow(["component", "signal_name", "type", "instance src", "component_src", "instance_dst", "component_dst"])
    
            for signal in external_signals:
                writer.writerow([
                module_name,
                signal[0],
                signal[1],
                convert_to_csv_string(signal[2]),
                convert_to_csv_string(signal[3]),
                convert_to_csv_string(signal[4]),
                convert_to_csv_string(signal[5])
            ])
            for signal in internal_signals:
                writer.writerow([
                    "Internal",
                    signal[0],
                    signal[1],
                    convert_to_csv_string(signal[2]),
                    convert_to_csv_string(signal[3]),
                    convert_to_csv_string(signal[4]),
                    convert_to_csv_string(signal[5])
                ])

def process_files_in_directory(directory_path, output_txt_path, file_extension):
    module_list = []
    if not os.path.exists(directory_path):
        print(f"The specified directory {directory_path} does not exist.\n")
    else:
        open(output_txt_path, 'w').close()                                                                             
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in ['bench', 'sim', 'testbench']]   
            for file_name in files:
                if file_name.lower().endswith(file_extension):                                                           
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, "r") as file:
                            verilog_code_full = file.read()
                            verilog_code = remove_comments(verilog_code_full)
                            module_list.append([file_name,extract_module(verilog_code)]) 
                    except FileNotFoundError:
                        print(f"Error: File '{file_path}' not found.")
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in ['bench', 'sim', 'testbench']]   
            # extract all modules in directory in modules
            for file_name in files:
                if file_name.lower().endswith(file_extension):                                                           
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, "r") as file:
                            verilog_code_full = file.read()
                            verilog_code = remove_comments(verilog_code_full)
                            write_signals_to_csv(file_name,output_txt_path,verilog_code,module_list)
                    except FileNotFoundError:
                        print(f"Error: File '{file_path}' not found.")
                             

        if os.path.getsize(output_txt_path) == 0 :
            print(f"{file_extension} files was not found. Or there is simply no {file_extension} file in project.\n")
        else :
            print(f"{file_extension} parsing done successfully\n")    



# Main program
def main():
    start_time = time.time()
    from_terminal = 0 # If this option is selected, you must provide input_directory and output_file_path as arguments.

    if from_terminal == 0:
        if len(sys.argv) != 3:
            print("Usage: python prog.py <input_directory> <output_file_path>")
            sys.exit(1)
        input_directory = sys.argv[1]
        output_file_path = sys.argv[2]
    else:
        input_directory = r"..\project\communication_controller_ethernet_10ge_mac\rtl" # modify this path 
        output_file_path = r"..\project\communication_controller_ethernet_10ge_mac\signals.csv" # modify this path
    
    print(f"Input Directory: {input_directory}")
    print(f"Output File Path: {output_file_path}")   
    directory_path = os.path.abspath(input_directory)
    process_files_in_directory(directory_path,output_file_path,'.v')
    end_time = time.time()  
    execution_time = end_time - start_time
    print (f"Temps d'exécution : {execution_time:.5f} secondes")


if __name__ == "__main__":
    main()
