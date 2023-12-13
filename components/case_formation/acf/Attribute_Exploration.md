# Attribute Exploration #
 
## Counterfactual (CF) ##
According to Keane & Smyth (from ICCBR 2020) a Counterfactual of an instance **i** is an instance **j** that is highly similar to **i** but different in at least two value (in terms of attribute) and has a different output.

### Creating a File for CounterFactual and Non-Counterfactual with Five Most Similar Variation ###
1. The input file is **`data/scratch/preprocessed_case_base_2_da.csv`** which contains 288 cases
2. To generate the CSV file, run **`analyze.py`**
3. For each case (each row in the csv file), five most similar cases are extracted. Values that are different for a specific attribute are shown in the output file. In the following columns, the variations are highlighted `Diff_Attributes: Most Similar Variation 1`, `Diff_Attributes: Most Similar Variation 2`, `... ...`, `Diff_Attributes: Most Similar Variation 5`. From these five columns, the attribute values that differ can be found. The output file is **`analyze_new_287_pg.csv`** located in the project root directory.

### Creating a File for Rules Generation Using CounterFactual  ###
1. Run **`generate_acf.py`** which takes input the file from previous Section **`analyze_new_287_pg.csv`**
2. For generating the rules, two attributes having different values are considered together 
3. In the code, for the current version, you need to manually set the attributes: For example: `str1=Mission` and `str2=Risktol`
4. The code will output the following for the command `>> python3 generate_acf.py`:
    ```python
    50   2.0  7.0  2.0  3.0 
    59   7.0  2.0  3.0  2.0 
    74   7.0  8.0  8.0  6.0 
    75   0.0  3.0  4.0  2.0 
    77   3.0  0.0  2.0  4.0 
    79   8.0  7.0  6.0  8.0 
    178  4.0  2.0  6.0  7.0 
    191  2.0  4.0  7.0  6.0
    
5. Here, the first column is the case no, second column is the actual value 'Mission' attribute, third column is the value of the similar case for 'Mission', fourth column is the actual value of the 'Risktol', fifth column is the value of the similar case for 'Risktol'.
6. Currently, copy the output from the command to an excel file. Similarly, check for the pairs: {'Mission', 'Denial'}, {'Mission', 'Timeurg'}, {'Denial', 'Risktol'} etc. The output is file `Cf_Demo.xlsx`. Then we format the file to have the difference as below:
   <table class="tg">
            <thead>
              <tr>
                <th class="tg-7btt">Case </th>
                <th class="tg-7btt">CF</th>
                <th class="tg-7btt" colspan="2">Mission<br></th>
                <th class="tg-7btt" colspan="2">Risktol</th>
                <th class="tg-7btt">Mission<br>(Diff)</th>
                <th class="tg-7btt">Risktol<br>(Diff)</th>
                <th class="tg-7btt">SIM(C,CF)</th>
                <th class="tg-7btt">Decision <br>(Original)</th>
                <th class="tg-7btt">Decision <br>(CF)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="tg-c3ow">50</td>
                <td class="tg-c3ow">59</td>
                <td class="tg-c3ow">2</td>
                <td class="tg-c3ow">7</td>
                <td class="tg-c3ow">2</td>
                <td class="tg-c3ow">3</td>
                <td class="tg-mq34">5</td>
                <td class="tg-mq34">1</td>
                <td class="tg-c3ow">0.96</td>
                <td class="tg-c3ow">11</td>
                <td class="tg-c3ow">10</td>
              </tr>
              <tr>
                <td class="tg-c3ow">191</td>
                <td class="tg-c3ow">178</td>
                <td class="tg-c3ow">2</td>
                <td class="tg-c3ow">4</td>
                <td class="tg-c3ow">7</td>
                <td class="tg-c3ow">6</td>
                <td class="tg-mq34">2</td>
                <td class="tg-mq34">-1</td>
                <td class="tg-c3ow">0.97</td>
                <td class="tg-c3ow">6</td>
                <td class="tg-c3ow">0</td>
              </tr>
              <tr>
                <td class="tg-c3ow">75</td>
                <td class="tg-c3ow">77</td>
                <td class="tg-c3ow">0</td>
                <td class="tg-c3ow">3</td>
                <td class="tg-c3ow">4</td>
                <td class="tg-c3ow">2</td>
                <td class="tg-mq34">3</td>
                <td class="tg-mq34">-2</td>
                <td class="tg-c3ow">0.96</td>
                <td class="tg-c3ow">10</td>
                <td class="tg-c3ow">9</td>
              </tr>
              <tr>
                <td class="tg-c3ow">74</td>
                <td class="tg-c3ow">79</td>
                <td class="tg-c3ow">7</td>
                <td class="tg-c3ow">8</td>
                <td class="tg-c3ow">8</td>
                <td class="tg-c3ow">6</td>
                <td class="tg-mq34">1</td>
                <td class="tg-mq34">-2</td>
                <td class="tg-c3ow">0.98</td>
                <td class="tg-c3ow">11</td>
                <td class="tg-c3ow">10</td>
              </tr>
              <tr>
                <td class="tg-c3ow">59</td>
                <td class="tg-c3ow">50</td>
                <td class="tg-c3ow">7</td>
                <td class="tg-c3ow">2</td>
                <td class="tg-c3ow">3</td>
                <td class="tg-c3ow">2</td>
                <td class="tg-mq34">-5</td>
                <td class="tg-mq34">-1</td>
                <td class="tg-c3ow">0.96</td>
                <td class="tg-c3ow">10</td>
                <td class="tg-c3ow">11</td>
              </tr>
              <tr>
                <td class="tg-c3ow">77</td>
                <td class="tg-c3ow">75</td>
                <td class="tg-c3ow">3</td>
                <td class="tg-c3ow">0</td>
                <td class="tg-c3ow">2</td>
                <td class="tg-c3ow">4</td>
                <td class="tg-mq34">-3</td>
                <td class="tg-mq34">2</td>
                <td class="tg-c3ow">0.96</td>
                <td class="tg-c3ow">9</td>
                <td class="tg-c3ow">10</td>
              </tr>
              <tr>
                <td class="tg-c3ow">79</td>
                <td class="tg-c3ow">74</td>
                <td class="tg-c3ow">8</td>
                <td class="tg-c3ow">7</td>
                <td class="tg-c3ow">6</td>
                <td class="tg-c3ow">8</td>
                <td class="tg-mq34">-1</td>
                <td class="tg-mq34">2</td>
                <td class="tg-c3ow">0.98</td>
                <td class="tg-c3ow">10</td>
                <td class="tg-c3ow">11</td>
              </tr>
              <tr>
                <td class="tg-c3ow">178</td>
                <td class="tg-c3ow">191</td>
                <td class="tg-c3ow">4</td>
                <td class="tg-c3ow">2</td>
                <td class="tg-c3ow">6</td>
                <td class="tg-c3ow">7</td>
                <td class="tg-mq34">-2</td>
                <td class="tg-mq34">1</td>
                <td class="tg-c3ow">0.97</td>
                <td class="tg-c3ow">0</td>
                <td class="tg-c3ow">6</td>
              </tr>
            </tbody>
        </table>
7. From this file, the rules are generated manually. The rules with all the final formatting is located in `app/learn/rules.csv`
        <table class="tg">
            <thead>
              <tr>
                <th class="tg-bobw">attr_1</th>
                <th class="tg-bobw">attr_2</th>
                <th class="tg-bobw">diff_1</th>
                <th class="tg-bobw">diff_2</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="tg-8d8j">mission</td>
                <td class="tg-8d8j">risktol</td>
                <td class="tg-8d8j">5</td>
                <td class="tg-8d8j">1</td>
              </tr>
              <tr>
                <td class="tg-8d8j">mission</td>
                <td class="tg-8d8j">risktol</td>
                <td class="tg-8d8j">2</td>
                <td class="tg-8d8j">-1</td>
              </tr>
              <tr>
                <td class="tg-8d8j">mission</td>
                <td class="tg-8d8j">risktol</td>
                <td class="tg-8d8j">3</td>
                <td class="tg-8d8j">-2</td>
              </tr>
              <tr>
                <td class="tg-8d8j">mission</td>
                <td class="tg-8d8j">risktol</td>
                <td class="tg-8d8j">1</td>
                <td class="tg-8d8j">-2</td>
              </tr>
              <tr>
                <td class="tg-8d8j">mission</td>
                <td class="tg-8d8j">risktol</td>
                <td class="tg-8d8j">-5</td>
                <td class="tg-8d8j">-1</td>
              </tr>
              <tr>
                <td class="tg-8d8j">mission</td>
                <td class="tg-8d8j">risktol</td>
                <td class="tg-8d8j">-3</td>
                <td class="tg-8d8j">2</td>
              </tr>
              <tr>
                <td class="tg-8d8j">mission</td>
                <td class="tg-8d8j">risktol</td>
                <td class="tg-8d8j">-1</td>
                <td class="tg-8d8j">2</td>
              </tr>
              <tr>
                <td class="tg-8d8j">mission</td>
                <td class="tg-8d8j">risktol</td>
                <td class="tg-8d8j">-2</td>
                <td class="tg-8d8j">1</td>
              </tr>
            </tbody>
        </table>
8. Similarly, by running the `generate_acf.py`, you can generate a list of non-counterfactual cases. This line do the staffs:
   ```python
    if "Non-Counterfactual" in variation1 and "Non-Counterfactual" in variation2 and "Non-Counterfactual" in variation3 and "Non-Counterfactual" in variation4 and "Non-Counterfactual" in variation5:
         print(case)
   ```
   For current version, you have to copy the list in a csv file. Currently, it's named `non_cf.csv`, located in the root directory.
10. Then run `generate_new_cases.py`, which will do the followings:
    
    (a) Read three files: (i) Non-Counterfactuals `(non_cf.csv)`, (ii) Rules `(app/learn/rules.csv)`, and (iii) Original Cases `(app/learn/casebase2_without_da.csv)`.
    (b) Loop each original cases
    (c) If the case is in the list of non-counterfactuals, then
      - read the KDMA vales (mission, denial, risktol, timeurg) for each case
      - apply each rule to this case by adding the values of the rules with the respective attributes of the original case. Each row will be a candiate for the case base. 
      - if the new values of the attributes of this new case is between 0 and 10 (inclusive), then add this new case to the original cases.
11. The new output file is `new_cases_within_range.csv`, located in the root directory.   
