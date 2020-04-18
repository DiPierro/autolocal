# this script is used to convert an HTML document with separate CSS into an
# HTML document with inline styles. Used as a utility to generate the 
# email template. Not used in production.

from premailer import transform
import pynliner
import toronado
import re
import requests

email = open("input_email_template.html").read()

style_links = re.findall("<link rel=\"stylesheet\" href=\"(.*)\"/>", email)
new_style_stuff = ""
for style_link in style_links:
  style = requests.get(style_link).text
  new_style_stuff += ("\n" + style)
new_style_stuff = "<style>\n{}\n/* end */</style>".format(new_style_stuff)
email = re.sub("<link rel=\"stylesheet\" href=\".*\"/>", new_style_stuff, email)

import_statements = re.findall("(@import.*\n)+", email)

# email = re.sub("\n[/][*] Row [*][/]\n(.[^*].*\n|\n)*", "\n\n", email)
# email = re.sub("\n[/][*] Actions [*][/]\n(.[^*].*\n|\n)*", "\n\n", email)
# email = re.sub("\n[/][*] Image [*][/]\n(.[^*].*\n|\n)*", "\n\n", email)
# email = re.sub("\n[/][*] Icon [*][/]\n(.[^*].*\n|\n)*", "\n\n", email)
# email = re.sub("\n[/][*] Feature Icons [*][/]\n(.[^*].*\n|\n)*", "\n\n", email)
# email = re.sub("\n[/][*] Features [*][/]\n(.[^*].*\n|\n)*", "\n\n", email)
# email = re.sub("\n[/][*] Header [*][/]\n(.[^*].*\n|\n)*", "\n\n", email)

rows_to_remove = [
  # "Row",
  # "Large",
  # "Actions",
  # "Image",
  # "Icon",
  # "Features",
  # "Feature Icons",
  # "Header",
  # "Button",
  # "Table",
  # "Icons",
  # "List",
  "XLarge",
  # "Large",
  "Medium",
  "Small",
  "XSmall"
]

for section_name in rows_to_remove:
  email = re.sub("\n[/][*] {} [*][/]\n(.[^*].*\n|\n)*".format(section_name), "\n\n", email)
# 
email = re.sub("\n[/][*] XLarge [*][/]\n\n\t\@media screen and \(max-width: [0-9]*px\) \{((.[^*].*\n|\n)*)\t\}", "\1", email)
email = re.sub("\n[/][*] Large [*][/]\n\n\t\@media screen and \(max-width: [0-9]*px\) \{((.[^*].*\n|\n)*)\t\}", "\1", email)
email = re.sub("\n[/][*] Medium [*][/]\n\n\t\@media screen and \(max-width: [0-9]*px\) \{((.[^*].*\n|\n)*)\t\}", "\1", email)
email = re.sub("\n[/][*] Small [*][/]\n\n\t\@media screen and \(max-width: [0-9]*px\) \{((.[^*].*\n|\n)*)\t\}", "\1", email)
email = re.sub("\n[/][*] XSmall [*][/]\n\n\t\@media screen and \(max-width: [0-9]*px\) \{((.[^*].*\n|\n)*)\t\}", "\1", email)


# At this point, we have the full email template in one page, including css


email = re.sub("\n.*~.*\{\n([^}]*\n)*[^}]*\}\n", "\n\n", email)
# email = re.sub("\n.*:[a-z].*\{\n([^}]*\n)*[^}]*\}\n", "\n\n", email)

# email = pynliner.fromString(email)
# email = toronado.from_string(email)
email = transform(email)

email = re.sub("  <style>.*\n(.*\n)*.*</style>", "  <style>\n"+"\n".join(import_statements)+"</style>\n\n", email)

# # # print(email)

# This is what should be copied into autolocal/autolocal/mailer/emails.py
open("email_template_with_inline_styles.html", "w").write(email)