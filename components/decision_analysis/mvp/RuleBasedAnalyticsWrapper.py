import subprocess
import re
import ast

def rule_based_analytics():
    p = subprocess.run(['sbcl', "--noinform", "--load", "rule-based-analytics", "--eval", '(progn (run) (sb-ext:quit))'], capture_output=True)

    string = p.stdout.decode("utf-8").replace('(', '[').replace(')', ']')
    string = re.sub("\s+", ", ", string.strip())
    lst = ast.literal_eval(string)
    return(lst)
