import os, sys, re, json

def match_all_inline(template_name: str, source: str):
   global _S, S_
   
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


_S = '{{'
S_ = '}}'

argv = sys.argv[1:]
pwd = os.path.abspath(os.path.dirname(__file__))

output_path = argv[1]

# taking start text
target_template = argv[0]
final_markdown = None
with open(target_template, 'r') as tpl_file:
   final_markdown = tpl_file.read()

TEMPLATES_FOLDER = argv[2] if( len(argv) == 3 )else os.path.join(pwd, 'markdown_templates')
# template names from default folder
templates = list(os.listdir(TEMPLATES_FOLDER))

# for each template
for template in templates:
   # taking name
   template_name = os.path.splitext(template)[0].split('/').pop()
   print(template_name.upper())
   
   # opening current template file
   with open(f'{TEMPLATES_FOLDER}/{template}') as template_file:
      template_content = template_file.read()
      
      #command_regex = re.compile(
      ##   0                               1    2
      #   '('+_S+r'\s*'+template_name+r'\s*(>>)?(?P<args>.*)'+S_+')',
      #   re.DOTALL
      #)
      #match_all = command_regex.findall(final_markdown)
      match_all = match_all_inline(template_name, final_markdown)
      
      if not match_all:
         print('  no matches')
      
      i = 0
      for match in match_all:
         full_match = match['full_match']
         replacement = template_content
         
         args_group = match['args']
         args = ', ' + args_group.strip()
         json_regex = re.compile(r'(,[\s\n]*)(\w*?)\s*:', re.DOTALL)
         args_json = json_regex.sub(r'\1"\2":', args)[2:]
         args_dict = json.loads('{' + args_json + '}')
         print(' ', args_dict)
         
         for arg_name, arg_val in args_dict.items():
            replacement = replacement.replace(_S+ arg_name +S_, str(arg_val))
         replacement = replacement.replace(_S+ '$n' +S_, str(i+1))
            
         final_markdown = final_markdown.replace(full_match, replacement)
         
         i += 1
         
         
# output to file         
with open(output_path, 'w+') as output_file:
   output_file.write(final_markdown)