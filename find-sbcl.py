import sys, subprocess

p = subprocess.run([ "sbcl", "--noinform", "--non-interactive", "--eval", 
                     '(progn (format t "~a" (car ql:*loca-project-directories*)) (quit))'],
                   capture_output=True, text=True, check=False)
if 0 != p.returncode:
    print(f"quicklisp must be installed before we run this command.")
    sys.exit(1)
QL_LOCAL_PROJECTS = p.stdout
print(f"[[{QL_LOCAL_PROJECTS}]]")
