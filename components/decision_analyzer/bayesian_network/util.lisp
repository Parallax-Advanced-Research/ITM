;(defpackage :util)
;(in-package :util)
; TODO: make packaging work. q.v. first few lines of package.lisp. export is important bit

; for quick and dirty debug output
; TODO: send to stderr
(defun debug-out (&rest argv)
  (if (typep (car argv) 'string)
    (apply #'format (append (cons t argv)))
    (apply #'format (cons t (cons "~a" argv))))
  (format t "~%")
  (force-output))


; INPUT: (pipe first f0 (f1 arg0 arg1) f2)
; first arg can be anything. The rest must be either functions, or a list A s.t. (car A) is a function that takes the output of the previous function
; as its first argument, and the remaining elements of the list as additional arguments.
; TODO: document placeholder once it works
; OUTPUT: 
; (eval (f2 (f1 (f0 first) arg0 arg1)))

(defvar placeholder "Placeholder")

(defmacro pipe (&rest args)
  (defun pipe-aux (current-val &optional next-function-spec &rest more-functions)
    (if (null next-function-spec) ; base case
      (return-from pipe-aux current-val))

    ; convert each function specification to a common representation
    (if (not (listp next-function-spec))
      (setq next-function-spec (list next-function-spec)))
    
    ; "Apply" next/innermost function and recurse
    (let* ((next-function (car next-function-spec))
           (extra-args (cdr next-function-spec))
           (args (cons current-val extra-args)))

      ; By default, current-val goes at the front of the argument list, but this can be
      ; overridden by putting `placeholder` in the list (*exactly* `placeholder` -- we're comparing addresses)
      (if (some #'(lambda (a) (eq 'placeholder a)) extra-args)
        (setq args (mapcar #'(lambda (a) (if (eq 'placeholder a) current-val a))
                           extra-args)))

      (apply #'pipe-aux 
             (cons 
               (cons next-function args) ; '(next-function current-val extra-args)
               more-functions)))) ; remaining function pipeline

  (apply #'pipe-aux args))

(defun cartesian-product (lst-of-lst)
  (cond
    ((null lst-of-lst) 
     nil)
    ((null (cdr lst-of-lst))
     (loop
       for a in (car lst-of-lst)
       collect (cons a nil)))
    (t
      (let (rest)
        (setq rest (cartesian-product (cdr lst-of-lst)))
        (loop
          for a in (car lst-of-lst)
          nconc (loop
                    for b in rest
                    collect (cons a b)))))))

(defun test-pipe ()
  (defun f0 (a) (+ a 7))
  (defun f1 (a) (* a 11))
  (defun f2 (a) (+ a 13))
  (defun f3 (a b c) (* (expt a b) c))

  (labels
	((test (macro expect-expansion expect-val)
		   (assert (equal expect-expansion (macroexpand macro)))
		   (assert (equal expect-val (eval macro)))))


	(test 19 19 19)

	(test '(pipe 19 f0 f1 f2)
		  '(f2 (f1 (f0 19)))
		  299)

	(test '(pipe 19 f0 (f3 3 5) f2)
		  '(f2 (f3 (f0 19) 3 5))
		  87893)

	(test '(pipe '((0 1 2) 3 4) car cdr)
		  '(cdr (car '((0 1 2) 3 4)))
		  '(1 2))

    ; NOTE: Don't need to quote placeholder. pipe is a defmacro, so it stays a symbol
	(test '(pipe 19 f0 (f3 placeholder 3 5) f2)
		  '(f2 (f3 (f0 19) 3 5))
		  87893)

	(test '(pipe 19 f0 (f3 3 placeholder 5) f2)
		  '(f2 (f3 3 (f0 19) 5))
		  12709329141658)

	(test '(pipe 19 f0 (f3 3 5 placeholder) f2)
		  '(f2 (f3 3 5 (f0 19)))
		  6331)
))


    ; TODO: needs a test with placeholder

(defun test-cartesian-product ()
  ;(trace cartesian-product)
  (labels
    ((test (lst correct)
       (assert (equal correct
                      (cartesian-product lst)))))
    (test nil
          nil)
    (test '((1 2))
          '((1) (2)))
    (test '((0 1) (10 11 12))
          '((0 10) (0 11) (0 12) (1 10) (1 11) (1 12)))
    (test '((0 1) nil (10 11 12))
          nil)
    (test '((0 1) (10 11 12) (20 21))
          '((0 10 20) (0 10 21) (0 11 20) (0 11 21) (0 12 20) (0 12 21)
                      (1 10 20) (1 10 21) (1 11 20) (1 11 21) (1 12 20) (1 12 21)))))


(if t
  (progn
	(test-cartesian-product)
	(test-pipe)))

