from json.decoder import JSONDecodeError
import os, sys, re, json

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
   _S, S_ = wrappers
   
   command_regex_str = '('+_S+r'\s*?'+ template_name +r'\s*?.*?'+S_+')'
   command_regex = re.compile(command_regex_str, re.DOTALL)

   match_all = command_regex.findall(source)
   
   if not match_all:
      return False
   
   matches = []
   for match in match_all:
      full_match = match
      match = match.replace('\n', '').replace('\r', '')
      match = re.sub(r',\s*', ', ', match)
      # get data
      #                           0                               1    2
      command_regex = re.compile('('+_S+r'\s*'+template_name+r'\s*(>>)?(?P<args>.*)'+S_+')')
      groups = command_regex.findall(match)
      matches += [{ 'full_match': full_match, 'args': groups[0][2] }]
      
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
      print(str(depth) + ':' + template_name.upper())
      
      match_all = match_all_inline(template_name, final_markdown, [_P, P_])
      
      if not match_all:
         print('  no matches')
         continue
      
      was_replace = True
      
      # if has matches
      i = 0
      for match in match_all:
         full_match = match['full_match']
         replacement = template_content
         
         try:
            args_dict = get_tpl_args_as_dict(match['args'])
            print(' ', args_dict)
         except JSONDecodeError:
            print(f'Error: Not correct syntax when use template "{template_name}". Error rise in this place: \n  {full_match}')
         
         # replacing vars in template
         for arg_name, arg_val in args_dict.items():
            replacement = replacement.replace(_V+ arg_name +V_, str(arg_val))
         replacement = replacement.replace(_V+ '$n' +V_, str(i+1))
         args_str = ', '.join(map(lambda it: f'{it[0]}:"{it[1]}"', args_dict.items()))
         replacement = replacement.replace(_V+ '$args' +V_, args_str)
            
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
_P, P_ = '::', '::' # piece execute

if 'var_wrappers' in argv_dict:
   _V, V_ = argv_dict['var_wrappers'].split(',')
   
if 'piece_wrappers' in argv_dict:
   _P, P_ = argv_dict['piece_wrappers'].split(',')


output_path = argv[1]

# taking start text
target_template = argv[0]
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