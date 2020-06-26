import os
import boto3
import re

translate = boto3.client('translate')
translate_folder = './app/translations'

def translate_text(text, target, source='en'):
  response = translate.translate_text(Text = text, SourceLanguageCode = source, TargetLanguageCode = target)
  return response['TranslatedText']

def line_split(text, length=76):
  if len(text) > 80:
    match = re.search(r'(msgid|msgstr)\s\"([^\"]*)\"', text)
    if match:
      words = match.group(2).split(' ')
      new_string = ''
      line_string = ''
      for word in words:
        if (len(line_string) + len(word) + 1) > length:
          new_string = new_string + '\n' + '"' + line_string + '"'
          line_string = ' ' + word
        else:
          line_string = word if line_string == '' else line_string + ' ' + word
      new_string = new_string + '\n' + '"' + line_string + '"'
      return f'{match.group(1)} ""{new_string}'
    else:
      return text
  else:
    return text

for lang in os.listdir(translate_folder):
  print(f'Language folder: {lang}')
  start_translating = False
  if os.path.exists(f'{translate_folder}/{lang}/LC_MESSAGES/messages.po'):
    f = open(f'{translate_folder}/{lang}/LC_MESSAGES/messages.po_new', mode='w', encoding='utf-8')
    messages_content = open(f'{translate_folder}/{lang}/LC_MESSAGES/messages.po', mode='r', encoding='utf-8').read()
    record_msg = False
    mulitline_msg = ''
    msgstr = ''
    for line in messages_content.split('\n'):
      if line.startswith('#:'):
        start_translating = True
      if start_translating:
        if line == 'msgid ""':
          record_msg = True
          mulitline_msg = ''
        elif line.startswith('msgid "'):
          f.write(line_split(line) + '\n')
          msgstr = translate_text(line[7:-1], lang)
          f.write(line_split(f'msgstr "{msgstr}"') + '\n')
        elif line.startswith('msgstr "'):
          if record_msg and mulitline_msg != '':
            msgstr = translate_text(mulitline_msg, lang)
            f.write(line_split(f'msgid "{mulitline_msg}"') + '\n')
            f.write(line_split(f'msgstr "{msgstr}"') + '\n')
            msgstr = ''
          record_msg = False
        elif record_msg:
          mulitline_msg += line[1:-1]
        else:
          if not(line.startswith('"') and line.endswith('"')):
            f.write(line_split(line) + '\n')
      else:
          f.write(line_split(line) + '\n')

