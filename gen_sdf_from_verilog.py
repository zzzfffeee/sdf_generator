import re
import csv
import os
import sys

DEBUG = True
warnings_set = set() # Stockage des warnings déjà signalés

default_config_file = r".\config_verilog.txt"




def log_warning(message):
    global warnings_set
    if message not in warnings_set:
        print(f"WARNING : {message}")
        warnings_set.add(message)   


## Modifie la configuration config = (input_directory, output_file, excluded_directories,excluded_files,define_list) à partir du contenue de config_file.txt
def extract_config(config_file,config) :
    if not os.path.exists(config_file):
        return config  # Retourne la config d'origine si le fichier n'as pas été trouvé
    input_directory, output_file, excluded_directories, excluded_files, define_list = config
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
            elif line.startswith("define_list ="):
                value = line.split("=")[1].strip().strip('"')
                if not define_list:  
                    define_list = value.split(',')
        return input_directory, output_file, excluded_directories, excluded_files, define_list
    
    
## Efface les commentaires dans le code verilog pour ne pas perturber le fonctionnement des regex
def remove_comments(verilog_code):                                                            
    verilog_code = re.sub(r'//.*', '', verilog_code)                                                
    verilog_code = re.sub(r'/\*.*?\*/', '', verilog_code, flags=re.DOTALL)                           
    verilog_code = re.sub(r'function\s.*?endfunction', '', verilog_code, flags=re.DOTALL) 
    return verilog_code
    
## Renvoi le nom du module à partir d'un code verilog
def find_module_name(verilog_code):
    module_pattern = r'module\s*(\w+)'  # Recherche le mot-clé "module" suivi du nom
    match = re.search(module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else None

## Renvoi [[nom_module_1,...],[code_module_1,...]] à partir du code verilog
def find_modules(verilog_code):
    module_pattern =  r'(module\s+(\w+)\s*(?:#\s*\(.*?\))?\s*\((.*?\)\s*;.*?)endmodule)'
    matches = re.findall(module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    if matches :
        return [(match[1], match[0]) for match in matches]
    return 0

## Revoi la taille du signal en bit à partir du signal_type (rq : lorsque le nom du générique est présent dans le signal_type, il n'est pas remplacé par la valeur qui lui est assignée)
def size_of_signal(signal_type):
    size_pattern = r'\[\s*(\d+)\s*(?:-\s*(\d+))?\s*:\s*(\d+)\s*\]'
    size_pattern_generic = r'\[\s*((?:\w+)|(?:\(.*?\)))\s*(?:-\s*(\d+))?\s*(?:-\s*(\d+))?\s*:\s*(\d+)\s*\]'
    integer_pattern = r'integer(.*?)'
    if (match:=re.search(integer_pattern,signal_type,re.DOTALL | re.IGNORECASE)):
        signal_size = '32'
    elif (match:=re.search(size_pattern,signal_type,re.DOTALL | re.IGNORECASE)):
        signal_size = str(int(match.group(1))-(int(match.group(2)) if match.group(2) is not None else 0)-int(match.group(3))+1)
    elif (match:=re.search(size_pattern_generic,signal_type,re.DOTALL | re.IGNORECASE)) :
        if((-(int(match.group(2)) if match.group(2) is not None else 0)-(int(match.group(3)) if match.group(3) is not None else 0)+1-int(match.group(4)))==0) :
            signal_size = match.group(1)
        else : 
            signal_size = match.group(1)+str(1-(int(match.group(2)) if match.group(2) is not None else 0)-(int(match.group(3)) if match.group(3) is not None else 0)-int(match.group(4)))
    elif ((signal_type.strip().lower()=='wire')|(signal_type.strip().lower()=='reg')) :
        signal_size = '1'
    else :
        signal_size = 'unknown'
        if(DEBUG == True) :
            log_warning(f'size of {signal_type} is unknown')  
    return signal_size

## Gère les ifdef, ifndef à partir de la liste define_liste : renvoie le code sans les parties non définies
def manage_define(verilog_code,define_list) :
    pattern_clean = r"^`(?!ifdef|ifndef|else|include)\w.*"
    verilog_code = re.sub(pattern_clean, "", verilog_code, flags=re.MULTILINE|re.IGNORECASE) # enlève tout ligne contenant le carractère ` mais qui n'est pas important 
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
    
## Renvoi la liste suivante : [[nom_module_1,[ [nom_port_1,direction(in/out/inout),type],[nom_port_2,direction(in/out/inout),type],...]]   ,[nom_module_2,[...]] , ... ]
def extract_module(verilog_code):
    module_pattern = r'module\s+(\w+)\s*(?:#\s*\(.*?\))?\s*\((.*?\)\s*;.*?)endmodule'
    matches = re.findall(module_pattern, verilog_code, re.IGNORECASE | re.DOTALL)
    modules = []

    if matches:
        for j in range(len(matches)) :     
            ports = []
            port_declarations = []
            single_port_pattern    = r'\b(input|output|inout)\s*(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)?\s*(\[\s*[\w\d\s\(\)\:\-/\*]+\])?\s*(\w+)'
            double_port_pattern    = r'\b(input|output|inout)\s*(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)?\s*(\[\s*[\w\d\s\(\)\:\-/\*]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            triple_port_pattern    = r'\b(input|output|inout)\s*(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)?\s*(\[\s*[\w\d\s\(\)\:\-/\*]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            quad_port_pattern      = r'\b(input|output|inout)\s*(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)?\s*(\[\s*[\w\d\s\(\)\:\-/\*]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            quintuple_port_pattern = r'\b(input|output|inout)\s*(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)?\s*(\[\s*[\w\d\s\(\)\:\-/\*]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
            sextuple_port_pattern  = r'\b(input|output|inout)\s*(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)?\s*(\[\s*[\w\d\s\(\)\:\-/\*]+\])?\s*(\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
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

# Retourne la liste : [nom_du_port,direction,type] si le port est trouvé, warning sinon
def find_port(port_name, module_name,module_list) : 
    for i in range (len(module_list)) :
        for j in range (len(module_list[i][1])) : 
            if (module_list[i][1][j][0]==module_name) :
                for k in range(len(module_list[i][1][j][1])) :
                    if module_list[i][1][j][1][k][0] == port_name : 
                        return module_list[i][1][j][1][k]
                log_warning(f"port {port_name} of module {module_name} is not found")
                return ['','unknow']
    log_warning(f"module {module_name} is not found")
    return ['','unknow']
    
# Extrait tout les sous-modules à partir du code d'un module. Retourne : [[inst_1,sub_module_name,submodule_ports],...]
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

# Extrait les signaux internes pour chaque section de code de module
def extract_internal_signals (module_code,module_name,submodule_list):
    signals = []
    signal_declarations_full = []
    single_signal_pattern    = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)\s*(\[\s*[\w\d\s\:\-\(\)/\*]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*'
    double_signal_pattern    = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)\s*(\[\s*[\w\d\s\:\-\(\)/\*]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*'
    triple_signal_pattern    = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)\s*(\[\s*[\w\d\s\:\-\(\)/\*]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
    quad_signal_pattern      = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)\s*(\[\s*[\w\d\s\:\-\(\)/\*]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
    quintuple_signal_pattern = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)\s*(\[\s*[\w\d\s\:\-\(\)/\*]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
    sextuple_signal_pattern  = r'\b(?:input|output|inout)\b\s*(?:wire|reg).*?[\),]|(\bwire\b\s*(?:signed|unsigned)?|\breg\b\s*(?:signed|unsigned)?)\s*(\[\s*[\w\d\s\:\-\(\)/\*]+\])?\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)\s*,\s*((?!input\b|output\b|inout\b)\w+)'
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

# Extrait les signaux provennant des ports du module pour chaque section de code de module
def extract_external_signals (module_list,module_name,submodule_list) :
    signals = []
    module = []
    for i in range (len(module_list)) :
        for j in range (len(module_list[i][1])) : 
            if (module_list[i][1][j][0]==module_name.strip().lower()) :
                module = module_list[i][1][j][1]
    if (module==[]) :
        print (f'module {module_name} is not found')
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
                                        module_list.append([file_name,extract_module(module_code)]) 
                        except FileNotFoundError:
                            print(f"Error: File '{file_path}' not found.")
        except KeyboardInterrupt :
            print (f"Module of file : {file_name} is extacted")
        try :
            for root, dirs, files in os.walk(directory_path):
                dirs[:] = [d for d in dirs if d not in excluded_directories]
                files[:] = [f for f in files if f not in excluded_files]      
                # extract all modules in directory in modules
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
