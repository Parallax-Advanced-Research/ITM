FROM python:3.10
WORKDIR /root
ADD requirements.txt /root/tad/requirements.txt

WORKDIR /root/tad
RUN apt-get install -y python3
RUN apt-get update
RUN python3 -m pip install -r requirements.txt
RUN apt-get install -y sbcl
RUN apt-get install -y git
RUN apt-get install -y wget

ADD components/ /root/tad/components
ADD data/ /root/tad/data
ADD domain/ /root/tad/domain
ADD runner/ /root/tad/runner
ADD scripts/ /root/tad/scripts
ADD temp/ /root/tad/temp
ADD util/ /root/tad/util
ADD tad.py /root/tad
ADD tad_tester.py /root/tad
ADD ta3_training.py /root/tad

WORKDIR /root
RUN wget https://beta.quicklisp.org/quicklisp.lisp 
RUN yes "" | sbcl --load quicklisp.lisp --eval "(progn (quicklisp-quickstart:install) (eval (read-from-string \"(quicklisp:add-to-init-file)\")) (quit))" 
RUN rm quicklisp.lisp

RUN git clone https://github.com/NextCenturyCorporation/itm-evaluation-client.git --branch development
RUN python3 -m pip install -e /root/itm-evaluation-client

WORKDIR /root/quicklisp/local-projects
RUN git clone https://github.com/dmenager/HEMS.git
ADD components/decision_analyzer/event_based_diagnosis/hems-package-replacement.lisp HEMS/package.lisp
RUN cp "HEMS/examples/Common Lisp/example.lisp" /

WORKDIR /root/tad
