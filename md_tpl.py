from json.decoder import JSONDecodeError
import os, sys, re, json

def precompile_regex(regex: str, wrappers: list = ['', '']):
   global _V, V_, _P, P_, SS
   
   _S, S_ = wrappers
   
   regex = regex.replace('<x', _S)
   regex = regex.replace('x>', S_)
   regex = regex.replace('~', SS)
   regex = regex.replace(' ', '\s*?')
   
   # autoescape
   #match = re.findall(r'<(.*?)>', regex)
   #if match:
   #   regex = regex.replace(f'<{match[0]}>', re.escape(match[0]))
   
   return regex


def read_templates(templates_folder):
   res = {}
   
   # template names from default folder
   templates_list = list(os.listdir(templates_folder))

   # for each template
   for template in templates_list:
      # taking name
      template_name = os.path.splitext(template)[0].split('/').pop()
      
      # opening current template file
      with open(f'{templates_folder}/{template}') as template_file:
         res[template_name] = template_file.read()
   
   return res


def match_all_inline(template_name: str, source: str, wrappers: str):
   global SS
   _S, S_ = wrappers
   
   template_name_start = template_name
   template_name = re.escape(template_name)
   
   command_regex_str = f'(<x {template_name}(?=(~|\s|x>)) .*?x>)'
   precompiled = precompile_regex(command_regex_str, [_S, S_])
   command_regex = re.compile(precompiled, re.DOTALL)

   match_all = command_regex.findall(source)
   
   if not match_all:
      return False
   
   matches = []
   for match in match_all:
      match = match[0]
      full_match = match
      # == to ==:
      match = re.sub(precompile_regex(f'{template_name} ==(?!:)'), f'{template_name_start} ==:', match)
      match = match.replace('\n', '').replace('\r', '')
      match = re.sub(r',\s*', ', ', match)
      # get data
      command_regex_str = f'(<x {template_name}(?=(~|\s|x>)) (x>|~(?P<args>.*?)x>))'
      precompiled = precompile_regex(command_regex_str, [_S, S_])
      #print('precompiled:', precompiled)
      command_regex = re.compile(precompiled)
      #print('match:', match)
      match_all_local = command_regex.findall(match)
      groups = match_all_local[0]
      matches += [{ 'full_match': full_match, 'args': groups[3] }]
      
   return matches

def get_tpl_args_as_dict(args_group: str) -> str:
   args = ', ' + args_group.strip()
   json_regex = re.compile(r'(,[\s\n]*)(\S*?)\s*:', re.DOTALL)
   args_json = json_regex.sub(r'\1"\2":', args)[2:]
   args_dict = json.loads('{' + args_json + '}')
   return args_dict

def paste_all_pieces(depth: int, source: str, var_wrappers: list, piece_wrappers: list) -> bool:
   global templates
   
   final_markdown = source
   _V, V_ = var_wrappers
   _P, P_ = piece_wrappers
   
   was_replace = False
   
   # for each template
   for template_name, template_content in templates.items():
      #print(str(depth) + ':' + template_name.upper())
      
      match_all = match_all_inline(template_name, final_markdown, [_P, P_])
      
      if not match_all:
         #print('  no matches')
         continue
      
      was_replace = True
      
      # if has matches
      i = 0
      for match in match_all:
         full_match = match['full_match']
         replacement = template_content
         
         try:
            args_dict = get_tpl_args_as_dict(match['args'])
            #print(' ', args_dict)
         except JSONDecodeError:
            print(f'Error: Not correct syntax when use template "{template_name}". Error rise in this place, on depth={depth}: \n  {full_match}')
         
         # replacing vars in template
         for arg_name, arg_val in args_dict.items():
            replacement = replacement.replace(_V+ arg_name +V_, str(arg_val))
            
         # $n
         regex = precompile_regex('<x \$n x>', [_V, V_])
         replacement = re.sub(regex, str(i+1), replacement)
         
         # $args
         args_str = ', '.join(map(lambda it: f'{it[0]}:"{it[1]}"', args_dict.items()))
         regex = precompile_regex('<x \$args x>', [_V, V_])
         replacement = re.sub(regex, args_str, replacement)
         
         # $file
         regex = precompile_regex('<x \$file\((.*?)\) x>', [_V, V_])
         regex_match = re.findall(regex, replacement)
         if regex_match:
            file_path = os.path.join(target_template_dir, re.sub(r'^\.\/', '', regex_match[0]))
            try:
               with open(file_path, 'r') as file:
                  replacement = re.sub(regex, file.read(), replacement)
            except IsADirectoryError:
               print(f'Error: You trying insert directory instead of file in "{template_name}". Error rise in this place, on depth={depth}: \n  {full_match}')
            except FileNotFoundError:
               print(f'Error: file not found "{template_name}". Target path was: {file_path}. Error rise in this place, on depth={depth}: \n  {full_match}')
            
            
         final_markdown = final_markdown.replace(full_match, replacement)
         
         i += 1
         
   return { 'was_replace': was_replace, 'text': final_markdown }


argv = sys.argv[1:]
argv_dict = {}
for arg in argv:
   if arg.startswith('--'):
      argv_dict[arg] = arg.split('=').pop()
pwd = os.path.abspath(os.path.dirname(__file__))


_V = '{' # var paste
V_ = '}' # var paste
_P, P_ = '\(\(', '\)\)' # piece execute
SS = '\=' # send sequence

if 'var_wrappers' in argv_dict:
   _V, V_ = argv_dict['var_wrappers'].split(',')
   
if 'piece_wrappers' in argv_dict:
   _P, P_ = argv_dict['piece_wrappers'].split(',')


output_path = argv[1]

# taking start text
target_template = os.path.abspath(argv[0])
target_template_dir = os.path.dirname(target_template)
final_markdown = None
with open(target_template, 'r') as tpl_file:
   final_markdown = tpl_file.read()

TEMPLATES_FOLDER = argv['template_folder'] if( 'template_folder' in argv_dict )else os.path.join(pwd, 'markdown_templates')
# template dict names from default folder = { tpl_name : tpl_file_content }
templates = read_templates(TEMPLATES_FOLDER)
templates = dict(sorted(templates.items(), key=lambda el: len(el[0]), reverse=True)) # sort by key length

depth = 0
while True:
   # replacing pieces
   # `Hello, :: bold_underline >> name: "Fedor", surname: "Nikonov" ::
   # `Hello, :: bold >> text: "{name}" :::: underline >> text: "{surname}" ::
   # `Hello, :: bold >> text: "Fedor" :::: underline >> text: "Nikonov" ::
   piece_paste_data = final_markdown = paste_all_pieces(depth, final_markdown, [_V, V_], [_P, P_])
   final_markdown = piece_paste_data['text']
   
   if not piece_paste_data['was_replace']:
      print('Depth reached:', depth)
      break
   
   depth += 1
         
# output to file         
with open(output_path, 'w+') as output_file:
   output_file.write(final_markdown)