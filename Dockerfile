FROM python:3.10
WORKDIR /root
ADD components/ /root/tad/components
ADD data/ /root/tad/data
ADD domain/ /root/tad/domain
ADD runner/ /root/tad/runner
ADD scripts/ /root/tad/scripts
ADD temp/ /root/tad/temp
ADD util/ /root/tad/util
ADD requirements.txt /root/tad
ADD tad.py /root/tad
RUN apt-get update
RUN apt-get install -y wget
RUN wget https://beta.quicklisp.org/quicklisp.lisp 
RUN apt-get install -y sbcl
RUN apt-get install -y git
RUN yes "" | sbcl --load quicklisp.lisp --eval "(progn (quicklisp-quickstart:install) (eval (read-from-string \"(quicklisp:add-to-init-file)\")) (quit))" 
RUN rm quicklisp.lisp
RUN git clone https://github.com/NextCenturyCorporation/itm-evaluation-client.git

WORKDIR /root/quicklisp/local-projects
RUN git clone https://github.com/dmenager/HEMS.git
ADD components/decision_analyzer/event_based_diagnosis/hems-package-replacement.lisp HEMS/package.lisp
RUN cp "HEMS/examples/Common Lisp/example.lisp" /

WORKDIR /root/tad
RUN apt-get install -y python3
RUN apt-get install -y pip
RUN pip install -r requirements.txt
RUN pip install -e /root/itm-evaluation-client