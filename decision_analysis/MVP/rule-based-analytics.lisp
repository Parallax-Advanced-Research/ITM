#|Notes
Airway: time: seconds. use: make sure patient airway is clear :resources: feew. System: [respiratory]

ChestSeal: time: seconds. use: prevents air from entering chest cavity, resources: few, steps: few. system: [respiratory]

SalineLock: use: IV drug delivery. time: seconds. resources: few. steps: few. system: [cariovascular]

IntraossDevice: time: minutes. resources: some. steps. system: [cardiovascular]. use: bone IV

IVFluids: systems: [vascular, renal], use: prevent dehydration and electrolyte imbalances resources: few time: some :resources: some

Hemorage control: systems: [cardiovascular] use: prevent bleeding resources: some

Medications: use: many systems: all time: few :resources: some.

TranexamicAcid: use: breakdown blood clots systems: [cardiovascular] resources: few. time: few

BloodProducts:

NeedleDecomp: use: remove air from the chest cavity. systems:[respiratory]. resources: few. time: few. 
|#
(defstruct rule
  (id (gensym "RULE-"))
  lhs
  rhs
  num-conditions)

(defparameter *facts* '(:A ((respiratory-rate 22)
			    (heart-rate 110)
			    (blood-pressure -1)
			    (o2 95)
			    (pain -1))
			:B ((respiratory-rate 18)
			    (heart-rate 100)
			    (blood-pressure 80)
			    (o2 98)
			    (pain 6))
			:C ((respiratory-rate 15)
			    (heart-rate 105)
			    (blood-pressure 120)
			    (o2 99)
			    (pain 8))
			:D ((respiratory-rate 15)
			    (heart-rate 105)
			    (blood-pressure 120)
			    (o2 99)
			    (pain 2))
			:E ((respiratory-rate 25)
			    (heart-rate 110)
			    (blood-pressure 90)
			    (o2 95)
			    (pain 10))
			:F ((respiratory-rate 18)
			    (heart-rate 110)
			    (blood-pressure 120)
			    (o2 99)
			    (pain 3))))
(defparameter *treatments* '(airway chestseal salinelock intraossdevice ivfluids hemorrhagecontrol medications tranexamicacid bloodproducts needledecomp))

(defparameter *rules* nil)

(defun mk-keyword (symbol)
  (intern (symbol-name symbol) "KEYWORD"))

(defun make-rules()
  (loop with rules
	for treatment in *treatments*
	do
	   (setq rules nil)
	   (case treatment
	     ((airway needledecomp)
	      (let ((rule (make-rule)))
		(setf (rule-lhs rule) (cons '(respiratory-rate <= 20)
					    (rule-lhs rule)))
		(setf (rule-lhs rule) (cons '(heart-rate <= 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(respiratory-rate <= 20)
					    (rule-lhs rule)))
		(setf (rule-lhs rule) (cons '(heart-rate > 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance med)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))
		
		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(respiratory-rate > 20)
					    (rule-lhs rule)))
	        (setf (rule-rhs rule) (cons '(treatment-relevance low)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))))
	     (chestseal
	      (let ((rule (make-rule)))
		(setf (rule-lhs rule) (cons '(heart-rate > 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(heart-rate <= 100)
					    (rule-lhs rule)))
		(setf (rule-lhs rule) (cons '(pain <= 5)
					    (rule-lhs rule)))
		(setf (rule-lhs rule) (cons '(pain > -1)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance low)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) 3)
		(setq rules (cons rule rules))))
	     (salinelock
	      (let ((rule (make-rule)))
		(setf (rule-lhs rule) (cons '(heart-rate > 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance med)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(heart-rate > 100)
					    (rule-lhs rule)))
		(setf (rule-lhs rule) (cons '(pain <= 5)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(heart-rate <= 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance low)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))))
	     (intraossdevice
	      (let ((rule (make-rule)))
		(setf (rule-lhs rule) (cons '(heart-rate <= 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance low)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(heart-rate > 100)
					    (rule-lhs rule)))
		(setf (rule-lhs rule) (cons '(pain > 5)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))))
	     (ivfluids
	      (let ((rule (make-rule)))
		(setf (rule-lhs rule) (cons '(pain > 5)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))))
	     (hemorrhagecontrol
	      (let ((rule (make-rule)))
		(setf (rule-lhs rule) (cons '(heart-rate > 100)
					    (rule-lhs rule)))
		(setf (rule-lhs rule) (cons '(blood-pressure <= 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(heart-rate > 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance med)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(heart-rate <= 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance low)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))))
	     (medications
	      (let ((rule (make-rule)))
	        (setf (rule-lhs rule) (cons '(pain > 5)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))))
	     (tranexamicacid
	      (let ((rule (make-rule)))
		(setf (rule-lhs rule) (cons '(blood-pressure <= 100)
					    (rule-lhs rule)))
		(setf (rule-lhs rule) (cons '(pain > 5)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(blood-pressure > 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance low)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))))
	     (bloodproducts
	      (let ((rule (make-rule)))
		(setf (rule-lhs rule) (cons '(blood-pressure <= 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(heart-rate > 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance high)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(heart-rate <= 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance low)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))

		(setq rule (make-rule))
		(setf (rule-lhs rule) (cons '(blood-pressure > 100)
					    (rule-lhs rule)))
		(setf (rule-rhs rule) (cons '(treatment-relevance low)
					    (rule-rhs rule)))
		(setf (rule-num-conditions rule) (length (rule-lhs rule)))
		(setq rules (cons rule rules))))
	     (otherwise
	      (format t "unrecognized key: ~A" treatment)
	      (break)))
	   (setq *rules* (cons rules *rules*))
	   (setq *rules* (cons (mk-keyword treatment) *rules*))))


(defun occurrences (list)
  (flet ((create-result-list (list)
           (mapcar (lambda (item)
                     (cons item 0))
                   (remove-duplicates list :test #'equal)))
         (count-occurrences (list result)
           (mapc (lambda (item)
                   (incf (cdr (assoc item result :test #'equal))))
                 list)
           result))
    (sort (count-occurrences list (create-result-list list))
          #'>
          :key #'cdr)))

(defun add-end (item list)
  (reverse (cons item (reverse list))))

(defun rule-based-analytics()
  (loop
    with res = nil
    for casualty in *facts* by #'cddr
    for vitals in  (rest *facts*) by #'cddr 
    do
       (setq res (add-end (symbol-name :casualty) res))
       (setq res (add-end (symbol-name casualty) res))
       (setq res (add-end (symbol-name :decisions) res))
       (loop
	 with treatments = nil
	 with best-rules = nil
	 with best-score = -1
	 for treatment in *rules* by #'cddr
	 for rules in (rest *rules*) by #'cddr
	 do
	    (setq treatments (add-end (symbol-name :name) treatments))
	    (setq treatments (add-end (symbol-name treatment) treatments))
	    (setq treatments (add-end (symbol-name :analytic) treatments))
	    (setq best-rules nil)
	    (setq best-score -1)
	    (loop
	      with analytics = nil
	      with num-matched-conditions = 0 and match-score = 0
	      for rule in rules
	      do
		 (setq num-matched-conditions 0)
		 (loop
		   with fluent and matchp
		   for condition in (rule-lhs rule)
		   do
		      (setq fluent (car (member (car condition) vitals :key #'car)))
		      (setq matchp (eval (list (second condition) (second fluent) (third condition))))
		      (when matchp
			(incf num-matched-conditions)))
		 (setq match-score (/ num-matched-conditions (rule-num-conditions rule)))
		 (cond ((> match-score best-score)
			(setq best-score match-score)
			(setq best-rules (list rule)))
		       ((= match-score best-score)
			(setq best-rules (cons rule best-rules))))
	      finally
		 (loop
		   with analytic
		   for rule in best-rules
		   collect (rule-rhs rule) into choices
		   finally
		      (setq analytic (caaar (occurrences choices)))
		      (setq analytics (cons (list (symbol-name (mk-keyword (car analytic))) (symbol-name (second analytic)))
					    analytics)))
		 (setq treatments (add-end analytics treatments)))
	 finally
	    (setq res (add-end treatments res)))
    finally
       (return res)))

(defun run ()
  (make-rules)
  (format t "~%~S~%" (rule-based-analytics)))
