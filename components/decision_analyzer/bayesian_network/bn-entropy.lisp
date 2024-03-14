;; double bn_entropy(Bayesian_Net bn) {
;;     alias Assignment = Tuple!(Node, string);
;;     /* TODO: 
;;     Node[] parents(Node)
;;     string[] get_possible_values(Node) : [ "val0", "val1", "val2"]
;;     double marginal_prob(Bayesian_Net, Assignment)
;;     double[] row_probabilities(Node, Assignment) : gets the entries from the row of the probability table for `node` that corresponds to `assignment`
;;     */
;;
;;     //Output: [ [ val0, val0, ... ], [ val0, val1, ... ], ... ], with values in each list in same order as parents
;;     Assignment[] parent_assignments(Node node) {
;;         return node.parents
;;                    .map!(parent => parent.get_possible_values)
;;                    .cartesianProduct;
;;          //TODO: needs to return Assignment[]. Right now, it's just returning the assigned values, but not the node ids
;;     }
;; 
;;     double H_node_given_parents(Node node) {
;;         // Each term is P(assignment) * [ -1 * \sum_{x \in node} P(x | assignment) log P(x | assignment) ]
;;         // NOTE: I'm assuming that we don't need to sum over pa_i \in Pa_i, since it's fixed
;;         return node.parent_assignments
;;             .map!(assignment => bn.marginal_prob(assignment)
;;                                 * node.row_values(assignment)
;;                                       .map!(p => -1 * p * log(p))
;;                                       .sum)
;;             .sum;
;;     }
;; 
;;     return bn.nodes.map!H_node_given_parents.sum;
;; }

; TODO: can potentially skip cartesian product by just looking at the rule table.
; Those use the compressed reprentation from David's talks, and don't include parent assignments with 0 probability associated
; So I can just get the parent marginal probabilities for the entries that do exist, and then the remaining probability mass just
; gets multiplied by...0 log 0, but that has a well defined limit of 0 if we restrict p>=0.

(defun bn-entropy (bn)
  (labels
    ; P(assignment) * -1 * \sum_{x \in node} P(x | assignment) log P(x | assignment)
    ((calc-term (assignment)
       (* (marginal-prob bn assignment)
          -1.0
          (loop for p in (get-row-probabilities bn node assignment)
                sum (* (log p 2)))))

     ; H(X_i | Pa_i)
     (H-node-given-parents (node)
       (loop for assignment in (parent-assignments bn node)
             sum (calc-term assignment))))

    ; H(X)
    (loop for node in (get-nodes bn)
          sum (H-node-given-parents node))))



