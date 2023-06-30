import subprocess
import re
import ast

p = subprocess.run(['sbcl', "--noinform", "--load", "rule-based-analytics", "--eval", '(progn (run) (sb-ext:quit))'], capture_output=True)

string = p.stdout.decode("utf-8").replace('(', '[').replace(')', ']')
string = re.sub("\s+", ", ", string.strip())
lst = ast.literal_eval(string)
print(lst)
